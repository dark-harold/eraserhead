"""
😐 Network Containment: Subnet restrictions for pentest modes.

Validates that all targets fall within authorized CIDR ranges.
Enforces gateway boundaries. Prevents accidental internet exposure.

📺 The Containment Story:
  In 2024, a security researcher accidentally pointed their pentest
  tool at production infrastructure instead of the lab. The tool
  dutifully deleted 14,000 customer records. Nobody was happy.

  Harold learned from this. Harold built containment.

🌑 Network containment is the difference between "authorized test"
   and "felony." Harold takes this very seriously.
"""

from __future__ import annotations

import ipaddress
import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


logger = logging.getLogger(__name__)


# ============================================================================
# Containment Errors
# ============================================================================


class ContainmentViolation(Exception):
    """
    Raised when a target extends beyond authorized network boundaries.

    🌑 This exception means you almost touched something you shouldn't.
    Harold intercepted it. You're welcome.
    """

    def __init__(
        self,
        message: str,
        target: str = "",
        allowed_ranges: list[str] | None = None,
    ) -> None:
        self.target = target
        self.allowed_ranges = allowed_ranges or []
        super().__init__(message)


# ============================================================================
# Containment Configuration
# ============================================================================


@dataclass
class ContainmentConfig:
    """
    Network containment rules for pentest modes.

    😐 Think of this as an invisible fence for your pentest tools.
    Cross it and everything stops. Immediately.
    """

    # Allowed target ranges (whitelist)
    allowed_cidrs: list[str] = field(default_factory=list)

    # Explicitly denied ranges (takes precedence over allowed)
    denied_cidrs: list[str] = field(default_factory=list)

    # Gateway boundary — traffic MUST NOT route past this IP
    gateway_boundary: str | None = None

    # Maximum CIDR prefix length allowed (prevents overly broad targeting)
    # /8 = 16M IPs — way too broad for contained pentest
    min_prefix_length_v4: int = 16  # No broader than /16 (65k IPs)
    min_prefix_length_v6: int = 48  # No broader than /48

    # Dangerous ranges that are ALWAYS denied regardless of config
    # 🌑 These are never valid pentest targets unless you own the internet
    always_denied: list[str] = field(
        default_factory=lambda: [
            "0.0.0.0/8",  # "This" network
            "10.0.0.0/8",  # *Conditionally* denied — must be explicitly allowed
            "127.0.0.0/8",  # Loopback
            "169.254.0.0/16",  # Link-local
            "224.0.0.0/4",  # Multicast
            "255.255.255.255/32",  # Broadcast
            "::/128",  # IPv6 unspecified
            "::1/128",  # IPv6 loopback
            "fe80::/10",  # IPv6 link-local
            "ff00::/8",  # IPv6 multicast
        ]
    )

    # Ultra-dangerous: blanket ranges that are NEVER allowed
    # Even if someone tries to add them to allowed_cidrs
    nuclear_denied: list[str] = field(
        default_factory=lambda: [
            "0.0.0.0/0",  # 🌑 THE ENTIRE INTERNET. NO.
            "::/0",  # 🌑 THE ENTIRE IPv6 INTERNET. ALSO NO.
            "0.0.0.0/1",  # Half the internet is still too much
            "128.0.0.0/1",  # The other half
            "::/1",  # Half of IPv6
            "8000::/1",  # Other half of IPv6
        ]
    )


# ============================================================================
# Network Containment Engine
# ============================================================================


