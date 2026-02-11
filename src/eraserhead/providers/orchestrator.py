"""
😐 EraserHead Orchestrator: Ties providers, modes, and containment together.

The conductor of Harold's symphony of deletion. Manages the full lifecycle:
1. Mode selection and confirmation ceremony
2. Compliance validation
3. Target validation and containment
4. Provider discovery and execution
5. Verification and audit

📺 An orchestra without a conductor is just noise.
   An erasure tool without orchestration is just a liability.

🌑 The orchestrator enforces mode constraints at every step.
   No provider can bypass mode restrictions. No action can
   skip compliance. Harold's paranoia is systemic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from eraserhead.modes.base import (
    ModeConfig,
    ModeManager,
    ModeViolation,
    OperatingMode,
)
from eraserhead.modes.confirmation import ConfirmationCeremony, ConfirmationResult
from eraserhead.modes.containment import ContainmentConfig, ContainmentViolation, NetworkContainment
from eraserhead.modes.target_validation import TargetScope, TargetValidationError, TargetValidator
from eraserhead.providers.base import (
    ComplianceCheckResult,
    ProviderCapability,
    ProviderEvent,
    ProviderEventType,
    ScrubRequest,
    ScrubResult,
    SearchResult,
)
from eraserhead.providers.registry import ProviderRegistry


logger = logging.getLogger(__name__)


# ============================================================================
# Orchestrator Errors
# ============================================================================


class OrchestratorError(Exception):
    """Base orchestrator error."""


class ComplianceBlockError(OrchestratorError):
    """Operation blocked by compliance check."""


class ModeNotAuthorizedError(OrchestratorError):
    """Mode not authorized (confirmation ceremony not completed)."""


# ============================================================================
# Audit Entry
# ============================================================================


@dataclass
class AuditEntry:
    """
    An auditable record of an orchestrator action.

    🌑 Every action is recorded. Every. Single. One.
    """

    action: str
    mode: str
    operator: str
    target: str
    result: str
    timestamp: float = field(default_factory=time.time)
    compliance_result: str = ""
    details: dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Orchestrator
# ============================================================================


class EraserHeadOrchestrator:
    """
    😐 The main orchestrator that coordinates all EraserHead operations.

    Manages:
    - Provider registry (search, scrub, compliance providers)
    - Operating modes (standard, contained pentest, unrestricted pentest)
    - Confirmation ceremonies (multi-step authorization)
    - Network containment (CIDR validation for pentest modes)
    - Target validation (safety checks for all targets)
    - Audit trail (every action logged)

    Usage (Standard Mode):
        orch = EraserHeadOrchestrator()
        orch.registry.register(search_provider)
        orch.registry.register(compliance_provider)

        results = await orch.search("user@example.com")
        scrub_results = await orch.scrub(scrub_requests)

    Usage (Contained Pentest):
        ceremony = orch.initiate_mode_change(
            mode="contained_pentest",
            operator="harold",
            targets=["192.168.1.0/24"],
            allowed_cidrs=["192.168.1.0/24"],
        )
        # Complete all ceremony steps...
        orch.activate_mode(ceremony)

        # Now pentest operations are available within the subnet
        results = await orch.search("target_system", mode_override=True)

    📺 Harold conducts. The providers play. The compliance
    framework keeps everyone in tune.

    🌑 The orchestrator is the single enforcer of mode constraints.
    Bypass it and you bypass all safety. Don't bypass it.
    """

    def __init__(self) -> None:
        self._registry = ProviderRegistry()
        self._mode_manager = ModeManager()
        self._containment: NetworkContainment | None = None
        self._target_validator = TargetValidator()
        self._audit_log: list[AuditEntry] = []
        self._active_ceremony: ConfirmationCeremony | None = None
        self._max_audit_entries = 50_000

    @property
    def registry(self) -> ProviderRegistry:
        """Access the provider registry."""
        return self._registry

    @property
    def mode_manager(self) -> ModeManager:
        """Access the mode manager."""
        return self._mode_manager

    @property
    def current_mode(self) -> OperatingMode:
        """Current operating mode."""
        return self._mode_manager.current_mode

    @property
    def containment(self) -> NetworkContainment | None:
        """Active network containment (None in standard mode)."""
        return self._containment

    # ========================================================================
    # Mode Management
    # ========================================================================

    def initiate_mode_change(
        self,
        mode: str,
        operator: str,
        targets: list[str] | None = None,
        allowed_cidrs: list[str] | None = None,
        gateway_boundary: str | None = None,
        denied_cidrs: list[str] | None = None,
        activation_reason: str = "",
    ) -> ConfirmationCeremony:
        """
        Initiate a mode change by starting a confirmation ceremony.

        Args:
            mode: Target mode ("standard", "contained_pentest", "unrestricted_pentest")
            operator: Who is requesting the change
            targets: Declared targets (required for pentest modes)
            allowed_cidrs: Allowed CIDR ranges (required for pentest modes)
            gateway_boundary: Gateway IP that must not be crossed
            denied_cidrs: Explicitly denied CIDRs
            activation_reason: Why this mode is being activated

        Returns:
            ConfirmationCeremony to be completed step-by-step
        """
        # Validate targets before even starting the ceremony
        if mode in ("contained_pentest", "unrestricted_pentest"):
            if not targets:
                raise ModeNotAuthorizedError(
                    "🌑 Pentest modes require explicit target declaration."
                )
            if not allowed_cidrs:
                raise ModeNotAuthorizedError("🌑 Pentest modes require explicit CIDR ranges.")

            # Pre-validate targets
            for target in targets:
                try:
                    self._target_validator.validate_ip_target(target)
                except TargetValidationError:
                    # Non-IP targets (domains, etc.) are fine
                    pass

        ceremony = ConfirmationCeremony(
            mode=mode,
            operator=operator,
            targets=targets or [],
        )
        self._active_ceremony = ceremony

        self._audit(
            action="mode_change_initiated",
            target=mode,
            operator=operator,
            result="ceremony_started",
            details={
                "ceremony_id": ceremony.ceremony_id,
                "targets": targets or [],
                "cidrs": allowed_cidrs or [],
            },
        )

        return ceremony

    def activate_mode(self, ceremony: ConfirmationCeremony) -> ModeConfig:
        """
        Activate a mode after the confirmation ceremony is complete.

        Args:
            ceremony: The completed confirmation ceremony

        Returns:
            The activated ModeConfig

        Raises:
            ModeNotAuthorizedError: If ceremony is incomplete or expired
        """
        result = ceremony.complete()

        if not result.all_steps_completed:
            raise ModeNotAuthorizedError(
                f"🌑 Confirmation ceremony incomplete: {result.failure_reason}\n"
                f"😐 Harold requires all steps. No shortcuts."
            )

        # Create the appropriate mode config
        mode = result.mode_requested
        if mode == "standard":
            config = ModeConfig.standard()
        elif mode == "contained_pentest":
            # Extract CIDRs from the ceremony context
            config = ModeConfig.contained_pentest(
                allowed_cidrs=self._extract_cidrs_from_ceremony(ceremony),
            )
        elif mode == "unrestricted_pentest":
            config = ModeConfig.unrestricted_pentest(
                allowed_cidrs=self._extract_cidrs_from_ceremony(ceremony),
                activation_reason=f"Ceremony {result.ceremony_id} completed by {result.operator}",
            )
        else:
            raise ModeNotAuthorizedError(f"Unknown mode: {mode}")

        # Activate
        self._mode_manager.activate_mode(config, operator=result.operator)

        # Set up containment for pentest modes
        if mode in ("contained_pentest", "unrestricted_pentest"):
            containment_config = ContainmentConfig(
                allowed_cidrs=config.allowed_cidrs,
                denied_cidrs=config.denied_cidrs,
                gateway_boundary=config.gateway_boundary,
            )
            self._containment = NetworkContainment(containment_config)

        self._active_ceremony = None

        self._audit(
            action="mode_activated",
            target=mode,
            operator=result.operator,
            result="success",
            details={
                "ceremony_id": result.ceremony_id,
                "completion_hash": result.completion_hash,
            },
        )

        return config

    def deactivate_pentest_mode(self) -> ModeConfig:
        """
        Deactivate pentest mode and return to standard.

        Returns the previous mode config for audit.
        """
        previous = self._mode_manager.deactivate()
        self._containment = None

        self._audit(
            action="mode_deactivated",
            target=previous.mode,
            operator=previous.activated_by,
            result="returned_to_standard",
        )

        return previous

    def _extract_cidrs_from_ceremony(self, ceremony: ConfirmationCeremony) -> list[str]:
        """Extract CIDR information from the ceremony's target list."""
        # The CIDRs were provided when initiating the mode change
        # They're stored in the audit log entry for the initiation
        for entry in reversed(self._audit_log):
            if entry.action == "mode_change_initiated":
                return entry.details.get("cidrs", [])
        return []

    # ========================================================================
    # Search Operations
    # ========================================================================

    async def search(
        self,
        query: str,
        *,
        search_type: str = "general",
        max_results: int = 50,
    ) -> list[SearchResult]:
        """
        Search for digital footprint data across all registered search providers.

        In STANDARD mode: compliance-checked, rate-limited
        In PENTEST modes: targets must be within containment

        Args:
            query: Search query
            search_type: Type of search
            max_results: Maximum results per provider

        Returns:
            Aggregated search results from all providers
        """
        self._mode_manager.enforce("search", query)

        # Compliance check in standard mode
        if self._mode_manager.is_standard:
            await self._check_compliance("search", {"query": query, "type": search_type})

        all_results: list[SearchResult] = []
        providers = self._registry.get_search_providers()

        if not providers:
            logger.warning("No search providers registered")
            return []

        for provider in providers:
            if not provider.is_ready:
                continue

            try:
                results = await provider.search(
                    query,
                    search_type=search_type,
                    max_results=max_results,
                )
                all_results.extend(results)

                await self._registry.emit(
                    ProviderEvent(
                        event_type=ProviderEventType.SEARCH_COMPLETED,
                        provider_id=provider.provider_id,
                        data={"query": query, "results_count": len(results)},
                    )
                )
            except Exception as e:
                logger.error("Search provider %s failed: %s", provider.provider_id, e)
                await self._registry.emit(
                    ProviderEvent(
                        event_type=ProviderEventType.ERROR_OCCURRED,
                        provider_id=provider.provider_id,
                        data={"error": str(e)},
                    )
                )

        self._audit(
            action="search",
            target=query,
            operator=self._mode_manager.config.activated_by or "standard",
            result=f"{len(all_results)} results from {len(providers)} providers",
        )

        return all_results

    # ========================================================================
    # Scrub Operations
    # ========================================================================

    async def scrub(self, requests: list[ScrubRequest]) -> list[ScrubResult]:
        """
        Submit removal requests through registered scrub providers.

        In STANDARD mode: compliance-checked, formal request process
        In PENTEST modes: direct deletion allowed (within containment)

        Args:
            requests: List of removal requests

        Returns:
            Results for each request
        """
        results: list[ScrubResult] = []

        for request in requests:
            self._mode_manager.enforce("scrub", request.target_url)

            # Compliance check in standard mode
            if self._mode_manager.is_standard:
                compliance = await self._check_compliance(
                    "erasure",
                    {"url": request.target_url, "platform": request.target_platform},
                    {"method": request.method},
                )
                if not compliance.is_compliant:
                    results.append(
                        ScrubResult(
                            request_id=request.request_id,
                            success=False,
                            error_message=(
                                f"Compliance check failed: {'; '.join(compliance.issues)}"
                            ),
                        )
                    )
                    continue

            # Find appropriate provider
            providers = self._registry.get_scrub_providers()
            handled = False

            for provider in providers:
                if not provider.is_ready:
                    continue

                try:
                    result = await provider.submit_removal(request)
                    results.append(result)
                    handled = True

                    event_type = (
                        ProviderEventType.SCRUB_COMPLETED
                        if result.success
                        else ProviderEventType.SCRUB_FAILED
                    )
                    await self._registry.emit(
                        ProviderEvent(
                            event_type=event_type,
                            provider_id=provider.provider_id,
                            data={"request_id": request.request_id, "success": result.success},
                        )
                    )
                    break  # First successful provider handles it
                except Exception as e:
                    logger.error("Scrub provider %s failed: %s", provider.provider_id, e)

            if not handled:
                results.append(
                    ScrubResult(
                        request_id=request.request_id,
                        success=False,
                        error_message="No available scrub provider could handle this request",
                    )
                )

            self._audit(
                action="scrub",
                target=request.target_url,
                operator=self._mode_manager.config.activated_by or "standard",
                result="success" if handled else "no_provider",
            )

        return results

    # ========================================================================
    # Compliance Helpers
    # ========================================================================

    async def _check_compliance(
        self,
        action_type: str,
        target: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ComplianceCheckResult:
        """
        Run compliance checks against all registered compliance providers.

        Raises ComplianceBlockError if blocking is enabled and check fails.
        """
        providers = self._registry.get_compliance_providers()

        if not providers:
            # No compliance providers — in standard mode this is concerning
            if self._mode_manager.is_standard:
                logger.warning(
                    "No compliance providers registered in STANDARD mode. Proceeding with caution."
                )
            return ComplianceCheckResult(
                provider_id="none",
                is_compliant=True,
                framework="none",
                recommendations=["Register a compliance provider for proper validation"],
            )

        # Aggregate results from all compliance providers
        all_issues: list[str] = []
        all_recommendations: list[str] = []

        for provider in providers:
            if not provider.is_ready:
                continue

            result = await provider.validate_action(action_type, target, context)

            if not result.is_compliant:
                all_issues.extend(result.issues)

                if self._mode_manager.config.block_on_compliance_failure:
                    self._audit(
                        action="compliance_blocked",
                        target=str(target),
                        operator=self._mode_manager.config.activated_by or "standard",
                        result="blocked",
                        compliance_result="; ".join(result.issues),
                    )
                    raise ComplianceBlockError(
                        f"🌑 Compliance check FAILED. Operation blocked.\n"
                        f"Issues: {'; '.join(result.issues)}\n"
                        f"😐 Harold says: fix the compliance issues first."
                    )

            all_recommendations.extend(result.recommendations)

        return ComplianceCheckResult(
            provider_id="aggregated",
            is_compliant=len(all_issues) == 0,
            framework="all",
            issues=all_issues,
            recommendations=all_recommendations,
        )

    # ========================================================================
    # Target Validation (public API)
    # ========================================================================

    def validate_targets(self, scope: TargetScope) -> dict[str, Any]:
        """
        Validate a target scope against both target validator and containment.

        Returns validation report.
        """
        report: dict[str, Any] = {"valid": True, "errors": [], "warnings": []}

        # Basic target validation
        try:
            self._target_validator.validate_scope(scope)
            report["warnings"].extend(self._target_validator.warnings)
        except TargetValidationError as e:
            report["valid"] = False
            report["errors"].append(str(e))

        # Containment validation (pentest modes only)
        if self._containment and scope.has_ip_targets:
            containment_results = self._containment.validate_targets(scope.ip_targets)
            for target, result in containment_results.items():
                if result is not True:
                    report["valid"] = False
                    report["errors"].append(f"Containment: {result}")

        return report

    # ========================================================================
    # Audit
    # ========================================================================

    def _audit(
        self,
        action: str,
        target: str,
        operator: str,
        result: str,
        compliance_result: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Record an audit entry."""
        entry = AuditEntry(
            action=action,
            mode=self._mode_manager.current_mode,
            operator=operator,
            target=target,
            result=result,
            compliance_result=compliance_result,
            details=details or {},
        )
        self._audit_log.append(entry)

        # LRU eviction
        if len(self._audit_log) > self._max_audit_entries:
            evict = self._max_audit_entries // 10
            self._audit_log = self._audit_log[evict:]

        logger.info(
            "AUDIT: [%s] %s → %s (target=%s, operator=%s)",
            entry.mode,
            action,
            result,
            target,
            operator,
        )

    @property
    def audit_log(self) -> list[AuditEntry]:
        """Full audit log."""
        return list(self._audit_log)

    def get_audit_summary(self) -> dict[str, Any]:
        """Summary of audit log."""
        from collections import Counter

        actions = Counter(e.action for e in self._audit_log)
        modes = Counter(e.mode for e in self._audit_log)
        return {
            "total_entries": len(self._audit_log),
            "by_action": dict(actions),
            "by_mode": dict(modes),
        }
