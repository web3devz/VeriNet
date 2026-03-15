"""
VeriNet Passport.xyz Integration — Human identity verification and sybil resistance.

Integrates with Passport.xyz (Holonym) API to verify human identity through multiple
verification methods. Verified humans receive priority in the VeriNet subnet consensus.

Passport.xyz Verification Methods:
1. Government ID verification (KYC) - Official document verification
2. Phone verification - SMS/call-based phone number validation
3. Biometrics verification - Face uniqueness and liveness detection

This provides humans with:
- Sybil resistance through identity verification
- Multiple verification factors for enhanced trust
- Cross-network verification status (Optimism, Base, Stellar)
- Governance participation eligibility
- Priority weight boost in subnet consensus

API Base: https://api.holonym.io
Documentation: https://docs.passport.xyz/
"""

import asyncio
import aiohttp
import logging
import typing
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("verinet.passport")

# API Configuration
PASSPORT_API_BASE = "https://api.holonym.io"
DEFAULT_ACTION_ID = "123456789"  # Universal sybil resistance ID

# Weight multiplier for verified humans
HUMAN_WEIGHT_BOOST = 1.5  # Higher boost than WaaP agents


class NetworkType(Enum):
    """Supported blockchain networks for Passport verification."""
    OPTIMISM = "optimism"
    BASE_SEPOLIA = "base-sepolia"


class VerificationType(Enum):
    """Types of identity verification available."""
    GOVERNMENT_ID = "gov-id"
    PHONE = "phone"
    BIOMETRICS = "biometrics"


@dataclass
class VerificationResult:
    """Result of a Passport.xyz verification check."""
    verified: bool
    expiration_date: typing.Optional[int] = None
    verification_type: typing.Optional[VerificationType] = None
    network: typing.Optional[NetworkType] = None


@dataclass
class PassportStatus:
    """Complete verification status for a user address."""
    address: str
    network: NetworkType
    gov_id_verified: bool = False
    phone_verified: bool = False
    biometrics_verified: bool = False
    gov_id_expiry: typing.Optional[int] = None
    phone_expiry: typing.Optional[int] = None
    biometrics_expiry: typing.Optional[int] = None

    @property
    def is_verified(self) -> bool:
        """Check if user has at least one verification."""
        return self.gov_id_verified or self.phone_verified or self.biometrics_verified

    @property
    def verification_count(self) -> int:
        """Count of active verifications."""
        return sum([self.gov_id_verified, self.phone_verified, self.biometrics_verified])

    @property
    def is_fully_verified(self) -> bool:
        """Check if user has all three verification types."""
        return self.gov_id_verified and self.phone_verified and self.biometrics_verified


