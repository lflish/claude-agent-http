"""
会话管理模块
支持多种存储后端：内存、Redis、文件、PostgreSQL
"""
import os
import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Literal
from datetime import datetime, timedelta
from .models import SessionInfo
from .exceptions import SessionStorageError


class SessionStorage(ABC):
    """会话存储抽象基类"""

    @abstractmethod
    async def save(self, session_id: str, session_info: SessionInfo) -> bool:
        """保存会话信息"""
        pass

    @abstractmethod
    async def get(self, session_id: str) -> Optional[SessionInfo]:
        """获取会话信息"""
        pass

    @abstractmethod
    async def delete(self, session_id: str) -> bool:
        """删除会话"""
        pass

    @abstractmethod
    async def touch(self, session_id: str) -> bool:
        """更新会话最后活跃时间"""
        pass

    @abstractmethod
    async def list_sessions(self) -> list[str]:
        """列出所有会话 ID"""
        pass


class MemoryStorage(SessionStorage):
    """内存存储实现"""

    def __init__(self, ttl: int = 3600):
        """
        初始化内存存储

        Args:
            ttl: 会话过期时间（秒），0 表示不过期
        """
        self._storage: Dict[str, SessionInfo] = {}
        self.ttl = ttl

    async def save(self, session_id: str, session_info: SessionInfo) -> bool:
        """保存会话信息"""
        try:
            self._storage[session_id] = session_info
            return True
        except Exception as e:
            raise SessionStorageError(f"Failed to save session: {e}")

    async def get(self, session_id: str) -> Optional[SessionInfo]:
        """获取会话信息"""
        session_info = self._storage.get(session_id)

        if not session_info:
            return None

        # 检查是否过期
        if self.ttl > 0:
            expired_at = session_info.last_active_at + timedelta(seconds=self.ttl)
            if datetime.now() > expired_at:
                await self.delete(session_id)
                return None

        return session_info

    async def delete(self, session_id: str) -> bool:
        """删除会话"""
        if session_id in self._storage:
            del self._storage[session_id]
            return True
        return False

    async def touch(self, session_id: str) -> bool:
        """更新会话最后活跃时间"""
        if session_id in self._storage:
            self._storage[session_id].last_active_at = datetime.now()
            self._storage[session_id].message_count += 1
            return True
        return False

    async def list_sessions(self) -> list[str]:
        """列出所有会话 ID"""
        return list(self._storage.keys())


class FileStorage(SessionStorage):
    """文件存储实现"""

    def __init__(self, storage_dir: str = ".sessions", ttl: int = 3600):
        """
        初始化文件存储

        Args:
            storage_dir: 存储目录
            ttl: 会话过期时间（秒），0 表示不过期
        """
        self.storage_dir = storage_dir
        self.ttl = ttl

        # 确保目录存在
        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_file_path(self, session_id: str) -> str:
        """获取会话文件路径"""
        return os.path.join(self.storage_dir, f"{session_id}.json")

    async def save(self, session_id: str, session_info: SessionInfo) -> bool:
        """保存会话信息"""
        try:
            file_path = self._get_file_path(session_id)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(session_info.model_dump(), f, ensure_ascii=False, indent=2, default=str)
            return True
        except Exception as e:
            raise SessionStorageError(f"Failed to save session to file: {e}")

    async def get(self, session_id: str) -> Optional[SessionInfo]:
        """获取会话信息"""
        try:
            file_path = self._get_file_path(session_id)
            if not os.path.exists(file_path):
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 转换字符串时间为 datetime
            if isinstance(data.get('created_at'), str):
                data['created_at'] = datetime.fromisoformat(data['created_at'])
            if isinstance(data.get('last_active_at'), str):
                data['last_active_at'] = datetime.fromisoformat(data['last_active_at'])

            session_info = SessionInfo(**data)

            # 检查是否过期
            if self.ttl > 0:
                expired_at = session_info.last_active_at + timedelta(seconds=self.ttl)
                if datetime.now() > expired_at:
                    await self.delete(session_id)
                    return None

            return session_info
        except Exception as e:
            raise SessionStorageError(f"Failed to load session from file: {e}")

    async def delete(self, session_id: str) -> bool:
        """删除会话"""
        try:
            file_path = self._get_file_path(session_id)
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            raise SessionStorageError(f"Failed to delete session file: {e}")

    async def touch(self, session_id: str) -> bool:
        """更新会话最后活跃时间"""
        session_info = await self.get(session_id)
        if session_info:
            session_info.last_active_at = datetime.now()
            session_info.message_count += 1
            await self.save(session_id, session_info)
            return True
        return False

    async def list_sessions(self) -> list[str]:
        """列出所有会话 ID"""
        try:
            files = os.listdir(self.storage_dir)
            return [f.replace('.json', '') for f in files if f.endswith('.json')]
        except Exception:
            return []


