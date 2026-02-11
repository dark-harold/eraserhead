"""
😐 Search Provider Implementations: Finding your digital footprint.

Concrete search provider implementations for various sources.
Each providers searches a specific platform or service to locate
traces of a user's online presence.

📺 Finding yourself online is like hide and seek, except you're
   hiding and the entire internet is seeking. These providers
   help you find what the internet found.

🌑 Search providers MUST:
   - Not create additional footprints while searching
   - Respect rate limits
   - Route through Anemochory when available
   - Be legally compliant search methods only
"""

from eraserhead.providers.search.providers import (
    CacheArchiveSearchProvider,
    DataBrokerSearchProvider,
    SearchEngineProvider,
    SocialMediaSearchProvider,
    create_default_search_providers,
)


__all__ = [
    "CacheArchiveSearchProvider",
    "DataBrokerSearchProvider",
    "SearchEngineProvider",
    "SocialMediaSearchProvider",
    "create_default_search_providers",
]
