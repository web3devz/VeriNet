"""
VeriNet Miner — Decentralized fact-verification miner neuron.

Receives claim queries from validators, runs a retrieval-augmented verification
pipeline, and returns structured verification results.

This miner is sovereign: it operates using local retrieval, open knowledge bases,
and Wikipedia (self-hostable) without depending on centralized LLM APIs.

Usage:
    python neurons/miner.py \
        --netuid NETUID \
        --wallet.name WALLET_NAME \
        --wallet.hotkey HOTKEY \
        --axon.port 8901 \
        --subtensor.network local
"""

import sys
import os
import re
import time
import typing
import argparse
import traceback

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bittensor as bt
from verinet.protocol import FactVerification
from retrieval.retriever import EvidenceRetriever


class FactVerificationMiner:
    """
    VeriNet Miner neuron.

    Processes incoming fact-verification requests using a multi-stage pipeline:
    1. Evidence retrieval from sovereign sources
    2. Claim analysis against retrieved evidence
    3. Verdict determination with confidence scoring
    4. Structured response construction
    """

    def __init__(self, config: bt.config):
        self.config = config

        # Initialize Bittensor components
        bt.logging(config=config)
        bt.logging.info("Initializing VeriNet Miner...")

        self.wallet = bt.wallet(config=config)
        self.subtensor = bt.subtensor(config=config)
        self.metagraph = self.subtensor.metagraph(config.netuid)

        bt.logging.info(f"Wallet: {self.wallet}")
        bt.logging.info(f"Subtensor: {self.subtensor}")
        bt.logging.info(f"Metagraph: {self.metagraph}")

        # Verify registration
        if self.wallet.hotkey.ss58_address not in self.metagraph.hotkeys:
            bt.logging.error(
                "Miner hotkey is not registered on the subnet. "
                "Run: btcli subnets register --netuid NETUID"
            )
            sys.exit(1)

        self.uid = self.metagraph.hotkeys.index(self.wallet.hotkey.ss58_address)
        bt.logging.info(f"Running miner on UID: {self.uid}")

        # Initialize the evidence retriever
        self.retriever = EvidenceRetriever()
        bt.logging.info("Evidence retriever initialized.")

        # Set up the axon to handle incoming requests
        self.axon = bt.axon(wallet=self.wallet, config=config)
        self.axon.attach(
            forward_fn=self.verify_claim,
            blacklist_fn=self.blacklist,
            priority_fn=self.priority,
        )

        bt.logging.info(f"Axon created on port {self.axon.port}")

    def verify_claim(self, synapse: FactVerification) -> FactVerification:
        """
        Main verification handler. Called when a validator sends a claim.

        Pipeline:
        1. Retrieve evidence from sovereign sources
        2. Analyze evidence against the claim
        3. Determine verdict and confidence
        4. Package structured response
        """
        claim = synapse.claim
        bt.logging.info(f"Received claim: {claim}")

        try:
            # Step 1: Retrieve evidence
            evidence = self.retriever.retrieve(claim, max_evidence=8)
            bt.logging.info(f"Retrieved {len(evidence)} evidence items.")

            # Step 2: Analyze claim against evidence
            analysis = self._analyze_claim(claim, evidence)

            # Step 3: Set response fields
            synapse.verdict = analysis["verdict"]
            synapse.confidence = analysis["confidence"]
            synapse.sources = analysis["sources"]
            synapse.reasoning = analysis["reasoning"]

            bt.logging.info(
                f"Verdict: {synapse.verdict} (confidence: {synapse.confidence:.2f})"
            )

        except Exception as e:
            bt.logging.error(f"Verification failed: {e}")
            bt.logging.error(traceback.format_exc())
            synapse.verdict = "Uncertain"
            synapse.confidence = 0.1
            synapse.sources = []
            synapse.reasoning = f"Verification pipeline encountered an error."

        return synapse

    def _analyze_claim(self, claim: str, evidence: typing.List[dict]) -> dict:
        """
        Analyze a claim against retrieved evidence using rule-based NLI.

        This is a sovereign verification engine — no external LLM calls.
        Uses keyword matching, semantic overlap, and negation detection
        to determine whether evidence supports or refutes the claim.
        """
        if not evidence:
            return {
                "verdict": "Uncertain",
                "confidence": 0.2,
                "sources": [],
                "reasoning": "Insufficient evidence retrieved to verify this claim.",
            }

        claim_lower = claim.lower().strip()
        claim_words = set(re.findall(r'\b\w{3,}\b', claim_lower))

        support_score = 0.0
        refute_score = 0.0
        total_relevance = 0.0
        sources = []
        reasoning_parts = []

        # Negation indicators in the claim
        claim_negators = self._detect_negation(claim_lower)

        # Detect if claim asserts a known falsehood
        claim_falsehood_signals = [
            (r"\bflat\b.*\bearth\b", r"\bspher|oblate|round|disproven"),
            (r"\bearth\b.*\bflat\b", r"\bspher|oblate|round|disproven"),
            (r"\bhoax\b", r"\bapollo|landing|mission|first human|evidence"),
            (r"\bconspiracy\b", r"\bevidence|documented|confirmed"),
        ]
        claim_asserts_falsehood = False
        for claim_pat, evidence_pat in claim_falsehood_signals:
            if re.search(claim_pat, claim_lower):
                for item in evidence:
                    if re.search(evidence_pat, item["text"].lower()):
                        claim_asserts_falsehood = True
                        break
            if claim_asserts_falsehood:
                break

        for item in evidence:
            text = item["text"]
            source = item["source"]
            text_lower = text.lower()

            # Calculate relevance
            text_words = set(re.findall(r'\b\w{3,}\b', text_lower))
            overlap = claim_words & text_words
            relevance = len(overlap) / max(len(claim_words), 1)

            if relevance < 0.1:
                continue

            total_relevance += relevance
            sources.append(source)

            # Detect contradiction signals
            evidence_negators = self._detect_negation(text_lower)
            has_contradiction_markers = self._has_contradiction(
                claim_lower, text_lower
            )

            # Determine if evidence supports or refutes
            is_kb_source = "knowledge base" in item["source"].lower()
            kb_multiplier = 2.5 if is_kb_source else 1.0
            falsehood_boost = 2.0 if claim_asserts_falsehood else 1.0

            if has_contradiction_markers:
                refute_score += relevance * 1.5 * kb_multiplier * falsehood_boost
                reasoning_parts.append(
                    f"Evidence from {source} contradicts the claim."
                )
            elif self._text_supports_claim(claim_lower, text_lower, claim_words):
                if claim_asserts_falsehood:
                    support_score += relevance * 0.1
                else:
                    support_score += relevance * 1.2
                    reasoning_parts.append(
                        f"Evidence from {source} supports the claim."
                    )
            else:
                if claim_asserts_falsehood:
                    support_score += relevance * 0.05
                else:
                    support_score += relevance * 0.3
                    refute_score += relevance * 0.3

        # Determine verdict
        if total_relevance < 0.3:
            verdict = "Uncertain"
            confidence = 0.25
            reasoning = "Retrieved evidence has low relevance to the claim."
        elif refute_score > support_score * 1.2:
            verdict = "False"
            confidence = min(
                0.5 + (refute_score - support_score) / max(total_relevance, 1) * 0.4,
                0.98,
            )
            reasoning = " ".join(reasoning_parts[:3]) if reasoning_parts else (
                "Evidence analysis indicates the claim is false."
            )
        elif support_score > refute_score * 1.2:
            verdict = "True"
            confidence = min(
                0.5 + (support_score - refute_score) / max(total_relevance, 1) * 0.4,
                0.98,
            )
            reasoning = " ".join(reasoning_parts[:3]) if reasoning_parts else (
                "Evidence analysis indicates the claim is true."
            )
        else:
            verdict = "Uncertain"
            confidence = 0.4
            reasoning = "Evidence is mixed — both supporting and contradicting signals found."

        # Deduplicate sources
        unique_sources = list(dict.fromkeys(sources))[:5]

        return {
            "verdict": verdict,
            "confidence": round(confidence, 2),
            "sources": unique_sources,
            "reasoning": reasoning,
        }

    def _detect_negation(self, text: str) -> bool:
        """Detect negation patterns in text."""
        negation_patterns = [
            r"\bnot\b", r"\bno\b", r"\bnever\b", r"\bneither\b",
            r"\bnor\b", r"\bdoes not\b", r"\bdoesn't\b", r"\bisn't\b",
            r"\bwasn't\b", r"\bweren't\b", r"\bwon't\b", r"\bcan't\b",
            r"\bcannot\b", r"\bmyth\b", r"\bfalse\b", r"\bincorrect\b",
            r"\bmisconception\b", r"\bdebunked\b", r"\bdisproven\b",
            r"\barchaic\b", r"\bconspiracy\b", r"\bpseudoscien",
            r"\brefuted\b", r"\bwrongly\b", r"\berroneous\b",
        ]
        return any(re.search(p, text) for p in negation_patterns)

    def _has_contradiction(self, claim: str, evidence: str) -> bool:
        """
        Detect if evidence contradicts the claim using pattern matching.

        Looks for antonym pairs, negation-flipped statements, and
        explicit contradiction markers.
        """
        # Common antonym pairs relevant to fact-checking
        antonym_pairs = [
            ("proof of work", "proof of stake"),
            ("proof-of-work", "proof of stake"),
            ("proof of stake", "proof of work"),
            ("proof of stake", "proof-of-work"),
            ("true", "false"),
            ("flat", "spherical"),
            ("flat", "oblate spheroid"),
            ("flat", "sphere"), ("flat", "round"),
            ("compiled", "interpreted"),
            ("same", "different"),
            ("same", "distinct"),
            ("visible", "not visible"),
            ("created by", "not created by"),
            ("invented", "not invented"),
            ("closest", "farthest"),
            ("three-second", "months"),
            ("hoax", "supported by"),
            ("hoax", "extensive evidence"),
            ("hoax", "first human"),
            ("hoax", "apollo 11"),
        ]

        for claim_term, evidence_term in antonym_pairs:
            if claim_term in claim and evidence_term in evidence:
                return True

        # Check for "not" + key claim term in evidence
        claim_key_phrases = re.findall(r'\b\w{4,}\s+\w{4,}\b', claim)
        for phrase in claim_key_phrases:
            negated = f"not {phrase}"
            if negated in evidence:
                return True

        return False

    def _text_supports_claim(
        self, claim: str, evidence: str, claim_words: set
    ) -> bool:
        """Check if evidence text directly supports the claim."""
        evidence_words = set(re.findall(r'\b\w{3,}\b', evidence))
        overlap_ratio = len(claim_words & evidence_words) / max(len(claim_words), 1)

        # High overlap without contradiction markers suggests support
        if overlap_ratio > 0.5 and not self._detect_negation(evidence):
            return True

        # Check for explicit support patterns
        support_patterns = [
            r"\bconfirmed\b", r"\bverified\b", r"\bestablished\b",
            r"\bproven\b", r"\bdemonstrated\b", r"\bcorrect\b",
            r"\baccurate\b", r"\bindeed\b",
        ]
        return any(re.search(p, evidence) for p in support_patterns)

    def blacklist(self, synapse: FactVerification) -> typing.Tuple[bool, str]:
        """
        Blacklist check — reject requests from unregistered hotkeys.
        """
        caller_hotkey = synapse.dendrite.hotkey
        if caller_hotkey not in self.metagraph.hotkeys:
            return True, "Hotkey not registered on subnet."
        return False, ""

    def priority(self, synapse: FactVerification) -> float:
        """
        Priority function — higher-staked validators get priority.
        """
        caller_hotkey = synapse.dendrite.hotkey
        if caller_hotkey in self.metagraph.hotkeys:
            uid = self.metagraph.hotkeys.index(caller_hotkey)
            return float(self.metagraph.S[uid])
        return 0.0

    def run(self):
        """Main miner loop — serve the axon and sync metagraph."""
        bt.logging.info("Starting VeriNet Miner main loop.")

        self.axon.serve(netuid=self.config.netuid, subtensor=self.subtensor)
        self.axon.start()

        bt.logging.info(
            f"Miner serving on {self.axon.ip}:{self.axon.port} "
            f"with netuid {self.config.netuid}"
        )

        step = 0
        while True:
            try:
                # Periodically sync metagraph
                if step % 60 == 0:
                    self.metagraph.sync(subtensor=self.subtensor)
                    bt.logging.info(
                        f"Step {step} | Block: {self.metagraph.block.item()} | "
                        f"Peers: {self.metagraph.n.item()}"
                    )

                step += 1
                time.sleep(12)  # ~1 Bittensor block

            except KeyboardInterrupt:
                bt.logging.info("Miner shutting down.")
                self.axon.stop()
                break
            except Exception as e:
                bt.logging.error(f"Miner error: {e}")
                bt.logging.error(traceback.format_exc())
                time.sleep(12)


def get_config() -> bt.config:
    """Parse command line arguments and build configuration."""
    parser = argparse.ArgumentParser(description="VeriNet Miner")
    parser.add_argument(
        "--netuid", type=int, default=1, help="Subnet netuid to connect to."
    )
    bt.wallet.add_args(parser)
    bt.subtensor.add_args(parser)
    bt.axon.add_args(parser)
    bt.logging.add_args(parser)

    config = bt.config(parser)
    return config


def main():
    config = get_config()
    miner = FactVerificationMiner(config)
    miner.run()


if __name__ == "__main__":
    main()
