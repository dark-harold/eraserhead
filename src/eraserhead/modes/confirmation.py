"""
😐 Confirmation Ceremony: Multi-layer authorization for dangerous modes.

Each operating mode requires a specific confirmation ceremony:
- STANDARD: Single acknowledgment (normal operations)
- CONTAINED_PENTEST: Triple confirmation with scope declaration
- UNRESTRICTED_PENTEST: Five-layer ceremony with airgap attestation

📺 The Confirmation Ceremony:
  Like a nuclear launch requiring two keys turned simultaneously,
  Harold's pentest modes require multiple confirmations from
  different angles. This isn't bureaucracy — it's survival.

🌑 The ceremony is not optional. It cannot be skipped. It cannot
   be automated (by design). If someone bypasses it programmatically,
   the audit log will record that fact for posterity and prosecution.
"""

from __future__ import annotations

import hashlib
import secrets
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


# ============================================================================
# Confirmation Types
# ============================================================================


class ConfirmationStepType(StrEnum):
    """Types of confirmation steps in the ceremony."""

    ACKNOWLEDGE = "acknowledge"  # Simple yes/no acknowledgment
    SCOPE_DECLARATION = "scope_declaration"  # Declare target scope
    LEGAL_ATTESTATION = "legal_attestation"  # Attest legal authorization
    CHALLENGE_RESPONSE = "challenge_response"  # Answer a randomized challenge
    AIRGAP_ATTESTATION = "airgap_attestation"  # Attest airgapped environment
    FINAL_CONFIRMATION = "final_confirmation"  # Type exact confirmation phrase


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class ConfirmationStep:
    """
    A single step in the confirmation ceremony.

    Each step presents a challenge and expects a specific response.
    """

    step_number: int
    step_type: ConfirmationStepType
    prompt: str  # What to show the operator
    expected_response: str | None = None  # Exact expected response (None = any truthy)
    challenge_code: str = ""  # Random code for challenge-response steps
    completed: bool = False
    completed_at: float = 0.0
    response_given: str = ""

    def validate_response(self, response: str) -> bool:
        """Check if the response is valid for this step."""
        if self.expected_response is not None:
            return response.strip() == self.expected_response.strip()
        # For non-exact steps, any non-empty response counts
        return bool(response.strip())


@dataclass
class ConfirmationResult:
    """
    Result of a complete confirmation ceremony.

    😐 Either all steps passed or the ceremony failed.
    There is no partial authorization.
    """

    ceremony_id: str
    mode_requested: str
    all_steps_completed: bool
    steps_completed: int
    steps_total: int
    operator: str = ""
    completed_at: float = 0.0
    failure_reason: str | None = None
    # 🌑 Cryptographic proof of completion (hash of all responses)
    completion_hash: str = ""


# ============================================================================
# Confirmation Ceremony
# ============================================================================


