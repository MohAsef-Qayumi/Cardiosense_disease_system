"""Application-specific exceptions for CardioSense."""


class CardioSenseError(Exception):
    """Base application exception with an HTTP-like status code."""

    def __init__(self, message: str, status_code: int = 400, code: str = "cardiosense_error"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class ConfigurationError(CardioSenseError):
    """Raised when runtime configuration is invalid."""

    def __init__(self, message: str):
        super().__init__(message, status_code=500, code="configuration_error")


class DependencyUnavailableError(CardioSenseError):
    """Raised when an optional runtime dependency is not installed."""

    def __init__(self, message: str):
        super().__init__(message, status_code=500, code="dependency_unavailable")


class ModelNotReadyError(CardioSenseError):
    """Raised when no active model can be served."""

    def __init__(self, message: str):
        super().__init__(message, status_code=503, code="model_not_ready")


class PersistenceError(CardioSenseError):
    """Raised when repository operations fail."""

    def __init__(self, message: str):
        super().__init__(message, status_code=500, code="persistence_error")


class NotFoundError(CardioSenseError):
    """Raised when a requested entity does not exist."""

    def __init__(self, message: str):
        super().__init__(message, status_code=404, code="not_found")


class IdempotencyConflictError(CardioSenseError):
    """Raised when an idempotency key is reused with a different payload."""

    def __init__(self, message: str):
        super().__init__(message, status_code=409, code="idempotency_conflict")


class ConflictError(CardioSenseError):
    """Raised when a resource conflicts with existing state."""

    def __init__(self, message: str):
        super().__init__(message, status_code=409, code="conflict")


class AuthenticationError(CardioSenseError):
    """Raised when authentication credentials are invalid."""

    def __init__(self, message: str):
        super().__init__(message, status_code=401, code="authentication_failed")
