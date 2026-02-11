"""
😐 Target Validation: Comprehensive target scope validation.

Validates targets before they reach containment or execution.
Catches dangerous patterns, overly broad targets, and the
ever-present threat of someone typing 0.0.0.0.

📺 The History of Accidental Targets:
  Every major security incident involving pentest tools can be
  traced to one of two problems: wrong target or wrong mode.
  This module exists to prevent the first. See confirmation.py
  for the second.

🌑 Target validation is defense-in-depth for target selection.
   Even if containment would catch a bad target, we want to
   catch it HERE, with a clear error message, before it gets
   anywhere near the execution layer.
"""

from __future__ import annotations

import ipaddress
import logging
import re
from dataclasses import dataclass, field
from typing import Any


logger = logging.getLogger(__name__)


# ============================================================================
# Errors
# ============================================================================


class TargetValidationError(Exception):
    """
    A target failed validation.

    🌑 This is Harold saving you from yourself.
    """

    def __init__(
        self,
        message: str,
        target: str = "",
        severity: str = "error",
    ) -> None:
        self.target = target
        self.severity = severity  # "warning", "error", "critical"
        super().__init__(message)


# ============================================================================
# Target Scope
# ============================================================================


@dataclass
class TargetScope:
    """
    Defines the authorized scope of targets for an operation.

    😐 Before you point the tool at anything, declare what
    you're pointing it at. Harold reviews the list.
    """

    # IP/CIDR targets
    ip_targets: list[str] = field(default_factory=list)

    # Domain/URL targets (for search/scrub operations)
    domain_targets: list[str] = field(default_factory=list)

    # Platform-specific targets (for standard mode)
    platform_targets: dict[str, list[str]] = field(default_factory=dict)

    # Free-form identifiers (emails, usernames, etc.)
    identity_targets: list[str] = field(default_factory=list)

    # Scope metadata
    declared_by: str = ""
    declared_at: float = 0.0
    authorization_reference: str = ""  # Reference to authorization document
    max_results_per_target: int = 100

    @property
    def total_targets(self) -> int:
        """Total number of declared targets across all categories."""
        return (
            len(self.ip_targets)
            + len(self.domain_targets)
            + sum(len(v) for v in self.platform_targets.values())
            + len(self.identity_targets)
        )

    @property
    def has_ip_targets(self) -> bool:
        """Check if scope includes network targets."""
        return bool(self.ip_targets)


# ============================================================================
# Target Validator
# ============================================================================