class ConfirmationCeremony:
    """
    😐 Multi-layer confirmation ceremony for mode activation.

    Generates and validates a series of confirmation steps that
    an operator must complete before a dangerous mode is activated.

    The ceremony is:
    - NOT automatable (challenge codes are random)
    - NOT skippable (all steps must complete in order)
    - Time-limited (ceremony expires after timeout)
    - Audited (every attempt is logged)

    📺 This is the most bureaucratic code Harold has ever written.
    It's also the most important. Every line prevents a disaster.

    🌑 The ceremony produces a completion_hash that proves the
    operator completed all steps. This hash is included in the
    audit trail and can be verified independently.
    """

    # Ceremony timeout (minutes) — must complete within this window
    STANDARD_TIMEOUT_MINUTES = 30
    CONTAINED_TIMEOUT_MINUTES = 15
    UNRESTRICTED_TIMEOUT_MINUTES = 10  # 🌑 Urgency is intentional

    def __init__(
        self,
        mode: str,
        operator: str,
        targets: list[str] | None = None,
    ) -> None:
        self._ceremony_id = secrets.token_hex(16)
        self._mode = mode
        self._operator = operator
        self._targets = targets or []
        self._steps: list[ConfirmationStep] = []
        self._started_at = time.time()
        self._completed = False
        self._attempts: list[dict[str, Any]] = []
        self._response_hashes: list[str] = []

        # Generate ceremony steps based on mode
        self._generate_steps()

    @property
    def ceremony_id(self) -> str:
        """Unique ceremony identifier."""
        return self._ceremony_id

    @property
    def steps(self) -> list[ConfirmationStep]:
        """All ceremony steps (read-only)."""
        return list(self._steps)

    @property
    def current_step(self) -> ConfirmationStep | None:
        """The next uncompleted step, or None if ceremony is complete."""
        for step in self._steps:
            if not step.completed:
                return step
        return None

    @property
    def is_complete(self) -> bool:
        """Check if all steps have been completed."""
        return all(s.completed for s in self._steps)

    @property
    def is_expired(self) -> bool:
        """Check if the ceremony has timed out."""
        timeout = self._get_timeout_minutes()
        elapsed = (time.time() - self._started_at) / 60.0
        return elapsed > timeout

    @property
    def progress(self) -> str:
        """Human-readable progress string."""
        completed = sum(1 for s in self._steps if s.completed)
        return f"{completed}/{len(self._steps)} steps completed"

    # ========================================================================
    # Step Generation
    # ========================================================================

    def _generate_steps(self) -> None:
        """Generate confirmation steps based on mode."""
        if self._mode == "standard":
            self._generate_standard_steps()
        elif self._mode == "contained_pentest":
            self._generate_contained_steps()
        elif self._mode == "unrestricted_pentest":
            self._generate_unrestricted_steps()
        else:
            raise ValueError(f"Unknown mode: {self._mode}")

    def _generate_standard_steps(self) -> None:
        """Standard mode: single acknowledgment."""
        self._steps = [
            ConfirmationStep(
                step_number=1,
                step_type=ConfirmationStepType.ACKNOWLEDGE,
                prompt=(
                    "😐 STANDARD MODE ACTIVATION\n"
                    "You are about to initiate digital footprint erasure in STANDARD mode.\n"
                    "All actions will comply with applicable privacy regulations.\n"
                    "Dry-run mode is enabled by default.\n\n"
                    "Type 'I UNDERSTAND' to proceed."
                ),
                expected_response="I UNDERSTAND",
            ),
        ]

    def _generate_contained_steps(self) -> None:
        """
        Contained pentest: triple confirmation with scope declaration.

        😐 Three steps. Three chances to reconsider.
        """
        challenge_code = secrets.token_hex(4).upper()
        target_list = ", ".join(self._targets) if self._targets else "[NO TARGETS DECLARED]"

        self._steps = [
            # Step 1: Explicit acknowledgment
            ConfirmationStep(
                step_number=1,
                step_type=ConfirmationStepType.ACKNOWLEDGE,
                prompt=(
                    "⚠️  CONTAINED PENTEST MODE — CONFIRMATION 1 of 3\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "You are requesting CONTAINED PENTEST mode.\n"
                    "This mode enables:\n"
                    "  • Aggressive scrubbing (rate limits bypassed)\n"
                    "  • Direct deletion (no formal request process)\n"
                    "  • Network operations restricted to declared CIDRs\n\n"
                    "⚠️  All operations are LOGGED and AUDITABLE.\n\n"
                    "Type 'ACTIVATE CONTAINED PENTEST' to proceed."
                ),
                expected_response="ACTIVATE CONTAINED PENTEST",
            ),
            # Step 2: Scope declaration
            ConfirmationStep(
                step_number=2,
                step_type=ConfirmationStepType.SCOPE_DECLARATION,
                prompt=(
                    "⚠️  CONTAINED PENTEST MODE — CONFIRMATION 2 of 3\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"Declared targets: {target_list}\n\n"
                    "Confirm that:\n"
                    "  1. You own or are authorized to test these targets\n"
                    "  2. All targets are within the declared CIDR ranges\n"
                    "  3. No public internet-facing systems are in scope\n\n"
                    "Type 'SCOPE CONFIRMED' to proceed."
                ),
                expected_response="SCOPE CONFIRMED",
            ),
            # Step 3: Challenge-response (anti-automation)
            ConfirmationStep(
                step_number=3,
                step_type=ConfirmationStepType.CHALLENGE_RESPONSE,
                prompt=(
                    "⚠️  CONTAINED PENTEST MODE — CONFIRMATION 3 of 3\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "🌑 ANTI-AUTOMATION CHALLENGE\n"
                    f"Type the following code to prove you are human: {challenge_code}\n\n"
                    "This code is randomly generated and cannot be predicted."
                ),
                expected_response=challenge_code,
                challenge_code=challenge_code,
            ),
        ]

    def _generate_unrestricted_steps(self) -> None:
        """
        Unrestricted pentest: five-layer ceremony with airgap attestation.

        🌑🌑🌑 This is the heaviest ceremony. Intentionally.

        Five steps:
        1. Acknowledge the danger
        2. Declare targets explicitly
        3. Attest legal authorization
        4. Attest airgapped environment
        5. Type a specific, hard-to-accidentally-type confirmation phrase
        """
        challenge_code = secrets.token_hex(6).upper()
        target_list = ", ".join(self._targets) if self._targets else "[NO TARGETS DECLARED]"

        # The final confirmation phrase is intentionally awkward
        final_phrase = (
            f"I AUTHORIZE UNRESTRICTED OPERATIONS ON {len(self._targets)} TARGETS AT MY OWN RISK"
        )

        self._steps = [
            # Step 1: Danger acknowledgment
            ConfirmationStep(
                step_number=1,
                step_type=ConfirmationStepType.ACKNOWLEDGE,
                prompt=(
                    "🌑🌑🌑 UNRESTRICTED PENTEST MODE — CONFIRMATION 1 of 5 🌑🌑🌑\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "⚠️  WARNING: UNRESTRICTED MODE REMOVES MOST SAFETY GUARDRAILS\n\n"
                    "This mode enables:\n"
                    "  • ALL deletion methods (including cache poisoning)\n"
                    "  • No compliance enforcement\n"
                    "  • Aggressive parallel operations\n"
                    "  • Direct resource manipulation\n\n"
                    "🌑 EXTREMELY RECOMMENDED: Use this mode ONLY in an\n"
                    "   AIRGAPPED ENVIRONMENT to prevent accidental exposure.\n\n"
                    "This mode is designed for:\n"
                    "  • Authorized penetration testing\n"
                    "  • Educational/lab environments\n"
                    "  • Security research\n\n"
                    "Session timeout: 60 minutes (non-extendable).\n"
                    "All actions are LOGGED with FULL AUDIT TRAIL.\n\n"
                    "Type 'I ACKNOWLEDGE THE RISKS' to proceed."
                ),
                expected_response="I ACKNOWLEDGE THE RISKS",
            ),
            # Step 2: Explicit target declaration
            ConfirmationStep(
                step_number=2,
                step_type=ConfirmationStepType.SCOPE_DECLARATION,
                prompt=(
                    "🌑🌑🌑 UNRESTRICTED PENTEST MODE — CONFIRMATION 2 of 5 🌑🌑🌑\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "Declared targets:\n" + "\n".join(f"  • {t}" for t in self._targets) + "\n\n"
                    "Confirm that EACH target listed above is:\n"
                    "  1. Owned by you OR you have written authorization\n"
                    "  2. Within the declared CIDR ranges\n"
                    "  3. Isolated from production systems\n"
                    "  4. Not connected to public internet (recommended)\n\n"
                    "⚠️  Blanket targets (0.0.0.0/0, ::/0) are ALWAYS BLOCKED.\n\n"
                    "Type 'TARGETS CONFIRMED AND AUTHORIZED' to proceed."
                ),
                expected_response="TARGETS CONFIRMED AND AUTHORIZED",
            ),
            # Step 3: Legal attestation
            ConfirmationStep(
                step_number=3,
                step_type=ConfirmationStepType.LEGAL_ATTESTATION,
                prompt=(
                    "🌑🌑🌑 UNRESTRICTED PENTEST MODE — CONFIRMATION 3 of 5 🌑🌑🌑\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "LEGAL ATTESTATION REQUIRED\n\n"
                    "By proceeding, you attest that:\n"
                    "  1. You have written authorization for this penetration test\n"
                    "  2. All targets are within your authorized scope\n"
                    "  3. You accept full legal responsibility for all actions\n"
                    "  4. You understand that unauthorized access is a crime\n"
                    "  5. Audit logs will be preserved for compliance\n\n"
                    "😐 Harold is not your lawyer, but Harold says: get it in writing.\n\n"
                    "Type 'I ATTEST LEGAL AUTHORIZATION' to proceed."
                ),
                expected_response="I ATTEST LEGAL AUTHORIZATION",
            ),
            # Step 4: Airgap attestation
            ConfirmationStep(
                step_number=4,
                step_type=ConfirmationStepType.AIRGAP_ATTESTATION,
                prompt=(
                    "🌑🌑🌑 UNRESTRICTED PENTEST MODE — CONFIRMATION 4 of 5 🌑🌑🌑\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "AIRGAP ENVIRONMENT CHECK\n\n"
                    "Unrestricted mode is EXTREMELY RECOMMENDED for use\n"
                    "only in airgapped environments.\n\n"
                    "Select one:\n"
                    "  A) 'AIRGAPPED CONFIRMED' — Environment is airgapped\n"
                    "  B) 'NOT AIRGAPPED I ACCEPT ADDITIONAL RISK' —\n"
                    "     Environment is NOT airgapped, I accept the additional risk\n\n"
                    f"Anti-automation challenge: Also include code {challenge_code}\n"
                    f"Example: 'AIRGAPPED CONFIRMED {challenge_code}'"
                ),
                expected_response=None,  # Custom validation below
                challenge_code=challenge_code,
            ),
            # Step 5: Final confirmation (intentionally verbose)
            ConfirmationStep(
                step_number=5,
                step_type=ConfirmationStepType.FINAL_CONFIRMATION,
                prompt=(
                    "🌑🌑🌑 UNRESTRICTED PENTEST MODE — FINAL CONFIRMATION 5 of 5 🌑🌑🌑\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "⚠️  THIS IS YOUR LAST CHANCE TO ABORT ⚠️\n\n"
                    "Mode: UNRESTRICTED PENTEST\n"
                    f"Targets: {target_list}\n"
                    f"Operator: {self._operator}\n"
                    "Session timeout: 60 minutes\n"
                    "Guardrails: DISABLED\n"
                    "Audit logging: ENABLED (cannot be disabled)\n\n"
                    f"Type EXACTLY:\n{final_phrase}"
                ),
                expected_response=final_phrase,
            ),
        ]

    # ========================================================================
    # Step Execution
    # ========================================================================

    def submit_response(self, step_number: int, response: str) -> bool:
        """
        Submit a response for a specific ceremony step.

        Args:
            step_number: Which step to respond to (1-indexed)
            response: The operator's response

        Returns:
            True if the response was accepted

        🌑 Responses are hashed and recorded. No take-backs.
        """
        if self.is_expired:
            self._attempts.append(
                {
                    "step": step_number,
                    "response": "[REDACTED]",
                    "accepted": False,
                    "reason": "Ceremony expired",
                    "timestamp": time.time(),
                }
            )
            return False

        # Steps must be completed in order
        current = self.current_step
        if current is None:
            return False  # Already complete

        if current.step_number != step_number:
            self._attempts.append(
                {
                    "step": step_number,
                    "response": "[REDACTED]",
                    "accepted": False,
                    "reason": f"Out of order — expected step {current.step_number}",
                    "timestamp": time.time(),
                }
            )
            return False

        # Special validation for airgap step (step 4 in unrestricted)
        if current.step_type == ConfirmationStepType.AIRGAP_ATTESTATION:
            accepted = self._validate_airgap_response(response, current.challenge_code)
        else:
            accepted = current.validate_response(response)

        self._attempts.append(
            {
                "step": step_number,
                "response": "[REDACTED]",
                "accepted": accepted,
                "reason": "Accepted" if accepted else "Invalid response",
                "timestamp": time.time(),
            }
        )

        if accepted:
            current.completed = True
            current.completed_at = time.time()
            current.response_given = response
            # Hash the response for the completion proof
            self._response_hashes.append(hashlib.sha256(response.encode()).hexdigest())

        return accepted

    def _validate_airgap_response(self, response: str, challenge: str) -> bool:
        """
        Custom validation for the airgap attestation step.

        Must contain either 'AIRGAPPED CONFIRMED' or
        'NOT AIRGAPPED I ACCEPT ADDITIONAL RISK' AND the challenge code.
        """
        response = response.strip().upper()
        has_valid_attestation = (
            "AIRGAPPED CONFIRMED" in response
            or "NOT AIRGAPPED I ACCEPT ADDITIONAL RISK" in response
        )
        has_challenge = challenge.upper() in response
        return has_valid_attestation and has_challenge

    # ========================================================================
    # Completion
    # ========================================================================

    def complete(self) -> ConfirmationResult:
        """
        Finalize the ceremony and produce a result.

        Returns:
            ConfirmationResult with completion status and proof hash
        """
        completed_count = sum(1 for s in self._steps if s.completed)

        # Generate completion hash from all response hashes
        if self._response_hashes:
            combined = "|".join(self._response_hashes)
            completion_hash = hashlib.sha256(f"{self._ceremony_id}:{combined}".encode()).hexdigest()
        else:
            completion_hash = ""

        failure_reason = None
        if self.is_expired:
            failure_reason = "Ceremony timed out"
        elif not self.is_complete:
            failure_reason = f"Incomplete — {completed_count}/{len(self._steps)} steps done"

        return ConfirmationResult(
            ceremony_id=self._ceremony_id,
            mode_requested=self._mode,
            all_steps_completed=self.is_complete and not self.is_expired,
            steps_completed=completed_count,
            steps_total=len(self._steps),
            operator=self._operator,
            completed_at=time.time() if self.is_complete else 0.0,
            failure_reason=failure_reason,
            completion_hash=completion_hash,
        )

    # ========================================================================
    # Helpers
    # ========================================================================

    def _get_timeout_minutes(self) -> float:
        """Get timeout for current ceremony type."""
        if self._mode == "unrestricted_pentest":
            return self.UNRESTRICTED_TIMEOUT_MINUTES
        if self._mode == "contained_pentest":
            return self.CONTAINED_TIMEOUT_MINUTES
        return self.STANDARD_TIMEOUT_MINUTES

    @property
    def attempts(self) -> list[dict[str, Any]]:
        """All confirmation attempts (for audit)."""
        return list(self._attempts)

    @property
    def time_remaining_seconds(self) -> float:
        """Seconds remaining before ceremony expires."""
        timeout = self._get_timeout_minutes() * 60
        elapsed = time.time() - self._started_at
        return max(0, timeout - elapsed)
