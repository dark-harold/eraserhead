"""
😐 EraserHead Provider Architecture: Modular Subscriber/Provider Model

A pluggable system for search, scrubbing, and compliance providers.
Register providers, subscribe to events, and let Harold orchestrate
the systematic erasure of digital footprints.

📺 The Provider Pattern Story:
  Monolithic deletion engines are brittle. Each platform, search engine,
  and compliance framework is a unique snowflake of pain. The provider
  model lets each snowflake melt independently.

🌑 Dark Harold: Extensibility is just another word for "more things
   that can break." But at least they break in isolation.
"""

from eraserhead.providers.base import (
    ComplianceProvider,
    ProviderCapability,
    ProviderEvent,
    ProviderEventType,
    ProviderHealth,
    ProviderInfo,
    ProviderStatus,
    ProviderType,
    ScrubProvider,
    SearchProvider,
)
from eraserhead.providers.registry import (
    EventSubscriber,
    ProviderRegistry,
)


__all__ = [
    "ComplianceProvider",
    "EventSubscriber",
    "ProviderCapability",
    "ProviderEvent",
    "ProviderEventType",
    "ProviderHealth",
    "ProviderInfo",
    "ProviderRegistry",
    "ProviderStatus",
    "ProviderType",
    "ScrubProvider",
    "SearchProvider",
]