class NetworkContainment:
    """
    😐 Validates that all network targets fall within authorized boundaries.

    The containment engine is the last line of defense between
    a pentest tool and the public internet. It validates:

    1. Target IPs/CIDRs are within allowed ranges
    2. No target falls in denied ranges
    3. No target is in nuclear-denied ranges (ever)
    4. CIDR ranges aren't too broad (no /0 or /1)
    5. Gateway boundaries are respected

    📺 This is Harold standing at the door of the subnet, checking IDs.

    🌑 Every validation failure is logged. Every attempt to bypass
    containment is recorded with full context. Harold remembers.
    """

    def __init__(self, config: ContainmentConfig) -> None:
        self._config = config
        self._violations: list[dict[str, Any]] = []

        # Pre-parse networks for efficiency
        self._allowed_networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        self._denied_networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        self._always_denied_networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        self._nuclear_denied_networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []

        self._parse_networks()

    def _parse_networks(self) -> None:
        """Parse all CIDR strings into network objects."""
        for cidr in self._config.allowed_cidrs:
            try:
                self._allowed_networks.append(ipaddress.ip_network(cidr, strict=False))
            except ValueError as e:
                logger.error("Invalid allowed CIDR '%s': %s", cidr, e)

        for cidr in self._config.denied_cidrs:
            try:
                self._denied_networks.append(ipaddress.ip_network(cidr, strict=False))
            except ValueError as e:
                logger.error("Invalid denied CIDR '%s': %s", cidr, e)

        for cidr in self._config.always_denied:
            try:
                self._always_denied_networks.append(ipaddress.ip_network(cidr, strict=False))
            except ValueError as e:
                logger.error("Invalid always-denied CIDR '%s': %s", cidr, e)

        for cidr in self._config.nuclear_denied:
            try:
                self._nuclear_denied_networks.append(ipaddress.ip_network(cidr, strict=False))
            except ValueError as e:
                logger.error("Invalid nuclear-denied CIDR '%s': %s", cidr, e)

    # ========================================================================
    # Public Validation API
    # ========================================================================

    def validate_target(self, target: str) -> bool:
        """
        Validate a single IP address or CIDR range against containment rules.

        Args:
            target: IP address or CIDR notation string

        Returns:
            True if the target is within allowed boundaries

        Raises:
            ContainmentViolation: If the target violates containment
        """
        try:
            # Try as network first (handles both IPs and CIDRs)
            network = ipaddress.ip_network(target, strict=False)
        except ValueError as e:
            raise ContainmentViolation(
                f"🌑 Invalid target address/CIDR: '{target}' — {e}",
                target=target,
            ) from e

        # Check 1: Nuclear denial (absolute, no exceptions)
        self._check_nuclear_denial(target, network)

        # Check 2: CIDR breadth check (prevent overly broad targets)
        self._check_cidr_breadth(target, network)

        # Check 3: Always-denied ranges (unless explicitly allowed)
        self._check_always_denied(target, network)

        # Check 4: Explicit denial list (takes precedence over allowed)
        self._check_explicit_denial(target, network)

        # Check 5: Must be within allowed ranges
        self._check_allowed(target, network)

        # Check 6: Gateway boundary
        self._check_gateway_boundary(target, network)

        return True

    def validate_targets(self, targets: list[str]) -> dict[str, bool | str]:
        """
        Validate multiple targets. Returns results for each.

        Does NOT raise — returns a dict of target → True/error_message.

        😐 Batch validation for the organized pentest.
        """
        results: dict[str, bool | str] = {}
        for target in targets:
            try:
                self.validate_target(target)
                results[target] = True
            except ContainmentViolation as e:
                results[target] = str(e)
                self._record_violation(target, str(e))
        return results

    def is_target_safe(self, target: str) -> bool:
        """
        Quick boolean check — does NOT raise.

        Returns True if target is within containment, False otherwise.
        """
        try:
            return self.validate_target(target)
        except ContainmentViolation:
            return False

    # ========================================================================
    # Validation Steps
    # ========================================================================

    def _check_nuclear_denial(
        self,
        target: str,
        network: ipaddress.IPv4Network | ipaddress.IPv6Network,
    ) -> None:
        """
        🌑🌑🌑 NUCLEAR CHECK: Catch attempts to target the entire internet.

        These ranges are NEVER valid targets, regardless of configuration.
        If someone adds 0.0.0.0/0 to allowed_cidrs, this still blocks it.
        """
        for nuclear in self._nuclear_denied_networks:
            if network == nuclear or (
                network.version == nuclear.version and network.supernet_of(nuclear)
            ):
                msg = (
                    f"🌑🌑🌑 NUCLEAR CONTAINMENT VIOLATION 🌑🌑🌑\n"
                    f"Target '{target}' matches nuclear-denied range {nuclear}.\n"
                    f"This would target {'the entire internet' if str(nuclear) in ('0.0.0.0/0', '::/0') else 'an unacceptably broad range'}.\n"
                    f"This is NEVER allowed, regardless of configuration.\n"
                    f"😐 Harold is watching. Harold is disappointed."
                )
                self._record_violation(target, msg)
                raise ContainmentViolation(
                    msg,
                    target=target,
                    allowed_ranges=[str(n) for n in self._allowed_networks],
                )

    def _check_cidr_breadth(
        self,
        target: str,
        network: ipaddress.IPv4Network | ipaddress.IPv6Network,
    ) -> None:
        """Ensure CIDR ranges aren't too broad."""
        if isinstance(network, ipaddress.IPv4Network):
            min_prefix = self._config.min_prefix_length_v4
        else:
            min_prefix = self._config.min_prefix_length_v6

        if network.prefixlen < min_prefix:
            host_count = network.num_addresses
            msg = (
                f"🌑 CIDR range too broad: '{target}' (/{network.prefixlen}) "
                f"covers {host_count:,} addresses.\n"
                f"Minimum prefix length: /{min_prefix}.\n"
                f"😐 Harold doesn't do carpet bombing. Be more specific."
            )
            self._record_violation(target, msg)
            raise ContainmentViolation(
                msg,
                target=target,
                allowed_ranges=[str(n) for n in self._allowed_networks],
            )

    def _check_always_denied(
        self,
        target: str,
        network: ipaddress.IPv4Network | ipaddress.IPv6Network,
    ) -> None:
        """Check against always-denied ranges (loopback, multicast, etc.)."""
        for denied in self._always_denied_networks:
            if network.version != denied.version:
                continue

            # Check if target overlaps with denied range
            if network.overlaps(denied):
                # Exception: if the target is explicitly in allowed_cidrs
                explicitly_allowed = any(
                    network.subnet_of(allowed)
                    for allowed in self._allowed_networks
                    if network.version == allowed.version
                )
                if not explicitly_allowed:
                    msg = (
                        f"🌑 Target '{target}' overlaps with reserved range {denied}.\n"
                        f"Add it to allowed_cidrs explicitly if this is intentional."
                    )
                    self._record_violation(target, msg)
                    raise ContainmentViolation(
                        msg,
                        target=target,
                        allowed_ranges=[str(n) for n in self._allowed_networks],
                    )

    def _check_explicit_denial(
        self,
        target: str,
        network: ipaddress.IPv4Network | ipaddress.IPv6Network,
    ) -> None:
        """Check against explicitly denied ranges (takes precedence over allowed)."""
        for denied in self._denied_networks:
            if network.version != denied.version:
                continue
            if network.overlaps(denied):
                msg = (
                    f"🌑 Target '{target}' falls in explicitly denied range {denied}.\n"
                    f"Denied ranges take precedence over allowed ranges.\n"
                    f"😐 Harold says no."
                )
                self._record_violation(target, msg)
                raise ContainmentViolation(
                    msg,
                    target=target,
                    allowed_ranges=[str(n) for n in self._allowed_networks],
                )

    def _check_allowed(
        self,
        target: str,
        network: ipaddress.IPv4Network | ipaddress.IPv6Network,
    ) -> None:
        """Ensure target is within at least one allowed range."""
        if not self._allowed_networks:
            raise ContainmentViolation(
                f"🌑 No allowed CIDR ranges configured. "
                f"Target '{target}' has nowhere to go.\n"
                f"😐 Configure allowed_cidrs before targeting anything.",
                target=target,
            )

        is_allowed = any(
            network.subnet_of(allowed)
            for allowed in self._allowed_networks
            if network.version == allowed.version
        )

        if not is_allowed:
            msg = (
                f"🌑 Target '{target}' is outside all allowed ranges.\n"
                f"Allowed: {[str(n) for n in self._allowed_networks]}\n"
                f"😐 Harold only operates within authorized boundaries."
            )
            self._record_violation(target, msg)
            raise ContainmentViolation(
                msg,
                target=target,
                allowed_ranges=[str(n) for n in self._allowed_networks],
            )

    def _check_gateway_boundary(
        self,
        target: str,
        network: ipaddress.IPv4Network | ipaddress.IPv6Network,
    ) -> None:
        """Ensure target doesn't cross the gateway boundary."""
        if self._config.gateway_boundary is None:
            return

        try:
            gateway = ipaddress.ip_address(self._config.gateway_boundary)
        except ValueError:
            logger.warning("Invalid gateway boundary: %s", self._config.gateway_boundary)
            return

        # If the target network contains the gateway, that's suspicious
        if gateway in network:
            msg = (
                f"🌑 Target '{target}' contains the gateway boundary "
                f"{self._config.gateway_boundary}.\n"
                f"Traffic would route past the gateway. Containment violation.\n"
                f"😐 Harold stops at the border."
            )
            self._record_violation(target, msg)
            raise ContainmentViolation(
                msg,
                target=target,
                allowed_ranges=[str(n) for n in self._allowed_networks],
            )

    # ========================================================================
    # Violation Tracking
    # ========================================================================

    def _record_violation(self, target: str, message: str) -> None:
        """Record a containment violation for audit."""
        import time

        self._violations.append(
            {
                "target": target,
                "message": message,
                "timestamp": time.time(),
                "allowed_cidrs": [str(n) for n in self._allowed_networks],
                "denied_cidrs": [str(n) for n in self._denied_networks],
            }
        )
        logger.warning("CONTAINMENT VIOLATION: %s → %s", target, message[:200])

    @property
    def violations(self) -> list[dict[str, Any]]:
        """Get all recorded violations."""
        return list(self._violations)

    @property
    def violation_count(self) -> int:
        """Number of containment violations recorded."""
        return len(self._violations)

    # ========================================================================
    # Summary
    # ========================================================================

    def summary(self) -> dict[str, Any]:
        """
        Get containment configuration summary.

        😐 Harold's containment report card.
        """
        return {
            "allowed_ranges": [str(n) for n in self._allowed_networks],
            "denied_ranges": [str(n) for n in self._denied_networks],
            "always_denied_count": len(self._always_denied_networks),
            "nuclear_denied_count": len(self._nuclear_denied_networks),
            "gateway_boundary": self._config.gateway_boundary,
            "min_prefix_v4": self._config.min_prefix_length_v4,
            "min_prefix_v6": self._config.min_prefix_length_v6,
            "violations_recorded": len(self._violations),
        }
