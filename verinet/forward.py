"""
VeriNet Forward Pass — Validator's query dispatch logic.

Constructs fact-verification queries, selects miners, and dispatches
synapse requests across the network.
"""

import random
import bittensor as bt
from verinet.protocol import FactVerification
from verinet.scoring import compute_miner_scores
from benchmarks.fever_loader import FEVERLoader


# Singleton benchmark loader. Claims are loaded once and sampled per round.
_fever_loader: FEVERLoader = None


def get_fever_loader() -> FEVERLoader:
    """Lazy-initialize the FEVER benchmark loader."""
    global _fever_loader
    if _fever_loader is None:
        _fever_loader = FEVERLoader()
        _fever_loader.load()
    return _fever_loader


async def forward(self) -> None:
    """
    Validator forward pass.

    1. Sample a claim from the benchmark dataset.
    2. Build a FactVerification synapse.
    3. Query available miners on the network.
    4. Evaluate responses and compute scores.
    5. Update miner weights.
    """
    bt.logging.info("Starting validator forward pass.")

    # -- 1. Sample a claim --
    loader = get_fever_loader()
    sample = loader.sample()
    claim_text = sample["claim"]
    ground_truth_label = sample.get("label", None)  # SUPPORTS / REFUTES / NOT ENOUGH INFO

    bt.logging.info(f"Sampled claim: {claim_text}")
    bt.logging.info(f"Ground truth: {ground_truth_label}")

    # -- 2. Build synapse --
    synapse = FactVerification(claim=claim_text)

    # -- 3. Query miners --
    miner_uids = get_available_miner_uids(self)
    if not miner_uids:
        bt.logging.warning("No miners available. Skipping round.")
        return

    bt.logging.info(f"Querying {len(miner_uids)} miners: {miner_uids}")

    axons = [self.metagraph.axons[uid] for uid in miner_uids]
    responses = await self.dendrite(
        axons=axons,
        synapse=synapse,
        deserialize=False,
        timeout=30.0,
    )

    # -- 4. Evaluate responses --
    scores = compute_miner_scores(
        responses=responses,
        ground_truth_label=ground_truth_label,
        claim=claim_text,
    )

    bt.logging.info(f"Miner scores: {dict(zip(miner_uids, scores))}")

    # -- 5. Update weights --
    for i, uid in enumerate(miner_uids):
        self.scores[uid] = (
            self.scores[uid] * 0.7 + scores[i] * 0.3
        )

    bt.logging.info("Forward pass complete. Weights updated.")


def get_available_miner_uids(self) -> list:
    """
    Get UIDs of available miners from the metagraph,
    excluding the validator's own UID.
    """
    all_uids = list(range(self.metagraph.n.item()))
    # Exclude our own UID
    available = [
        uid for uid in all_uids
        if uid != self.uid
        and self.metagraph.axons[uid].ip != "0.0.0.0"
    ]
    # Sample up to 16 miners per round to keep query costs bounded
    if len(available) > 16:
        available = random.sample(available, 16)
    return available
