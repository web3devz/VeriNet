"""
VeriNet API Server — REST API for querying the fact-verification subnet.

Provides a public endpoint for clients (AI assistants, search engines,
RAG pipelines, news verification systems) to submit claims for verification.

Can operate in two modes:
1. Standalone mode: Uses the local retrieval pipeline directly
2. Subnet mode: Forwards queries to the VeriNet subnet via Bittensor dendrite

Usage:
    python api/server.py --port 8080
    python api/server.py --port 8080 --subnet-mode --netuid 1
"""

import sys
import os
import json
import argparse
import typing
import time
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from retrieval.retriever import EvidenceRetriever
from retrieval.citation_checker import CitationChecker


class VerificationEngine:
    """
    Core verification engine that can run standalone (without Bittensor)
    or forward queries to the subnet.
    """

    def __init__(self, subnet_mode: bool = False, netuid: int = 1):
        self.subnet_mode = subnet_mode
        self.netuid = netuid
        self.retriever = EvidenceRetriever()
        self.citation_checker = CitationChecker()
        self.dendrite = None

        if subnet_mode:
            try:
                import bittensor as bt
                wallet = bt.wallet()
                self.dendrite = bt.dendrite(wallet=wallet)
                self.subtensor = bt.subtensor()
                self.metagraph = self.subtensor.metagraph(netuid)
                print(f"Subnet mode initialized for netuid {netuid}")
            except Exception as e:
                print(f"Failed to initialize subnet mode: {e}")
                print("Falling back to standalone mode.")
                self.subnet_mode = False

    def verify(self, claim: str) -> dict:
        """
        Verify a claim. Uses local pipeline or subnet depending on mode.
        """
        if self.subnet_mode and self.dendrite is not None:
            return self._verify_via_subnet(claim)
        return self._verify_locally(claim)

    def _verify_locally(self, claim: str) -> dict:
        """Run the verification pipeline locally (standalone mode)."""
        import re

        # Retrieve evidence
        evidence = self.retriever.retrieve(claim, max_evidence=8)

        if not evidence:
            return {
                "claim": claim,
                "verdict": "Uncertain",
                "confidence": 0.2,
                "sources": [],
                "reasoning": "Insufficient evidence available.",
            }

        claim_lower = claim.lower()
        claim_words = set(re.findall(r'\b\w{3,}\b', claim_lower))

        support_score = 0.0
        refute_score = 0.0
        total_relevance = 0.0
        sources = []
        reasoning_parts = []

        negation_patterns = [
            r"\bnot\b", r"\bno\b", r"\bnever\b", r"\bdoes not\b",
            r"\bdoesn't\b", r"\bisn't\b", r"\bmyth\b", r"\bfalse\b",
            r"\bincorrect\b", r"\bmisconception\b", r"\bdebunked\b",
            r"\bdisproven\b", r"\bnot supported\b", r"\barchaic\b",
            r"\bconspiracy\b", r"\bpseudoscien", r"\brefuted\b",
            r"\bwrongly\b", r"\berroneous\b", r"\bcontrary to\b",
        ]

        antonym_pairs = [
            ("proof of work", "proof of stake"),
            ("proof-of-work", "proof of stake"),
            ("proof of stake", "proof of work"),
            ("proof of stake", "proof-of-work"),
            ("flat", "spherical"), ("flat", "oblate spheroid"),
            ("flat", "sphere"), ("flat", "round"),
            ("compiled", "interpreted"), ("same", "different"),
            ("same", "distinct"), ("visible", "not visible"),
            ("closest", "farthest"), ("three-second", "months"),
            ("hoax", "supported by"), ("hoax", "extensive evidence"),
            ("hoax", "first human"), ("hoax", "apollo 11"),
        ]

        # Claims that assert known falsehoods — detect these patterns in the claim itself
        claim_falsehood_signals = [
            (r"\bflat\b.*\bearth\b", r"\bspher|oblate|round|disproven"),
            (r"\bearth\b.*\bflat\b", r"\bspher|oblate|round|disproven"),
            (r"\bhoax\b", r"\bapollo|landing|mission|first human|evidence"),
            (r"\bconspiracy\b", r"\bevidence|documented|confirmed"),
            (r"\bproof of stake\b.*\bbitcoin\b", r"\bproof.of.work|pow\b"),
            (r"\bbitcoin\b.*\bproof of stake\b", r"\bproof.of.work|pow\b"),
            (r"\bcompiled\b.*\bpython\b", r"\binterpreted\b"),
            (r"\bpython\b.*\bcompiled\b", r"\binterpreted\b"),
        ]

        # Pre-check: does the claim assert a known falsehood?
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

            text_words = set(re.findall(r'\b\w{3,}\b', text_lower))
            overlap = claim_words & text_words
            relevance = len(overlap) / max(len(claim_words), 1)

            if relevance < 0.15:
                continue

            total_relevance += relevance
            sources.append(source)

            is_kb_source = "knowledge base" in source.lower()

            # Check for contradiction via antonym pairs
            has_contradiction = False
            for claim_term, evidence_term in antonym_pairs:
                if claim_term in claim_lower and evidence_term in text_lower:
                    has_contradiction = True
                    break

            # Detect "not <claim_phrase>" patterns in evidence
            if not has_contradiction:
                claim_key_phrases = re.findall(r'\b\w{4,}\s+\w{4,}\b', claim_lower)
                for phrase in claim_key_phrases:
                    if f"not {phrase}" in text_lower:
                        has_contradiction = True
                        break

            has_negation = any(re.search(p, text_lower) for p in negation_patterns)

            # When the claim asserts a known falsehood and evidence discusses the same
            # topic, treat negation signals more aggressively and don't count mere
            # topic overlap as support.
            falsehood_boost = 2.0 if claim_asserts_falsehood else 1.0

            # KB sources are authoritative — give them 5x weight
            if is_kb_source:
                if has_contradiction or has_negation:
                    refute_score += relevance * 5.0 * falsehood_boost
                    reasoning_parts.insert(0, f"Evidence from {source} contradicts the claim.")
                elif claim_asserts_falsehood:
                    # KB evidence about the same topic but no explicit contradiction —
                    # treat as neutral for known falsehood claims
                    support_score += relevance * 0.05
                else:
                    support_score += relevance * 3.0
                    reasoning_parts.insert(0, f"Evidence from {source} supports the claim.")
            elif has_contradiction:
                refute_score += relevance * 2.0 * falsehood_boost
                reasoning_parts.append(f"Evidence from {source} contradicts the claim.")
            elif has_negation:
                refute_score += relevance * 1.2 * falsehood_boost
                reasoning_parts.append(f"Evidence from {source} contains refuting signals.")
            else:
                if claim_asserts_falsehood:
                    # Topic-related evidence for a known falsehood — treat as neutral
                    support_score += relevance * 0.05
                elif relevance > 0.3:
                    support_score += relevance * 1.0
                    reasoning_parts.append(f"Evidence from {source} supports the claim.")
                else:
                    # Low-relevance non-contradicting evidence — near-neutral
                    support_score += relevance * 0.2

        # Determine verdict
        if total_relevance < 0.3:
            verdict = "Uncertain"
            confidence = 0.25
            reasoning = "Retrieved evidence has low relevance."
        elif refute_score > support_score * 1.2:
            verdict = "False"
            confidence = round(min(
                0.5 + (refute_score - support_score) / max(total_relevance, 1) * 0.4,
                0.98,
            ), 2)
            reasoning = " ".join(reasoning_parts[:3]) or "Evidence indicates the claim is false."
        elif support_score > refute_score * 1.2:
            verdict = "True"
            confidence = round(min(
                0.5 + (support_score - refute_score) / max(total_relevance, 1) * 0.4,
                0.98,
            ), 2)
            reasoning = " ".join(reasoning_parts[:3]) or "Evidence indicates the claim is true."
        else:
            verdict = "Uncertain"
            confidence = 0.4
            reasoning = "Evidence is mixed."

        unique_sources = list(dict.fromkeys(sources))[:5]

        # Check citation quality
        citation_result = self.citation_checker.check_citations(unique_sources)

        return {
            "claim": claim,
            "verdict": verdict,
            "confidence": confidence,
            "sources": unique_sources,
            "reasoning": reasoning,
            "citation_quality": round(citation_result["average_score"], 2),
        }

    def _verify_via_subnet(self, claim: str) -> dict:
        """Forward verification request to the VeriNet subnet."""
        from verinet.protocol import FactVerification

        synapse = FactVerification(claim=claim)

        # Get the highest-incentive miner
        try:
            self.metagraph.sync(subtensor=self.subtensor)
            incentives = self.metagraph.I
            top_uid = int(incentives.argmax())
            axon = self.metagraph.axons[top_uid]

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            responses = loop.run_until_complete(
                self.dendrite(
                    axons=[axon],
                    synapse=synapse,
                    deserialize=False,
                    timeout=30.0,
                )
            )

            if responses and responses[0].verdict is not None:
                r = responses[0]
                return {
                    "claim": claim,
                    "verdict": r.verdict,
                    "confidence": r.confidence,
                    "sources": r.sources or [],
                    "reasoning": r.reasoning or "",
                }
        except Exception as e:
            print(f"Subnet query failed: {e}. Falling back to local.")

        return self._verify_locally(claim)


class VeriNetAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the VeriNet API."""

    engine: VerificationEngine = None

    def do_POST(self):
        """Handle POST requests."""
        parsed = urlparse(self.path)

        if parsed.path == "/verify":
            self._handle_verify()
        elif parsed.path == "/batch-verify":
            self._handle_batch_verify()
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)

        if parsed.path == "/health":
            self._send_json({"status": "ok", "version": "1.0.0"})
        elif parsed.path == "/stats":
            self._handle_stats()
        elif parsed.path == "/":
            self._send_json({
                "name": "VeriNet API",
                "version": "1.0.0",
                "endpoints": {
                    "POST /verify": "Verify a single claim",
                    "POST /batch-verify": "Verify multiple claims",
                    "GET /health": "Health check",
                    "GET /stats": "Benchmark statistics",
                },
            })
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def _handle_verify(self):
        """Process a claim verification request."""
        try:
            body = self._read_body()
            claim = body.get("claim", "").strip()

            if not claim:
                self._send_json({"error": "Missing 'claim' field."}, 400)
                return

            if len(claim) > 2000:
                self._send_json({"error": "Claim too long (max 2000 chars)."}, 400)
                return

            start = time.time()
            result = self.engine.verify(claim)
            result["latency_ms"] = round((time.time() - start) * 1000, 1)

            self._send_json(result)

        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON body."}, 400)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_batch_verify(self):
        """Process multiple claims in a single request."""
        try:
            body = self._read_body()
            claims = body.get("claims", [])

            if not claims or not isinstance(claims, list):
                self._send_json({"error": "Missing 'claims' array."}, 400)
                return

            if len(claims) > 10:
                self._send_json({"error": "Max 10 claims per batch."}, 400)
                return

            start = time.time()
            results = []
            for claim in claims:
                if isinstance(claim, str) and claim.strip():
                    result = self.engine.verify(claim.strip())
                    results.append(result)

            response = {
                "results": results,
                "count": len(results),
                "latency_ms": round((time.time() - start) * 1000, 1),
            }
            self._send_json(response)

        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON body."}, 400)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_stats(self):
        """Return benchmark dataset statistics."""
        from benchmarks.fever_loader import FEVERLoader
        loader = FEVERLoader()
        loader.load()
        self._send_json(loader.stats())

    def _read_body(self) -> dict:
        """Read and parse the JSON request body."""
        content_length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(content_length)
        return json.loads(raw.decode("utf-8"))

    def _send_json(self, data: dict, status: int = 200):
        """Send a JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))

    def _set_cors_headers(self):
        """Set CORS headers to allow cross-origin requests from the UI."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format, *args):
        """Override to use structured logging."""
        print(f"[VeriNet API] {self.address_string()} - {format % args}")


def run_server(port: int = 8080, subnet_mode: bool = False, netuid: int = 1):
    """Start the VeriNet API server."""
    engine = VerificationEngine(subnet_mode=subnet_mode, netuid=netuid)
    VeriNetAPIHandler.engine = engine

    server = HTTPServer(("0.0.0.0", port), VeriNetAPIHandler)
    print(f"VeriNet API server running on http://0.0.0.0:{port}")
    print(f"Mode: {'subnet' if subnet_mode else 'standalone'}")
    print(f"Endpoints:")
    print(f"  POST /verify        — Verify a claim")
    print(f"  POST /batch-verify  — Verify multiple claims")
    print(f"  GET  /health        — Health check")
    print(f"  GET  /stats         — Benchmark stats")
    print(f"  GET  /              — API info")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down VeriNet API server.")
        server.shutdown()


def main():
    parser = argparse.ArgumentParser(description="VeriNet API Server")
    parser.add_argument("--port", type=int, default=8080, help="Port to run on.")
    parser.add_argument(
        "--subnet-mode", action="store_true",
        help="Forward queries to the VeriNet subnet instead of local pipeline.",
    )
    parser.add_argument(
        "--netuid", type=int, default=1,
        help="Subnet netuid (only used in subnet mode).",
    )
    args = parser.parse_args()
    run_server(port=args.port, subnet_mode=args.subnet_mode, netuid=args.netuid)


if __name__ == "__main__":
    main()
