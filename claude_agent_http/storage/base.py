"""
Abstract base class for session storage.
"""
from abc import ABC, abstractmethod
from typing import Optional, List

from ..models import SessionInfo


class SessionStorage(ABC):
    """Abstract base class for session storage implementations."""

    @abstractmethod
    async def save(self, session_id: str, session_info: SessionInfo) -> bool:
        """
        Save session information.

        Args:
            session_id: Session identifier
            session_info: Session information to save

        Returns:
            True if saved successfully
        """
        pass

    @abstractmethod
    async def get(self, session_id: str) -> Optional[SessionInfo]:
        """
        Get session information.

        Args:
            session_id: Session identifier

        Returns:
            SessionInfo if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete(self, session_id: str) -> bool:
        """
        Delete session.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def touch(self, session_id: str) -> bool:
        """
        Update session last_active_at and increment message_count.

        Args:
            session_id: Session identifier

        Returns:
            True if updated, False if not found
        """
        pass

    @abstractmethod
    async def list_sessions(self, user_id: Optional[str] = None) -> List[str]:
        """
        List all session IDs, optionally filtered by user_id.

        Args:
            user_id: Optional user ID to filter by

        Returns:
            List of session IDs
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close storage connection and cleanup resources."""
        pass