class RedisStorage(SessionStorage):
    """Redis 存储实现（需要安装 redis 包）"""

    def __init__(self, redis_url: str, key_prefix: str = "claude_agent:session:", ttl: int = 3600):
        """
        初始化 Redis 存储

        Args:
            redis_url: Redis 连接 URL
            key_prefix: 键前缀
            ttl: 会话过期时间（秒），0 表示不过期
        """
        try:
            import redis.asyncio as aioredis
        except ImportError:
            raise ImportError("Redis storage requires 'redis' package. Install with: pip install redis")

        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.ttl = ttl
        self._redis = None

    async def _get_redis(self):
        """获取 Redis 连接（懒加载）"""
        if self._redis is None:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    def _make_key(self, session_id: str) -> str:
        """生成 Redis 键"""
        return f"{self.key_prefix}{session_id}"

    async def save(self, session_id: str, session_info: SessionInfo) -> bool:
        """保存会话信息"""
        try:
            redis = await self._get_redis()
            key = self._make_key(session_id)
            value = json.dumps(session_info.model_dump(), ensure_ascii=False, default=str)

            if self.ttl > 0:
                await redis.setex(key, self.ttl, value)
            else:
                await redis.set(key, value)

            return True
        except Exception as e:
            raise SessionStorageError(f"Failed to save session to Redis: {e}")

    async def get(self, session_id: str) -> Optional[SessionInfo]:
        """获取会话信息"""
        try:
            redis = await self._get_redis()
            key = self._make_key(session_id)
            value = await redis.get(key)

            if not value:
                return None

            data = json.loads(value)

            # 转换字符串时间为 datetime
            if isinstance(data.get('created_at'), str):
                data['created_at'] = datetime.fromisoformat(data['created_at'])
            if isinstance(data.get('last_active_at'), str):
                data['last_active_at'] = datetime.fromisoformat(data['last_active_at'])

            return SessionInfo(**data)
        except Exception as e:
            raise SessionStorageError(f"Failed to load session from Redis: {e}")

    async def delete(self, session_id: str) -> bool:
        """删除会话"""
        try:
            redis = await self._get_redis()
            key = self._make_key(session_id)
            result = await redis.delete(key)
            return result > 0
        except Exception as e:
            raise SessionStorageError(f"Failed to delete session from Redis: {e}")

    async def touch(self, session_id: str) -> bool:
        """更新会话最后活跃时间"""
        session_info = await self.get(session_id)
        if session_info:
            session_info.last_active_at = datetime.now()
            session_info.message_count += 1
            await self.save(session_id, session_info)
            return True
        return False

    async def list_sessions(self) -> list[str]:
        """列出所有会话 ID"""
        try:
            redis = await self._get_redis()
            pattern = f"{self.key_prefix}*"
            keys = await redis.keys(pattern)
            return [key.replace(self.key_prefix, '') for key in keys]
        except Exception:
            return []

    async def close(self):
        """关闭 Redis 连接"""
        if self._redis:
            await self._redis.close()


