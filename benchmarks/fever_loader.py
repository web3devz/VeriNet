"""
VeriNet FEVER Benchmark Loader — Loads and serves fact-checking benchmark claims.

Uses the FEVER (Fact Extraction and VERification) dataset format for structured
fact-checking evaluation. Includes a built-in curated set for offline operation,
and can download the full FEVER dataset for comprehensive benchmarking.
"""

import json
import os
import random
import typing
import urllib.request
from pathlib import Path


DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


# Curated benchmark claims for offline operation and testing.
# These cover multiple domains and difficulty levels.
CURATED_CLAIMS = [
    {
        "id": 1,
        "claim": "Bitcoin uses proof of stake.",
        "label": "REFUTES",
        "evidence": "Bitcoin uses proof-of-work consensus mechanism as described in the Bitcoin whitepaper by Satoshi Nakamoto.",
    },
    {
        "id": 2,
        "claim": "The Earth is flat.",
        "label": "REFUTES",
        "evidence": "Earth is an oblate spheroid, confirmed by satellite imagery, physics, and centuries of scientific observation.",
    },
    {
        "id": 3,
        "claim": "Water boils at 100 degrees Celsius at standard atmospheric pressure.",
        "label": "SUPPORTS",
        "evidence": "Water boils at 100°C (212°F) at standard atmospheric pressure (1 atm).",
    },
    {
        "id": 4,
        "claim": "Python is a compiled programming language.",
        "label": "REFUTES",
        "evidence": "Python is primarily an interpreted programming language, though it compiles to bytecode.",
    },
    {
        "id": 5,
        "claim": "The speed of light is approximately 300,000 kilometers per second.",
        "label": "SUPPORTS",
        "evidence": "The speed of light in a vacuum is approximately 299,792 km/s, commonly rounded to 300,000 km/s.",
    },
    {
        "id": 6,
        "claim": "HTML is a programming language.",
        "label": "REFUTES",
        "evidence": "HTML (HyperText Markup Language) is a markup language, not a programming language.",
    },
    {
        "id": 7,
        "claim": "The Moon landing in 1969 was a hoax.",
        "label": "REFUTES",
        "evidence": "The Apollo 11 Moon landing on July 20, 1969, is supported by extensive evidence including rock samples, retroreflectors, and independent verification.",
    },
    {
        "id": 8,
        "claim": "Photosynthesis converts carbon dioxide and water into glucose and oxygen.",
        "label": "SUPPORTS",
        "evidence": "Photosynthesis uses sunlight to convert CO2 and H2O into C6H12O6 (glucose) and O2 (oxygen).",
    },
    {
        "id": 9,
        "claim": "Ethereum was created by Satoshi Nakamoto.",
        "label": "REFUTES",
        "evidence": "Ethereum was proposed by Vitalik Buterin in 2013 and launched in 2015. Satoshi Nakamoto created Bitcoin.",
    },
    {
        "id": 10,
        "claim": "DNA stands for deoxyribonucleic acid.",
        "label": "SUPPORTS",
        "evidence": "DNA is the abbreviation for deoxyribonucleic acid, the molecule that carries genetic information.",
    },
    {
        "id": 11,
        "claim": "The Great Wall of China is visible from space with the naked eye.",
        "label": "REFUTES",
        "evidence": "The Great Wall of China is generally not visible from low Earth orbit with the naked eye. This is a common misconception.",
    },
    {
        "id": 12,
        "claim": "Albert Einstein developed the theory of general relativity.",
        "label": "SUPPORTS",
        "evidence": "Albert Einstein published the theory of general relativity in 1915.",
    },
    {
        "id": 13,
        "claim": "TCP/IP is the fundamental protocol suite of the Internet.",
        "label": "SUPPORTS",
        "evidence": "The TCP/IP protocol suite is the foundational communication protocol of the Internet.",
    },
    {
        "id": 14,
        "claim": "Humans only use 10 percent of their brains.",
        "label": "REFUTES",
        "evidence": "Neuroimaging studies show that virtually all areas of the brain are active at various times. The 10% myth is not supported by neuroscience.",
    },
    {
        "id": 15,
        "claim": "The Amazon rainforest produces 20 percent of the world's oxygen.",
        "label": "REFUTES",
        "evidence": "While the Amazon produces significant oxygen during photosynthesis, it also consumes nearly the same amount through respiration. Net oxygen contribution is close to zero.",
    },
    {
        "id": 16,
        "claim": "Gravity on the Moon is about one-sixth of Earth's gravity.",
        "label": "SUPPORTS",
        "evidence": "The Moon's surface gravity is approximately 1.62 m/s², about 16.6% of Earth's 9.81 m/s².",
    },
    {
        "id": 17,
        "claim": "Linux was created by Linus Torvalds in 1991.",
        "label": "SUPPORTS",
        "evidence": "Linus Torvalds released the first version of the Linux kernel in 1991.",
    },
    {
        "id": 18,
        "claim": "Vaccines cause autism.",
        "label": "REFUTES",
        "evidence": "Extensive research involving millions of children has found no link between vaccines and autism. The original 1998 study was retracted due to fraud.",
    },
    {
        "id": 19,
        "claim": "The boiling point of water decreases at higher altitudes.",
        "label": "SUPPORTS",
        "evidence": "At higher altitudes, atmospheric pressure is lower, which reduces the boiling point of water.",
    },
    {
        "id": 20,
        "claim": "Bittensor uses a mechanism called Yuma Consensus.",
        "label": "SUPPORTS",
        "evidence": "Bittensor's core consensus mechanism is called Yuma Consensus, which drives network participants into agreement on value creation.",
    },
    {
        "id": 21,
        "claim": "The human body has 206 bones.",
        "label": "SUPPORTS",
        "evidence": "An adult human skeleton typically contains 206 bones.",
    },
    {
        "id": 22,
        "claim": "Diamond is the hardest naturally occurring substance.",
        "label": "SUPPORTS",
        "evidence": "Diamond is the hardest known naturally occurring material, scoring 10 on the Mohs hardness scale.",
    },
    {
        "id": 23,
        "claim": "The Sun revolves around the Earth.",
        "label": "REFUTES",
        "evidence": "The heliocentric model, confirmed by centuries of astronomical observation, shows Earth revolves around the Sun.",
    },
    {
        "id": 24,
        "claim": "JavaScript and Java are the same programming language.",
        "label": "REFUTES",
        "evidence": "JavaScript and Java are distinct programming languages with different type systems, runtimes, and use cases.",
    },
    {
        "id": 25,
        "claim": "World War II ended in 1945.",
        "label": "SUPPORTS",
        "evidence": "World War II ended with Japan's surrender on September 2, 1945.",
    },
    {
        "id": 26,
        "claim": "Neptune is the planet closest to the Sun.",
        "label": "REFUTES",
        "evidence": "Mercury is the planet closest to the Sun. Neptune is the eighth and farthest known planet from the Sun.",
    },
    {
        "id": 27,
        "claim": "The Internet was invented in 1989 by Tim Berners-Lee.",
        "label": "REFUTES",
        "evidence": "Tim Berners-Lee invented the World Wide Web in 1989, not the Internet. The Internet originated from ARPANET in the late 1960s.",
    },
    {
        "id": 28,
        "claim": "Sound travels faster in water than in air.",
        "label": "SUPPORTS",
        "evidence": "Sound travels approximately 4.3 times faster in water (~1,480 m/s) than in air (~343 m/s).",
    },
    {
        "id": 29,
        "claim": "Mount Everest is the tallest mountain on Earth.",
        "label": "SUPPORTS",
        "evidence": "Mount Everest, at 8,849 meters, is the tallest mountain above sea level on Earth.",
    },
    {
        "id": 30,
        "claim": "Goldfish have a three-second memory.",
        "label": "REFUTES",
        "evidence": "Studies have shown goldfish can retain memories for months, debunking the three-second memory myth.",
    },
]


