"""
😐 Tests for the Legal Compliance Provider.

📺 Testing compliance is like testing seatbelts:
   You hope you never need them, but you'd better
   make sure they work before the crash.

🌑 Inadequate compliance testing → regulatory fines.
"""

from __future__ import annotations

import pytest

from eraserhead.providers.base import ProviderStatus
from eraserhead.providers.compliance import (
    CCPA,
    FRAMEWORKS,
    GDPR,
    LGPD,
    PIPEDA,
    LegalComplianceProvider,
    LegalFramework,
)


# ============================================================================
# Framework Definitions
# ============================================================================


class TestLegalFramework:
    """Test pre-defined legal framework configurations."""

    def test_gdpr_exists(self) -> None:
        assert "GDPR" in FRAMEWORKS
        assert GDPR.framework_id == "GDPR"
        assert GDPR.jurisdiction == "EU/EEA"
        assert GDPR.response_deadline_days == 30

    def test_ccpa_exists(self) -> None:
        assert "CCPA" in FRAMEWORKS
        assert CCPA.framework_id == "CCPA"
        assert CCPA.jurisdiction == "California, USA"
        assert CCPA.response_deadline_days == 45

    def test_pipeda_exists(self) -> None:
        assert "PIPEDA" in FRAMEWORKS
        assert PIPEDA.response_deadline_days == 30

    def test_lgpd_exists(self) -> None:
        assert "LGPD" in FRAMEWORKS
        assert LGPD.jurisdiction == "Brazil"
        assert LGPD.response_deadline_days == 15

    def test_gdpr_supports_erasure(self) -> None:
        assert "erasure" in GDPR.supported_request_types
        assert "access" in GDPR.supported_request_types
        assert "portability" in GDPR.supported_request_types

    def test_ccpa_supports_deletion(self) -> None:
        assert "deletion" in CCPA.supported_request_types
        assert "access" in CCPA.supported_request_types
        assert "opt_out" in CCPA.supported_request_types

    def test_custom_framework(self) -> None:
        fw = LegalFramework(
            framework_id="TEST",
            name="Test Framework",
            jurisdiction="Testland",
            response_deadline_days=7,
            supported_request_types=["deletion"],
        )
        assert fw.framework_id == "TEST"
        assert fw.requires_identity_proof is True


# ============================================================================
# Compliance Provider
# ============================================================================


class TestLegalComplianceProvider:
    """Test the LegalComplianceProvider implementation."""

    def test_provider_creation(self) -> None:
        provider = LegalComplianceProvider()
        assert provider.provider_id == "compliance-legal"
        assert provider.info.provider_type.value == "compliance"

    def test_provider_with_specific_frameworks(self) -> None:
        provider = LegalComplianceProvider(frameworks=["GDPR"])
        assert "GDPR" in provider._active_frameworks
        assert "CCPA" not in provider._active_frameworks

    def test_provider_ignores_unknown_frameworks(self) -> None:
        provider = LegalComplianceProvider(frameworks=["GDPR", "NONEXISTENT"])
        assert "GDPR" in provider._active_frameworks
        assert "NONEXISTENT" not in provider._active_frameworks

    @pytest.mark.anyio
    async def test_initialize(self) -> None:
        provider = LegalComplianceProvider()
        result = await provider.initialize({"frameworks": ["CCPA"]})
        assert result is True
        assert "CCPA" in provider._active_frameworks

    @pytest.mark.anyio
    async def test_health_check_healthy(self) -> None:
        provider = LegalComplianceProvider()
        health = await provider.health_check()
        assert health.is_healthy is True
        assert health.status == ProviderStatus.READY

    @pytest.mark.anyio
    async def test_health_check_no_frameworks(self) -> None:
        provider = LegalComplianceProvider(frameworks=["NONEXISTENT_ONLY"])
        await provider.initialize({})
        health = await provider.health_check()
        assert health.is_healthy is False
        assert health.status == ProviderStatus.ERROR


# ============================================================================
# Compliance Validation
# ============================================================================


