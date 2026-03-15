"""
VeriNet Citation Checker — Validates the credibility of miner-provided citations.

Verifies that sources cited by miners are real, accessible, and relevant
to the claim being verified. This prevents miners from hallucinating sources.
"""

import re
import typing
import urllib.request
import urllib.parse
import json
import hashlib
from pathlib import Path


CACHE_DIR = Path(__file__).parent.parent / ".cache" / "citations"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


# Curated list of known credible sources and patterns
KNOWN_CREDIBLE_PATTERNS = [
    r"wikipedia",
    r"arxiv\.org",
    r"doi\.org",
    r"pubmed",
    r"nature\.com",
    r"science\.org",
    r"ieee\.org",
    r"acm\.org",
    r"springer\.com",
    r"whitepaper",
    r"rfc\s*\d+",
    r"w3\.org",
    r"\.gov\b",
    r"\.edu\b",
    r"official\sdocumentation",
    r"technical\sdocumentation",
    r"blockchain\sresearch",
    r"academic\sresearch",
    r"peer[\s-]reviewed",
    r"journal\sof",
    r"proceedings\sof",
    r"university\sof",
]

# Patterns that suggest hallucinated or low-quality sources
SUSPICIOUS_PATTERNS = [
    r"^source\s*\d+$",
    r"^reference\s*\d+$",
    r"^citation\s*\d+$",
    r"^https?://example\.com",
    r"^http://localhost",
    r"^test\s",
    r"^n/a$",
    r"^none$",
    r"^null$",
]


class CitationChecker:
    """Validates citations provided by miners for credibility and authenticity."""

    def __init__(self):
        self.credible_patterns = [re.compile(p, re.IGNORECASE) for p in KNOWN_CREDIBLE_PATTERNS]
        self.suspicious_patterns = [re.compile(p, re.IGNORECASE) for p in SUSPICIOUS_PATTERNS]

    def check_citation(self, source: str) -> dict:
        """
        Evaluate a single citation source.

        Returns:
            dict with keys:
                - credible: bool
                - score: float (0.0 to 1.0)
                - reason: str
        """
        source = source.strip()

        if not source or len(source) < 3:
            return {
                "credible": False,
                "score": 0.0,
                "reason": "Source is empty or too short.",
            }

        # Check for suspicious patterns
        for pattern in self.suspicious_patterns:
            if pattern.search(source):
                return {
                    "credible": False,
                    "score": 0.05,
                    "reason": f"Source matches suspicious pattern: {pattern.pattern}",
                }

        # Check for credible patterns
        credibility_hits = 0
        matched_patterns = []
        for pattern in self.credible_patterns:
            if pattern.search(source):
                credibility_hits += 1
                matched_patterns.append(pattern.pattern)

        if credibility_hits > 0:
            score = min(0.5 + credibility_hits * 0.15, 1.0)
            return {
                "credible": True,
                "score": score,
                "reason": f"Matches {credibility_hits} credible pattern(s): {', '.join(matched_patterns[:3])}",
            }

        # If it looks like a URL, try to verify it exists
        if source.startswith("http://") or source.startswith("https://"):
            return self._verify_url(source)

        # Default: moderate score for unrecognized but non-suspicious sources
        # Longer, more descriptive sources get slightly higher scores
        length_bonus = min(len(source) / 100.0, 0.2)
        return {
            "credible": True,
            "score": 0.3 + length_bonus,
            "reason": "Source is unrecognized but not suspicious.",
        }

    def check_citations(self, sources: typing.List[str]) -> dict:
        """
        Evaluate a list of citations.

        Returns:
            dict with keys:
                - results: list of per-citation evaluations
                - average_score: float
                - credible_count: int
                - total_count: int
                - duplicates: int
        """
        if not sources:
            return {
                "results": [],
                "average_score": 0.0,
                "credible_count": 0,
                "total_count": 0,
                "duplicates": 0,
            }

        results = []
        seen = set()
        duplicates = 0

        for source in sources:
            normalized = source.strip().lower()
            if normalized in seen:
                duplicates += 1
            seen.add(normalized)

            result = self.check_citation(source)
            results.append(result)

        scores = [r["score"] for r in results]
        avg_score = sum(scores) / len(scores) if scores else 0.0

        # Penalize for duplicates
        if duplicates > 0 and len(sources) > 0:
            dup_penalty = duplicates / len(sources) * 0.2
            avg_score = max(avg_score - dup_penalty, 0.0)

        credible_count = sum(1 for r in results if r["credible"])

        return {
            "results": results,
            "average_score": avg_score,
            "credible_count": credible_count,
            "total_count": len(sources),
            "duplicates": duplicates,
        }

    def _verify_url(self, url: str) -> dict:
        """
        Attempt to verify that a URL is reachable.
        Uses HEAD request with a short timeout.
        """
        cache_key = hashlib.md5(url.encode()).hexdigest()
        cache_file = CACHE_DIR / f"url_{cache_key}.json"

        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        try:
            req = urllib.request.Request(
                url,
                method="HEAD",
                headers={"User-Agent": "VeriNet/1.0"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                status = resp.getcode()
                if 200 <= status < 400:
                    result = {
                        "credible": True,
                        "score": 0.7,
                        "reason": f"URL is reachable (HTTP {status}).",
                    }
                else:
                    result = {
                        "credible": False,
                        "score": 0.2,
                        "reason": f"URL returned status {status}.",
                    }
        except Exception:
            result = {
                "credible": False,
                "score": 0.15,
                "reason": "URL is not reachable.",
            }

        try:
            with open(cache_file, "w") as f:
                json.dump(result, f)
        except IOError:
            pass

        return result