class PostgresStorage(SessionStorage):
    """PostgreSQL 存储实现（需要安装 asyncpg 包）"""

    def __init__(
        self,
        postgres_url: str,
        table_name: str = "claude_agent_sessions",
        ttl: int = 3600
    ):
        """
        初始化 PostgreSQL 存储

        Args:
            postgres_url: PostgreSQL 连接 URL
                格式: postgresql://user:password@host:port/database
            table_name: 会话表名
            ttl: 会话过期时间（秒），0 表示不过期
        """
        try:
            import asyncpg
        except ImportError:
            raise ImportError(
                "PostgreSQL storage requires 'asyncpg' package. "
                "Install with: pip install asyncpg"
            )

        self.postgres_url = postgres_url
        self.table_name = table_name
        self.ttl = ttl
        self._pool = None

    async def _get_pool(self):
        """获取连接池（懒加载）"""
        if self._pool is None:
            import asyncpg
            self._pool = await asyncpg.create_pool(self.postgres_url, min_size=2, max_size=10)
            # 创建表（如果不存在）
            await self._init_table()
        return self._pool

    async def _init_table(self):
        """初始化数据库表"""
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            session_id VARCHAR(255) PRIMARY KEY,
            system_prompt TEXT,
            mcp_servers JSONB,
            metadata JSONB,
            created_at TIMESTAMP NOT NULL,
            last_active_at TIMESTAMP NOT NULL,
            message_count INTEGER DEFAULT 0
        );

        -- 创建索引加速查询
        CREATE INDEX IF NOT EXISTS idx_{self.table_name}_last_active
        ON {self.table_name}(last_active_at);
        """
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(create_table_sql)

    async def save(self, session_id: str, session_info: SessionInfo) -> bool:
        """保存会话信息"""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                # 使用 UPSERT 操作（INSERT ... ON CONFLICT UPDATE）
                await conn.execute(
                    f"""
                    INSERT INTO {self.table_name}
                    (session_id, system_prompt, mcp_servers, metadata, created_at, last_active_at, message_count)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (session_id)
                    DO UPDATE SET
                        system_prompt = EXCLUDED.system_prompt,
                        mcp_servers = EXCLUDED.mcp_servers,
                        metadata = EXCLUDED.metadata,
                        last_active_at = EXCLUDED.last_active_at,
                        message_count = EXCLUDED.message_count
                    """,
                    session_id,
                    session_info.system_prompt,
                    json.dumps(session_info.mcp_servers or {}),
                    json.dumps(session_info.metadata or {}),
                    session_info.created_at,
                    session_info.last_active_at,
                    session_info.message_count
                )
            return True
        except Exception as e:
            raise SessionStorageError(f"Failed to save session to PostgreSQL: {e}")

    async def get(self, session_id: str) -> Optional[SessionInfo]:
        """获取会话信息"""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    f"""
                    SELECT session_id, system_prompt, mcp_servers, metadata,
                           created_at, last_active_at, message_count
                    FROM {self.table_name}
                    WHERE session_id = $1
                    """,
                    session_id
                )

                if not row:
                    return None

                # 检查是否过期
                if self.ttl > 0:
                    expired_at = row['last_active_at'] + timedelta(seconds=self.ttl)
                    if datetime.now() > expired_at:
                        await self.delete(session_id)
                        return None

                # 转换为 SessionInfo
                return SessionInfo(
                    session_id=row['session_id'],
                    system_prompt=row['system_prompt'],
                    mcp_servers=json.loads(row['mcp_servers']) if row['mcp_servers'] else {},
                    metadata=json.loads(row['metadata']) if row['metadata'] else {},
                    created_at=row['created_at'],
                    last_active_at=row['last_active_at'],
                    message_count=row['message_count']
                )
        except Exception as e:
            raise SessionStorageError(f"Failed to load session from PostgreSQL: {e}")

    async def delete(self, session_id: str) -> bool:
        """删除会话"""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                result = await conn.execute(
                    f"DELETE FROM {self.table_name} WHERE session_id = $1",
                    session_id
                )
                # result 格式: "DELETE n" 其中 n 是删除的行数
                return result != "DELETE 0"
        except Exception as e:
            raise SessionStorageError(f"Failed to delete session from PostgreSQL: {e}")

    async def touch(self, session_id: str) -> bool:
        """更新会话最后活跃时间"""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                result = await conn.execute(
                    f"""
                    UPDATE {self.table_name}
                    SET last_active_at = $1, message_count = message_count + 1
                    WHERE session_id = $2
                    """,
                    datetime.now(),
                    session_id
                )
                return result != "UPDATE 0"
        except Exception as e:
            raise SessionStorageError(f"Failed to touch session in PostgreSQL: {e}")

    async def list_sessions(self) -> list[str]:
        """列出所有会话 ID"""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                # 只返回未过期的会话
                if self.ttl > 0:
                    cutoff_time = datetime.now() - timedelta(seconds=self.ttl)
                    rows = await conn.fetch(
                        f"""
                        SELECT session_id
                        FROM {self.table_name}
                        WHERE last_active_at > $1
                        ORDER BY last_active_at DESC
                        """,
                        cutoff_time
                    )
                else:
                    rows = await conn.fetch(
                        f"""
                        SELECT session_id
                        FROM {self.table_name}
                        ORDER BY last_active_at DESC
                        """
                    )
                return [row['session_id'] for row in rows]
        except Exception:
            return []

    async def cleanup_expired(self) -> int:
        """清理过期会话（可选的维护任务）"""
        if self.ttl <= 0:
            return 0

        try:
            pool = await self._get_pool()
            cutoff_time = datetime.now() - timedelta(seconds=self.ttl)
            async with pool.acquire() as conn:
                result = await conn.execute(
                    f"DELETE FROM {self.table_name} WHERE last_active_at < $1",
                    cutoff_time
                )
                # 提取删除的行数
                return int(result.split()[-1]) if result else 0
        except Exception:
            return 0

    async def close(self):
        """关闭连接池"""
        if self._pool:
            await self._pool.close()



class SessionManager:
    """会话管理器（门面类）"""

    def __init__(
        self,
        storage_type: Literal['memory', 'redis', 'file', 'postgres'] = 'memory',
        ttl: int = 3600,
        **kwargs
    ):
        """
        初始化会话管理器

        Args:
            storage_type: 存储类型 (memory/file/redis/postgres)
            ttl: 会话过期时间（秒）
            **kwargs: 传递给具体存储实现的参数
        """
        self.storage_type = storage_type
        self.ttl = ttl

        # 根据类型创建存储实现
        if storage_type == 'memory':
            self.storage = MemoryStorage(ttl=ttl)
        elif storage_type == 'file':
            storage_dir = kwargs.get('storage_dir', '.sessions')
            self.storage = FileStorage(storage_dir=storage_dir, ttl=ttl)
        elif storage_type == 'redis':
            redis_url = kwargs.get('redis_url')
            if not redis_url:
                raise ValueError("redis_url is required for Redis storage")
            key_prefix = kwargs.get('key_prefix', 'claude_agent:session:')
            self.storage = RedisStorage(redis_url=redis_url, key_prefix=key_prefix, ttl=ttl)
        elif storage_type == 'postgres':
            postgres_url = kwargs.get('postgres_url')
            if not postgres_url:
                raise ValueError("postgres_url is required for PostgreSQL storage")
            table_name = kwargs.get('table_name', 'claude_agent_sessions')
            self.storage = PostgresStorage(postgres_url=postgres_url, table_name=table_name, ttl=ttl)
        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")

    async def save(self, session_id: str, session_info: SessionInfo) -> bool:
        """保存会话信息"""
        return await self.storage.save(session_id, session_info)

    async def get(self, session_id: str) -> Optional[SessionInfo]:
        """获取会话信息"""
        return await self.storage.get(session_id)

    async def delete(self, session_id: str) -> bool:
        """删除会话"""
        return await self.storage.delete(session_id)

    async def touch(self, session_id: str) -> bool:
        """更新会话最后活跃时间"""
        return await self.storage.touch(session_id)

    async def list_sessions(self) -> list[str]:
        """列出所有会话 ID"""
        return await self.storage.list_sessions()

    async def cleanup(self):
        """清理资源（如关闭 Redis/PostgreSQL 连接）"""
        if isinstance(self.storage, (RedisStorage, PostgresStorage)):
            await self.storage.close()
