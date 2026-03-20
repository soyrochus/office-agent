from __future__ import annotations


class OffagentError(RuntimeError):
    """Base runtime error for Office Agent failures."""


class InvalidArgumentsError(ValueError):
    """Raised when user input is syntactically or semantically invalid."""


class TargetNotFoundError(LookupError):
    """Raised when a document, item, or indexed target cannot be resolved."""


class TargetNotEditableError(OffagentError):
    """Raised when a target exists but the requested edit is unsupported."""


class PolicyRefusedError(OffagentError):
    """Raised when a configured path policy refuses an operation."""


class StaleLocatorError(TargetNotFoundError):
    """Raised when a previously indexed target no longer resolves safely."""


class NoEmbeddingsError(TargetNotFoundError):
    """Raised when semantic retrieval is requested without indexed embeddings."""
