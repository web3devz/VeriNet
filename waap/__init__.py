"""
VeriNet WaaP Integration — Wallet-as-a-Person AI agent authentication.

Integrates with Human.tech's WaaP CLI to authenticate AI agents and provide
them with secure wallet capabilities. Authenticated agents receive priority
in the VeriNet subnet consensus.

WaaP Agent Flow:
1. Agent runs `waap-cli signup` to create an authenticated agent account
2. Agent runs `waap-cli login` to establish a session
3. Agent can check status with `waap-cli whoami` and `waap-cli policy get`
4. Authenticated agents get weight boost in Bittensor consensus
5. Agents can sign transactions and messages through the WaaP wallet

This provides AI agents with:
- Secure wallet operations with 2FA and spending limits
- Human-controlled policy management
- Persistent authentication sessions
- Transaction signing capabilities
- Identity verification for subnet participation
"""

import os
import json
import time
import subprocess
import typing
import logging
from pathlib import Path

logger = logging.getLogger("verinet.waap")

# WaaP session directory (where waap-cli stores its session data)
WAAP_DIR = Path.home() / ".waap"
WAAP_SESSION_FILE = WAAP_DIR / "session.json"
WAAP_CONFIG_FILE = WAAP_DIR / "config.json"

# Weight multiplier for authenticated agents
AGENT_WEIGHT_BOOST = 1.3


class WaaPAgent:
    """Represents an authenticated WaaP agent with wallet capabilities."""

    def __init__(
        self,
        email: str,
        wallet_address: str,
        session_active: bool,
        policy: typing.Dict[str, typing.Any],
    ):
        self.email = email
        self.wallet_address = wallet_address
        self.session_active = session_active
        self.policy = policy

    def to_dict(self) -> dict:
        return {
            "email": self.email,
            "wallet_address": self.wallet_address,
            "session_active": self.session_active,
            "policy": self.policy,
        }

    @classmethod
    def from_session_data(cls, data: dict) -> "WaaPAgent":
        return cls(
            email=data.get("email", ""),
            wallet_address=data.get("wallet_address", ""),
            session_active=data.get("session_active", False),
            policy=data.get("policy", {}),
        )


