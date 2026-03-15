"""
VeriNet Retriever — Evidence retrieval pipeline for fact verification.

Implements a sovereign retrieval system that does NOT depend on centralized APIs.
Uses local knowledge bases, Wikipedia dumps, and open datasets for evidence retrieval.
Passes the sovereignty test: works even if OpenAI/Google disappear.
"""

import re
import json
import typing
import hashlib
import os
import urllib.request
import urllib.parse
from pathlib import Path
from collections import Counter


# Local knowledge cache directory
CACHE_DIR = Path(__file__).parent.parent / ".cache" / "retrieval"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class KnowledgeBase:
    """
    Embedded knowledge base with curated facts for common verification domains.
    Acts as a fallback when external retrieval is unavailable.
    """

    FACTS = {
        "bitcoin": {
            "consensus": "Bitcoin uses proof-of-work (PoW) consensus mechanism, not proof of stake.",
            "creator": "Bitcoin was created by the pseudonymous Satoshi Nakamoto.",
            "whitepaper": "The Bitcoin whitepaper was published on October 31, 2008.",
            "genesis": "The Bitcoin genesis block was mined on January 3, 2009.",
            "supply": "Bitcoin has a maximum supply cap of 21 million coins.",
            "halving": "Bitcoin block rewards halve approximately every 4 years (210,000 blocks).",
        },
        "ethereum": {
            "consensus": "Ethereum transitioned from proof-of-work to proof-of-stake in September 2022 (The Merge).",
            "creator": "Ethereum was proposed by Vitalik Buterin in 2013.",
            "smart_contracts": "Ethereum supports Turing-complete smart contracts via the EVM.",
        },
        "earth": {
            "shape": "Earth is an oblate spheroid, approximately spherical.",
            "age": "Earth is approximately 4.54 billion years old.",
            "sun_distance": "Earth is approximately 93 million miles (150 million km) from the Sun.",
            "moon": "Earth has one natural satellite, the Moon.",
            "rotation": "Earth rotates on its axis approximately once every 24 hours.",
        },
        "physics": {
            "speed_of_light": "The speed of light in a vacuum is approximately 299,792,458 meters per second.",
            "gravity": "The acceleration due to gravity on Earth's surface is approximately 9.81 m/s².",
            "water_boiling": "Water boils at 100°C (212°F) at standard atmospheric pressure.",
        },
        "biology": {
            "dna": "DNA stands for deoxyribonucleic acid and carries genetic information.",
            "cells": "All living organisms are composed of cells.",
            "photosynthesis": "Photosynthesis converts carbon dioxide and water into glucose and oxygen using sunlight.",
        },
        "history": {
            "moon_landing": "The first human moon landing was on July 20, 1969, during the Apollo 11 mission.",
            "wwii_end": "World War II ended in 1945.",
            "internet": "The World Wide Web was invented by Tim Berners-Lee in 1989.",
        },
        "computing": {
            "python_type": "Python is an interpreted, high-level programming language, not a compiled language.",
            "javascript_java": "JavaScript and Java are distinct programming languages with different designs.",
            "html": "HTML is a markup language, not a programming language.",
            "linux_creator": "Linux was created by Linus Torvalds in 1991.",
            "turing": "Alan Turing is considered the father of theoretical computer science.",
        },
        "astronomy": {
            "sun_star": "The Sun is a G-type main-sequence star (yellow dwarf).",
            "neptune": "Neptune is the eighth and farthest known planet from the Sun in the Solar System.",
            "moon_gravity": "The Moon's surface gravity is about 1.62 m/s², roughly one-sixth of Earth's.",
            "everest": "Mount Everest is the tallest mountain above sea level at approximately 8,849 meters.",
        },
        "health": {
            "vaccines": "Vaccines work by training the immune system to recognize and fight pathogens.",
            "brain_myth": "Humans use virtually all of their brain, not just 10 percent. The 10% myth is false.",
            "bones": "An adult human has 206 bones.",
        },
    }

    @classmethod
    def search(cls, query: str) -> typing.List[dict]:
        """
        Search the embedded knowledge base for facts relevant to the query.

        Returns list of dicts with 'text' and 'source' keys.
        """
        query_lower = query.lower()
        results = []

        for domain, facts in cls.FACTS.items():
            if domain in query_lower:
                for topic, fact in facts.items():
                    results.append({
                        "text": fact,
                        "source": f"VeriNet Knowledge Base — {domain}/{topic}",
                    })
            else:
                # Keyword matching across all facts
                for topic, fact in facts.items():
                    fact_words = set(re.findall(r'\b\w{4,}\b', fact.lower()))
                    query_words = set(re.findall(r'\b\w{4,}\b', query_lower))
                    overlap = fact_words & query_words
                    if len(overlap) >= 2:
                        results.append({
                            "text": fact,
                            "source": f"VeriNet Knowledge Base — {domain}/{topic}",
                        })

        return results


