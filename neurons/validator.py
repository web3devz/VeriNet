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
from waap import WaaPClient, AGENT_WEIGHT_BOOST
from passport import PassportClient, NetworkType, HUMAN_WEIGHT_BOOST


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

        # Agent authentication (WaaP integration)
        self.waap = WaaPClient(
            hotkey_ss58=self.wallet.hotkey.ss58_address
        )
        self.agent_authenticated = self.waap.is_authenticated
        if self.agent_authenticated:
            bt.logging.info(
                f"WaaP: AGENT AUTHENTICATED — weight boost {AGENT_WEIGHT_BOOST}x active"
            )
        else:
            bt.logging.info(
                "WaaP: NOT AUTHENTICATED — run './scripts/verify_human.sh' for agent setup"
            )

        # Human verification (Passport.xyz integration)
        self.passport = PassportClient(NetworkType.OPTIMISM)
        # For demo purposes, use a static address -> UID mapping
        # In production, this would be stored/retrieved from on-chain metadata
        self.address_to_uid = {}
        self.verified_human_addresses = set()
        bt.logging.info("Passport.xyz: Human verification system initialized")

    def get_authenticated_uids(self) -> typing.Set[int]:
        """
        Return the set of UIDs that have authenticated WaaP agents.
        In a full deployment this queries on-chain agent attestations.
        For local mode, only this validator's UID is tracked.
        """
        authenticated = set()
        if self.agent_authenticated:
            authenticated.add(self.uid)
        return authenticated

    def get_verified_human_uids(self) -> typing.Set[int]:
        """
        Return the set of UIDs that have verified human identity through Passport.xyz.
        In a full deployment this would query on-chain human attestations.
        For local mode, uses a static mapping of verified addresses.
        """
        verified_uids = set()
        for address in self.verified_human_addresses:
            uid = self.address_to_uid.get(address)
            if uid is not None:
                verified_uids.add(uid)
        return verified_uids

    async def update_human_verifications(self) -> None:
        """
        Update human verification status for known addresses.
        In production, this would check all miner addresses against Passport.xyz.
        """
        if not self.address_to_uid:
            # For demo, create a sample mapping - replace with real address discovery
            bt.logging.debug("No address->UID mappings available for human verification")
            return

        try:
            # Check verification status for addresses we know about
            addresses_to_check = list(self.address_to_uid.keys())
            if addresses_to_check:
                async with self.passport as client:
                    tasks = [client.get_full_status(addr) for addr in addresses_to_check]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    new_verified = set()
                    for addr, result in zip(addresses_to_check, results):
                        if isinstance(result, Exception):
                            bt.logging.warning(f"Human verification check failed for {addr}: {result}")
                            continue

                        if result.is_verified:
                            new_verified.add(addr)
                            bt.logging.debug(
                                f"Human verified: {addr} ({result.verification_count}/3 verifications)"
                            )

                    # Update verified set
                    prev_count = len(self.verified_human_addresses)
                    self.verified_human_addresses = new_verified
                    new_count = len(self.verified_human_addresses)

                    if new_count != prev_count:
                        bt.logging.info(
                            f"Human verification status updated: {new_count} verified addresses "
                            f"(was {prev_count})"
                        )

        except Exception as e:
            bt.logging.warning(f"Failed to update human verifications: {e}")

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
        Authenticated WaaP agents get a weight boost.
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

        # Apply WaaP agent boost
        authenticated_uids = self.get_authenticated_uids()
        if authenticated_uids:
            weights_list = self.waap.apply_weight_boost(
                weights.tolist(), authenticated_uids
            )
            weights = torch.tensor(weights_list, dtype=torch.float32)
            bt.logging.info(
                f"WaaP boost applied to {len(authenticated_uids)} authenticated agent(s)"
            )

        # Apply Passport.xyz human verification boost
        verified_human_uids = self.get_verified_human_uids()
        if verified_human_uids:
            weights_list = self.passport.apply_human_boost(
                weights.tolist(), self.verified_human_addresses, self.address_to_uid
            )
            weights = torch.tensor(weights_list, dtype=torch.float32)
            bt.logging.info(
                f"Passport.xyz boost applied to {len(verified_human_uids)} verified human(s) "
                f"(boost: {HUMAN_WEIGHT_BOOST}x)"
            )

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

                    # Update human verification status
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(self.update_human_verifications())
                    except Exception as e:
                        bt.logging.warning(f"Human verification update failed: {e}")
                    finally:
                        loop.close()

                    bt.logging.info(
                        f"Block: {self.metagraph.block.item()} | "
                        f"Peers: {n} | "
                        f"Active scores: {(self.scores > 0).sum().item()} | "
                        f"Verified humans: {len(self.verified_human_addresses)}"
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
