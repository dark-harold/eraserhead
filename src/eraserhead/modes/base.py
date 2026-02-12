"""
😐 Operating Mode Definitions: The three faces of Harold.

Defines the operating modes that control what EraserHead is allowed to do,
how aggressively it does it, and how many times Harold needs to confirm
before proceeding.

🌑 Mode selection is NOT a configuration preference — it's a safety
   classification. Getting this wrong has legal consequences.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from typing import Any


# ============================================================================
# Safety & Mode Enums
# ============================================================================


class SafetyLevel(IntEnum):
    """
    Safety classification levels.

    Higher number = more restrictive safety.

    😐 Like DEFCON but for privacy tools.
    """

    UNRESTRICTED = 1  # All guardrails off, airgap recommended
    CONTAINED = 3  # Pentest mode, subnet-locked, triple confirm
    STANDARD = 5  # Normal operation, full compliance


class OperatingMode(StrEnum):
    """
    The three operating modes of EraserHead.

    Each mode has different:
    - Allowed actions
    - Confirmation requirements
    - Network restrictions
    - Compliance enforcement
    """

    STANDARD = "standard"
    CONTAINED_PENTEST = "contained_pentest"
    UNRESTRICTED_PENTEST = "unrestricted_pentest"


# ============================================================================
# Mode Configuration
# ============================================================================


@dataclass
class ModeConfig:
    """
    Configuration for an operating mode.

    😐 This dataclass determines how much havoc Harold is
    authorized to wreak. Choose wisely.

    🌑 UNRESTRICTED mode config should only exist in memory,
    never serialized to disk. If someone finds it in a config
    file, something has gone very wrong.
    """

    mode: OperatingMode = OperatingMode.STANDARD
    safety_level: SafetyLevel = SafetyLevel.STANDARD

    # Confirmation requirements
    confirmations_required: int = 1  # STANDARD=1, CONTAINED=3, UNRESTRICTED=5
    require_explicit_acknowledgment: bool = False
    require_scope_declaration: bool = False
    require_legal_attestation: bool = True  # 😐 Always True for STANDARD

    # Compliance enforcement
    enforce_compliance: bool = True  # STANDARD=True, PENTEST modes=configurable
    compliance_frameworks: list[str] = field(default_factory=lambda: ["GDPR", "CCPA"])
    block_on_compliance_failure: bool = True

    # Network restrictions
    network_restricted: bool = False  # Only True for CONTAINED mode
    allowed_cidrs: list[str] = field(default_factory=list)
    denied_cidrs: list[str] = field(default_factory=list)
    gateway_boundary: str | None = None  # IP/gateway that MUST NOT be crossed
    require_airgap_attestation: bool = False  # Only True for UNRESTRICTED

    # Behavioral limits
    allow_aggressive_scrub: bool = False  # Bypass rate limits, parallel requests
    allow_direct_deletion: bool = False  # Skip formal request process
    allow_cache_poisoning: bool = False  # 🌑 Only UNRESTRICTED, and even then...
    dry_run_default: bool = True  # STANDARD defaults to dry-run

    # Session management
    session_timeout_minutes: int = 60  # Auto-expire mode after timeout
    max_targets: int = 10  # Max simultaneous targets
    activated_at: float = 0.0
    activated_by: str = ""
    activation_reason: str = ""

    # Audit
    audit_all_actions: bool = True
    require_post_session_report: bool = False

    def is_expired(self) -> bool:
        """Check if the mode session has expired."""
        if self.activated_at == 0.0:
            return False  # Never activated
        elapsed = (time.time() - self.activated_at) / 60.0
        return elapsed > self.session_timeout_minutes

    @classmethod
    def standard(cls) -> ModeConfig:
        """
        Create standard (compliant) mode configuration.

        😐 The default. Legal. Safe. Boring. Exactly how Harold likes it.
        """
        return cls(
            mode=OperatingMode.STANDARD,
            safety_level=SafetyLevel.STANDARD,
            confirmations_required=1,
            require_explicit_acknowledgment=False,
            require_scope_declaration=False,
            require_legal_attestation=True,
            enforce_compliance=True,
            compliance_frameworks=["GDPR", "CCPA"],
            block_on_compliance_failure=True,
            network_restricted=False,
            allow_aggressive_scrub=False,
            allow_direct_deletion=False,
            dry_run_default=True,
            session_timeout_minutes=480,  # 8 hours
            max_targets=10,
            audit_all_actions=True,
            require_post_session_report=False,
        )

    @classmethod
    def contained_pentest(
        cls,
        allowed_cidrs: list[str],
        gateway_boundary: str | None = None,
        denied_cidrs: list[str] | None = None,
    ) -> ModeConfig:
        """
        Create contained pentest mode configuration.

        Requires explicit CIDR ranges. Cannot operate outside them.

        😐 Harold is locked in a subnet. He can break things,
        but only within his enclosure. Like a zoo, but for packets.

        🌑 Triple confirmation required EVERY TIME this mode is initiated.
        """
        if not allowed_cidrs:
            raise ModeViolation(
                "🌑 CONTAINED mode requires at least one allowed CIDR range. "
                "Harold doesn't do 'everywhere is allowed.'"
            )

        return cls(
            mode=OperatingMode.CONTAINED_PENTEST,
            safety_level=SafetyLevel.CONTAINED,
            confirmations_required=3,
            require_explicit_acknowledgment=True,
            require_scope_declaration=True,
            require_legal_attestation=True,
            enforce_compliance=False,  # Pentest bypasses normal compliance
            compliance_frameworks=[],
            block_on_compliance_failure=False,
            network_restricted=True,
            allowed_cidrs=allowed_cidrs,
            denied_cidrs=denied_cidrs
            or [],  # 🌑 Specific denials within the allowed range; _check_allowed handles the rest,
            gateway_boundary=gateway_boundary,
            allow_aggressive_scrub=True,
            allow_direct_deletion=True,
            dry_run_default=False,
            session_timeout_minutes=120,  # 2 hours max
            max_targets=50,
            audit_all_actions=True,
            require_post_session_report=True,
        )

    @classmethod
    def unrestricted_pentest(
        cls,
        allowed_cidrs: list[str],
        activation_reason: str = "",
    ) -> ModeConfig:
        """
        Create unrestricted pentest mode configuration.

        🌑🌑🌑 HERE BE DRAGONS 🌑🌑🌑

        This mode removes most guardrails. It is designed for:
        - Authorized penetration testing
        - Educational/lab environments
        - Airgapped networks

        EXTREMELY RECOMMENDED to use ONLY in airgapped environments.

        Five-layer confirmation ceremony required.
        Targets MUST still be explicitly declared (no blanket targeting).

        😐 Harold wishes you weren't reading this constructor.
        """
        if not allowed_cidrs:
            raise ModeViolation(
                "🌑 Even UNRESTRICTED mode requires explicit target CIDRs. "
                "Harold draws the line at 'delete everything everywhere.'"
            )

        return cls(
            mode=OperatingMode.UNRESTRICTED_PENTEST,
            safety_level=SafetyLevel.UNRESTRICTED,
            confirmations_required=5,
            require_explicit_acknowledgment=True,
            require_scope_declaration=True,
            require_legal_attestation=True,  # Still required — authorization matters
            require_airgap_attestation=True,
            enforce_compliance=False,
            compliance_frameworks=[],
            block_on_compliance_failure=False,
            network_restricted=True,  # 🌑 Still restricted to declared CIDRs
            allowed_cidrs=allowed_cidrs,
            denied_cidrs=[],  # Explicit allow-list only
            gateway_boundary=None,
            allow_aggressive_scrub=True,
            allow_direct_deletion=True,
            allow_cache_poisoning=True,
            dry_run_default=False,
            session_timeout_minutes=60,  # 1 hour max — short leash
            max_targets=100,
            audit_all_actions=True,
            require_post_session_report=True,
            activation_reason=activation_reason,
        )


# ============================================================================
# Mode Violation
# ============================================================================


class ModeViolation(Exception):
    """
    Raised when an operation violates the current operating mode's constraints.

    🌑 This exception means Harold caught you trying something
    you're not authorized to do. Harold is disappointed.
    """

    def __init__(self, message: str, mode: OperatingMode | None = None) -> None:
        self.mode = mode
        super().__init__(message)


# ============================================================================
# Mode Manager
# ============================================================================


class ModeManager:
    """
    😐 Manages the active operating mode and enforces its constraints.

    Only one mode can be active at a time. Mode transitions require
    the appropriate confirmation ceremony.

    🌑 The ModeManager is the adult in the room. It says "no" a lot.
    """

    def __init__(self) -> None:
        self._config = ModeConfig.standard()
        self._activation_history: list[dict[str, Any]] = []
        self._active = True

    @property
    def current_mode(self) -> OperatingMode:
        """The currently active operating mode."""
        return self._config.mode

    @property
    def config(self) -> ModeConfig:
        """Current mode configuration (read-only view)."""
        return self._config

    @property
    def safety_level(self) -> SafetyLevel:
        """Current safety level."""
        return self._config.safety_level

    @property
    def is_standard(self) -> bool:
        """Check if in standard (compliant) mode."""
        return self._config.mode == OperatingMode.STANDARD

    @property
    def is_pentest(self) -> bool:
        """Check if in any pentest mode."""
        return self._config.mode in (
            OperatingMode.CONTAINED_PENTEST,
            OperatingMode.UNRESTRICTED_PENTEST,
        )

    @property
    def is_unrestricted(self) -> bool:
        """Check if in unrestricted pentest mode."""
        return self._config.mode == OperatingMode.UNRESTRICTED_PENTEST

    def activate_mode(self, config: ModeConfig, operator: str = "unknown") -> None:
        """
        Activate a new operating mode.

        This should only be called AFTER the confirmation ceremony
        has been completed successfully.

        Args:
            config: The mode configuration to activate
            operator: Who is activating this mode
        """
        config.activated_at = time.time()
        config.activated_by = operator

        self._activation_history.append(
            {
                "previous_mode": self._config.mode,
                "new_mode": config.mode,
                "activated_at": config.activated_at,
                "activated_by": operator,
                "reason": config.activation_reason,
            }
        )

        self._config = config
        self._active = True

    def deactivate(self) -> ModeConfig:
        """
        Deactivate current mode and return to STANDARD.

        Returns the previous mode config for audit purposes.
        """
        previous = self._config
        self._config = ModeConfig.standard()
        self._active = True

        self._activation_history.append(
            {
                "previous_mode": previous.mode,
                "new_mode": OperatingMode.STANDARD,
                "activated_at": time.time(),
                "activated_by": "deactivation",
                "reason": "Mode deactivated, returning to standard",
            }
        )

        return previous

    def check_expired(self) -> bool:
        """
        Check if the current mode has expired.

        If expired, automatically returns to STANDARD mode.

        Returns:
            True if mode was expired and reset
        """
        if self._config.is_expired():
            self.deactivate()
            return True
        return False

    def enforce(self, action: str, target: str | None = None) -> None:
        """
        Enforce mode constraints for an action.

        Args:
            action: What is being attempted
            target: Optional target of the action

        Raises:
            ModeViolation: If the action violates mode constraints
        """
        # Check expiration first
        if self.check_expired():
            raise ModeViolation(
                f"😐 Mode session expired. Returned to STANDARD mode. "
                f"Action '{action}' blocked pending re-authorization.",
                mode=OperatingMode.STANDARD,
            )

        mode = self._config

        # Standard mode restrictions
        if mode.mode == OperatingMode.STANDARD:
            if action in ("aggressive_scrub", "direct_deletion", "cache_poison"):
                raise ModeViolation(
                    f"🌑 Action '{action}' not permitted in STANDARD mode. "
                    f"Harold does things by the book.",
                    mode=mode.mode,
                )

        # All pentest modes require explicit targets
        if mode.mode in (OperatingMode.CONTAINED_PENTEST, OperatingMode.UNRESTRICTED_PENTEST):
            if target is None:
                raise ModeViolation(
                    f"🌑 Pentest action '{action}' requires an explicit target. "
                    f"Harold doesn't do blanket operations.",
                    mode=mode.mode,
                )

    def get_history(self) -> list[dict[str, Any]]:
        """Get mode activation history for audit."""
        return list(self._activation_history)
