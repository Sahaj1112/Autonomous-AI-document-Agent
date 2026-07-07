"""
Infrastructure exception hierarchy.

These exceptions are internal to the infrastructure layer and must NOT be imported
by the domain or application layers. The application layer catches these at the
adapter boundary and re-raises them as appropriate domain exceptions when required.
"""


class InfrastructureError(Exception):
    """Base exception for all infrastructure-level failures."""
    pass


class LLMAdapterError(InfrastructureError):
    """Raised when the LLM adapter encounters a non-retryable API error."""
    pass


class LLMRateLimitError(LLMAdapterError):
    """Raised when the LLM provider returns a rate-limit (429) response after all retries."""
    pass


class LLMEmptyResponseError(LLMAdapterError):
    """Raised when the LLM returns a response with empty or null content."""
    pass


class ConfigurationError(InfrastructureError):
    """Raised when infrastructure configuration is missing or invalid (e.g. missing env vars)."""
    pass


class StorageError(InfrastructureError):
    """Raised when a file storage operation fails."""
    pass
