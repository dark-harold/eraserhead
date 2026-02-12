"""
😐 Tests for Operating Modes, Confirmation Ceremonies, and Containment

Testing the safety systems that prevent Harold from accidentally
deleting the internet.

🌑 harold-tester: Breaking safety systems with maximum paranoia.
"""

from __future__ import annotations

import time

import pytest

from eraserhead.modes.base import (
    ModeConfig,
    ModeManager,
    ModeViolation,
    OperatingMode,
    SafetyLevel,
)
from eraserhead.modes.confirmation import (
    ConfirmationCeremony,
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


# ============================================================================
# ModeConfig Tests
# ============================================================================


class TestModeConfig:
    """😐 Testing mode configurations — the rules of engagement."""

    def test_standard_defaults(self):
        config = ModeConfig.standard()
        assert config.mode == OperatingMode.STANDARD
        assert config.safety_level == SafetyLevel.STANDARD
        assert config.confirmations_required == 1
        assert config.enforce_compliance
        assert config.block_on_compliance_failure
        assert not config.allow_aggressive_scrub
        assert not config.allow_direct_deletion
        assert config.dry_run_default

    def test_contained_pentest_requires_cidrs(self):
        with pytest.raises(ModeViolation):
            ModeConfig.contained_pentest(allowed_cidrs=[])

    def test_contained_pentest_config(self):
        config = ModeConfig.contained_pentest(
            allowed_cidrs=["192.168.1.0/24"],
            gateway_boundary="192.168.1.1",
        )
        assert config.mode == OperatingMode.CONTAINED_PENTEST
        assert config.safety_level == SafetyLevel.CONTAINED
        assert config.confirmations_required == 3
        assert config.network_restricted
        assert config.allow_aggressive_scrub
        assert config.allow_direct_deletion
        assert not config.dry_run_default
        assert config.require_post_session_report

    def test_unrestricted_pentest_requires_cidrs(self):
        with pytest.raises(ModeViolation):
            ModeConfig.unrestricted_pentest(allowed_cidrs=[])

    def test_unrestricted_pentest_config(self):
        config = ModeConfig.unrestricted_pentest(
            allowed_cidrs=["10.0.0.0/16"],
            activation_reason="Lab test",
        )
        assert config.mode == OperatingMode.UNRESTRICTED_PENTEST
        assert config.safety_level == SafetyLevel.UNRESTRICTED
        assert config.confirmations_required == 5
        assert config.require_airgap_attestation
        assert config.allow_cache_poisoning
        assert config.session_timeout_minutes == 60

    def test_mode_expiration(self):
        config = ModeConfig.standard()
        config.session_timeout_minutes = 0  # Immediately expired
        config.activated_at = time.time() - 1
        assert config.is_expired()

    def test_mode_not_expired(self):
        config = ModeConfig.standard()
        config.activated_at = time.time()
        assert not config.is_expired()


# ============================================================================
# ModeManager Tests
# ============================================================================


class TestModeManager:
    """😐 Testing mode transitions — Harold's inner conflict manager."""

    @pytest.fixture
    def manager(self):
        return ModeManager()

    def test_starts_in_standard(self, manager):
        assert manager.current_mode == OperatingMode.STANDARD
        assert manager.is_standard
        assert not manager.is_pentest

    def test_activate_contained(self, manager):
        config = ModeConfig.contained_pentest(allowed_cidrs=["192.168.1.0/24"])
        manager.activate_mode(config, operator="harold")
        assert manager.current_mode == OperatingMode.CONTAINED_PENTEST
        assert manager.is_pentest
        assert not manager.is_standard

    def test_activate_unrestricted(self, manager):
        config = ModeConfig.unrestricted_pentest(allowed_cidrs=["10.0.0.0/16"])
        manager.activate_mode(config, operator="harold")
        assert manager.is_unrestricted
        assert manager.is_pentest

    def test_deactivate_returns_to_standard(self, manager):
        config = ModeConfig.contained_pentest(allowed_cidrs=["192.168.1.0/24"])
        manager.activate_mode(config, operator="harold")

        previous = manager.deactivate()
        assert previous.mode == OperatingMode.CONTAINED_PENTEST
        assert manager.is_standard

    def test_enforce_standard_blocks_aggressive(self, manager):
        with pytest.raises(ModeViolation):
            manager.enforce("aggressive_scrub")

    def test_enforce_standard_blocks_direct_deletion(self, manager):
        with pytest.raises(ModeViolation):
            manager.enforce("direct_deletion")

    def test_enforce_pentest_requires_target(self, manager):
        config = ModeConfig.contained_pentest(allowed_cidrs=["192.168.1.0/24"])
        manager.activate_mode(config, operator="harold")

        with pytest.raises(ModeViolation):
            manager.enforce("scrub")  # No target specified

    def test_enforce_pentest_with_target_ok(self, manager):
        config = ModeConfig.contained_pentest(allowed_cidrs=["192.168.1.0/24"])
        manager.activate_mode(config, operator="harold")
        # Should not raise
        manager.enforce("scrub", target="192.168.1.50")

    def test_expired_mode_auto_deactivates(self, manager):
        config = ModeConfig.contained_pentest(allowed_cidrs=["192.168.1.0/24"])
        config.session_timeout_minutes = 0
        config.activated_at = time.time() - 1
        manager.activate_mode(config, operator="harold")

        with pytest.raises(ModeViolation, match="expired"):
            manager.enforce("scrub", target="192.168.1.50")

        assert manager.is_standard

    def test_activation_history(self, manager):
        config = ModeConfig.contained_pentest(allowed_cidrs=["192.168.1.0/24"])
        manager.activate_mode(config, operator="harold")
        manager.deactivate()

        history = manager.get_history()
        assert len(history) == 2  # Activate + deactivate


# ============================================================================
# Confirmation Ceremony Tests
# ============================================================================


class TestConfirmationCeremony:
    """😐 Testing the confirmation ceremony — Harold's authorization ritual."""

    def test_standard_ceremony_single_step(self):
        ceremony = ConfirmationCeremony(
            mode="standard",
            operator="harold",
        )
        assert len(ceremony.steps) == 1
        assert not ceremony.is_complete

    def test_standard_ceremony_complete(self):
        ceremony = ConfirmationCeremony(mode="standard", operator="harold")
        accepted = ceremony.submit_response(1, "I UNDERSTAND")
        assert accepted
        assert ceremony.is_complete

    def test_standard_ceremony_wrong_response(self):
        ceremony = ConfirmationCeremony(mode="standard", operator="harold")
        accepted = ceremony.submit_response(1, "WRONG ANSWER")
        assert not accepted
        assert not ceremony.is_complete

    def test_contained_ceremony_three_steps(self):
        ceremony = ConfirmationCeremony(
            mode="contained_pentest",
            operator="harold",
            targets=["192.168.1.0/24"],
        )
        assert len(ceremony.steps) == 3

    def test_contained_ceremony_full_flow(self):
        ceremony = ConfirmationCeremony(
            mode="contained_pentest",
            operator="harold",
            targets=["192.168.1.0/24"],
        )

        # Step 1: Acknowledge
        assert ceremony.submit_response(1, "ACTIVATE CONTAINED PENTEST")
        assert ceremony.progress == "1/3 steps completed"

        # Step 2: Scope confirmation
        assert ceremony.submit_response(2, "SCOPE CONFIRMED")

        # Step 3: Challenge response — get the code from the step
        challenge = ceremony.steps[2].challenge_code
        assert ceremony.submit_response(3, challenge)

        assert ceremony.is_complete

    def test_contained_ceremony_out_of_order(self):
        ceremony = ConfirmationCeremony(
            mode="contained_pentest",
            operator="harold",
            targets=["192.168.1.0/24"],
        )
        # Try step 2 before step 1
        accepted = ceremony.submit_response(2, "SCOPE CONFIRMED")
        assert not accepted

    def test_unrestricted_ceremony_five_steps(self):
        ceremony = ConfirmationCeremony(
            mode="unrestricted_pentest",
            operator="harold",
            targets=["10.0.0.0/16"],
        )
        assert len(ceremony.steps) == 5

    def test_unrestricted_ceremony_full_flow(self):
        targets = ["10.0.0.0/16"]
        ceremony = ConfirmationCeremony(
            mode="unrestricted_pentest",
            operator="harold",
            targets=targets,
        )

        # Step 1: Risk acknowledgment
        assert ceremony.submit_response(1, "I ACKNOWLEDGE THE RISKS")

        # Step 2: Target confirmation
        assert ceremony.submit_response(2, "TARGETS CONFIRMED AND AUTHORIZED")

        # Step 3: Legal attestation
        assert ceremony.submit_response(3, "I ATTEST LEGAL AUTHORIZATION")

        # Step 4: Airgap attestation (with challenge code)
        challenge = ceremony.steps[3].challenge_code
        assert ceremony.submit_response(4, f"AIRGAPPED CONFIRMED {challenge}")

        # Step 5: Final confirmation
        final_phrase = (
            f"I AUTHORIZE UNRESTRICTED OPERATIONS ON {len(targets)} TARGETS AT MY OWN RISK"
        )
        assert ceremony.submit_response(5, final_phrase)

        assert ceremony.is_complete

    def test_unrestricted_airgap_not_airgapped(self):
        """Test the 'not airgapped' path."""
        ceremony = ConfirmationCeremony(
            mode="unrestricted_pentest",
            operator="harold",
            targets=["10.0.0.0/16"],
        )

        ceremony.submit_response(1, "I ACKNOWLEDGE THE RISKS")
        ceremony.submit_response(2, "TARGETS CONFIRMED AND AUTHORIZED")
        ceremony.submit_response(3, "I ATTEST LEGAL AUTHORIZATION")

        challenge = ceremony.steps[3].challenge_code
        assert ceremony.submit_response(4, f"NOT AIRGAPPED I ACCEPT ADDITIONAL RISK {challenge}")

    def test_ceremony_completion_result(self):
        ceremony = ConfirmationCeremony(mode="standard", operator="harold")
        ceremony.submit_response(1, "I UNDERSTAND")

        result = ceremony.complete()
        assert result.all_steps_completed
        assert result.steps_completed == 1
        assert result.steps_total == 1
        assert result.completion_hash  # Has a hash
        assert result.failure_reason is None

    def test_ceremony_incomplete_result(self):
        ceremony = ConfirmationCeremony(mode="standard", operator="harold")
        result = ceremony.complete()
        assert not result.all_steps_completed
        assert result.failure_reason is not None

    def test_ceremony_audit_trail(self):
        ceremony = ConfirmationCeremony(mode="standard", operator="harold")
        ceremony.submit_response(1, "WRONG")  # Fail
        ceremony.submit_response(1, "I UNDERSTAND")  # Succeed

        attempts = ceremony.attempts
        assert len(attempts) == 2
        assert not attempts[0]["accepted"]
        assert attempts[1]["accepted"]


# ============================================================================
# Network Containment Tests
# ============================================================================


class TestNetworkContainment:
    """
    😐 Testing network containment — Harold's invisible fence.

    🌑 These tests verify that dangerous targets are ALWAYS blocked
    and legitimate targets pass through. Getting these wrong means
    either breaking the tool or breaking the internet.
    """

    @pytest.fixture
    def containment(self):
        """Standard containment for a /24 subnet."""
        config = ContainmentConfig(
            allowed_cidrs=["192.168.1.0/24"],
            denied_cidrs=[],
        )
        return NetworkContainment(config)

    @pytest.fixture
    def strict_containment(self):
        """Containment with gateway boundary."""
        config = ContainmentConfig(
            allowed_cidrs=["10.0.1.0/24"],
            denied_cidrs=["10.0.1.1/32"],  # Deny the gateway
            gateway_boundary="10.0.1.1",
        )
        return NetworkContainment(config)

    def test_valid_target_in_range(self, containment):
        assert containment.validate_target("192.168.1.50")

    def test_valid_subnet_in_range(self, containment):
        assert containment.validate_target("192.168.1.128/25")

    def test_target_outside_range(self, containment):
        with pytest.raises(ContainmentViolation):
            containment.validate_target("192.168.2.1")

    def test_target_outside_range_different_class(self, containment):
        with pytest.raises(ContainmentViolation):
            containment.validate_target("10.0.0.1")

    # -- Nuclear denial tests (THE most important tests) --

    def test_nuclear_denial_all_ipv4(self, containment):
        """🌑 0.0.0.0/0 must ALWAYS be blocked."""
        with pytest.raises(ContainmentViolation, match="NUCLEAR"):
            containment.validate_target("0.0.0.0/0")

    def test_nuclear_denial_all_ipv6(self, containment):
        """🌑 ::/0 must ALWAYS be blocked."""
        with pytest.raises(ContainmentViolation, match="NUCLEAR"):
            containment.validate_target("::/0")

    def test_nuclear_denial_half_internet_low(self, containment):
        """🌑 0.0.0.0/1 (half the internet) must be blocked."""
        with pytest.raises(ContainmentViolation, match="NUCLEAR"):
            containment.validate_target("0.0.0.0/1")

    def test_nuclear_denial_half_internet_high(self, containment):
        """🌑 128.0.0.0/1 (other half) must be blocked."""
        with pytest.raises(ContainmentViolation, match="NUCLEAR"):
            containment.validate_target("128.0.0.0/1")

    # -- CIDR breadth tests --

    def test_cidr_too_broad_ipv4(self, containment):
        """Reject CIDRs broader than /16."""
        with pytest.raises(ContainmentViolation, match="too broad"):
            containment.validate_target("10.0.0.0/8")

    def test_cidr_acceptable_breadth(self):
        """Accept /16 CIDR within allowed range."""
        config = ContainmentConfig(
            allowed_cidrs=["10.0.0.0/16"],
            min_prefix_length_v4=16,
        )
        c = NetworkContainment(config)
        assert c.validate_target("10.0.0.0/16")

    # -- Explicit denial tests --

    def test_explicit_deny_overrides_allow(self, strict_containment):
        """Denied ranges take precedence over allowed."""
        with pytest.raises(ContainmentViolation):
            strict_containment.validate_target("10.0.1.1")

    def test_allowed_not_denied(self, strict_containment):
        """Non-denied addresses in allowed range pass."""
        assert strict_containment.validate_target("10.0.1.50")

    # -- Gateway boundary tests --

    def test_gateway_boundary_violation(self):
        """Target containing the gateway is blocked."""
        config = ContainmentConfig(
            allowed_cidrs=["10.0.0.0/16"],
            gateway_boundary="10.0.1.1",
        )
        c = NetworkContainment(config)
        with pytest.raises(ContainmentViolation, match="gateway"):
            c.validate_target("10.0.1.0/24")  # Contains gateway

    def test_gateway_single_ip_ok(self):
        """Single IP not containing gateway is fine."""
        config = ContainmentConfig(
            allowed_cidrs=["10.0.0.0/16"],
            gateway_boundary="10.0.1.1",
        )
        c = NetworkContainment(config)
        assert c.validate_target("10.0.2.50")

    # -- Batch validation tests --

    def test_batch_validation(self, containment):
        results = containment.validate_targets(
            [
                "192.168.1.10",  # Valid
                "192.168.1.20",  # Valid
                "10.0.0.1",  # Invalid — outside range
            ]
        )
        assert results["192.168.1.10"] is True
        assert results["192.168.1.20"] is True
        assert isinstance(results["10.0.0.1"], str)  # Error message

    def test_is_target_safe(self, containment):
        assert containment.is_target_safe("192.168.1.10")
        assert not containment.is_target_safe("10.0.0.1")

    # -- Violation tracking --

    def test_violations_recorded(self, containment):
        containment.is_target_safe("10.0.0.1")  # Will fail silently
        assert containment.violation_count >= 1

    # -- Summary --

    def test_summary(self, containment):
        summary = containment.summary()
        assert "allowed_ranges" in summary
        assert "violations_recorded" in summary

    # -- No allowed ranges configured --

    def test_no_allowed_ranges(self):
        config = ContainmentConfig(allowed_cidrs=[])
        c = NetworkContainment(config)
        with pytest.raises(ContainmentViolation, match="No allowed"):
            c.validate_target("192.168.1.1")

    # -- Invalid target format --

    def test_invalid_target_format(self, containment):
        with pytest.raises(ContainmentViolation, match="Invalid"):
            containment.validate_target("not-an-ip")


# ============================================================================
# Target Validation Tests
# ============================================================================


class TestTargetValidator:
    """😐 Testing target validation — catching bad targets before they escape."""

    @pytest.fixture
    def validator(self):
        return TargetValidator()

    @pytest.fixture
    def strict_validator(self):
        return TargetValidator(strict_mode=True, max_targets=5)

    def test_valid_ip_target(self, validator):
        assert validator.validate_ip_target("192.168.1.50")

    def test_valid_cidr_target(self, validator):
        assert validator.validate_ip_target("192.168.1.0/24")

    def test_nuclear_target_blocked(self, validator):
        """🌑🌑🌑 The big one: 0.0.0.0/0 must NEVER pass."""
        with pytest.raises(TargetValidationError, match="NUCLEAR"):
            validator.validate_ip_target("0.0.0.0/0")

    def test_nuclear_ipv6_blocked(self, validator):
        """🌑 ::/0 must also be blocked."""
        with pytest.raises(TargetValidationError, match="NUCLEAR"):
            validator.validate_ip_target("::/0")

    def test_nuclear_unspecified_blocked(self, validator):
        """🌑 0.0.0.0 alone must be blocked."""
        with pytest.raises(TargetValidationError, match="NUCLEAR"):
            validator.validate_ip_target("0.0.0.0")

    def test_nuclear_ipv6_unspecified_blocked(self, validator):
        """🌑 :: alone must be blocked."""
        with pytest.raises(TargetValidationError, match="NUCLEAR"):
            validator.validate_ip_target("::")

    def test_broad_cidr_blocked(self, validator):
        with pytest.raises(TargetValidationError, match="broad"):
            validator.validate_ip_target("10.0.0.0/8")

    def test_empty_target_blocked(self, validator):
        with pytest.raises(TargetValidationError):
            validator.validate_ip_target("")

    def test_invalid_target_blocked(self, validator):
        with pytest.raises(TargetValidationError, match="Invalid"):
            validator.validate_ip_target("not-an-ip")

    def test_multicast_blocked(self, validator):
        with pytest.raises(TargetValidationError, match="multicast"):
            validator.validate_ip_target("224.0.0.1")

    def test_domain_validation(self, validator):
        assert validator.validate_domain_target("example.com")

    def test_wildcard_tld_blocked(self, validator):
        with pytest.raises(TargetValidationError, match="suspicious"):
            validator.validate_domain_target("*.com")

    def test_empty_domain_blocked(self, validator):
        with pytest.raises(TargetValidationError, match="Empty"):
            validator.validate_domain_target("")

    def test_identity_validation(self, validator):
        assert validator.validate_identity_target("harold@example.com")

    def test_empty_identity_blocked(self, validator):
        with pytest.raises(TargetValidationError):
            validator.validate_identity_target("")

    def test_too_long_identity_blocked(self, validator):
        with pytest.raises(TargetValidationError, match="too long"):
            validator.validate_identity_target("x" * 501)

    # -- Scope validation --

    def test_validate_scope(self, validator):
        scope = TargetScope(
            ip_targets=["192.168.1.0/24"],
            domain_targets=["example.com"],
            identity_targets=["harold@example.com"],
        )
        assert validator.validate_scope(scope)

    def test_empty_scope_rejected(self, validator):
        scope = TargetScope()
        with pytest.raises(TargetValidationError, match="Empty"):
            validator.validate_scope(scope)

    def test_too_many_targets(self, strict_validator):
        scope = TargetScope(
            ip_targets=[f"192.168.1.{i}" for i in range(10)],
        )
        with pytest.raises(TargetValidationError, match="exceeds maximum"):
            strict_validator.validate_scope(scope)

    def test_report(self, validator):
        report = validator.get_report()
        assert "warnings_count" in report
        assert "errors_count" in report
