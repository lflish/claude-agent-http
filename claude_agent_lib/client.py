"""
核心库函数类
提供 Claude Agent 的主要功能接口
"""
import asyncio
from typing import Optional, Dict, Any, AsyncIterator
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

from .models import SessionInfo, Message, StreamChunk
from .config import LibraryConfig
from .session import SessionManager
from .exceptions import (
    SessionNotFoundError,
    ClientCreationError,
    MessageSendError,
    SessionExpiredError,
    SessionBusyError
)


class ClaudeAgentLibrary:
    """
    Claude Agent 核心库函数

    Usage:
        async with ClaudeAgentLibrary(config) as library:
            session_id = await library.create_session()
            response = await library.send_message(session_id, "Hello")
    """

    def __init__(self, config: LibraryConfig):
        """
        初始化库

        Args:
            config: 库配置对象
        """
        self.config = config

        # 创建会话管理器
        self.session_manager = SessionManager(
            storage_type=config.session_storage,
            ttl=config.session_ttl,
            storage_dir=config.file_storage_dir,
            redis_url=config.redis_url,
            key_prefix=config.redis_key_prefix,
            postgres_url=config.postgres_url,
            table_name=config.postgres_table_name
        )

        # 维护 session_id -> ClaudeSDKClient 映射
        self._clients: Dict[str, ClaudeSDKClient] = {}

        # 并发锁保护 _clients 字典（支持 30+ 并发会话）
        self._clients_lock = asyncio.Lock()

        # 每个 session 独立的操作锁，防止同一 session 的并发请求导致消息混乱
        self._session_locks: Dict[str, asyncio.Lock] = {}

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出：清理所有资源"""
        await self.cleanup()
        # 关闭存储后端连接（Redis/PostgreSQL）
        await self.session_manager.cleanup()

    # ============ 核心方法 ============

    async def create_session(
        self,
        system_prompt: Optional[str] = None,
        mcp_servers: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
        init_message: Optional[str] = None
    ) -> str:
        """
        创建新会话

        Args:
            system_prompt: 自定义系统提示词（覆盖全局配置）
            mcp_servers: 自定义 MCP 服务器（覆盖全局配置）
            metadata: 会话元数据（用于存储业务信息，如 user_id）
            init_message: 初始化消息（覆盖配置中的 init_message）

        Returns:
            session_id: 新创建的会话 ID

        Raises:
            ClientCreationError: 创建失败
        """
        # 1. 创建 ClaudeAgentOptions
        options = self._build_options(
            system_prompt=system_prompt or self.config.system_prompt,
            mcp_servers=mcp_servers or self.config.mcp_servers,
            resume=None  # 新会话，不传 resume
        )

        # 2. 创建 ClaudeSDKClient
        client = ClaudeSDKClient(options=options)
        await client.__aenter__()

        try:
            # 3. 发送初始化消息获取 session_id
            await client.query(prompt=init_message or self.config.init_message)
            session_id = await self._extract_session_id(client)

            if not session_id:
                raise ClientCreationError("Failed to extract session_id from response")

            # 4. 保存到 session_manager
            session_info = SessionInfo(
                session_id=session_id,
                system_prompt=system_prompt or self.config.system_prompt,
                mcp_servers=mcp_servers or self.config.mcp_servers,
                metadata=metadata or {}
            )
            await self.session_manager.save(session_id, session_info)

            # 5. 保存 client 实例（加锁保护并发安全）
            async with self._clients_lock:
                self._clients[session_id] = client

            return session_id

        except Exception as e:
            # 如果创建失败，清理 client
            await client.__aexit__(None, None, None)
            raise ClientCreationError(f"Failed to create session: {e}")

    async def resume_session(
        self,
        session_id: str,
        system_prompt: Optional[str] = None,
        mcp_servers: Optional[Dict] = None
    ) -> bool:
        """
        复用已有会话

        Args:
            session_id: 已有的会话 ID
            system_prompt: 覆盖原有的系统提示词（可选）
            mcp_servers: 覆盖原有的 MCP 服务器（可选）

        Returns:
            bool: 是否成功复用

        Raises:
            SessionNotFoundError: 会话不存在
            SessionExpiredError: 会话已过期
        """
        # 1. 检查是否已经在内存中（加锁检查避免重复创建）
        async with self._clients_lock:
            if session_id in self._clients:
                return True

        # 2. 从 storage 加载 session 信息
        session_info = await self.session_manager.get(session_id)
        if not session_info:
            raise SessionNotFoundError(f"Session {session_id} not found or expired")

        # 3. 创建 client 并传入 resume 参数
        options = self._build_options(
            system_prompt=system_prompt or session_info.system_prompt,
            mcp_servers=mcp_servers or session_info.mcp_servers,
            resume=session_id  # 关键：传入 resume
        )

        client = ClaudeSDKClient(options=options)
        await client.__aenter__()

        # 4. 保存到内存（加锁保护，再次检查避免重复）
        async with self._clients_lock:
            if session_id not in self._clients:
                self._clients[session_id] = client
            else:
                # 如果已存在，关闭新创建的 client
                await client.__aexit__(None, None, None)

        # 5. 更新 last_active_at
        await self.session_manager.touch(session_id)

        return True

    async def send_message(
        self,
        session_id: str,
        message: str,
        timeout: Optional[int] = None
    ) -> Message:
        """
        发送消息（同步模式，等待完整响应）

        Args:
            session_id: 会话 ID
            message: 用户消息
            timeout: 超时时间（秒）

        Returns:
            Message: 完整响应对象

        Raises:
            SessionNotFoundError: 会话不存在
            MessageSendError: 发送失败
        """
        # 获取 session 专用锁，防止同一 session 的并发请求
        session_lock = await self._get_session_lock(session_id)

        # 检查锁状态，如果已被占用则拒绝请求
        if session_lock.locked():
            raise SessionBusyError(f"Session {session_id} is busy, please wait for the previous request to complete")

        async with session_lock:
            try:
                # 1. 获取 client
                client = await self._get_or_load_client(session_id)

                # 2. 发送查询
                await client.query(prompt=message)

                # 3. 收集完整响应
                full_text = ""
                tool_calls = []

                async for msg in client.receive_response():
                    if hasattr(msg, 'content') and msg.content:
                        for block in msg.content:
                            # 提取文本
                            if hasattr(block, 'text') and block.text:
                                full_text = block.text

                            # 提取工具调用
                            if hasattr(block, 'type') and block.type == 'tool_use':
                                tool_calls.append({
                                    'tool': getattr(block, 'name', 'unknown'),
                                    'input': getattr(block, 'input', {})
                                })

                    # 检查错误
                    if hasattr(msg, 'is_error') and msg.is_error:
                        raise MessageSendError(f"Error in response: {getattr(msg, 'result', 'Unknown error')}")

                # 4. 更新会话活跃时间
                await self.session_manager.touch(session_id)

                return Message(
                    session_id=session_id,
                    text=full_text,
                    tool_calls=tool_calls
                )

            except SessionNotFoundError:
                raise
            except SessionBusyError:
                raise
            except Exception as e:
                raise MessageSendError(f"Failed to send message: {e}")

    async def send_message_stream(
        self,
        session_id: str,
        message: str
    ) -> AsyncIterator[StreamChunk]:
        """
        发送消息（流式模式）

        Args:
            session_id: 会话 ID
            message: 用户消息

        Yields:
            StreamChunk: 流式数据块

        Raises:
            SessionNotFoundError: 会话不存在
            MessageSendError: 发送失败
        """
        # 获取 session 专用锁，防止同一 session 的并发请求
        session_lock = await self._get_session_lock(session_id)

        # 检查锁状态，如果已被占用则拒绝请求
        if session_lock.locked():
            raise SessionBusyError(f"Session {session_id} is busy, please wait for the previous request to complete")

        async with session_lock:
            try:
                # 1. 获取 client
                client = await self._get_or_load_client(session_id)

                # 2. 发送查询
                await client.query(prompt=message)

                # 3. 流式返回
                full_text = ""
                async for msg in client.receive_response():
                    if hasattr(msg, 'content') and msg.content:
                        for block in msg.content:
                            # 文本增量
                            if hasattr(block, 'text') and block.text:
                                new_text = block.text
                                if new_text.startswith(full_text):
                                    # 新文本是累积的，计算增量
                                    delta = new_text[len(full_text):]
                                    full_text = new_text
                                else:
                                    # 新文本不是累积的，直接使用
                                    delta = new_text
                                    full_text += new_text

                                if delta:
                                    yield StreamChunk(
                                        type='text_delta',
                                        text=delta
                                    )

                            # 工具调用
                            if hasattr(block, 'type') and block.type == 'tool_use':
                                yield StreamChunk(
                                    type='tool_use',
                                    tool_name=getattr(block, 'name', 'unknown'),
                                    tool_input=getattr(block, 'input', {})
                                )

                    # 检查错误
                    if hasattr(msg, 'is_error') and msg.is_error:
                        yield StreamChunk(
                            type='error',
                            error=getattr(msg, 'result', 'Unknown error')
                        )
                        return

                # 4. 发送完成信号
                yield StreamChunk(type='done')

                # 5. 更新会话活跃时间
                await self.session_manager.touch(session_id)

            except SessionNotFoundError:
                raise
            except SessionBusyError:
                raise
            except Exception as e:
                yield StreamChunk(type='error', error=str(e))

    async def close_session(self, session_id: str) -> bool:
        """
        关闭会话

        Args:
            session_id: 会话 ID

        Returns:
            bool: 是否成功关闭
        """
        # 关闭 client 并清理 session 锁（加锁保护）
        async with self._clients_lock:
            if session_id in self._clients:
                client = self._clients[session_id]
                try:
                    await client.__aexit__(None, None, None)
                except Exception as e:
                    # 忽略客户端清理时的错误（Claude SDK 内部问题）
                    print(f"Warning: Error closing client for session {session_id}: {e}")
                finally:
                    # 无论是否出错，都从字典中移除
                    del self._clients[session_id]

            # 清理 session 锁
            if session_id in self._session_locks:
                del self._session_locks[session_id]

        # 删除存储中的会话信息
        await self.session_manager.delete(session_id)
        return True

    async def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        """
        获取会话信息

        Args:
            session_id: 会话 ID

        Returns:
            SessionInfo: 会话信息对象
        """
        return await self.session_manager.get(session_id)

    async def list_sessions(self) -> list[str]:
        """
        列出所有会话 ID

        Returns:
            list[str]: 会话 ID 列表
        """
        return await self.session_manager.list_sessions()

    async def cleanup(self):
        """
        清理客户端连接

        注意：此方法只关闭 client 连接，不删除会话存储，也不关闭存储后端连接
        存储后端连接会在 __aexit__ 时关闭
        如果需要删除会话，请显式调用 close_session()
        """
        # 只关闭 client 连接，不删除存储（加锁保护）
        async with self._clients_lock:
            for session_id in list(self._clients.keys()):
                if session_id in self._clients:
                    client = self._clients[session_id]
                    try:
                        await client.__aexit__(None, None, None)
                    except Exception as e:
                        # 忽略客户端清理时的错误（Claude SDK 内部问题）
                        print(f"Warning: Error closing client for session {session_id}: {e}")
                    finally:
                        del self._clients[session_id]

            # 清理所有 session 锁
            self._session_locks.clear()

        # 注意：不在这里关闭存储后端连接（Redis/PostgreSQL）
        # 存储后端连接会在 __aexit__ 时关闭

    # ============ 私有方法 ============

    async def _get_session_lock(self, session_id: str) -> asyncio.Lock:
        """获取 session 专用锁（并发安全）"""
        async with self._clients_lock:
            if session_id not in self._session_locks:
                self._session_locks[session_id] = asyncio.Lock()
            return self._session_locks[session_id]

    def _build_options(
        self,
        system_prompt: str,
        mcp_servers: Dict,
        resume: Optional[str]
    ) -> ClaudeAgentOptions:
        """构建 ClaudeAgentOptions"""
        options_dict = {
            'system_prompt': system_prompt,
            'permission_mode': self.config.permission_mode,
            'allowed_tools': self.config.allowed_tools,
            'mcp_servers': mcp_servers or {}
        }

        # 添加可选配置
        if self.config.cwd:
            options_dict['cwd'] = self.config.cwd

        if self.config.setting_sources:
            options_dict['setting_sources'] = self.config.setting_sources

        if resume:
            options_dict['resume'] = resume

        return ClaudeAgentOptions(**options_dict)

    async def _extract_session_id(self, client: ClaudeSDKClient) -> Optional[str]:
        """从 SDK 响应中提取 session_id

        注意：必须完整消费响应流，否则下次 query() 的响应会错位
        """
        session_id = None
        async for message in client.receive_response():
            if hasattr(message, 'subtype') and message.subtype == 'init':
                if not session_id:  # 只取第一个 session_id
                    session_id = message.data.get('session_id')
            # 继续消费直到响应流结束
        return session_id

    async def _get_or_load_client(self, session_id: str) -> ClaudeSDKClient:
        """获取或加载 client（并发安全）"""
        # 先检查是否已存在（加锁）
        async with self._clients_lock:
            if session_id in self._clients:
                return self._clients[session_id]

        # 不在内存中，尝试复用会话
        success = await self.resume_session(session_id)
        if not success:
            raise SessionNotFoundError(f"Session {session_id} not found")

        # 再次检查并返回（此时一定存在）
        async with self._clients_lock:
            if session_id in self._clients:
                return self._clients[session_id]
            else:
                raise SessionNotFoundError(f"Session {session_id} failed to load")