class TestComplianceValidation:
    """Test action validation against legal frameworks."""

    @pytest.mark.anyio
    async def test_compliant_action(self) -> None:
        """A fully compliant erasure request should pass."""
        provider = LegalComplianceProvider(frameworks=["GDPR"])
        result = await provider.validate_action(
            action_type="erasure",
            target={"type": "social_media", "jurisdiction": "EU"},
            context={
                "identity_proof": "passport_scan_ref_123",
                "data_subject_consent": True,
            },
        )
        assert result.is_compliant is True
        assert len(result.issues) == 0

    @pytest.mark.anyio
    async def test_missing_identity_proof(self) -> None:
        """Missing identity proof should fail GDPR compliance."""
        provider = LegalComplianceProvider(frameworks=["GDPR"])
        result = await provider.validate_action(
            action_type="erasure",
            target={"type": "social_media", "jurisdiction": "EU"},
            context={"data_subject_consent": True},
        )
        assert result.is_compliant is False
        assert any("identity_proof" in issue.lower() for issue in result.issues)

    @pytest.mark.anyio
    async def test_missing_consent(self) -> None:
        """Missing data subject consent should fail."""
        provider = LegalComplianceProvider(frameworks=["GDPR"])
        result = await provider.validate_action(
            action_type="erasure",
            target={"type": "social_media", "jurisdiction": "EU"},
            context={"identity_proof": "ref_123"},
        )
        assert result.is_compliant is False
        assert any("consent" in issue.lower() for issue in result.issues)

    @pytest.mark.anyio
    async def test_unsupported_action_type(self) -> None:
        """An action type not supported by the framework should fail."""
        provider = LegalComplianceProvider(frameworks=["CCPA"])
        result = await provider.validate_action(
            action_type="erasure",  # CCPA uses "deletion", not "erasure"
            target={"type": "social_media", "jurisdiction": "US"},
            context={
                "identity_proof": "ref_123",
                "data_subject_consent": True,
            },
        )
        assert result.is_compliant is False
        assert any("erasure" in issue for issue in result.issues)

    @pytest.mark.anyio
    async def test_direct_deletion_blocked_under_gdpr(self) -> None:
        """Direct deletion (bypassing formal channels) should be flagged."""
        provider = LegalComplianceProvider(frameworks=["GDPR"])
        result = await provider.validate_action(
            action_type="erasure",
            target={
                "type": "social_media",
                "jurisdiction": "EU",
                "method": "direct_deletion",
            },
            context={
                "identity_proof": "ref_123",
                "data_subject_consent": True,
            },
        )
        assert result.is_compliant is False
        assert any("direct deletion" in issue.lower() for issue in result.issues)

    @pytest.mark.anyio
    async def test_no_applicable_frameworks(self) -> None:
        """When no frameworks apply, should pass with recommendation."""
        provider = LegalComplianceProvider(frameworks=["GDPR"])
        result = await provider.validate_action(
            action_type="erasure",
            target={"type": "unknown_type", "jurisdiction": "Mars"},
            context={
                "identity_proof": "ref_123",
                "data_subject_consent": True,
            },
        )
        # No applicable framework → no violations
        assert result.is_compliant is True
        assert any("no specific" in r.lower() for r in result.recommendations)

    @pytest.mark.anyio
    async def test_multiple_frameworks(self) -> None:
        """Validation against multiple frameworks at once."""
        provider = LegalComplianceProvider(frameworks=["GDPR", "CCPA"])
        result = await provider.validate_action(
            action_type="access",  # Supported by both
            target={"type": "social_media", "jurisdiction": ""},  # Unknown → all apply
            context={
                "identity_proof": "ref_123",
                "data_subject_consent": True,
            },
        )
        assert result.is_compliant is True

    @pytest.mark.anyio
    async def test_check_history(self) -> None:
        """Compliance checks should be recorded in history."""
        provider = LegalComplianceProvider()
        assert len(provider.check_history) == 0

        await provider.validate_action(
            action_type="erasure",
            target={"type": "social_media"},
            context={"identity_proof": "ref", "data_subject_consent": True},
        )
        assert len(provider.check_history) == 1

    @pytest.mark.anyio
    async def test_no_context_fails(self) -> None:
        """Missing context entirely should fail (no proof, no consent)."""
        provider = LegalComplianceProvider(frameworks=["GDPR"])
        result = await provider.validate_action(
            action_type="erasure",
            target={"type": "social_media", "jurisdiction": "EU"},
        )
        assert result.is_compliant is False
        assert len(result.issues) >= 2  # Missing identity_proof AND consent


# ============================================================================
# Applicable Frameworks
# ============================================================================


