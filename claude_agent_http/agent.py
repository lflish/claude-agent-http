"""
Core Claude Agent class for managing sessions and sending messages.
"""
import asyncio
from typing import Optional, Dict, Any, List, AsyncIterator

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

from .config import Config
from .models import SessionInfo, ChatResponse, StreamChunk
from .storage import SessionStorage, create_storage
from .security import build_cwd, build_add_dirs, ensure_directory
from .exceptions import (
    SessionNotFoundError,
    SessionBusyError,
    ClientCreationError,
    MessageSendError,
)


class ClaudeAgent:
    """
    Claude Agent core class.

    Manages Claude SDK clients and sessions.

    Usage:
        async with ClaudeAgent(config) as agent:
            session_id = await agent.create_session(user_id="user1")
            response = await agent.send_message(session_id, "Hello")
    """

    def __init__(self, config: Config):
        """
        Initialize Claude Agent.

        Args:
            config: Configuration object
        """
        self.config = config

        # Create storage backend
        self.storage: SessionStorage = create_storage(
            storage_type=config.session.storage,
            ttl=config.session.ttl,
            sqlite_path=config.session.sqlite_path,
            pg_host=config.session.pg_host,
            pg_port=config.session.pg_port,
            pg_database=config.session.pg_database,
            pg_user=config.session.pg_user,
            pg_password=config.session.pg_password,
        )

        # Session ID -> ClaudeSDKClient mapping
        self._clients: Dict[str, ClaudeSDKClient] = {}

        # Lock for protecting _clients dict
        self._clients_lock = asyncio.Lock()

        # Per-session locks to prevent concurrent messages
        self._session_locks: Dict[str, asyncio.Lock] = {}

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit: cleanup resources."""
        await self.cleanup()
        await self.storage.close()

    # ============ Session Management ============

    async def create_session(
        self,
        user_id: str,
        subdir: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new session.

        Args:
            user_id: User identifier
            subdir: Subdirectory under user's home (optional)
            metadata: Custom metadata

        Returns:
            session_id: New session ID

        Raises:
            ClientCreationError: If session creation fails
        """
        # Build cwd
        cwd = build_cwd(user_id, subdir, self.config.user.base_dir)

        # Ensure directory exists
        ensure_directory(cwd, self.config.user.auto_create_dir)

        # Use all values from config
        system_prompt = self.config.defaults.system_prompt
        mcp_servers = self.config.mcp_servers
        plugins = self.config.plugins
        setting_sources = self.config.defaults.setting_sources
        model = self.config.defaults.model
        permission_mode = self.config.defaults.permission_mode
        allowed_tools = self.config.defaults.allowed_tools
        max_turns = self.config.defaults.max_turns
        max_budget_usd = self.config.defaults.max_budget_usd

        # Build SDK options
        options = self._build_options(
            cwd=cwd,
            system_prompt=system_prompt,
            mcp_servers=mcp_servers,
            plugins=plugins,
            setting_sources=setting_sources,
            model=model,
            permission_mode=permission_mode,
            allowed_tools=allowed_tools,
            disallowed_tools=[],
            add_dirs=[],
            max_turns=max_turns,
            max_budget_usd=max_budget_usd,
            resume=None,
        )

        # Create SDK client
        client = ClaudeSDKClient(options=options)
        await client.__aenter__()

        try:
            # Send init message to get session_id
            await client.query(prompt="Hello")
            session_id = await self._extract_session_id(client)

            if not session_id:
                raise ClientCreationError("Failed to extract session_id from response")

            # Save session info
            session_info = SessionInfo(
                session_id=session_id,
                user_id=user_id,
                subdir=subdir,
                cwd=cwd,
                system_prompt=system_prompt,
                mcp_servers=mcp_servers,
                plugins=plugins,
                setting_sources=setting_sources,
                model=model,
                permission_mode=permission_mode,
                allowed_tools=allowed_tools,
                disallowed_tools=[],
                add_dirs=[],
                max_turns=max_turns,
                max_budget_usd=max_budget_usd,
                metadata=metadata or {},
            )
            await self.storage.save(session_id, session_info)

            # Save client instance
            async with self._clients_lock:
                self._clients[session_id] = client

            return session_id

        except Exception as e:
            await client.__aexit__(None, None, None)
            raise ClientCreationError(f"Failed to create session: {e}")

    async def resume_session(self, session_id: str) -> bool:
        """
        Resume an existing session.

        Args:
            session_id: Session ID to resume

        Returns:
            True if resumed successfully

        Raises:
            SessionNotFoundError: If session not found
        """
        # Check if already in memory
        async with self._clients_lock:
            if session_id in self._clients:
                return True

        # Load session info from storage
        session_info = await self.storage.get(session_id)
        if not session_info:
            raise SessionNotFoundError(f"Session {session_id} not found or expired")

        # Rebuild absolute add_dirs
        abs_add_dirs = build_add_dirs(
            session_info.add_dirs,
            session_info.user_id,
            self.config.user.base_dir
        )

        # Build options with resume
        options = self._build_options(
            cwd=session_info.cwd,
            system_prompt=session_info.system_prompt,
            mcp_servers=session_info.mcp_servers,
            plugins=session_info.plugins,
            setting_sources=session_info.setting_sources,
            model=session_info.model,
            permission_mode=session_info.permission_mode,
            allowed_tools=session_info.allowed_tools,
            disallowed_tools=session_info.disallowed_tools,
            add_dirs=abs_add_dirs,
            max_turns=session_info.max_turns,
            max_budget_usd=session_info.max_budget_usd,
            resume=session_id,
        )

        # Create client
        client = ClaudeSDKClient(options=options)
        await client.__aenter__()

        # Save to memory
        async with self._clients_lock:
            if session_id not in self._clients:
                self._clients[session_id] = client
            else:
                await client.__aexit__(None, None, None)

        # Update last_active_at
        await self.storage.touch(session_id)

        return True

    async def close_session(self, session_id: str) -> bool:
        """
        Close a session.

        Args:
            session_id: Session ID to close

        Returns:
            True if closed successfully
        """
        async with self._clients_lock:
            if session_id in self._clients:
                client = self._clients[session_id]
                try:
                    await client.__aexit__(None, None, None)
                except Exception:
                    pass
                finally:
                    del self._clients[session_id]

            if session_id in self._session_locks:
                del self._session_locks[session_id]

        await self.storage.delete(session_id)
        return True

    async def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        """Get session information."""
        return await self.storage.get(session_id)

    async def list_sessions(self, user_id: Optional[str] = None) -> List[str]:
        """List session IDs, optionally filtered by user_id."""
        return await self.storage.list_sessions(user_id)

    # ============ Chat Methods ============

    async def send_message(self, session_id: str, message: str) -> ChatResponse:
        """
        Send a message (sync mode, wait for complete response).

        Args:
            session_id: Session ID
            message: User message

        Returns:
            ChatResponse with full response

        Raises:
            SessionNotFoundError: If session not found
            SessionBusyError: If session is busy
            MessageSendError: If message send fails
        """
        session_lock = await self._get_session_lock(session_id)

        if session_lock.locked():
            raise SessionBusyError(f"Session {session_id} is busy")

        async with session_lock:
            try:
                client = await self._get_or_load_client(session_id)
                await client.query(prompt=message)

                full_text = ""
                tool_calls = []

                async for msg in client.receive_response():
                    if hasattr(msg, 'content') and msg.content:
                        for block in msg.content:
                            if hasattr(block, 'text') and block.text:
                                full_text = block.text

                            if hasattr(block, 'type') and block.type == 'tool_use':
                                tool_calls.append({
                                    'tool': getattr(block, 'name', 'unknown'),
                                    'input': getattr(block, 'input', {})
                                })

                    if hasattr(msg, 'is_error') and msg.is_error:
                        raise MessageSendError(
                            f"Error in response: {getattr(msg, 'result', 'Unknown error')}"
                        )

                await self.storage.touch(session_id)

                return ChatResponse(
                    session_id=session_id,
                    text=full_text,
                    tool_calls=tool_calls,
                )

            except (SessionNotFoundError, SessionBusyError):
                raise
            except Exception as e:
                raise MessageSendError(f"Failed to send message: {e}")

    async def send_message_stream(
        self, session_id: str, message: str
    ) -> AsyncIterator[StreamChunk]:
        """
        Send a message (streaming mode).

        Args:
            session_id: Session ID
            message: User message

        Yields:
            StreamChunk objects

        Raises:
            SessionNotFoundError: If session not found
            SessionBusyError: If session is busy
        """
        session_lock = await self._get_session_lock(session_id)

        if session_lock.locked():
            raise SessionBusyError(f"Session {session_id} is busy")

        async with session_lock:
            try:
                client = await self._get_or_load_client(session_id)
                await client.query(prompt=message)

                full_text = ""
                async for msg in client.receive_response():
                    if hasattr(msg, 'content') and msg.content:
                        for block in msg.content:
                            if hasattr(block, 'text') and block.text:
                                new_text = block.text
                                if new_text.startswith(full_text):
                                    delta = new_text[len(full_text):]
                                    full_text = new_text
                                else:
                                    delta = new_text
                                    full_text += new_text

                                if delta:
                                    yield StreamChunk(type='text_delta', text=delta)

                            if hasattr(block, 'type') and block.type == 'tool_use':
                                yield StreamChunk(
                                    type='tool_use',
                                    tool_name=getattr(block, 'name', 'unknown'),
                                    tool_input=getattr(block, 'input', {}),
                                )

                    if hasattr(msg, 'is_error') and msg.is_error:
                        yield StreamChunk(
                            type='error',
                            error=getattr(msg, 'result', 'Unknown error')
                        )
                        return

                yield StreamChunk(type='done')
                await self.storage.touch(session_id)

            except (SessionNotFoundError, SessionBusyError):
                raise
            except Exception as e:
                yield StreamChunk(type='error', error=str(e))

    # ============ Cleanup ============

    async def cleanup(self) -> None:
        """Cleanup all client connections."""
        async with self._clients_lock:
            for session_id in list(self._clients.keys()):
                client = self._clients[session_id]
                try:
                    await client.__aexit__(None, None, None)
                except Exception:
                    pass
                finally:
                    del self._clients[session_id]

            self._session_locks.clear()

    # ============ Private Methods ============

    async def _get_session_lock(self, session_id: str) -> asyncio.Lock:
        """Get per-session lock."""
        async with self._clients_lock:
            if session_id not in self._session_locks:
                self._session_locks[session_id] = asyncio.Lock()
            return self._session_locks[session_id]

    def _build_options(
        self,
        cwd: str,
        system_prompt: Optional[str],
        mcp_servers: Dict,
        plugins: List[Dict],
        setting_sources: List[str],
        model: Optional[str],
        permission_mode: str,
        allowed_tools: List[str],
        disallowed_tools: List[str],
        add_dirs: List[str],
        max_turns: Optional[int],
        max_budget_usd: Optional[float],
        resume: Optional[str],
    ) -> ClaudeAgentOptions:
        """Build ClaudeAgentOptions."""
        options_dict = {
            'cwd': cwd,
            'permission_mode': permission_mode,
            'allowed_tools': allowed_tools,
            'mcp_servers': mcp_servers or {},
        }

        if system_prompt:
            options_dict['system_prompt'] = system_prompt

        if plugins:
            options_dict['plugins'] = plugins

        if setting_sources:
            options_dict['setting_sources'] = setting_sources

        if model:
            options_dict['model'] = model

        if disallowed_tools:
            options_dict['disallowed_tools'] = disallowed_tools

        if add_dirs:
            options_dict['add_dirs'] = add_dirs

        if max_turns:
            options_dict['max_turns'] = max_turns

        if max_budget_usd:
            options_dict['max_budget_usd'] = max_budget_usd

        if resume:
            options_dict['resume'] = resume

        return ClaudeAgentOptions(**options_dict)

    async def _extract_session_id(self, client: ClaudeSDKClient) -> Optional[str]:
        """Extract session_id from SDK response."""
        session_id = None
        async for message in client.receive_response():
            if hasattr(message, 'subtype') and message.subtype == 'init':
                if not session_id:
                    session_id = message.data.get('session_id')
        return session_id

    async def _get_or_load_client(self, session_id: str) -> ClaudeSDKClient:
        """Get client from memory or resume session."""
        async with self._clients_lock:
            if session_id in self._clients:
                return self._clients[session_id]

        await self.resume_session(session_id)

        async with self._clients_lock:
            if session_id in self._clients:
                return self._clients[session_id]
            else:
                raise SessionNotFoundError(f"Session {session_id} failed to load")
