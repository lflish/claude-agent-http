"""
SQLite session storage implementation.
"""
import json
import aiosqlite
from datetime import datetime, timedelta
from typing import Optional, List

from .base import SessionStorage
from ..models import SessionInfo
from ..exceptions import StorageError


class SQLiteStorage(SessionStorage):
    """SQLite session storage (for production single-instance)."""

    def __init__(self, db_path: str = "sessions.db", ttl: int = 3600):
        """
        Initialize SQLite storage.

        Args:
            db_path: Path to SQLite database file
            ttl: Session TTL in seconds (0 = no expiration)
        """
        self.db_path = db_path
        self.ttl = ttl
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """Initialize database schema if not already done."""
        if self._initialized:
            return

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    subdir TEXT,
                    cwd TEXT NOT NULL,
                    system_prompt TEXT,
                    mcp_servers TEXT,
                    plugins TEXT,
                    model TEXT,
                    permission_mode TEXT,
                    allowed_tools TEXT,
                    disallowed_tools TEXT,
                    add_dirs TEXT,
                    max_turns INTEGER,
                    max_budget_usd REAL,
                    created_at TEXT NOT NULL,
                    last_active_at TEXT NOT NULL,
                    message_count INTEGER DEFAULT 0,
                    metadata TEXT
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user_id
                ON sessions(user_id)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_last_active
                ON sessions(last_active_at)
            """)
            await db.commit()

        self._initialized = True

    async def save(self, session_id: str, session_info: SessionInfo) -> bool:
        """Save session information."""
        await self._ensure_initialized()

        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO sessions (
                        session_id, user_id, subdir, cwd,
                        system_prompt, mcp_servers, plugins, model,
                        permission_mode, allowed_tools, disallowed_tools, add_dirs,
                        max_turns, max_budget_usd,
                        created_at, last_active_at, message_count, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    session_info.user_id,
                    session_info.subdir,
                    session_info.cwd,
                    session_info.system_prompt,
                    json.dumps(session_info.mcp_servers),
                    json.dumps(session_info.plugins),
                    session_info.model,
                    session_info.permission_mode,
                    json.dumps(session_info.allowed_tools),
                    json.dumps(session_info.disallowed_tools),
                    json.dumps(session_info.add_dirs),
                    session_info.max_turns,
                    session_info.max_budget_usd,
                    session_info.created_at.isoformat(),
                    session_info.last_active_at.isoformat(),
                    session_info.message_count,
                    json.dumps(session_info.metadata)
                ))
                await db.commit()
            return True
        except Exception as e:
            raise StorageError(f"Failed to save session: {e}")

    async def get(self, session_id: str) -> Optional[SessionInfo]:
        """Get session information."""
        await self._ensure_initialized()

        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT * FROM sessions WHERE session_id = ?",
                    (session_id,)
                ) as cursor:
                    row = await cursor.fetchone()

                    if not row:
                        return None

                    # Check expiration
                    last_active = datetime.fromisoformat(row['last_active_at'])
                    if self.ttl > 0:
                        expired_at = last_active + timedelta(seconds=self.ttl)
                        if datetime.now() > expired_at:
                            await self.delete(session_id)
                            return None

                    return SessionInfo(
                        session_id=row['session_id'],
                        user_id=row['user_id'],
                        subdir=row['subdir'],
                        cwd=row['cwd'],
                        system_prompt=row['system_prompt'],
                        mcp_servers=json.loads(row['mcp_servers'] or '{}'),
                        plugins=json.loads(row['plugins'] or '[]'),
                        model=row['model'],
                        permission_mode=row['permission_mode'] or 'bypassPermissions',
                        allowed_tools=json.loads(row['allowed_tools'] or '[]'),
                        disallowed_tools=json.loads(row['disallowed_tools'] or '[]'),
                        add_dirs=json.loads(row['add_dirs'] or '[]'),
                        max_turns=row['max_turns'],
                        max_budget_usd=row['max_budget_usd'],
                        created_at=datetime.fromisoformat(row['created_at']),
                        last_active_at=last_active,
                        message_count=row['message_count'] or 0,
                        metadata=json.loads(row['metadata'] or '{}')
                    )
        except Exception as e:
            raise StorageError(f"Failed to get session: {e}")

    async def delete(self, session_id: str) -> bool:
        """Delete session."""
        await self._ensure_initialized()

        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM sessions WHERE session_id = ?",
                    (session_id,)
                )
                await db.commit()
                return cursor.rowcount > 0
        except Exception as e:
            raise StorageError(f"Failed to delete session: {e}")

    async def touch(self, session_id: str) -> bool:
        """Update session last_active_at and increment message_count."""
        await self._ensure_initialized()

        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    UPDATE sessions
                    SET last_active_at = ?, message_count = message_count + 1
                    WHERE session_id = ?
                """, (datetime.now().isoformat(), session_id))
                await db.commit()
                return cursor.rowcount > 0
        except Exception as e:
            raise StorageError(f"Failed to touch session: {e}")

    async def list_sessions(self, user_id: Optional[str] = None) -> List[str]:
        """List all session IDs, optionally filtered by user_id."""
        await self._ensure_initialized()

        try:
            async with aiosqlite.connect(self.db_path) as db:
                if user_id:
                    # Filter by user_id and exclude expired
                    if self.ttl > 0:
                        cutoff = (datetime.now() - timedelta(seconds=self.ttl)).isoformat()
                        async with db.execute(
                            "SELECT session_id FROM sessions WHERE user_id = ? AND last_active_at > ?",
                            (user_id, cutoff)
                        ) as cursor:
                            rows = await cursor.fetchall()
                    else:
                        async with db.execute(
                            "SELECT session_id FROM sessions WHERE user_id = ?",
                            (user_id,)
                        ) as cursor:
                            rows = await cursor.fetchall()
                else:
                    # All sessions (exclude expired)
                    if self.ttl > 0:
                        cutoff = (datetime.now() - timedelta(seconds=self.ttl)).isoformat()
                        async with db.execute(
                            "SELECT session_id FROM sessions WHERE last_active_at > ?",
                            (cutoff,)
                        ) as cursor:
                            rows = await cursor.fetchall()
                    else:
                        async with db.execute("SELECT session_id FROM sessions") as cursor:
                            rows = await cursor.fetchall()

                return [row[0] for row in rows]
        except Exception as e:
            raise StorageError(f"Failed to list sessions: {e}")

    async def cleanup_expired(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            Number of sessions deleted
        """
        if self.ttl <= 0:
            return 0

        await self._ensure_initialized()

        try:
            cutoff = (datetime.now() - timedelta(seconds=self.ttl)).isoformat()
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM sessions WHERE last_active_at < ?",
                    (cutoff,)
                )
                await db.commit()
                return cursor.rowcount
        except Exception as e:
            raise StorageError(f"Failed to cleanup expired sessions: {e}")

    async def close(self) -> None:
        """Close storage (SQLite connections are per-operation, so this is a no-op)."""
        pass
