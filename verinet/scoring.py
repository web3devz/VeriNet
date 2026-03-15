"""
VeriNet Scoring System — Evaluates miner fact-verification outputs.

Combines verdict accuracy, citation credibility, reasoning quality,
and consensus agreement into a final composite score per miner.
"""

from __future__ import annotations

import typing
import re
import logging

try:
    import bittensor as bt
    _log = bt.logging
except ImportError:
    _log = logging.getLogger("verinet.scoring")

if typing.TYPE_CHECKING:
    from verinet.protocol import FactVerification


# Mapping from FEVER labels to our verdict format
FEVER_LABEL_MAP = {
    "SUPPORTS": "True",
    "REFUTES": "False",
    "NOT ENOUGH INFO": "Uncertain",
}

# Known credible source keywords for citation scoring
CREDIBLE_SOURCE_KEYWORDS = [
    "wikipedia", "arxiv", "doi", "pubmed", "nature", "science",
    "ieee", "acm", "springer", "whitepaper", "rfc", "w3c",
    "documentation", "official", "gov", "edu", "research",
    "journal", "conference", "proceedings", "academic",
    "blockchain", "protocol", "specification", "standard",
]


def verdict_accuracy_score(
    response: "FactVerification",
    ground_truth_label: typing.Optional[str],
) -> float:
    """
    Score the miner's verdict against the ground truth.

    Returns:
        1.0 for exact match
        0.3 for 'Uncertain' when ground truth exists (partial credit)
        0.0 for incorrect verdict or missing response
    """
    if response.verdict is None:
        return 0.0

    miner_verdict = response.verdict.strip().capitalize()

    # If no ground truth is available, give moderate score for any structured response
    if ground_truth_label is None:
        return 0.5 if miner_verdict in ("True", "False", "Uncertain") else 0.0

    expected_verdict = FEVER_LABEL_MAP.get(ground_truth_label, None)
    if expected_verdict is None:
        return 0.5

    if miner_verdict == expected_verdict:
        return 1.0
    elif miner_verdict == "Uncertain":
        return 0.3
    else:
        return 0.0


def citation_quality_score(
    response: "FactVerification",
) -> float:
    """
    Score the credibility of cited sources.

    Evaluates:
    - Whether sources are provided at all
    - Whether sources match known credible keywords
    - Penalizes empty or single-character sources
    - Penalizes duplicate sources

    Returns:
        Score between 0.0 and 1.0
    """
    if not response.sources or len(response.sources) == 0:
        return 0.0

    sources = response.sources
    total = len(sources)

    # Penalize trivially short sources (likely hallucinated)
    valid_sources = [s for s in sources if len(s.strip()) > 3]
    if not valid_sources:
        return 0.05

    # Penalize exact duplicates
    unique_sources = set(s.strip().lower() for s in valid_sources)
    uniqueness_ratio = len(unique_sources) / total

    # Score each source for credibility
    credibility_hits = 0
    for source in valid_sources:
        source_lower = source.lower()
        for keyword in CREDIBLE_SOURCE_KEYWORDS:
            if keyword in source_lower:
                credibility_hits += 1
                break

    credibility_ratio = credibility_hits / len(valid_sources) if valid_sources else 0.0

    # Bonus for providing multiple distinct sources (up to 5)
    quantity_bonus = min(len(unique_sources) / 5.0, 1.0)

    # Weighted combination
    score = (
        credibility_ratio * 0.5
        + uniqueness_ratio * 0.25
        + quantity_bonus * 0.25
    )

    return min(max(score, 0.0), 1.0)


def reasoning_quality_score(
    response: "FactVerification",
) -> float:
    """
    Score the quality of the miner's reasoning.

    Evaluates:
    - Presence and length of reasoning
    - Whether reasoning references the claim
    - Structural completeness

    Returns:
        Score between 0.0 and 1.0
    """
    if not response.reasoning or len(response.reasoning.strip()) == 0:
        return 0.0

    reasoning = response.reasoning.strip()
    claim = response.claim.lower() if response.claim else ""

    score = 0.0

    # Length scoring — require substantive reasoning (at least 20 chars)
    char_count = len(reasoning)
    if char_count < 10:
        return 0.05
    elif char_count < 50:
        score += 0.2
    elif char_count < 150:
        score += 0.4
    elif char_count < 500:
        score += 0.6
    else:
        score += 0.5  # Slightly penalize extremely verbose responses

    # Check if reasoning references key terms from the claim
    claim_words = set(re.findall(r'\b\w{4,}\b', claim))
    reasoning_lower = reasoning.lower()
    overlap = sum(1 for w in claim_words if w in reasoning_lower)
    if claim_words:
        relevance = min(overlap / max(len(claim_words), 1), 1.0)
        score += relevance * 0.3

    # Structural markers — sentences, logical connectors
    sentence_count = len(re.split(r'[.!?]+', reasoning))
    if sentence_count >= 2:
        score += 0.1

    return min(max(score, 0.0), 1.0)


def consensus_score(
    response: "FactVerification",
    all_verdicts: typing.List[str],
) -> float:
    """
    Score based on agreement with the majority verdict.

    Miners whose verdicts align with the consensus get higher scores.
    This protects against adversarial miners who submit random results.

    Returns:
        Score between 0.0 and 1.0
    """
    if response.verdict is None or not all_verdicts:
        return 0.0

    miner_verdict = response.verdict.strip().capitalize()
    normalized_verdicts = [v.strip().capitalize() for v in all_verdicts if v]

    if not normalized_verdicts:
        return 0.5

    # Count agreement
    total = len(normalized_verdicts)
    agreement = sum(1 for v in normalized_verdicts if v == miner_verdict)
    agreement_ratio = agreement / total

    return agreement_ratio


def compute_miner_scores(
    responses: typing.List["FactVerification"],
    ground_truth_label: typing.Optional[str],
    claim: str,
) -> typing.List[float]:
    """
    Compute the final composite score for each miner response.

    Combines:
    - Verdict accuracy (40%)
    - Citation quality (20%)
    - Reasoning quality (20%)
    - Consensus agreement (20%)

    Returns:
        List of floats (one per miner) between 0.0 and 1.0
    """
    # Collect all verdicts for consensus scoring
    all_verdicts = []
    for r in responses:
        if r.verdict is not None:
            all_verdicts.append(r.verdict)

    scores = []
    for response in responses:
        # Check if the response has any content
        if response.verdict is None and response.reasoning is None:
            scores.append(0.0)
            continue

        v_score = verdict_accuracy_score(response, ground_truth_label)
        c_score = citation_quality_score(response)
        r_score = reasoning_quality_score(response)
        con_score = consensus_score(response, all_verdicts)

        # Weighted composite
        final = (
            v_score * 0.40
            + c_score * 0.20
            + r_score * 0.20
            + con_score * 0.20
        )

        # Clamp to [0, 1]
        final = min(max(final, 0.0), 1.0)

        _log.debug(
            f"Miner score breakdown — "
            f"verdict={v_score:.2f} citation={c_score:.2f} "
            f"reasoning={r_score:.2f} consensus={con_score:.2f} "
            f"→ final={final:.2f}"
        )

        scores.append(final)

    return scores