class FEVERLoader:
    """
    Loads fact-checking benchmark claims for validator evaluation rounds.

    Supports:
    1. Built-in curated claims (always available — no external dependencies)
    2. FEVER dataset file loading (if downloaded)

    The curated claims cover multiple domains and ensure the subnet works
    offline, satisfying the sovereignty requirement.
    """

    def __init__(self, data_dir: typing.Optional[str] = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.claims: typing.List[dict] = []
        self._loaded = False

    def load(self) -> None:
        """
        Load claims from available sources.
        Priority: FEVER file > curated claims.
        Always includes curated claims as a baseline.
        """
        # Always start with curated claims
        self.claims = list(CURATED_CLAIMS)

        # Try to load FEVER dataset file if available
        fever_file = self.data_dir / "fever_train.jsonl"
        if fever_file.exists():
            try:
                fever_claims = self._load_fever_file(fever_file)
                self.claims.extend(fever_claims)
            except Exception as e:
                print(f"Warning: Could not load FEVER file: {e}")

        self._loaded = True

    def _load_fever_file(self, filepath: Path) -> typing.List[dict]:
        """Load claims from a FEVER JSONL file."""
        claims = []
        with open(filepath, "r") as f:
            for i, line in enumerate(f):
                if i >= 10000:  # Cap at 10k claims to manage memory
                    break
                try:
                    data = json.loads(line.strip())
                    claim_entry = {
                        "id": data.get("id", i + 10000),
                        "claim": data.get("claim", ""),
                        "label": data.get("label", "NOT ENOUGH INFO"),
                        "evidence": data.get("evidence", ""),
                    }
                    if claim_entry["claim"]:
                        claims.append(claim_entry)
                except (json.JSONDecodeError, KeyError):
                    continue
        return claims

    def download_fever(self) -> bool:
        """
        Download the FEVER shared task training data.
        This is a large file (~150MB). Falls back gracefully on failure.

        Returns True if download succeeded.
        """
        url = "https://fever.ai/download/fever/train.jsonl"
        dest = self.data_dir / "fever_train.jsonl"

        if dest.exists():
            return True

        try:
            print(f"Downloading FEVER dataset to {dest}...")
            req = urllib.request.Request(url, headers={"User-Agent": "VeriNet/1.0"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                with open(dest, "wb") as f:
                    while True:
                        chunk = resp.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
            print("FEVER dataset downloaded successfully.")
            return True
        except Exception as e:
            print(f"Could not download FEVER dataset: {e}")
            print("Continuing with curated claims only.")
            return False

    def sample(self, n: int = 1) -> typing.Union[dict, typing.List[dict]]:
        """
        Randomly sample claim(s) from the loaded dataset.

        Args:
            n: Number of claims to sample.

        Returns:
            Single claim dict if n=1, list of claim dicts otherwise.
        """
        if not self._loaded:
            self.load()

        if not self.claims:
            raise RuntimeError("No claims available. Call load() first.")

        if n == 1:
            return random.choice(self.claims)
        else:
            return random.sample(self.claims, min(n, len(self.claims)))

    def get_by_id(self, claim_id: int) -> typing.Optional[dict]:
        """Get a specific claim by its ID."""
        if not self._loaded:
            self.load()

        for claim in self.claims:
            if claim["id"] == claim_id:
                return claim
        return None

    def stats(self) -> dict:
        """Return statistics about the loaded dataset."""
        if not self._loaded:
            self.load()

        labels = {}
        for claim in self.claims:
            label = claim.get("label", "UNKNOWN")
            labels[label] = labels.get(label, 0) + 1

        return {
            "total_claims": len(self.claims),
            "label_distribution": labels,
            "has_fever_file": (self.data_dir / "fever_train.jsonl").exists(),
        }
