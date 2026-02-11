"""
😐 EraserHead Operating Modes: Safety levels for different use cases.

Three modes, three levels of paranoia, three confirmation ceremonies.

📺 The Three Harolds:
  1. STANDARD Harold: Compliant, legal, careful. Files GDPR requests.
  2. CONTAINED Harold: Paranoid pentester. Triple-confirms everything.
     Locked to a subnet. Cannot escape. Like Harold in a stock photo studio.
  3. UNRESTRICTED Harold: All guardrails off. Airgapped recommended.
     This Harold has been authorized to break things. Carefully.

🌑 Mode escalation requires increasingly absurd levels of confirmation
   because the consequences of accidental deployment escalate
   proportionally. Harold has seen what happens when test tools
   reach production. Harold doesn't sleep well anymore.
"""

from eraserhead.modes.base import (
    ModeConfig,
    ModeViolation,
    OperatingMode,
    SafetyLevel,
)
from eraserhead.modes.confirmation import (
    ConfirmationCeremony,
    ConfirmationResult,
    ConfirmationStep,
)
from eraserhead.modes.containment import (
    ContainmentConfig,
    ContainmentViolation,
    NetworkContainment,
)
from eraserhead.modes.target_validation import (
    TargetScope,
    TargetValidationError,
    TargetValidator,
)


__all__ = [
    "ConfirmationCeremony",
    "ConfirmationResult",
    "ConfirmationStep",
    "ContainmentConfig",
    "ContainmentViolation",
    "ModeConfig",
    "ModeViolation",
    "NetworkContainment",
    "OperatingMode",
    "SafetyLevel",
    "TargetScope",
    "TargetValidationError",
    "TargetValidator",
]