class TargetValidator:
    """
    😐 Validates targets for safety and sanity before any operations.

    Checks for:
    - Invalid IP/CIDR syntax
    - Dangerously broad targets (0.0.0.0/0, ::/0, etc.)
    - Reserved/special-purpose addresses
    - Suspiciously broad CIDR ranges
    - Empty/null targets
    - Duplicate targets
    - Target count limits

    📺 Harold checks IDs at the door. No exceptions.

    🌑 This validator is intentionally paranoid. False positives
    (blocking a valid target) are vastly preferable to false
    negatives (allowing a destructive target through).
    """

    # IP patterns that are ALWAYS dangerous
    NUCLEAR_PATTERNS: list[str] = [
        "0.0.0.0",
        "::",
        "0.0.0.0/0",
        "::/0",
        "0.0.0.0/1",
        "128.0.0.0/1",
        "::/1",
        "8000::/1",
    ]

    # Domain patterns that are always suspicious
    SUSPICIOUS_DOMAINS: list[str] = [
        "*",
        "*.com",
        "*.net",
        "*.org",
        "*.io",
        "*.gov",
        "*.edu",
        "*.mil",
        "localhost",
    ]

    # Maximum targets per operation (can be overridden)
    DEFAULT_MAX_TARGETS = 100

    def __init__(
        self,
        max_targets: int = DEFAULT_MAX_TARGETS,
        allow_private_ranges: bool = True,
        strict_mode: bool = False,
    ) -> None:
        self._max_targets = max_targets
        self._allow_private = allow_private_ranges
        self._strict = strict_mode
        self._warnings: list[str] = []
        self._errors: list[str] = []

    # ========================================================================
    # Public API
    # ========================================================================

    def validate_scope(self, scope: TargetScope) -> bool:
        """
        Validate an entire target scope.

        Args:
            scope: The target scope to validate

        Returns:
            True if all targets pass validation

        Raises:
            TargetValidationError: On critical validation failure
        """
        self._warnings.clear()
        self._errors.clear()

        # Check total target count
        if scope.total_targets == 0:
            raise TargetValidationError(
                "😐 Empty target scope. Nothing to do.",
                severity="error",
            )

        if scope.total_targets > self._max_targets:
            raise TargetValidationError(
                f"🌑 Target count ({scope.total_targets}) exceeds maximum "
                f"({self._max_targets}). Break into smaller operations.",
                severity="error",
            )

        # Validate each category
        for ip_target in scope.ip_targets:
            self.validate_ip_target(ip_target)

        for domain in scope.domain_targets:
            self.validate_domain_target(domain)

        for identities in scope.identity_targets:
            self.validate_identity_target(identities)

        # Check for duplicates
        self._check_duplicates(scope)

        return True

    def validate_ip_target(self, target: str) -> bool:
        """
        Validate a single IP/CIDR target.

        Raises:
            TargetValidationError: If target is dangerous or invalid
        """
        target = target.strip()

        if not target:
            raise TargetValidationError(
                "😐 Empty target string. Harold needs something to work with.",
                target=target,
                severity="error",
            )

        # Nuclear pattern check (these are ALWAYS blocked)
        self._check_nuclear_patterns(target)

        # Parse and validate
        try:
            network = ipaddress.ip_network(target, strict=False)
        except ValueError as e:
            raise TargetValidationError(
                f"🌑 Invalid IP/CIDR: '{target}' — {e}",
                target=target,
                severity="error",
            ) from e

        # Check for unspecified address
        if network.network_address.is_unspecified:
            raise TargetValidationError(
                f"🌑🌑🌑 Target '{target}' is the unspecified address (0.0.0.0 or ::).\n"
                f"This would match ALL traffic. BLOCKED.\n"
                f"😐 Harold caught this. You're welcome.",
                target=target,
                severity="critical",
            )

        # CIDR breadth warning
        if isinstance(network, ipaddress.IPv4Network) and network.prefixlen < 16:
            raise TargetValidationError(
                f"🌑 Target '{target}' is very broad (/{network.prefixlen}, "
                f"{network.num_addresses:,} addresses).\n"
                f"Minimum recommended: /16 for pentest targets.",
                target=target,
                severity="error",
            )

        if isinstance(network, ipaddress.IPv6Network) and network.prefixlen < 48:
            raise TargetValidationError(
                f"🌑 IPv6 target '{target}' is very broad (/{network.prefixlen}).\n"
                f"Minimum recommended: /48 for pentest targets.",
                target=target,
                severity="error",
            )

        # Private range check (warning only, not blocking by default)
        if network.is_private and not self._allow_private:
            raise TargetValidationError(
                f"😐 Target '{target}' is a private range. "
                f"Set allow_private_ranges=True if this is intentional.",
                target=target,
                severity="warning",
            )

        # Loopback check
        if network.is_loopback:
            self._warnings.append(
                f"⚠️ Target '{target}' is a loopback address. Are you pentesting yourself? 😐"
            )

        # Multicast check
        if network.is_multicast:
            raise TargetValidationError(
                f"🌑 Target '{target}' is a multicast address. "
                f"Multicast targets are not valid for erasure operations.",
                target=target,
                severity="error",
            )

        return True

    def validate_domain_target(self, domain: str) -> bool:
        """
        Validate a domain target.

        Raises:
            TargetValidationError: If domain is suspicious
        """
        domain = domain.strip().lower()

        if not domain:
            raise TargetValidationError(
                "😐 Empty domain target.",
                severity="error",
            )

        # Check suspicious wildcards
        for pattern in self.SUSPICIOUS_DOMAINS:
            if domain == pattern or domain == pattern.lstrip("*."):
                raise TargetValidationError(
                    f"🌑 Domain target '{domain}' matches suspicious pattern '{pattern}'.\n"
                    f"Wildcard TLD targeting is not allowed.\n"
                    f"😐 Be more specific.",
                    target=domain,
                    severity="critical",
                )

        # Basic domain format validation
        if not re.match(
            r"^[a-z0-9]([a-z0-9\-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9\-]*[a-z0-9])?)*$", domain
        ):
            # Allow URLs too
            if not domain.startswith(("http://", "https://")):
                self._warnings.append(
                    f"⚠️ Domain '{domain}' has unusual format. Verify it's correct."
                )

        return True

    def validate_identity_target(self, identity: str) -> bool:
        """
        Validate an identity target (email, username, etc.).

        Basic sanity checks — not format validation.
        """
        identity = identity.strip()

        if not identity:
            raise TargetValidationError(
                "😐 Empty identity target.",
                severity="error",
            )

        if len(identity) < 2:
            raise TargetValidationError(
                f"😐 Identity target '{identity}' is suspiciously short.",
                target=identity,
                severity="warning",
            )

        if len(identity) > 500:
            raise TargetValidationError(
                f"🌑 Identity target is too long ({len(identity)} chars). "
                f"That's not an identity, that's a novel.",
                target=identity[:50] + "...",
                severity="error",
            )

        return True

    # ========================================================================
    # Internal Checks
    # ========================================================================

    def _check_nuclear_patterns(self, target: str) -> None:
        """
        Check against nuclear (always-blocked) patterns.

        🌑 These patterns would target everything. NEVER allowed.
        """
        normalized = target.strip().lower()
        for pattern in self.NUCLEAR_PATTERNS:
            if normalized == pattern.lower():
                raise TargetValidationError(
                    f"🌑🌑🌑 NUCLEAR TARGET BLOCKED 🌑🌑🌑\n"
                    f"Target '{target}' matches nuclear pattern '{pattern}'.\n"
                    f"This would target {'the entire internet' if '/' in pattern else 'all addresses'}.\n"
                    f"This is NEVER allowed, regardless of mode.\n\n"
                    f"😐 Harold stopped this. Harold always stops this.\n"
                    f"🌑 If you need to target everything, you've made a mistake.",
                    target=target,
                    severity="critical",
                )

    def _check_duplicates(self, scope: TargetScope) -> None:
        """Check for duplicate targets within the scope."""
        all_targets = scope.ip_targets + scope.domain_targets + scope.identity_targets
        seen: set[str] = set()
        for t in all_targets:
            normalized = t.strip().lower()
            if normalized in seen:
                self._warnings.append(
                    f"⚠️ Duplicate target detected: '{t}' — will be processed once."
                )
            seen.add(normalized)

    # ========================================================================
    # Results
    # ========================================================================

    @property
    def warnings(self) -> list[str]:
        """Validation warnings (non-blocking)."""
        return list(self._warnings)

    @property
    def errors(self) -> list[str]:
        """Validation errors encountered."""
        return list(self._errors)

    def get_report(self) -> dict[str, Any]:
        """
        Get a validation report summary.

        😐 Harold's report card for your target list.
        """
        return {
            "warnings_count": len(self._warnings),
            "errors_count": len(self._errors),
            "warnings": self._warnings,
            "errors": self._errors,
        }