class WaaPClient:
    """
    Client for interacting with the WaaP CLI.

    Provides methods for:
    - Agent account creation (signup)
    - Authentication (login/logout)
    - Session management
    - Policy configuration
    - Transaction signing (future enhancement)
    """

    def __init__(self, hotkey_ss58: str = ""):
        self.hotkey = hotkey_ss58
        self._cli_available: typing.Optional[bool] = None
        self._agent: typing.Optional[WaaPAgent] = None
        WAAP_DIR.mkdir(parents=True, exist_ok=True)

    @property
    def is_authenticated(self) -> bool:
        """Check if the agent is authenticated with WaaP."""
        agent = self.get_agent_info()
        return agent is not None and agent.session_active

    @property
    def cli_available(self) -> bool:
        """Check if waap-cli is installed and accessible."""
        if self._cli_available is None:
            self._cli_available = self._check_cli()
        return self._cli_available

    def get_status(self) -> dict:
        """Return full agent authentication status (for API/UI)."""
        agent = self.get_agent_info()
        return {
            "authenticated": self.is_authenticated,
            "cli_available": self.cli_available,
            "agent": agent.to_dict() if agent else None,
            "boost_multiplier": AGENT_WEIGHT_BOOST if self.is_authenticated else 1.0,
            "waap_dir": str(WAAP_DIR),
            "session_file": str(WAAP_SESSION_FILE),
        }

    def signup(self, email: str, password: str, name: str = "") -> dict:
        """
        Create a new WaaP agent account.

        Args:
            email: Agent email address
            password: Agent password (≥ 8 characters)
            name: Display name (optional, defaults to email prefix)

        Returns:
            dict with success/error info
        """
        if not self.cli_available:
            return {
                "success": False,
                "error": "WaaP CLI not available. Install with: npm install -g @human.tech/waap-cli",
            }

        try:
            cmd = ["npx", "@human.tech/waap-cli", "signup", "-e", email, "-p", password]
            if name:
                cmd.extend(["-n", name])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                # Signup successful, agent should now be logged in
                agent_info = self._fetch_agent_info()
                return {
                    "success": True,
                    "message": "Agent account created and logged in",
                    "agent": agent_info.to_dict() if agent_info else None,
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr.strip() or "Signup failed",
                }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Signup timed out"}
        except FileNotFoundError:
            return {"success": False, "error": "npx not found. Install Node.js 20+"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def login(self, email: str, password: str) -> dict:
        """
        Authenticate with existing WaaP agent credentials.

        Args:
            email: Agent email address
            password: Agent password

        Returns:
            dict with success/error info
        """
        if not self.cli_available:
            return {
                "success": False,
                "error": "WaaP CLI not available. Install with: npm install -g @human.tech/waap-cli",
            }

        try:
            result = subprocess.run(
                ["npx", "@human.tech/waap-cli", "login", "-e", email, "-p", password],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                agent_info = self._fetch_agent_info()
                return {
                    "success": True,
                    "message": "Agent authenticated successfully",
                    "agent": agent_info.to_dict() if agent_info else None,
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr.strip() or "Login failed",
                }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Login timed out"}
        except FileNotFoundError:
            return {"success": False, "error": "npx not found. Install Node.js 20+"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def logout(self) -> dict:
        """Clear the agent session."""
        if not self.cli_available:
            return {"success": False, "error": "WaaP CLI not available"}

        try:
            result = subprocess.run(
                ["npx", "@human.tech/waap-cli", "logout"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            self._agent = None  # Clear cached agent info
            return {"success": True, "message": "Agent logged out"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_agent_info(self) -> typing.Optional[WaaPAgent]:
        """Get current agent information from WaaP CLI."""
        if self._agent is None:
            self._agent = self._fetch_agent_info()
        return self._agent

    def apply_weight_boost(self, weights: typing.List[float], authenticated_uids: typing.Set[int]) -> typing.List[float]:
        """
        Apply weight boost to authenticated agents' scores.
        Authenticated agents get an AGENT_WEIGHT_BOOST multiplier.
        """
        boosted = []
        for i, w in enumerate(weights):
            if i in authenticated_uids:
                boosted.append(w * AGENT_WEIGHT_BOOST)
            else:
                boosted.append(w)

        # Re-normalize so weights sum to 1
        total = sum(boosted)
        if total > 0:
            boosted = [w / total for w in boosted]

        return boosted

    # -- Private methods --

    def _check_cli(self) -> bool:
        """Check if waap-cli is available."""
        try:
            result = subprocess.run(
                ["npx", "@human.tech/waap-cli", "--version"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        try:
            result = subprocess.run(
                ["waap-cli", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return False

    def _fetch_agent_info(self) -> typing.Optional[WaaPAgent]:
        """Fetch current agent info using whoami and policy commands."""
        if not self.cli_available:
            return None

        try:
            # Get wallet address
            whoami_result = subprocess.run(
                ["npx", "@human.tech/waap-cli", "whoami"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if whoami_result.returncode != 0:
                # Not logged in
                return None

            wallet_address = whoami_result.stdout.strip()

            # Get policy info
            policy_result = subprocess.run(
                ["npx", "@human.tech/waap-cli", "policy", "get"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            policy = {}
            if policy_result.returncode == 0:
                try:
                    policy = json.loads(policy_result.stdout)
                except json.JSONDecodeError:
                    # Policy output might not be JSON, parse text
                    policy = {"raw_output": policy_result.stdout.strip()}

            # Get session info for email
            session_result = subprocess.run(
                ["npx", "@human.tech/waap-cli", "session-info"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            email = "unknown"
            if session_result.returncode == 0:
                try:
                    session_data = json.loads(session_result.stdout)
                    email = session_data.get("email", "unknown")
                except json.JSONDecodeError:
                    pass

            return WaaPAgent(
                email=email,
                wallet_address=wallet_address,
                session_active=True,
                policy=policy,
            )

        except Exception as e:
            logger.warning(f"Failed to fetch agent info: {e}")
            return None