"""
PostgreSQL session storage implementation.
"""
import json
import asyncpg
from datetime import datetime, timedelta
from typing import Optional, List

from .base import SessionStorage
from ..models import SessionInfo
from ..exceptions import StorageError


class PostgreSQLStorage(SessionStorage):
    """PostgreSQL session storage (for multi-instance production)."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "claude_agent",
        user: str = "postgresql",
        password: str = "postgresql",
        ttl: int = 3600,
    ):
        """
        Initialize PostgreSQL storage.

        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            database: Database name
            user: Database user
            password: Database password
            ttl: Session TTL in seconds (0 = no expiration)
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.ttl = ttl
        self._pool: Optional[asyncpg.Pool] = None
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """Initialize database connection pool and schema."""
        if self._initialized:
            return

        try:
            # Create connection pool
            self._pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                min_size=2,
                max_size=10,
            )

            # Create table if not exists
            async with self._pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id VARCHAR(255) PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL,
                        subdir VARCHAR(500),
                        cwd VARCHAR(1000) NOT NULL,
                        system_prompt TEXT,
                        mcp_servers JSONB DEFAULT '{}',
                        plugins JSONB DEFAULT '[]',
                        model VARCHAR(255),
                        permission_mode VARCHAR(50),
                        allowed_tools JSONB DEFAULT '[]',
                        disallowed_tools JSONB DEFAULT '[]',
                        add_dirs JSONB DEFAULT '[]',
                        max_turns INTEGER,
                        max_budget_usd REAL,
                        created_at TIMESTAMP NOT NULL,
                        last_active_at TIMESTAMP NOT NULL,
                        message_count INTEGER DEFAULT 0,
                        metadata JSONB DEFAULT '{}'
                    )
                """)

                # Create indexes
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_sessions_user_id
                    ON sessions(user_id)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_sessions_last_active
                    ON sessions(last_active_at)
                """)

            self._initialized = True

        except Exception as e:
            raise StorageError(f"Failed to initialize PostgreSQL: {e}")

    async def save(self, session_id: str, session_info: SessionInfo) -> bool:
        """Save session information."""
        await self._ensure_initialized()

        try:
            async with self._pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO sessions (
                        session_id, user_id, subdir, cwd,
                        system_prompt, mcp_servers, plugins, model,
                        permission_mode, allowed_tools, disallowed_tools, add_dirs,
                        max_turns, max_budget_usd,
                        created_at, last_active_at, message_count, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
                    ON CONFLICT (session_id) DO UPDATE SET
                        user_id = EXCLUDED.user_id,
                        subdir = EXCLUDED.subdir,
                        cwd = EXCLUDED.cwd,
                        system_prompt = EXCLUDED.system_prompt,
                        mcp_servers = EXCLUDED.mcp_servers,
                        plugins = EXCLUDED.plugins,
                        model = EXCLUDED.model,
                        permission_mode = EXCLUDED.permission_mode,
                        allowed_tools = EXCLUDED.allowed_tools,
                        disallowed_tools = EXCLUDED.disallowed_tools,
                        add_dirs = EXCLUDED.add_dirs,
                        max_turns = EXCLUDED.max_turns,
                        max_budget_usd = EXCLUDED.max_budget_usd,
                        last_active_at = EXCLUDED.last_active_at,
                        message_count = EXCLUDED.message_count,
                        metadata = EXCLUDED.metadata
                """,
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
                    session_info.created_at,
                    session_info.last_active_at,
                    session_info.message_count,
                    json.dumps(session_info.metadata),
                )
            return True
        except Exception as e:
            raise StorageError(f"Failed to save session: {e}")

    async def get(self, session_id: str) -> Optional[SessionInfo]:
        """Get session information."""
        await self._ensure_initialized()

        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM sessions WHERE session_id = $1",
                    session_id
                )

                if not row:
                    return None

                # Check expiration
                last_active = row['last_active_at']
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
                    mcp_servers=json.loads(row['mcp_servers']) if row['mcp_servers'] else {},
                    plugins=json.loads(row['plugins']) if row['plugins'] else [],
                    model=row['model'],
                    permission_mode=row['permission_mode'] or 'bypassPermissions',
                    allowed_tools=json.loads(row['allowed_tools']) if row['allowed_tools'] else [],
                    disallowed_tools=json.loads(row['disallowed_tools']) if row['disallowed_tools'] else [],
                    add_dirs=json.loads(row['add_dirs']) if row['add_dirs'] else [],
                    max_turns=row['max_turns'],
                    max_budget_usd=row['max_budget_usd'],
                    created_at=row['created_at'],
                    last_active_at=last_active,
                    message_count=row['message_count'] or 0,
                    metadata=json.loads(row['metadata']) if row['metadata'] else {},
                )
        except Exception as e:
            raise StorageError(f"Failed to get session: {e}")

    async def delete(self, session_id: str) -> bool:
        """Delete session."""
        await self._ensure_initialized()

        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM sessions WHERE session_id = $1",
                    session_id
                )
                # Result format: "DELETE N"
                return result.split()[-1] != '0'
        except Exception as e:
            raise StorageError(f"Failed to delete session: {e}")

    async def touch(self, session_id: str) -> bool:
        """Update session last_active_at and increment message_count."""
        await self._ensure_initialized()

        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute("""
                    UPDATE sessions
                    SET last_active_at = $1, message_count = message_count + 1
                    WHERE session_id = $2
                """, datetime.now(), session_id)
                return result.split()[-1] != '0'
        except Exception as e:
            raise StorageError(f"Failed to touch session: {e}")

    async def list_sessions(self, user_id: Optional[str] = None) -> List[str]:
        """List all session IDs, optionally filtered by user_id."""
        await self._ensure_initialized()

        try:
            async with self._pool.acquire() as conn:
                if user_id:
                    if self.ttl > 0:
                        cutoff = datetime.now() - timedelta(seconds=self.ttl)
                        rows = await conn.fetch(
                            "SELECT session_id FROM sessions WHERE user_id = $1 AND last_active_at > $2",
                            user_id, cutoff
                        )
                    else:
                        rows = await conn.fetch(
                            "SELECT session_id FROM sessions WHERE user_id = $1",
                            user_id
                        )
                else:
                    if self.ttl > 0:
                        cutoff = datetime.now() - timedelta(seconds=self.ttl)
                        rows = await conn.fetch(
                            "SELECT session_id FROM sessions WHERE last_active_at > $1",
                            cutoff
                        )
                    else:
                        rows = await conn.fetch("SELECT session_id FROM sessions")

                return [row['session_id'] for row in rows]
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
            cutoff = datetime.now() - timedelta(seconds=self.ttl)
            async with self._pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM sessions WHERE last_active_at < $1",
                    cutoff
                )
                # Result format: "DELETE N"
                return int(result.split()[-1])
        except Exception as e:
            raise StorageError(f"Failed to cleanup expired sessions: {e}")

    async def close(self) -> None:
        """Close PostgreSQL connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            self._initialized = False
