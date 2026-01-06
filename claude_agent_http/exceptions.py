"""
Custom exceptions for Claude Agent HTTP service.
"""


class ClaudeAgentError(Exception):
    """Base exception for all Claude Agent errors."""
    pass


class SessionNotFoundError(ClaudeAgentError):
    """Session does not exist or has expired."""
    pass


class SessionBusyError(ClaudeAgentError):
    """Session is currently processing another request."""
    pass


class SessionExpiredError(ClaudeAgentError):
    """Session has expired due to TTL."""
    pass


class ClientCreationError(ClaudeAgentError):
    """Failed to create Claude SDK client."""
    pass


class MessageSendError(ClaudeAgentError):
    """Failed to send message to Claude."""
    pass


class PathSecurityError(ClaudeAgentError):
    """Path security violation (traversal, escape, etc.)."""
    pass


class StorageError(ClaudeAgentError):
    """Storage operation failed."""
    pass


class ConfigurationError(ClaudeAgentError):
    """Configuration error."""
    pass
