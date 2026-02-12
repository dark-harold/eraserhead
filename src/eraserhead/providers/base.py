"""
😐 Provider Base Classes: Abstract interfaces for the provider ecosystem.

Three provider types, each handling a different aspect of digital erasure:
1. SearchProvider — Discovers your digital footprint (the "find" phase)
2. ScrubProvider — Handles deletion via appropriate procedures (the "erase" phase)
3. ComplianceProvider — Ensures legal compliance throughout (the "don't get sued" phase)

📺 The Interface Segregation Principle says: don't force a search engine
   to implement deletion methods. Harold agrees, having once tried to
   delete something from Google by shouting at it.

🌑 Every provider reports health, supports capability querying, and
   can be hot-swapped at runtime. Because if one fails at 3 AM,
   Harold would like to sleep through it.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


# ============================================================================
# Provider Type & Status Enums
# ============================================================================


class ProviderType(StrEnum):
    """Classification of provider functionality."""

    SEARCH = "search"  # Discovers digital footprint data
    SCRUB = "scrub"  # Handles deletion/removal requests
    COMPLIANCE = "compliance"  # Validates legal compliance
    VERIFICATION = "verification"  # Confirms erasure success


class ProviderStatus(StrEnum):
    """Current operational state of a provider."""

    UNINITIALIZED = "uninitialized"
    READY = "ready"
    BUSY = "busy"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    DISABLED = "disabled"
    SUSPENDED = "suspended"  # 😐 Temporarily paused, not dead yet


class ProviderCapability(StrEnum):
    """Granular capabilities a provider may support."""

    # Search capabilities
    SEARCH_BY_EMAIL = "search_by_email"
    SEARCH_BY_USERNAME = "search_by_username"
    SEARCH_BY_PHONE = "search_by_phone"
    SEARCH_BY_REAL_NAME = "search_by_real_name"
    SEARCH_BY_IMAGE = "search_by_image"
    SEARCH_CACHED_CONTENT = "search_cached_content"
    SEARCH_ARCHIVED_CONTENT = "search_archived_content"

    # Scrub capabilities
    SCRUB_GDPR_REQUEST = "scrub_gdpr_request"
    SCRUB_CCPA_REQUEST = "scrub_ccpa_request"
    SCRUB_DIRECT_API = "scrub_direct_api"
    SCRUB_FORM_SUBMISSION = "scrub_form_submission"
    SCRUB_EMAIL_REQUEST = "scrub_email_request"

    # Compliance capabilities
    COMPLIANCE_GDPR = "compliance_gdpr"
    COMPLIANCE_CCPA = "compliance_ccpa"
    COMPLIANCE_RIGHT_TO_FORGET = "compliance_right_to_forget"
    COMPLIANCE_DATA_PORTABILITY = "compliance_data_portability"

    # Verification capabilities
    VERIFY_DELETION = "verify_deletion"
    VERIFY_CACHE_CLEAR = "verify_cache_clear"
    VERIFY_SEARCH_REMOVAL = "verify_search_removal"


class ProviderEventType(StrEnum):
    """Events emitted by providers for subscriber notification."""

    PROVIDER_REGISTERED = "provider_registered"
    PROVIDER_REMOVED = "provider_removed"
    PROVIDER_STATUS_CHANGED = "provider_status_changed"
    SEARCH_STARTED = "search_started"
    SEARCH_RESULT = "search_result"
    SEARCH_COMPLETED = "search_completed"
    SCRUB_STARTED = "scrub_started"
    SCRUB_COMPLETED = "scrub_completed"
    SCRUB_FAILED = "scrub_failed"
    COMPLIANCE_CHECK_PASSED = "compliance_check_passed"
    COMPLIANCE_CHECK_FAILED = "compliance_check_failed"
    RATE_LIMIT_HIT = "rate_limit_hit"
    ERROR_OCCURRED = "error_occurred"


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class ProviderInfo:
    """
    Metadata describing a provider's identity and capabilities.

    😐 Every provider must identify itself. Anonymous providers
    are just as suspicious as anonymous network traffic.
    """

    provider_id: str
    name: str
    provider_type: ProviderType
    version: str = "0.1.0"
    description: str = ""
    capabilities: set[ProviderCapability] = field(default_factory=set)
    homepage: str = ""
    requires_auth: bool = False
    # 😐 Rate limiting metadata so the registry can schedule intelligently
    max_requests_per_minute: int = 60
    supports_batch: bool = False


@dataclass
class ProviderHealth:
    """
    Health status report from a provider.

    🌑 If a provider reports healthy but isn't, that's a lie.
    Harold monitors independently.
    """

    is_healthy: bool
    status: ProviderStatus
    last_check: float = field(default_factory=time.time)
    error_message: str | None = None
    latency_ms: float = 0.0
    requests_remaining: int | None = None  # For rate-limited APIs
    uptime_seconds: float = 0.0


@dataclass
class ProviderEvent:
    """
    An event emitted by a provider or the registry.

    Subscribers receive these to react to system changes.
    """

    event_type: ProviderEventType
    provider_id: str
    timestamp: float = field(default_factory=time.time)
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """
    A single result from a search provider.

    Represents one piece of your digital footprint found online.

    😐 Each of these is something someone shouldn't know about you.
    """

    provider_id: str
    source_url: str
    source_platform: str
    content_type: str  # post, profile, comment, cached_page, etc.
    content_preview: str = ""
    confidence: float = 1.0  # 0.0-1.0 how confident the match is
    metadata: dict[str, Any] = field(default_factory=dict)
    found_at: float = field(default_factory=time.time)
    removal_difficulty: str = "unknown"  # easy, moderate, hard, legal_required
    applicable_laws: list[str] = field(default_factory=list)  # GDPR, CCPA, etc.


@dataclass
class ScrubRequest:
    """
    A request to remove content through appropriate procedures.

    🌑 This is not a deletion — it's a formal request for removal
    through legal or API-defined channels. Harold does things properly.
    """

    request_id: str
    provider_id: str
    target_url: str
    target_platform: str
    content_type: str
    legal_basis: str = ""  # GDPR Art. 17, CCPA, etc.
    requester_identity: dict[str, str] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)
    method: str = "api"  # api, form, email, legal
    created_at: float = field(default_factory=time.time)


@dataclass
class ScrubResult:
    """
    Result of a scrub/removal request.
    """

    request_id: str
    success: bool
    method_used: str = ""
    reference_number: str = ""  # Platform's tracking/case number
    expected_completion: str = ""  # When removal should be effective
    error_message: str | None = None
    completed_at: float = field(default_factory=time.time)
    requires_followup: bool = False
    followup_date: str = ""


@dataclass
class ComplianceCheckResult:
    """
    Result of a compliance validation check.

    😐 If this fails, Harold does NOT proceed. Legal risk is
    the one thing Harold takes more seriously than key management.
    """

    provider_id: str
    is_compliant: bool
    framework: str  # GDPR, CCPA, etc.
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    checked_at: float = field(default_factory=time.time)


# ============================================================================
# Abstract Provider Base
# ============================================================================


class BaseProvider(ABC):
    """
    😐 Base class for all EraserHead providers.

    Provides common lifecycle management: initialize, health check,
    status reporting, and teardown. Subclasses implement domain-specific
    methods.

    🌑 Every provider MUST support health checks. Trust but verify.
    Actually, don't trust. Just verify.
    """

    def __init__(self, info: ProviderInfo) -> None:
        self._info = info
        self._status = ProviderStatus.UNINITIALIZED
        self._initialized_at: float = 0.0
        self._last_error: str | None = None

    @property
    def info(self) -> ProviderInfo:
        """Provider metadata."""
        return self._info

    @property
    def provider_id(self) -> str:
        """Shortcut to provider ID."""
        return self._info.provider_id

    @property
    def status(self) -> ProviderStatus:
        """Current operational status."""
        return self._status

    @property
    def is_ready(self) -> bool:
        """Check if provider is ready for operations."""
        return self._status == ProviderStatus.READY

    async def initialize(self, config: dict[str, Any] | None = None) -> bool:
        """
        Initialize the provider with optional configuration.

        Returns True on success.
        """
        try:
            success = await self._do_initialize(config or {})
            if success:
                self._status = ProviderStatus.READY
                self._initialized_at = time.time()
            else:
                self._status = ProviderStatus.ERROR
            return success
        except Exception as e:
            self._status = ProviderStatus.ERROR
            self._last_error = str(e)
            return False

    async def health_check(self) -> ProviderHealth:
        """
        Perform a health check.

        😐 Providers that can't report health are like employees
        who never answer emails. Concerning.
        """
        try:
            health = await self._do_health_check()
            self._status = health.status
            return health
        except Exception as e:
            self._status = ProviderStatus.ERROR
            self._last_error = str(e)
            return ProviderHealth(
                is_healthy=False,
                status=ProviderStatus.ERROR,
                error_message=str(e),
            )

    async def teardown(self) -> None:
        """Clean shutdown of the provider."""
        try:
            await self._do_teardown()
        finally:
            self._status = ProviderStatus.DISABLED

    def has_capability(self, capability: ProviderCapability) -> bool:
        """Check if this provider supports a specific capability."""
        return capability in self._info.capabilities

    # ========================================================================
    # Abstract methods for subclass implementation
    # ========================================================================

    @abstractmethod
    async def _do_initialize(self, config: dict[str, Any]) -> bool:
        """Provider-specific initialization logic."""
        ...

    @abstractmethod
    async def _do_health_check(self) -> ProviderHealth:
        """Provider-specific health check."""
        ...

    async def _do_teardown(self) -> None:
        """Provider-specific cleanup. Override if needed."""
        pass


# ============================================================================
# Search Provider
# ============================================================================


class SearchProvider(BaseProvider):
    """
    😐 Abstract search provider for discovering digital footprints.

    Implementations search specific platforms, search engines, data brokers,
    or cached/archived content to find traces of a user's online presence.

    📺 The story of finding yourself online is rarely a happy one.
    Each search result is a reminder that the internet never forgets.

    🌑 Search providers MUST:
    - Respect rate limits (don't DDoS search engines)
    - Not create additional footprints (use anonymized queries)
    - Route through Anemochory when available
    - Log what was searched (for audit trail) but NOT the results
      (those are ephemeral and belong to the user)
    """

    @abstractmethod
    async def search(
        self,
        query: str,
        *,
        search_type: str = "general",
        max_results: int = 50,
        metadata: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """
        Search for digital footprint data.

        Args:
            query: Search query (email, username, phone, name, etc.)
            search_type: Category of search (email, username, phone, name, image)
            max_results: Maximum results to return
            metadata: Additional search parameters

        Returns:
            List of search results found
        """
        ...

    async def search_by_email(self, email: str, **kwargs: Any) -> list[SearchResult]:
        """Convenience: search by email address."""
        if not self.has_capability(ProviderCapability.SEARCH_BY_EMAIL):
            return []
        return await self.search(email, search_type="email", **kwargs)

    async def search_by_username(self, username: str, **kwargs: Any) -> list[SearchResult]:
        """Convenience: search by username."""
        if not self.has_capability(ProviderCapability.SEARCH_BY_USERNAME):
            return []
        return await self.search(username, search_type="username", **kwargs)


# ============================================================================
# Scrub Provider
# ============================================================================


class ScrubProvider(BaseProvider):
    """
    😐 Abstract scrub provider for handling content removal.

    Handles the actual removal of content through appropriate channels:
    - Direct API calls (platform-specific)
    - GDPR/CCPA formal requests
    - Form submissions
    - Email-based requests

    📺 Deletion is never as simple as pressing delete. Each platform
    has its own bureaucracy, and Harold navigates all of it.

    🌑 Scrub providers MUST:
    - Operate only through legal/authorized channels
    - Maintain audit trail of all requests
    - Verify removal after request
    - Handle request tracking (case numbers, follow-ups)
    """

    @abstractmethod
    async def submit_removal(self, request: ScrubRequest) -> ScrubResult:
        """
        Submit a content removal request through the appropriate procedure.

        This may be an API call, form submission, GDPR request email, etc.
        depending on the platform and legal basis.

        Args:
            request: The removal request with all required evidence

        Returns:
            Result including tracking information
        """
        ...

    @abstractmethod
    async def check_removal_status(self, request_id: str) -> ScrubResult:
        """
        Check the status of a previously submitted removal request.

        Args:
            request_id: The ID of the original request

        Returns:
            Updated result with current status
        """
        ...

    @abstractmethod
    async def get_supported_methods(self) -> list[str]:
        """
        Return the removal methods this provider supports.

        e.g., ["api", "gdpr_request", "form", "email"]
        """
        ...


# ============================================================================
# Compliance Provider
# ============================================================================


class ComplianceProvider(BaseProvider):
    """
    😐 Abstract compliance provider ensuring legal safety.

    Validates that actions comply with applicable regulations before
    they are executed. If compliance fails, the operation is BLOCKED.

    📺 The EU's GDPR, California's CCPA, and various other regulations
    give individuals rights over their data. These providers ensure
    Harold exercises those rights correctly.

    🌑 Compliance is NOT optional. Non-compliance means fines,
    lawsuits, and Harold having a very bad day. Every scrub action
    goes through compliance validation FIRST.
    """

    @abstractmethod
    async def validate_action(
        self,
        action_type: str,
        target: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ComplianceCheckResult:
        """
        Validate whether an action is legally compliant.

        Args:
            action_type: What's being done (search, delete, archive, etc.)
            target: What it's being done to (URL, platform, resource)
            context: Additional context (jurisdiction, requester info)

        Returns:
            Compliance check result (blocks action if non-compliant)
        """
        ...

    @abstractmethod
    async def get_applicable_frameworks(
        self,
        target: dict[str, Any],
    ) -> list[str]:
        """
        Determine which legal frameworks apply to a target.

        Args:
            target: The target resource/platform

        Returns:
            List of applicable framework identifiers (GDPR, CCPA, etc.)
        """
        ...

    @abstractmethod
    async def generate_request_template(
        self,
        framework: str,
        request_type: str,
    ) -> dict[str, Any]:
        """
        Generate a compliant request template for a given framework.

        Args:
            framework: Legal framework (GDPR, CCPA, etc.)
            request_type: Type of request (erasure, access, portability)

        Returns:
            Template with required fields for a compliant request
        """
        ...
