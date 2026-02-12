"""
😐 Tests for the EraserHead Orchestrator.

📺 Testing the conductor of Harold's deletion symphony.
   If the orchestrator breaks, everything breaks.

🌑 The orchestrator is the single point of enforcement.
   These tests verify that enforcement cannot be bypassed.
"""

from __future__ import annotations

from typing import Any

import pytest

from eraserhead.modes.base import OperatingMode
from eraserhead.modes.confirmation import ConfirmationStepType
from eraserhead.modes.target_validation import TargetScope
from eraserhead.providers.base import (
    ComplianceCheckResult,
    ComplianceProvider,
    ProviderCapability,
    ProviderHealth,
    ProviderInfo,
    ProviderStatus,
    ProviderType,
    ScrubProvider,
    ScrubRequest,
    ScrubResult,
    SearchProvider,
    SearchResult,
)
from eraserhead.providers.orchestrator import (
    AuditEntry,
    ComplianceBlockError,
    EraserHeadOrchestrator,
    ModeNotAuthorizedError,
    OrchestratorError,
)


# ============================================================================
# Mock Providers
# ============================================================================


class MockOrchestratorSearchProvider(SearchProvider):
    """Search provider for orchestrator tests."""

    def __init__(self, results: list[SearchResult] | None = None) -> None:
        super().__init__(
            info=ProviderInfo(
                provider_id="mock-search",
                name="Mock Search",
                provider_type=ProviderType.SEARCH,
                version="0.1.0",
                description="Mock search for testing",
                capabilities={ProviderCapability.SEARCH_BY_EMAIL},
            )
        )
        self._results = results or []
        self._initialized = False

    async def _do_initialize(self, config: dict[str, Any]) -> bool:
        self._initialized = True
        return True

    async def _do_health_check(self) -> ProviderHealth:
        return ProviderHealth(is_healthy=True, status=ProviderStatus.READY)

    async def search(
        self,
        query: str,
        *,
        search_type: str = "general",
        max_results: int = 50,
        metadata: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        return self._results[:max_results]


class MockOrchestratorScrubProvider(ScrubProvider):
    """Scrub provider for orchestrator tests."""

    def __init__(self, success: bool = True) -> None:
        super().__init__(
            info=ProviderInfo(
                provider_id="mock-scrub",
                name="Mock Scrub",
                provider_type=ProviderType.SCRUB,
                version="0.1.0",
                description="Mock scrub for testing",
                capabilities={ProviderCapability.SCRUB_EMAIL_REQUEST},
            )
        )
        self._success = success

    async def _do_initialize(self, config: dict[str, Any]) -> bool:
        return True

    async def _do_health_check(self) -> ProviderHealth:
        return ProviderHealth(is_healthy=True, status=ProviderStatus.READY)

    async def submit_removal(self, request: ScrubRequest) -> ScrubResult:
        return ScrubResult(
            request_id=request.request_id,
            success=self._success,
            error_message=None if self._success else "Mock failure",
        )

    async def check_removal_status(self, request_id: str) -> ScrubResult:
        return ScrubResult(request_id=request_id, success=self._success)

    async def get_supported_methods(self) -> list[str]:
        return ["api"]


class MockOrchestratorComplianceProvider(ComplianceProvider):
    """Compliance provider for orchestrator tests."""

    def __init__(self, compliant: bool = True) -> None:
        super().__init__(
            info=ProviderInfo(
                provider_id="mock-compliance",
                name="Mock Compliance",
                provider_type=ProviderType.COMPLIANCE,
                version="0.1.0",
                description="Mock compliance for testing",
                capabilities={ProviderCapability.COMPLIANCE_GDPR},
            )
        )
        self._compliant = compliant

    async def _do_initialize(self, config: dict[str, Any]) -> bool:
        return True

    async def _do_health_check(self) -> ProviderHealth:
        return ProviderHealth(is_healthy=True, status=ProviderStatus.READY)

    async def validate_action(
        self,
        action_type: str,
        target: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ComplianceCheckResult:
        if self._compliant:
            return ComplianceCheckResult(
                provider_id=self.provider_id,
                is_compliant=True,
                framework="MOCK",
            )
        return ComplianceCheckResult(
            provider_id=self.provider_id,
            is_compliant=False,
            framework="MOCK",
            issues=["Mock compliance failure"],
        )

    async def get_applicable_frameworks(self, target: dict[str, Any]) -> list[str]:
        return ["MOCK"]

    async def generate_request_template(self, framework: str, request_type: str) -> dict[str, Any]:
        return {"framework": framework, "request_type": request_type}


class FailingSearchProvider(SearchProvider):
    """Search provider that always raises."""

    def __init__(self) -> None:
        super().__init__(
            info=ProviderInfo(
                provider_id="failing-search",
                name="Failing Search",
                provider_type=ProviderType.SEARCH,
                version="0.1.0",
                description="Always fails",
                capabilities={ProviderCapability.SEARCH_BY_EMAIL},
            )
        )

    async def _do_initialize(self, config: dict[str, Any]) -> bool:
        return True

    async def _do_health_check(self) -> ProviderHealth:
        return ProviderHealth(is_healthy=True, status=ProviderStatus.READY)

    async def search(
        self,
        query: str,
        *,
        search_type: str = "general",
        max_results: int = 50,
        metadata: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        raise RuntimeError("Search exploded")


class FailingScrubProvider(ScrubProvider):
    """Scrub provider that always raises."""

    def __init__(self) -> None:
        super().__init__(
            info=ProviderInfo(
                provider_id="failing-scrub",
                name="Failing Scrub",
                provider_type=ProviderType.SCRUB,
                version="0.1.0",
                description="Always fails",
                capabilities={ProviderCapability.SCRUB_EMAIL_REQUEST},
            )
        )

    async def _do_initialize(self, config: dict[str, Any]) -> bool:
        return True

    async def _do_health_check(self) -> ProviderHealth:
        return ProviderHealth(is_healthy=True, status=ProviderStatus.READY)

    async def submit_removal(self, request: ScrubRequest) -> ScrubResult:
        raise RuntimeError("Scrub exploded")

    async def check_removal_status(self, request_id: str) -> ScrubResult:
        raise RuntimeError("Status check exploded")

    async def get_supported_methods(self) -> list[str]:
        return ["api"]


# ============================================================================
# Helper to complete a ceremony
# ============================================================================


def complete_ceremony(ceremony, is_airgapped: bool = True):
    """Complete all steps of a ceremony with correct responses."""
    steps = ceremony.steps
    for step in steps:
        if step.step_type == ConfirmationStepType.ACKNOWLEDGE:
            ceremony.submit_response(step.step_number, step.expected_response or "I UNDERSTAND")
        elif step.step_type == ConfirmationStepType.SCOPE_DECLARATION:
            ceremony.submit_response(step.step_number, step.expected_response or "CONFIRMED")
        elif step.step_type == ConfirmationStepType.LEGAL_ATTESTATION:
            ceremony.submit_response(
                step.step_number, step.expected_response or "I ACCEPT FULL RESPONSIBILITY"
            )
        elif step.step_type == ConfirmationStepType.CHALLENGE_RESPONSE:
            ceremony.submit_response(step.step_number, step.challenge_code)
        elif step.step_type == ConfirmationStepType.AIRGAP_ATTESTATION:
            if is_airgapped:
                ceremony.submit_response(
                    step.step_number, f"AIRGAPPED CONFIRMED {step.challenge_code}"
                )
            else:
                ceremony.submit_response(
                    step.step_number,
                    f"NOT AIRGAPPED I ACCEPT ADDITIONAL RISK {step.challenge_code}",
                )
        elif step.step_type == ConfirmationStepType.FINAL_CONFIRMATION:
            ceremony.submit_response(step.step_number, step.expected_response or "")


# ============================================================================
# Orchestrator Basics
# ============================================================================


class TestOrchestratorBasics:
    """Test orchestrator initialization and properties."""

    def test_starts_in_standard_mode(self) -> None:
        orch = EraserHeadOrchestrator()
        assert orch.current_mode == OperatingMode.STANDARD
        assert orch.containment is None

    def test_has_registry(self) -> None:
        orch = EraserHeadOrchestrator()
        assert orch.registry is not None

    def test_has_mode_manager(self) -> None:
        orch = EraserHeadOrchestrator()
        assert orch.mode_manager is not None

    def test_audit_log_starts_empty(self) -> None:
        orch = EraserHeadOrchestrator()
        assert len(orch.audit_log) == 0


# ============================================================================
# Mode Change Ceremonies
# ============================================================================


class TestOrchestratorModeChange:
    """Test mode change initiation and activation."""

    def test_initiate_contained_pentest(self) -> None:
        orch = EraserHeadOrchestrator()
        ceremony = orch.initiate_mode_change(
            mode="contained_pentest",
            operator="harold",
            targets=["192.168.1.0/24"],
            allowed_cidrs=["192.168.1.0/24"],
        )
        assert ceremony is not None
        assert ceremony.ceremony_id  # Has a valid ceremony ID
        assert len(orch.audit_log) == 1

    def test_initiate_unrestricted_pentest(self) -> None:
        orch = EraserHeadOrchestrator()
        ceremony = orch.initiate_mode_change(
            mode="unrestricted_pentest",
            operator="harold",
            targets=["10.0.0.0/8"],
            allowed_cidrs=["10.0.0.0/8"],
        )
        assert ceremony is not None
        assert ceremony.ceremony_id  # Has a valid ceremony ID

    def test_pentest_requires_targets(self) -> None:
        orch = EraserHeadOrchestrator()
        with pytest.raises(ModeNotAuthorizedError, match="target declaration"):
            orch.initiate_mode_change(
                mode="contained_pentest",
                operator="harold",
                allowed_cidrs=["192.168.1.0/24"],
            )

    def test_pentest_requires_cidrs(self) -> None:
        orch = EraserHeadOrchestrator()
        with pytest.raises(ModeNotAuthorizedError, match="CIDR"):
            orch.initiate_mode_change(
                mode="contained_pentest",
                operator="harold",
                targets=["192.168.1.0/24"],
            )

    def test_activate_contained_mode(self) -> None:
        orch = EraserHeadOrchestrator()
        ceremony = orch.initiate_mode_change(
            mode="contained_pentest",
            operator="harold",
            targets=["192.168.1.0/24"],
            allowed_cidrs=["192.168.1.0/24"],
        )
        complete_ceremony(ceremony)
        config = orch.activate_mode(ceremony)
        assert orch.current_mode == OperatingMode.CONTAINED_PENTEST
        assert orch.containment is not None

    def test_activate_unrestricted_mode(self) -> None:
        orch = EraserHeadOrchestrator()
        ceremony = orch.initiate_mode_change(
            mode="unrestricted_pentest",
            operator="harold",
            targets=["10.0.0.0/8"],
            allowed_cidrs=["10.0.0.0/8"],
        )
        complete_ceremony(ceremony, is_airgapped=True)
        config = orch.activate_mode(ceremony)
        assert orch.current_mode == OperatingMode.UNRESTRICTED_PENTEST
        assert orch.containment is not None

    def test_activate_standard_mode(self) -> None:
        orch = EraserHeadOrchestrator()
        ceremony = orch.initiate_mode_change(
            mode="standard",
            operator="harold",
        )
        complete_ceremony(ceremony)
        config = orch.activate_mode(ceremony)
        assert orch.current_mode == OperatingMode.STANDARD

    def test_incomplete_ceremony_rejected(self) -> None:
        orch = EraserHeadOrchestrator()
        ceremony = orch.initiate_mode_change(
            mode="contained_pentest",
            operator="harold",
            targets=["192.168.1.0/24"],
            allowed_cidrs=["192.168.1.0/24"],
        )
        # Don't complete any steps
        with pytest.raises(ModeNotAuthorizedError, match="incomplete"):
            orch.activate_mode(ceremony)

    def test_unknown_mode_rejected(self) -> None:
        """An unknown mode should be rejected at activation."""
        orch = EraserHeadOrchestrator()
        # Create a standard ceremony and tamper with its mode
        ceremony = orch.initiate_mode_change(
            mode="standard",
            operator="harold",
        )
        complete_ceremony(ceremony)
        # Monkey-patch mode to something invalid
        ceremony._mode = "quantum_pentest"
        with pytest.raises(ModeNotAuthorizedError, match="Unknown mode"):
            orch.activate_mode(ceremony)


# ============================================================================
# Mode Deactivation
# ============================================================================


class TestOrchestratorDeactivation:
    """Test pentest mode deactivation."""

    def test_deactivate_returns_to_standard(self) -> None:
        orch = EraserHeadOrchestrator()
        ceremony = orch.initiate_mode_change(
            mode="contained_pentest",
            operator="harold",
            targets=["192.168.1.0/24"],
            allowed_cidrs=["192.168.1.0/24"],
        )
        complete_ceremony(ceremony)
        orch.activate_mode(ceremony)
        assert orch.current_mode == OperatingMode.CONTAINED_PENTEST

        prev = orch.deactivate_pentest_mode()
        assert orch.current_mode == OperatingMode.STANDARD
        assert orch.containment is None

    def test_deactivation_audit(self) -> None:
        orch = EraserHeadOrchestrator()
        ceremony = orch.initiate_mode_change(
            mode="contained_pentest",
            operator="harold",
            targets=["192.168.1.0/24"],
            allowed_cidrs=["192.168.1.0/24"],
        )
        complete_ceremony(ceremony)
        orch.activate_mode(ceremony)
        orch.deactivate_pentest_mode()

        deactivation_entries = [e for e in orch.audit_log if e.action == "mode_deactivated"]
        assert len(deactivation_entries) == 1


# ============================================================================
# Search Operations
# ============================================================================


class TestOrchestratorSearch:
    """Test search operations through the orchestrator."""

    @pytest.mark.anyio
    async def test_search_with_provider(self) -> None:
        orch = EraserHeadOrchestrator()
        search = MockOrchestratorSearchProvider(
            results=[
                SearchResult(
                    provider_id="mock-search",
                    source_url="https://test.example.com/user",
                    source_platform="test",
                    content_type="profile",
                    metadata={"email": "user@example.com"},
                ),
            ]
        )
        await search.initialize({})
        orch.registry.register(search)

        results = await orch.search("user@example.com")
        assert len(results) == 1
        assert results[0].metadata["email"] == "user@example.com"

    @pytest.mark.anyio
    async def test_search_no_providers(self) -> None:
        orch = EraserHeadOrchestrator()
        results = await orch.search("user@example.com")
        assert results == []

    @pytest.mark.anyio
    async def test_search_with_compliance(self) -> None:
        """In standard mode, compliance should be checked before search."""
        orch = EraserHeadOrchestrator()

        search = MockOrchestratorSearchProvider(
            results=[
                SearchResult(
                    provider_id="mock-search",
                    source_url="https://test.example.com",
                    source_platform="test",
                    content_type="profile",
                )
            ]
        )
        await search.initialize({})
        orch.registry.register(search)

        compliance = MockOrchestratorComplianceProvider(compliant=True)
        await compliance.initialize({})
        orch.registry.register(compliance)

        results = await orch.search("user@example.com")
        assert len(results) == 1

    @pytest.mark.anyio
    async def test_search_compliance_failure_blocks(self) -> None:
        """In standard mode, failing compliance should block the search."""
        orch = EraserHeadOrchestrator()

        search = MockOrchestratorSearchProvider(
            results=[
                SearchResult(
                    provider_id="mock-search",
                    source_url="https://test.example.com",
                    source_platform="test",
                    content_type="profile",
                )
            ]
        )
        await search.initialize({})
        orch.registry.register(search)

        compliance = MockOrchestratorComplianceProvider(compliant=False)
        await compliance.initialize({})
        orch.registry.register(compliance)

        with pytest.raises(ComplianceBlockError):
            await orch.search("user@example.com")

    @pytest.mark.anyio
    async def test_search_provider_failure_handled(self) -> None:
        """A failing search provider should not crash the orchestrator."""
        orch = EraserHeadOrchestrator()
        search = FailingSearchProvider()
        await search.initialize({})
        orch.registry.register(search)

        results = await orch.search("user@example.com")
        assert results == []

    @pytest.mark.anyio
    async def test_search_audit(self) -> None:
        orch = EraserHeadOrchestrator()
        search = MockOrchestratorSearchProvider()
        await search.initialize({})
        orch.registry.register(search)

        await orch.search("user@example.com")

        search_entries = [e for e in orch.audit_log if e.action == "search"]
        assert len(search_entries) == 1
        assert search_entries[0].target == "user@example.com"


# ============================================================================
# Scrub Operations
# ============================================================================


class TestOrchestratorScrub:
    """Test scrub (removal request) operations."""

    @pytest.mark.anyio
    async def test_scrub_success(self) -> None:
        orch = EraserHeadOrchestrator()
        scrub = MockOrchestratorScrubProvider(success=True)
        await scrub.initialize({})
        orch.registry.register(scrub)

        requests = [
            ScrubRequest(
                provider_id="mock-scrub",
                request_id="req-1",
                target_url="https://example.com/profile/user",
                target_platform="example",
                content_type="profile",
            ),
        ]
        results = await orch.scrub(requests)
        assert len(results) == 1
        assert results[0].success is True

    @pytest.mark.anyio
    async def test_scrub_compliance_failure(self) -> None:
        """In standard mode, compliance failure should block scrub."""
        orch = EraserHeadOrchestrator()

        scrub = MockOrchestratorScrubProvider(success=True)
        await scrub.initialize({})
        orch.registry.register(scrub)

        compliance = MockOrchestratorComplianceProvider(compliant=False)
        await compliance.initialize({})
        orch.registry.register(compliance)

        requests = [
            ScrubRequest(
                provider_id="mock-scrub",
                request_id="req-1",
                target_url="https://example.com/profile/user",
                target_platform="example",
                content_type="profile",
            ),
        ]
        with pytest.raises(ComplianceBlockError):
            await orch.scrub(requests)

    @pytest.mark.anyio
    async def test_scrub_no_provider(self) -> None:
        """When no scrub provider is available, should return failure."""
        orch = EraserHeadOrchestrator()
        requests = [
            ScrubRequest(
                provider_id="mock-scrub",
                request_id="req-1",
                target_url="https://example.com/profile/user",
                target_platform="example",
                content_type="profile",
            ),
        ]
        results = await orch.scrub(requests)
        assert len(results) == 1
        assert results[0].success is False
        assert "no available" in results[0].error_message.lower()

    @pytest.mark.anyio
    async def test_scrub_provider_failure(self) -> None:
        """A failing scrub provider should result in a failure result."""
        orch = EraserHeadOrchestrator()
        scrub = FailingScrubProvider()
        await scrub.initialize({})
        orch.registry.register(scrub)

        requests = [
            ScrubRequest(
                provider_id="mock-scrub",
                request_id="req-1",
                target_url="https://example.com/profile/user",
                target_platform="example",
                content_type="profile",
            ),
        ]
        results = await orch.scrub(requests)
        assert len(results) == 1
        assert results[0].success is False

    @pytest.mark.anyio
    async def test_scrub_multiple_requests(self) -> None:
        orch = EraserHeadOrchestrator()
        scrub = MockOrchestratorScrubProvider(success=True)
        await scrub.initialize({})
        orch.registry.register(scrub)

        requests = [
            ScrubRequest(
                provider_id="mock-scrub",
                request_id=f"req-{i}",
                target_url=f"https://example.com/user/{i}",
                target_platform="example",
                content_type="profile",
            )
            for i in range(3)
        ]
        results = await orch.scrub(requests)
        assert len(results) == 3
        assert all(r.success for r in results)


# ============================================================================
# Target Validation
# ============================================================================


class TestOrchestratorTargets:
    """Test target validation through the orchestrator."""

    def test_validate_targets_standard_mode(self) -> None:
        orch = EraserHeadOrchestrator()
        scope = TargetScope(domain_targets=["example.com"])
        report = orch.validate_targets(scope)
        assert report["valid"] is True

    def test_validate_targets_nuclear_blocked(self) -> None:
        orch = EraserHeadOrchestrator()
        scope = TargetScope(ip_targets=["0.0.0.0/0"])
        report = orch.validate_targets(scope)
        assert report["valid"] is False

    def test_validate_targets_empty_scope(self) -> None:
        orch = EraserHeadOrchestrator()
        scope = TargetScope()
        report = orch.validate_targets(scope)
        assert report["valid"] is False

    def test_validate_targets_with_containment(self) -> None:
        """In pentest mode, containment should further restrict targets."""
        orch = EraserHeadOrchestrator()
        ceremony = orch.initiate_mode_change(
            mode="contained_pentest",
            operator="harold",
            targets=["192.168.1.0/24"],
            allowed_cidrs=["192.168.1.0/24"],
        )
        complete_ceremony(ceremony)
        orch.activate_mode(ceremony)

        # Valid target within containment
        scope = TargetScope(ip_targets=["192.168.1.100"])
        report = orch.validate_targets(scope)
        assert report["valid"] is True

    def test_validate_targets_outside_containment(self) -> None:
        """Targets outside containment range should be rejected."""
        orch = EraserHeadOrchestrator()
        ceremony = orch.initiate_mode_change(
            mode="contained_pentest",
            operator="harold",
            targets=["192.168.1.0/24"],
            allowed_cidrs=["192.168.1.0/24"],
        )
        complete_ceremony(ceremony)
        orch.activate_mode(ceremony)

        # Target outside range
        scope = TargetScope(ip_targets=["10.0.0.1"])
        report = orch.validate_targets(scope)
        assert report["valid"] is False


# ============================================================================
# Audit
# ============================================================================


class TestOrchestratorAudit:
    """Test audit trail functionality."""

    def test_audit_entries_accumulate(self) -> None:
        orch = EraserHeadOrchestrator()
        ceremony = orch.initiate_mode_change(
            mode="contained_pentest",
            operator="harold",
            targets=["192.168.1.0/24"],
            allowed_cidrs=["192.168.1.0/24"],
        )
        complete_ceremony(ceremony)
        orch.activate_mode(ceremony)
        orch.deactivate_pentest_mode()

        # Should have: initiate + activate + deactivate
        assert len(orch.audit_log) >= 3

    def test_audit_summary(self) -> None:
        orch = EraserHeadOrchestrator()
        orch.initiate_mode_change(
            mode="contained_pentest",
            operator="harold",
            targets=["192.168.1.0/24"],
            allowed_cidrs=["192.168.1.0/24"],
        )
        summary = orch.get_audit_summary()
        assert summary["total_entries"] == 1
        assert "mode_change_initiated" in summary["by_action"]

    def test_audit_eviction(self) -> None:
        """Audit log should evict oldest entries when over limit."""
        orch = EraserHeadOrchestrator()
        orch._max_audit_entries = 10  # Low limit for testing

        for i in range(15):
            orch._audit(
                action=f"test_{i}",
                target="target",
                operator="harold",
                result="ok",
            )

        # Should have evicted oldest entries
        assert len(orch.audit_log) <= 10

    def test_audit_entry_structure(self) -> None:
        entry = AuditEntry(
            action="test",
            mode="standard",
            operator="harold",
            target="example.com",
            result="success",
        )
        assert entry.action == "test"
        assert entry.timestamp > 0
        assert entry.compliance_result == ""
        assert entry.details == {}


# ============================================================================
# Error Classes
# ============================================================================


class TestOrchestratorErrors:
    """Test orchestrator error hierarchy."""

    def test_orchestrator_error_base(self) -> None:
        err = OrchestratorError("test")
        assert str(err) == "test"

    def test_compliance_block_error(self) -> None:
        err = ComplianceBlockError("blocked")
        assert isinstance(err, OrchestratorError)

    def test_mode_not_authorized_error(self) -> None:
        err = ModeNotAuthorizedError("not authorized")
        assert isinstance(err, OrchestratorError)
