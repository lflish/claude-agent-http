"""
In-memory session storage implementation.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict

from .base import SessionStorage
from ..models import SessionInfo


class MemoryStorage(SessionStorage):
    """In-memory session storage (for development/testing)."""

    def __init__(self, ttl: int = 3600):
        """
        Initialize memory storage.

        Args:
            ttl: Session TTL in seconds (0 = no expiration)
        """
        self._storage: Dict[str, SessionInfo] = {}
        self.ttl = ttl

    async def save(self, session_id: str, session_info: SessionInfo) -> bool:
        """Save session information."""
        self._storage[session_id] = session_info
        return True

    async def get(self, session_id: str) -> Optional[SessionInfo]:
        """Get session information."""
        session_info = self._storage.get(session_id)

        if not session_info:
            return None

        # Check expiration
        if self.ttl > 0:
            expired_at = session_info.last_active_at + timedelta(seconds=self.ttl)
            if datetime.now() > expired_at:
                await self.delete(session_id)
                return None

        return session_info

    async def delete(self, session_id: str) -> bool:
        """Delete session."""
        if session_id in self._storage:
            del self._storage[session_id]
            return True
        return False

    async def touch(self, session_id: str) -> bool:
        """Update session last_active_at and increment message_count."""
        if session_id in self._storage:
            self._storage[session_id].last_active_at = datetime.now()
            self._storage[session_id].message_count += 1
            return True
        return False

    async def list_sessions(self, user_id: Optional[str] = None) -> List[str]:
        """List all session IDs, optionally filtered by user_id."""
        if user_id:
            return [
                sid for sid, info in self._storage.items()
                if info.user_id == user_id
            ]
        return list(self._storage.keys())

    async def close(self) -> None:
        """Close storage (no-op for memory storage)."""
        self._storage.clear()
