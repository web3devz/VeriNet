"""
VeriNet Validator — Decentralized fact-verification validator neuron.

Distributes claims to miners, evaluates their verification outputs,
computes scores, and sets weights on the Bittensor network.

Usage:
    python neurons/validator.py \
        --netuid NETUID \
        --wallet.name WALLET_NAME \
        --wallet.hotkey HOTKEY \
        --subtensor.network local
"""

import sys
import os
import time
import typing
import argparse
import traceback
import asyncio
import random

import numpy as np
import torch

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bittensor as bt
from verinet.protocol import FactVerification
from verinet.scoring import compute_miner_scores
from benchmarks.fever_loader import FEVERLoader


class FactVerificationValidator:
    """
    VeriNet Validator neuron.

    Orchestrates the fact-verification evaluation loop:
    1. Samples claims from the FEVER benchmark
    2. Sends claims to registered miners
    3. Evaluates miner responses using multi-criteria scoring
    4. Updates miner weights on-chain via Yuma Consensus
    """

    def __init__(self, config: bt.config):
        self.config = config

        # Initialize Bittensor components
        bt.logging(config=config)
        bt.logging.info("Initializing VeriNet Validator...")

        self.wallet = bt.wallet(config=config)
        self.subtensor = bt.subtensor(config=config)
        self.metagraph = self.subtensor.metagraph(config.netuid)
        self.dendrite = bt.dendrite(wallet=self.wallet)

        bt.logging.info(f"Wallet: {self.wallet}")
        bt.logging.info(f"Subtensor: {self.subtensor}")

        # Verify registration
        if self.wallet.hotkey.ss58_address not in self.metagraph.hotkeys:
            bt.logging.error(
                "Validator hotkey is not registered on the subnet. "
                "Run: btcli subnets register --netuid NETUID"
            )
            sys.exit(1)

        self.uid = self.metagraph.hotkeys.index(self.wallet.hotkey.ss58_address)
        bt.logging.info(f"Running validator on UID: {self.uid}")

        # Initialize scoring state
        self.scores = torch.zeros(self.metagraph.n.item(), dtype=torch.float32)

        # Initialize benchmark loader
        self.fever_loader = FEVERLoader()
        self.fever_loader.load()
        stats = self.fever_loader.stats()
        bt.logging.info(f"Benchmark loaded: {stats['total_claims']} claims available.")

        # Human verification state (WaaP integration)
        self.human_verified = self._check_human_verification()

    def _check_human_verification(self) -> bool:
        """
        Check if this validator has been verified as human via WaaP CLI.
        This is optional but gives priority in the network.
        """
        waap_marker = os.path.expanduser("~/.waap/verified")
        if os.path.exists(waap_marker):
            bt.logging.info("Human verification: VERIFIED via WaaP.")
            return True
        bt.logging.info(
            "Human verification: NOT VERIFIED. "
            "Run 'npx @human.tech/waap-cli verify' for priority."
        )
        return False

    def get_miner_uids(self) -> typing.List[int]:
        """
        Get UIDs of available miners, excluding the validator's own UID.
        Filters out miners with no reachable axon.
        """
        all_uids = list(range(self.metagraph.n.item()))
        available = [
            uid for uid in all_uids
            if uid != self.uid
            and self.metagraph.axons[uid].ip != "0.0.0.0"
            and self.metagraph.axons[uid].port != 0
        ]

        # Sample up to 16 miners per round
        if len(available) > 16:
            available = random.sample(available, 16)

        return available

    async def forward(self) -> None:
        """
        Single validator forward pass.

        1. Sample a claim from the benchmark
        2. Build synapse and query miners
        3. Score responses
        4. Update local score tracking
        """
        # 1. Sample claim
        sample = self.fever_loader.sample()
        claim_text = sample["claim"]
        ground_truth_label = sample.get("label", None)

        bt.logging.info(f"Claim: {claim_text}")
        bt.logging.info(f"Ground truth: {ground_truth_label}")

        # 2. Build synapse and query
        synapse = FactVerification(claim=claim_text)
        miner_uids = self.get_miner_uids()

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

        # 3. Score responses
        scores = compute_miner_scores(
            responses=responses,
            ground_truth_label=ground_truth_label,
            claim=claim_text,
        )

        # 4. Update scores (exponential moving average)
        for i, uid in enumerate(miner_uids):
            # Grow scores tensor if metagraph has expanded
            if uid >= len(self.scores):
                new_scores = torch.zeros(
                    self.metagraph.n.item(), dtype=torch.float32
                )
                new_scores[:len(self.scores)] = self.scores
                self.scores = new_scores

            self.scores[uid] = self.scores[uid] * 0.7 + scores[i] * 0.3

        # Log results
        for i, uid in enumerate(miner_uids):
            r = responses[i]
            bt.logging.info(
                f"UID {uid}: verdict={r.verdict}, confidence={r.confidence}, "
                f"score={scores[i]:.3f}, ema={self.scores[uid]:.3f}"
            )

    def set_weights(self) -> None:
        """
        Set weights on the Bittensor network based on accumulated miner scores.
        Weights are normalized to sum to 1.0.
        """
        bt.logging.info("Setting weights on the network...")

        # Normalize scores to weights
        raw_weights = self.scores.clone()
        total = raw_weights.sum()

        if total > 0:
            weights = raw_weights / total
        else:
            # Equal weights if no scores yet
            n = self.metagraph.n.item()
            weights = torch.ones(n, dtype=torch.float32) / n

        uids = torch.arange(len(weights), dtype=torch.int64)

        try:
            result = self.subtensor.set_weights(
                wallet=self.wallet,
                netuid=self.config.netuid,
                uids=uids,
                weights=weights,
                wait_for_inclusion=True,
            )
            if result:
                bt.logging.info("Weights set successfully.")
            else:
                bt.logging.warning("Weight setting returned False.")
        except Exception as e:
            bt.logging.error(f"Failed to set weights: {e}")

    def run(self):
        """
        Main validator loop.

        Each iteration:
        1. Runs a forward pass (query miners, score, update)
        2. Periodically sets weights on-chain
        3. Syncs the metagraph
        """
        bt.logging.info("Starting VeriNet Validator main loop.")

        step = 0
        weights_interval = 25  # Set weights every N steps (~5 minutes at 12s blocks)

        while True:
            try:
                bt.logging.info(f"--- Validator step {step} ---")

                # Run forward pass
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.forward())
                finally:
                    loop.close()

                # Periodically set weights
                if (step + 1) % weights_interval == 0:
                    self.set_weights()

                # Periodically sync metagraph
                if step % 10 == 0:
                    self.metagraph.sync(subtensor=self.subtensor)

                    # Resize scores if metagraph changed
                    n = self.metagraph.n.item()
                    if n > len(self.scores):
                        new_scores = torch.zeros(n, dtype=torch.float32)
                        new_scores[:len(self.scores)] = self.scores
                        self.scores = new_scores

                    bt.logging.info(
                        f"Block: {self.metagraph.block.item()} | "
                        f"Peers: {n} | "
                        f"Active scores: {(self.scores > 0).sum().item()}"
                    )

                step += 1
                time.sleep(12)  # ~1 Bittensor block

            except KeyboardInterrupt:
                bt.logging.info("Validator shutting down.")
                break
            except Exception as e:
                bt.logging.error(f"Validator error: {e}")
                bt.logging.error(traceback.format_exc())
                time.sleep(12)


def get_config() -> bt.config:
    """Parse command line arguments and build configuration."""
    parser = argparse.ArgumentParser(description="VeriNet Validator")
    parser.add_argument(
        "--netuid", type=int, default=1, help="Subnet netuid to connect to."
    )
    bt.wallet.add_args(parser)
    bt.subtensor.add_args(parser)
    bt.logging.add_args(parser)

    config = bt.config(parser)
    return config


def main():
    config = get_config()
    validator = FactVerificationValidator(config)
    validator.run()


if __name__ == "__main__":
    main()
