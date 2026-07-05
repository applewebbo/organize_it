from suggestions.ai.base import AISuggestionError, TripSuggestionProvider
from suggestions.ai.gemini import GeminiProvider
from suggestions.ai.mistral import MistralProvider

# Adding a provider is one entry here plus its module.
_PROVIDERS = {
    "gemini": GeminiProvider,
    "mistral": MistralProvider,
}


def get_provider(name: str, api_key: str) -> TripSuggestionProvider:
    """Return a configured provider for ``name`` using the user's ``api_key``."""
    try:
        provider_cls = _PROVIDERS[name]
    except KeyError as exc:
        raise AISuggestionError(f"Unknown AI provider: {name}") from exc
    return provider_cls(api_key)
