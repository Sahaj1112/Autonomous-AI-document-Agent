class DomainError(Exception):
    """Base exception for all domain-specific exceptions."""
    pass


class PlanningError(DomainError):
    """Raised when task planning fails or LLM planning response is malformed."""
    pass


class ExecutionError(DomainError):
    """Raised when sequential task execution fails completely."""
    pass


class ReflectionError(DomainError):
    """Raised when self-check verification process encounters critical failures."""
    pass


class DocumentGenerationError(DomainError):
    """Raised when the final document rendering adapter fails."""
    pass