class PassportClient:
    """
    Client for interacting with Passport.xyz identity verification API.

    Provides methods for:
    - Government ID verification checks
    - Phone verification checks
    - Biometrics verification checks
    - Bulk status retrieval for multiple addresses
    - Clean hands verification (sanctions/PEP list)
    """

    def __init__(self, network: NetworkType = NetworkType.OPTIMISM, action_id: str = DEFAULT_ACTION_ID):
        self.network = network
        self.action_id = action_id
        self.session: typing.Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def check_government_id(self, address: str) -> VerificationResult:
        """
        Check if user has completed government ID (KYC) verification.

        Args:
            address: User's blockchain address

        Returns:
            VerificationResult with verification status and expiry
        """
        return await self._check_verification(address, VerificationType.GOVERNMENT_ID)

    async def check_phone(self, address: str) -> VerificationResult:
        """
        Check if user has completed phone verification.

        Args:
            address: User's blockchain address

        Returns:
            VerificationResult with verification status and expiry
        """
        return await self._check_verification(address, VerificationType.PHONE)

    async def check_biometrics(self, address: str) -> VerificationResult:
        """
        Check if user has completed biometrics verification.

        Args:
            address: User's blockchain address

        Returns:
            VerificationResult with verification status and expiry
        """
        return await self._check_verification(address, VerificationType.BIOMETRICS)

    async def get_full_status(self, address: str) -> PassportStatus:
        """
        Get complete verification status for a user address.

        Args:
            address: User's blockchain address

        Returns:
            PassportStatus with all verification types checked
        """
        # Run all three checks concurrently
        gov_task = self.check_government_id(address)
        phone_task = self.check_phone(address)
        bio_task = self.check_biometrics(address)

        gov_result, phone_result, bio_result = await asyncio.gather(
            gov_task, phone_task, bio_task, return_exceptions=True
        )

        status = PassportStatus(address=address, network=self.network)

        # Process government ID result
        if isinstance(gov_result, VerificationResult):
            status.gov_id_verified = gov_result.verified
            status.gov_id_expiry = gov_result.expiration_date
        elif isinstance(gov_result, Exception):
            logger.warning(f"Gov ID check failed for {address}: {gov_result}")

        # Process phone result
        if isinstance(phone_result, VerificationResult):
            status.phone_verified = phone_result.verified
            status.phone_expiry = phone_result.expiration_date
        elif isinstance(phone_result, Exception):
            logger.warning(f"Phone check failed for {address}: {phone_result}")

        # Process biometrics result
        if isinstance(bio_result, VerificationResult):
            status.biometrics_verified = bio_result.verified
            status.biometrics_expiry = bio_result.expiration_date
        elif isinstance(bio_result, Exception):
            logger.warning(f"Biometrics check failed for {address}: {bio_result}")

        return status

    async def check_clean_hands(self, address: str) -> VerificationResult:
        """
        Check proof of clean hands (sanctions/PEP list verification).

        Args:
            address: User's blockchain address

        Returns:
            VerificationResult indicating clean hands status
        """
        if not self.session:
            raise RuntimeError("PassportClient must be used as async context manager")

        url = f"{PASSPORT_API_BASE}/attestation/sbts/clean-hands"
        params = {
            "user": address,
            "action-id": self.action_id
        }

        try:
            async with self.session.get(url, params=params, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    return VerificationResult(
                        verified=data.get("result", False),
                        expiration_date=data.get("expirationDate"),
                        verification_type=None,  # Clean hands is separate verification
                        network=self.network
                    )
                else:
                    logger.warning(f"Clean hands check returned {response.status} for {address}")
                    return VerificationResult(verified=False)

        except asyncio.TimeoutError:
            logger.error(f"Clean hands check timed out for {address}")
            return VerificationResult(verified=False)
        except Exception as e:
            logger.error(f"Clean hands check failed for {address}: {e}")
            return VerificationResult(verified=False)

    def apply_human_boost(self, weights: typing.List[float], verified_addresses: typing.Set[str],
                         address_to_uid: typing.Dict[str, int]) -> typing.List[float]:
        """
        Apply weight boost to verified human addresses.

        Args:
            weights: List of current weights
            verified_addresses: Set of addresses that are verified humans
            address_to_uid: Mapping from addresses to UIDs

        Returns:
            List of boosted weights, re-normalized to sum to 1
        """
        boosted = list(weights)

        for address in verified_addresses:
            uid = address_to_uid.get(address)
            if uid is not None and uid < len(boosted):
                boosted[uid] *= HUMAN_WEIGHT_BOOST

        # Re-normalize so weights sum to 1
        total = sum(boosted)
        if total > 0:
            boosted = [w / total for w in boosted]

        return boosted

    # -- Private methods --

    async def _check_verification(self, address: str, verification_type: VerificationType) -> VerificationResult:
        """Internal method to check a specific verification type."""
        if not self.session:
            raise RuntimeError("PassportClient must be used as async context manager")

        # Validate Ethereum address format
        if not self._is_valid_ethereum_address(address):
            logger.warning(f"Invalid Ethereum address format: {address}")
            raise ValueError(f"Invalid Ethereum address format: {address}")

        url = f"{PASSPORT_API_BASE}/sybil-resistance/{verification_type.value}/{self.network.value}"
        params = {
            "user": address,
            "action-id": self.action_id
        }

        try:
            async with self.session.get(url, params=params, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()

                    # Handle API error responses (e.g., "Invalid user address")
                    if "error" in data:
                        logger.warning(f"Holonym API error for {address}: {data['error']}")
                        raise ValueError(f"Holonym API error: {data['error']}")

                    return VerificationResult(
                        verified=data.get("result", False),
                        expiration_date=data.get("expirationDate"),
                        verification_type=verification_type,
                        network=self.network
                    )
                else:
                    # Try to get error details from response
                    try:
                        error_data = await response.json()
                        error_msg = error_data.get("error", f"HTTP {response.status}")
                    except:
                        error_msg = f"HTTP {response.status}"

                    logger.warning(f"{verification_type.value} check returned {response.status} for {address}: {error_msg}")
                    raise ValueError(f"Holonym API returned {response.status}: {error_msg}")

        except asyncio.TimeoutError:
            logger.error(f"{verification_type.value} check timed out for {address}")
            raise ValueError(f"Verification check timed out for {address}")
        except ValueError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            logger.error(f"{verification_type.value} check failed for {address}: {e}")
            raise ValueError(f"Verification check failed: {str(e)}")

    def _is_valid_ethereum_address(self, address: str) -> bool:
        """Validate Ethereum address format."""
        return (
            isinstance(address, str) and
            address.startswith("0x") and
            len(address) == 42 and
            all(c in "0123456789abcdefABCDEF" for c in address[2:])
        )


# Convenience functions for synchronous usage

def check_address_sync(address: str, network: NetworkType = NetworkType.OPTIMISM) -> PassportStatus:
    """
    Synchronous wrapper for checking an address verification status.

    Args:
        address: Blockchain address to verify
        network: Network to check on (default: Optimism)

    Returns:
        PassportStatus with full verification details
    """
    async def _check():
        async with PassportClient(network) as client:
            return await client.get_full_status(address)

    return asyncio.run(_check())


def batch_check_sync(addresses: typing.List[str], network: NetworkType = NetworkType.OPTIMISM) -> typing.Dict[str, PassportStatus]:
    """
    Synchronous batch check for multiple addresses.

    Args:
        addresses: List of addresses to verify
        network: Network to check on (default: Optimism)

    Returns:
        Dictionary mapping addresses to their PassportStatus
    """
    async def _batch_check():
        async with PassportClient(network) as client:
            tasks = [client.get_full_status(addr) for addr in addresses]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            status_map = {}
            for addr, result in zip(addresses, results):
                if isinstance(result, PassportStatus):
                    status_map[addr] = result
                else:
                    logger.error(f"Verification failed for {addr}: {result}")
                    status_map[addr] = PassportStatus(address=addr, network=network)

            return status_map

    return asyncio.run(_batch_check())