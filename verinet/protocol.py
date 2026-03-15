"""
VeriNet Protocol — Wire-protocol definitions for fact-verification synapses.

Defines the Synapse subclass used for communication between miners and validators
in the VeriNet decentralized fact-verification subnet.
"""

import typing
import bittensor as bt
from pydantic import Field


class FactVerification(bt.Synapse):
    """
    Synapse for fact-verification tasks.

    Validators send a claim string to miners. Miners return a structured
    verification result including verdict, confidence, sources, and reasoning.
    """

    # -- Request fields (sent by validator to miner) --
    claim: str = Field(
        ...,
        description="The factual claim to verify.",
        title="Claim",
    )

    # -- Response fields (filled by miner, returned to validator) --
    verdict: typing.Optional[str] = Field(
        default=None,
        description="Verification verdict: 'True', 'False', or 'Uncertain'.",
        title="Verdict",
    )
    confidence: typing.Optional[float] = Field(
        default=None,
        description="Confidence score between 0.0 and 1.0.",
        title="Confidence",
    )
    sources: typing.Optional[typing.List[str]] = Field(
        default=None,
        description="List of sources supporting the verdict.",
        title="Sources",
    )
    reasoning: typing.Optional[str] = Field(
        default=None,
        description="Explanation of how the verdict was reached.",
        title="Reasoning",
    )

    def deserialize(self) -> dict:
        """Deserialize the miner response into a structured dictionary."""
        return {
            "claim": self.claim,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "sources": self.sources or [],
            "reasoning": self.reasoning,
        }
