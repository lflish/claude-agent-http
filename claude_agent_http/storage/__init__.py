"""
Session storage implementations.
"""
from typing import Literal

from .base import SessionStorage
from .memory import MemoryStorage
from .sqlite import SQLiteStorage


def create_storage(
    storage_type: Literal["memory", "sqlite"],
    ttl: int = 3600,
    **kwargs
) -> SessionStorage:
    """
    Create a session storage instance.

    Args:
        storage_type: Type of storage ("memory" or "sqlite")
        ttl: Session TTL in seconds
        **kwargs: Additional arguments for specific storage types

    Returns:
        SessionStorage instance
    """
    if storage_type == "memory":
        return MemoryStorage(ttl=ttl)
    elif storage_type == "sqlite":
        db_path = kwargs.get("sqlite_path", "sessions.db")
        return SQLiteStorage(db_path=db_path, ttl=ttl)
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")


__all__ = [
    "SessionStorage",
    "MemoryStorage",
    "SQLiteStorage",
    "create_storage",
]
