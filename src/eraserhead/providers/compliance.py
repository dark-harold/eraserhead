"""
😐 Compliance Framework Provider: GDPR, CCPA, and beyond.

Concrete implementation of the ComplianceProvider that validates
actions against known legal frameworks before they are executed.

📺 The Compliance Story:
  In Europe, GDPR Article 17 gives you the Right to Erasure.
  In California, CCPA gives similar rights. In other jurisdictions,
  the legal landscape is a patchwork of varying protections.

  Harold navigates all of them. Harold is tired.

🌑 Compliance checking is BLOCKING for standard mode.
   If compliance fails, the operation does NOT proceed.
   This is not configurable. This is not negotiable.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from eraserhead.providers.base import (
    ComplianceCheckResult,
    ComplianceProvider,
    ProviderCapability,
    ProviderHealth,
    ProviderInfo,
    ProviderStatus,
    ProviderType,
)


# ============================================================================
# Legal Framework Definitions
# ============================================================================


@dataclass
class LegalFramework:
    """
    A legal framework that provides data protection rights.

    😐 Each framework is a set of rules that Harold must follow.
    Breaking them has consequences measured in Euros and prison time.
    """

    framework_id: str
    name: str
    jurisdiction: str
    requires_identity_proof: bool = True
    requires_data_subject_consent: bool = True
    response_deadline_days: int = 30
    supported_request_types: list[str] = field(default_factory=list)
    applicable_to: list[str] = field(default_factory=list)  # Platform types


# Pre-defined frameworks
GDPR = LegalFramework(
    framework_id="GDPR",
    name="General Data Protection Regulation",
    jurisdiction="EU/EEA",
    requires_identity_proof=True,
    requires_data_subject_consent=True,
    response_deadline_days=30,
    supported_request_types=[
        "erasure",  # Art. 17 — Right to Erasure
        "access",  # Art. 15 — Right of Access
        "portability",  # Art. 20 — Right to Data Portability
        "rectification",  # Art. 16 — Right to Rectification
        "objection",  # Art. 21 — Right to Object
    ],
    applicable_to=["social_media", "search_engine", "data_broker", "website"],
)

CCPA = LegalFramework(
    framework_id="CCPA",
    name="California Consumer Privacy Act",
    jurisdiction="California, USA",
    requires_identity_proof=True,
    requires_data_subject_consent=True,
    response_deadline_days=45,
    supported_request_types=[
        "deletion",  # Right to Delete
        "access",  # Right to Know
        "opt_out",  # Right to Opt-Out of Sale
    ],
    applicable_to=["social_media", "search_engine", "data_broker", "website"],
)

PIPEDA = LegalFramework(
    framework_id="PIPEDA",
    name="Personal Information Protection and Electronic Documents Act",
    jurisdiction="Canada",
    requires_identity_proof=True,
    requires_data_subject_consent=True,
    response_deadline_days=30,
    supported_request_types=["access", "correction", "deletion"],
    applicable_to=["social_media", "search_engine", "data_broker", "website"],
)

LGPD = LegalFramework(
    framework_id="LGPD",
    name="Lei Geral de Proteção de Dados",
    jurisdiction="Brazil",
    requires_identity_proof=True,
    requires_data_subject_consent=True,
    response_deadline_days=15,
    supported_request_types=["erasure", "access", "portability", "correction"],
    applicable_to=["social_media", "search_engine", "data_broker", "website"],
)

# Framework registry
FRAMEWORKS: dict[str, LegalFramework] = {
    "GDPR": GDPR,
    "CCPA": CCPA,
    "PIPEDA": PIPEDA,
    "LGPD": LGPD,
}


# ============================================================================
# Compliance Provider Implementation
# ============================================================================


class LegalComplianceProvider(ComplianceProvider):
    """
    😐 Validates actions against applicable legal frameworks.

    Checks that:
    1. The action type is supported by applicable frameworks
    2. Required identity proof is available
    3. Data subject consent is documented
    4. The request will be made through proper channels

    📺 Harold is not a lawyer. But Harold follows legal advice
    very carefully, because Harold has seen what happens when
    software developers ignore privacy law.

    🌑 This provider blocks non-compliant actions. Period.
    """

    def __init__(
        self,
        frameworks: list[str] | None = None,
        jurisdiction_overrides: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            info=ProviderInfo(
                provider_id="compliance-legal",
                name="Legal Compliance Framework",
                provider_type=ProviderType.COMPLIANCE,
                version="0.1.0",
                description="Validates actions against GDPR, CCPA, and other frameworks",
                capabilities={
                    ProviderCapability.COMPLIANCE_GDPR,
                    ProviderCapability.COMPLIANCE_CCPA,
                    ProviderCapability.COMPLIANCE_RIGHT_TO_FORGET,
                    ProviderCapability.COMPLIANCE_DATA_PORTABILITY,
                },
            )
        )
        self._active_frameworks = {
            fid: FRAMEWORKS[fid] for fid in (frameworks or ["GDPR", "CCPA"]) if fid in FRAMEWORKS
        }
        self._jurisdiction_overrides = jurisdiction_overrides or {}
        self._check_history: list[ComplianceCheckResult] = []

    async def _do_initialize(self, config: dict[str, Any]) -> bool:
        """Initialize with optional framework configuration."""
        if "frameworks" in config:
            self._active_frameworks = {
                fid: FRAMEWORKS[fid] for fid in config["frameworks"] if fid in FRAMEWORKS
            }
        return True

    async def _do_health_check(self) -> ProviderHealth:
        """Compliance provider is always healthy if frameworks are loaded."""
        return ProviderHealth(
            is_healthy=bool(self._active_frameworks),
            status=ProviderStatus.READY if self._active_frameworks else ProviderStatus.ERROR,
            error_message=None if self._active_frameworks else "No frameworks configured",
        )

    async def validate_action(
        self,
        action_type: str,
        target: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ComplianceCheckResult:
        """
        Validate an action against all applicable frameworks.

        Args:
            action_type: e.g., "erasure", "search", "access"
            target: Target details (platform, url, resource_type)
            context: Requester info, jurisdiction, authorization

        Returns:
            ComplianceCheckResult (blocks if non-compliant)
        """
        ctx = context or {}
        issues: list[str] = []
        recommendations: list[str] = []

        # Determine applicable frameworks
        applicable = await self.get_applicable_frameworks(target)
        if not applicable:
            recommendations.append(
                "No specific privacy frameworks identified for this target. "
                "Proceeding with general best practices."
            )

        for framework_id in applicable:
            framework = self._active_frameworks.get(framework_id)
            if not framework:
                continue

            # Check 1: Action type supported
            if action_type not in framework.supported_request_types:
                issues.append(
                    f"[{framework_id}] Action '{action_type}' is not a recognized "
                    f"request type. Supported: {framework.supported_request_types}"
                )

            # Check 2: Identity proof required
            if framework.requires_identity_proof:
                if not ctx.get("identity_proof"):
                    issues.append(
                        f"[{framework_id}] Identity proof required. "
                        f"Provide 'identity_proof' in context."
                    )

            # Check 3: Data subject consent
            if framework.requires_data_subject_consent:
                if not ctx.get("data_subject_consent"):
                    issues.append(
                        f"[{framework_id}] Data subject consent required. "
                        f"Provide 'data_subject_consent' in context."
                    )

            # Check 4: Proper channels
            method = target.get("method", "api")
            if method == "direct_deletion" and framework_id in ("GDPR", "CCPA"):
                issues.append(
                    f"[{framework_id}] Direct deletion bypasses formal request process. "
                    f"Use GDPR Art. 17 / CCPA deletion request instead."
                )
                recommendations.append(
                    f"Submit a formal {framework_id} request via the platform's "
                    f"designated privacy contact or data protection officer."
                )

        is_compliant = len(issues) == 0

        result = ComplianceCheckResult(
            provider_id=self.provider_id,
            is_compliant=is_compliant,
            framework=", ".join(applicable) if applicable else "general",
            issues=issues,
            recommendations=recommendations,
        )

        self._check_history.append(result)
        return result

    async def get_applicable_frameworks(
        self,
        target: dict[str, Any],
    ) -> list[str]:
        """
        Determine which frameworks apply to a target.

        Uses jurisdiction and platform type to determine applicability.
        """
        applicable: list[str] = []
        target_type = target.get("type", "website")
        jurisdiction = target.get("jurisdiction", "")

        # Check jurisdiction overrides first
        if jurisdiction and jurisdiction in self._jurisdiction_overrides:
            override = self._jurisdiction_overrides[jurisdiction]
            if override in self._active_frameworks:
                return [override]

        for fid, framework in self._active_frameworks.items():
            # Check if target type is applicable
            if target_type in framework.applicable_to:
                # GDPR applies to EU data subjects regardless of company location
                if fid == "GDPR" and jurisdiction in (
                    "",
                    "EU",
                    "EEA",
                    "UK",
                    *[  # All EU member states
                        "AT",
                        "BE",
                        "BG",
                        "HR",
                        "CY",
                        "CZ",
                        "DK",
                        "EE",
                        "FI",
                        "FR",
                        "DE",
                        "GR",
                        "HU",
                        "IE",
                        "IT",
                        "LV",
                        "LT",
                        "LU",
                        "MT",
                        "NL",
                        "PL",
                        "PT",
                        "RO",
                        "SK",
                        "SI",
                        "ES",
                        "SE",
                    ],
                ):
                    applicable.append(fid)
                elif fid == "CCPA" and jurisdiction in ("", "US", "CA", "California"):
                    applicable.append(fid)
                elif fid == "PIPEDA" and jurisdiction in ("", "CA", "Canada"):
                    applicable.append(fid)
                elif fid == "LGPD" and jurisdiction in ("", "BR", "Brazil"):
                    applicable.append(fid)
                elif jurisdiction == "":  # Unknown jurisdiction — apply all
                    if fid not in applicable:
                        applicable.append(fid)

        return applicable

    async def generate_request_template(
        self,
        framework: str,
        request_type: str,
    ) -> dict[str, Any]:
        """
        Generate a compliant request template.

        Returns a dict with all required fields for a compliant
        data subject request under the specified framework.
        """
        fw = self._active_frameworks.get(framework)
        if not fw:
            return {"error": f"Unknown framework: {framework}"}

        if request_type not in fw.supported_request_types:
            return {
                "error": f"Request type '{request_type}' not supported by {framework}",
                "supported": fw.supported_request_types,
            }

        template: dict[str, Any] = {
            "framework": framework,
            "request_type": request_type,
            "jurisdiction": fw.jurisdiction,
            "response_deadline_days": fw.response_deadline_days,
            "required_fields": {
                "data_subject_name": "",
                "data_subject_email": "",
                "identity_proof_type": "",  # ID, utility bill, etc.
                "identity_proof_reference": "",
                "data_subject_consent": False,
                "request_description": "",
                "specific_data_referenced": [],
                "platform_or_controller": "",
            },
            "optional_fields": {
                "legal_representative": "",
                "previous_request_reference": "",
                "urgency_reason": "",
            },
        }

        # Framework-specific additions
        if framework == "GDPR":
            template["required_fields"]["legal_basis"] = "Article 17 — Right to Erasure"
            template["required_fields"]["dpo_contact"] = ""  # Data Protection Officer
            template["notes"] = (
                "Under GDPR Article 17, the controller must erase personal data "
                "without undue delay when: (a) data is no longer necessary, "
                "(b) consent is withdrawn, (c) data subject objects to processing, "
                "(d) data was unlawfully processed, (e) legal obligation, or "
                "(f) data was collected re: information society services to a child."
            )
        elif framework == "CCPA":
            template["required_fields"]["california_resident"] = True
            template["notes"] = (
                "Under CCPA, California residents have the right to request "
                "deletion of personal information collected by businesses. "
                "Businesses must verify the identity of the requestor."
            )

        return template

    @property
    def check_history(self) -> list[ComplianceCheckResult]:
        """All compliance checks performed."""
        return list(self._check_history)