class WikipediaRetriever:
    """
    Retrieves evidence from Wikipedia using the public MediaWiki API.
    This is a sovereign-compatible source — Wikipedia is open and self-hostable.
    """

    API_URL = "https://en.wikipedia.org/w/api.php"

    @classmethod
    def search(cls, query: str, max_results: int = 5) -> typing.List[dict]:
        """
        Search Wikipedia for passages relevant to the query.
        Falls back gracefully if the Wikipedia API is unreachable.
        """
        # Check cache first
        cache_key = hashlib.md5(query.encode()).hexdigest()
        cache_file = CACHE_DIR / f"wiki_{cache_key}.json"

        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        results = []
        try:
            # Step 1: Search for relevant pages
            search_params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": str(max_results),
                "format": "json",
            }
            url = cls.API_URL + "?" + urllib.parse.urlencode(search_params)
            req = urllib.request.Request(url, headers={"User-Agent": "VeriNet/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())

            search_results = data.get("query", {}).get("search", [])

            # Step 2: Get extracts for each page
            for sr in search_results[:max_results]:
                page_title = sr["title"]
                extract = cls._get_extract(page_title)
                if extract:
                    results.append({
                        "text": extract,
                        "source": f"Wikipedia — {page_title}",
                    })

            # Cache results
            if results:
                try:
                    with open(cache_file, "w") as f:
                        json.dump(results, f)
                except IOError:
                    pass

        except Exception:
            # Fail silently — retriever should not crash the miner
            pass

        return results

    @classmethod
    def _get_extract(cls, title: str, max_chars: int = 1000) -> typing.Optional[str]:
        """Get a text extract for a Wikipedia page."""
        try:
            params = {
                "action": "query",
                "titles": title,
                "prop": "extracts",
                "exintro": "true",
                "explaintext": "true",
                "exchars": str(max_chars),
                "format": "json",
            }
            url = cls.API_URL + "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(url, headers={"User-Agent": "VeriNet/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())

            pages = data.get("query", {}).get("pages", {})
            for page_id, page_data in pages.items():
                if page_id != "-1":
                    return page_data.get("extract", "")
        except Exception:
            pass
        return None


class EvidenceRetriever:
    """
    Main retrieval orchestrator. Combines multiple retrieval sources
    and deduplicates / ranks evidence.
    """

    def __init__(self):
        self.knowledge_base = KnowledgeBase()
        self.wiki_retriever = WikipediaRetriever()

    def retrieve(self, claim: str, max_evidence: int = 8) -> typing.List[dict]:
        """
        Retrieve evidence for a claim from all available sources.

        Returns a ranked list of evidence items, each with 'text' and 'source'.
        """
        all_evidence = []

        # 1. Local knowledge base (always available — sovereign)
        kb_results = self.knowledge_base.search(claim)
        all_evidence.extend(kb_results)

        # 2. Wikipedia (open, self-hostable — sovereign)
        wiki_results = self.wiki_retriever.search(claim, max_results=5)
        all_evidence.extend(wiki_results)

        # 3. Deduplicate by content similarity
        deduped = self._deduplicate(all_evidence)

        # 4. Rank by relevance to the claim
        ranked = self._rank(deduped, claim)

        return ranked[:max_evidence]

    def _deduplicate(self, evidence: typing.List[dict]) -> typing.List[dict]:
        """Remove near-duplicate evidence items."""
        seen_hashes = set()
        deduped = []
        for item in evidence:
            # Use first 100 chars as dedup key
            key = hashlib.md5(item["text"][:100].lower().encode()).hexdigest()
            if key not in seen_hashes:
                seen_hashes.add(key)
                deduped.append(item)
        return deduped

    def _rank(self, evidence: typing.List[dict], claim: str) -> typing.List[dict]:
        """Rank evidence by relevance to the claim using keyword overlap."""
        claim_words = set(re.findall(r'\b\w{3,}\b', claim.lower()))

        scored = []
        for item in evidence:
            text_words = set(re.findall(r'\b\w{3,}\b', item["text"].lower()))
            overlap = len(claim_words & text_words)
            scored.append((overlap, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored]