class TestApplicableFrameworks:
    """Test framework applicability determination."""

    @pytest.mark.anyio
    async def test_eu_jurisdiction_returns_gdpr(self) -> None:
        provider = LegalComplianceProvider(frameworks=["GDPR", "CCPA"])
        applicable = await provider.get_applicable_frameworks(
            {"type": "social_media", "jurisdiction": "EU"}
        )
        assert "GDPR" in applicable
        assert "CCPA" not in applicable

    @pytest.mark.anyio
    async def test_us_jurisdiction_returns_ccpa(self) -> None:
        provider = LegalComplianceProvider(frameworks=["GDPR", "CCPA"])
        applicable = await provider.get_applicable_frameworks(
            {"type": "social_media", "jurisdiction": "US"}
        )
        assert "CCPA" in applicable
        assert "GDPR" not in applicable

    @pytest.mark.anyio
    async def test_unknown_jurisdiction_returns_all(self) -> None:
        provider = LegalComplianceProvider(frameworks=["GDPR", "CCPA"])
        applicable = await provider.get_applicable_frameworks(
            {"type": "social_media", "jurisdiction": ""}
        )
        assert "GDPR" in applicable
        assert "CCPA" in applicable

    @pytest.mark.anyio
    async def test_member_state_returns_gdpr(self) -> None:
        """Individual EU member state codes should trigger GDPR."""
        provider = LegalComplianceProvider(frameworks=["GDPR"])
        for code in ("DE", "FR", "IT", "ES", "NL", "PL"):
            applicable = await provider.get_applicable_frameworks(
                {"type": "social_media", "jurisdiction": code}
            )
            assert "GDPR" in applicable, f"GDPR should apply for {code}"

    @pytest.mark.anyio
    async def test_brazil_returns_lgpd(self) -> None:
        provider = LegalComplianceProvider(frameworks=["LGPD"])
        applicable = await provider.get_applicable_frameworks(
            {"type": "social_media", "jurisdiction": "BR"}
        )
        assert "LGPD" in applicable

    @pytest.mark.anyio
    async def test_canada_returns_pipeda(self) -> None:
        provider = LegalComplianceProvider(frameworks=["PIPEDA"])
        applicable = await provider.get_applicable_frameworks(
            {"type": "social_media", "jurisdiction": "Canada"}
        )
        assert "PIPEDA" in applicable

    @pytest.mark.anyio
    async def test_jurisdiction_override(self) -> None:
        provider = LegalComplianceProvider(
            frameworks=["GDPR", "CCPA"],
            jurisdiction_overrides={"CH": "GDPR"},  # Switzerland → GDPR
        )
        applicable = await provider.get_applicable_frameworks(
            {"type": "social_media", "jurisdiction": "CH"}
        )
        assert applicable == ["GDPR"]

    @pytest.mark.anyio
    async def test_unknown_platform_type(self) -> None:
        """Non-standard platform types should not match framework applicability."""
        provider = LegalComplianceProvider(frameworks=["GDPR"])
        applicable = await provider.get_applicable_frameworks(
            {"type": "alien_database", "jurisdiction": "EU"}
        )
        assert "GDPR" not in applicable


# ============================================================================
# Request Templates
# ============================================================================


class TestRequestTemplates:
    """Test compliant request template generation."""

    @pytest.mark.anyio
    async def test_gdpr_erasure_template(self) -> None:
        provider = LegalComplianceProvider(frameworks=["GDPR"])
        template = await provider.generate_request_template("GDPR", "erasure")
        assert template["framework"] == "GDPR"
        assert template["request_type"] == "erasure"
        assert template["response_deadline_days"] == 30
        assert "required_fields" in template
        assert "data_subject_name" in template["required_fields"]
        assert "legal_basis" in template["required_fields"]
        assert "notes" in template

    @pytest.mark.anyio
    async def test_ccpa_deletion_template(self) -> None:
        provider = LegalComplianceProvider(frameworks=["CCPA"])
        template = await provider.generate_request_template("CCPA", "deletion")
        assert template["framework"] == "CCPA"
        assert template["response_deadline_days"] == 45
        assert "california_resident" in template["required_fields"]
        assert "notes" in template

    @pytest.mark.anyio
    async def test_unknown_framework_template(self) -> None:
        provider = LegalComplianceProvider()
        template = await provider.generate_request_template("NONEXISTENT", "erasure")
        assert "error" in template

    @pytest.mark.anyio
    async def test_unsupported_request_type_template(self) -> None:
        provider = LegalComplianceProvider(frameworks=["GDPR"])
        template = await provider.generate_request_template("GDPR", "nuclear_launch")
        assert "error" in template
        assert "supported" in template

    @pytest.mark.anyio
    async def test_pipeda_template(self) -> None:
        """PIPEDA template should work without framework-specific extras."""
        provider = LegalComplianceProvider(frameworks=["PIPEDA"])
        template = await provider.generate_request_template("PIPEDA", "access")
        assert template["framework"] == "PIPEDA"
        assert template["response_deadline_days"] == 30
        assert "optional_fields" in template
