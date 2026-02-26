"""
Core Claude Agent class for managing sessions and sending messages.
"""
import asyncio
import os
import re
import time
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

        # Track last activity time for idle session cleanup
        self._last_activity: Dict[str, float] = {}

        # Concurrency control semaphore
        self._concurrent_semaphore = asyncio.Semaphore(config.api.max_concurrent_requests)

        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit: cleanup resources."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
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
        # Check memory pressure before creating new session
        if not self._check_memory_pressure():
            mem_mb = self._get_process_memory_mb()
            raise ClientCreationError(
                f"Memory pressure too high ({mem_mb:.0f}MB / {self.config.api.memory_limit_mb}MB limit). "
                f"Close existing sessions or wait for idle cleanup."
            )

        # Check global session limit
        async with self._clients_lock:
            if len(self._clients) >= self.config.api.max_sessions:
                raise ClientCreationError(
                    f"Maximum sessions limit ({self.config.api.max_sessions}) reached"
                )

        # Check per-user session limit
        user_sessions = await self.list_sessions(user_id=user_id)
        if len(user_sessions) >= self.config.api.max_sessions_per_user:
            raise ClientCreationError(
                f"User {user_id} has reached maximum sessions ({self.config.api.max_sessions_per_user})"
            )

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
                self._last_activity[session_id] = time.time()

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

        # Fallback: recover from JSONL files when storage has no record
        # (e.g. after container restart with memory storage, or after TTL expiry)
        if not session_info:
            session_info = self._recover_session_from_jsonl(session_id)
            if session_info:
                await self.storage.save(session_id, session_info)

        if not session_info:
            raise SessionNotFoundError(f"Session {session_id} not found or expired")

        # Ensure working directory exists (may have been removed or renamed)
        ensure_directory(session_info.cwd, self.config.user.auto_create_dir)

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
                self._last_activity[session_id] = time.time()
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

            self._last_activity.pop(session_id, None)

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

        async with self._concurrent_semaphore:
            async with session_lock:
                try:
                    client = await self._get_or_load_client(session_id)
                    self._last_activity[session_id] = time.time()
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

        async with self._concurrent_semaphore:
            async with session_lock:
                try:
                    client = await self._get_or_load_client(session_id)
                    self._last_activity[session_id] = time.time()
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
            self._last_activity.clear()

    # ============ Memory Management ============

    def _get_process_memory_mb(self) -> float:
        """Get total memory usage of this process and its children in MB."""
        try:
            pid = os.getpid()
            # Read own RSS
            with open(f'/proc/{pid}/status', 'r') as f:
                for line in f:
                    if line.startswith('VmRSS:'):
                        own_rss_kb = int(line.split()[1])
                        break
                else:
                    own_rss_kb = 0

            # Read children RSS
            children_rss_kb = 0
            try:
                children_dir = f'/proc/{pid}/task/{pid}/children'
                if os.path.exists(children_dir):
                    with open(children_dir, 'r') as f:
                        child_pids = f.read().strip().split()
                else:
                    child_pids = []
                    # Fallback: scan /proc for children
                    for entry in os.listdir('/proc'):
                        if entry.isdigit():
                            try:
                                with open(f'/proc/{entry}/stat', 'r') as sf:
                                    parts = sf.read().split()
                                    if len(parts) > 3 and parts[3] == str(pid):
                                        child_pids.append(entry)
                            except (OSError, IOError):
                                continue

                for cpid in child_pids:
                    try:
                        with open(f'/proc/{cpid}/status', 'r') as f:
                            for line in f:
                                if line.startswith('VmRSS:'):
                                    children_rss_kb += int(line.split()[1])
                                    break
                    except (OSError, IOError):
                        continue
            except (OSError, IOError):
                pass

            return (own_rss_kb + children_rss_kb) / 1024.0
        except Exception:
            return 0.0

    def _check_memory_pressure(self) -> bool:
        """Check if system is under memory pressure. Returns True if safe."""
        limit_mb = self.config.api.memory_limit_mb
        if limit_mb <= 0:
            return True
        current_mb = self._get_process_memory_mb()
        return current_mb < limit_mb

    # ============ Session Recovery ============

    def _recover_session_from_jsonl(self, session_id: str) -> Optional[SessionInfo]:
        """
        Try to recover session info from JSONL files on disk.

        Used as fallback when storage has no record (e.g., memory storage
        after container restart, or after session TTL expiry).

        Claude CLI stores sessions at:
            ~/.claude/projects/{encoded_cwd}/{session_id}.jsonl
        where encoded_cwd is the absolute cwd path with '/' replaced by '-'.
        """
        projects_dir = os.path.join(os.path.expanduser('~'), '.claude', 'projects')

        if not os.path.isdir(projects_dir):
            return None

        # Find which project directory contains this session's JSONL file
        jsonl_filename = f"{session_id}.jsonl"
        found_dir_name = None

        try:
            for dir_name in os.listdir(projects_dir):
                jsonl_path = os.path.join(projects_dir, dir_name, jsonl_filename)
                if os.path.isfile(jsonl_path):
                    found_dir_name = dir_name
                    break
        except OSError:
            return None

        if not found_dir_name:
            return None

        # Decode: directory name is the cwd with '/' replaced by '-'
        # e.g., '-data-claude-users-22user' represents '/data/claude-users/22user'
        # Since this encoding is lossy (can't distinguish '-' in names from '/'),
        # we match against actual user directories under base_dir.
        base_dir = os.path.normpath(os.path.expanduser(self.config.user.base_dir))
        encoded_base = base_dir.replace('/', '-')

        if not found_dir_name.startswith(encoded_base):
            return None

        # Try to match against existing user directories
        # NOTE: Claude CLI encoding is lossy (replaces '/' with '-'), so
        # we can't distinguish '-' in user_id from path separators.
        # Use normalized comparison (treat '_' and '-' as equivalent) as fallback.
        user_id = None
        subdir = None
        cwd = None

        def _normalize(s: str) -> str:
            """Normalize string for comparison: treat '_' and '-' as equivalent."""
            return s.replace('_', '-')

        if os.path.isdir(base_dir):
            try:
                for entry in sorted(os.listdir(base_dir)):
                    entry_path = os.path.join(base_dir, entry)
                    if not os.path.isdir(entry_path):
                        continue

                    candidate_cwd = os.path.normpath(entry_path)
                    candidate_encoded = candidate_cwd.replace('/', '-')

                    if found_dir_name == candidate_encoded:
                        # Exact match: cwd = base_dir/user_id (no subdir)
                        user_id = entry
                        cwd = candidate_cwd
                        break
                    elif _normalize(found_dir_name) == _normalize(candidate_encoded):
                        # Normalized match: user_id contains '_' or '-' that
                        # got conflated in the lossy '/' → '-' encoding
                        user_id = entry
                        cwd = candidate_cwd
                        break
                    elif found_dir_name.startswith(candidate_encoded + '-'):
                        # Prefix match: session has a subdir
                        user_id = entry
                        subdir_encoded = found_dir_name[len(candidate_encoded) + 1:]
                        # Best-effort subdir decode (ambiguous with hyphens)
                        subdir = subdir_encoded
                        cwd = os.path.normpath(os.path.join(base_dir, user_id, subdir))
                        break
                    elif _normalize(found_dir_name).startswith(_normalize(candidate_encoded) + '-'):
                        # Normalized prefix match
                        user_id = entry
                        norm_prefix_len = len(_normalize(candidate_encoded)) + 1
                        subdir_encoded = _normalize(found_dir_name)[norm_prefix_len:]
                        subdir = subdir_encoded
                        cwd = os.path.normpath(os.path.join(base_dir, user_id, subdir))
                        break
            except OSError:
                pass

        # Fallback: extract user_id directly from remaining portion
        if not user_id:
            remaining = found_dir_name[len(encoded_base):]
            if remaining.startswith('-'):
                remaining = remaining[1:]
            if remaining and re.match(r'^[a-zA-Z0-9_-]+$', remaining):
                user_id = remaining
                cwd = os.path.normpath(os.path.join(base_dir, user_id))

        if not user_id or not cwd:
            return None

        print(f"[recovery] Recovered session {session_id} for user '{user_id}' from JSONL (cwd: {cwd})")

        return SessionInfo(
            session_id=session_id,
            user_id=user_id,
            subdir=subdir,
            cwd=cwd,
            system_prompt=self.config.defaults.system_prompt,
            mcp_servers=self.config.mcp_servers,
            plugins=self.config.plugins,
            setting_sources=self.config.defaults.setting_sources,
            model=self.config.defaults.model,
            permission_mode=self.config.defaults.permission_mode,
            allowed_tools=self.config.defaults.allowed_tools,
            disallowed_tools=[],
            add_dirs=[],
            max_turns=self.config.defaults.max_turns,
            max_budget_usd=self.config.defaults.max_budget_usd,
            metadata={"recovered_from_jsonl": True},
        )

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

        # Use npm-installed claude CLI instead of bundled Bun binary
        # (Bun crashes on CPUs without AVX support)
        cli_path = self.config.defaults.cli_path
        if cli_path:
            options_dict['cli_path'] = cli_path

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

    async def _periodic_cleanup(self) -> None:
        """Periodically cleanup expired/idle sessions and monitor memory."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every 1 minute

                now = time.time()
                expired = []
                idle = []
                idle_timeout = self.config.api.idle_session_timeout

                async with self._clients_lock:
                    for sid in list(self._clients.keys()):
                        info = await self.storage.get(sid)
                        if info is None:
                            # Storage has no record - try JSONL recovery before expiring
                            recovered = self._recover_session_from_jsonl(sid)
                            if recovered:
                                await self.storage.save(sid, recovered)
                            else:
                                expired.append(sid)
                        elif idle_timeout > 0:
                            last_active = self._last_activity.get(sid, 0)
                            if now - last_active > idle_timeout:
                                idle.append(sid)

                # Close truly expired sessions (no JSONL record either)
                for sid in expired:
                    await self.close_session(sid)

                # Evict idle in-memory clients (keep session in storage for resume)
                for sid in idle:
                    async with self._clients_lock:
                        if sid in self._clients:
                            client = self._clients[sid]
                            try:
                                await client.__aexit__(None, None, None)
                            except Exception:
                                pass
                            finally:
                                del self._clients[sid]
                            self._last_activity.pop(sid, None)

                # Memory pressure: force-evict oldest clients if over limit
                if not self._check_memory_pressure():
                    mem_mb = self._get_process_memory_mb()
                    print(f"[cleanup] Memory pressure: {mem_mb:.0f}MB, evicting idle clients")
                    async with self._clients_lock:
                        # Sort by last activity, evict oldest first
                        sorted_sids = sorted(
                            self._clients.keys(),
                            key=lambda s: self._last_activity.get(s, 0)
                        )
                        for sid in sorted_sids:
                            if self._check_memory_pressure():
                                break
                            if sid in self._clients:
                                client = self._clients[sid]
                                try:
                                    await client.__aexit__(None, None, None)
                                except Exception:
                                    pass
                                finally:
                                    del self._clients[sid]
                                self._last_activity.pop(sid, None)
                                print(f"[cleanup] Force-evicted session {sid} due to memory pressure")

                total_cleaned = len(expired) + len(idle)
                if total_cleaned > 0:
                    mem_mb = self._get_process_memory_mb()
                    print(f"[cleanup] Closed {len(expired)} expired, evicted {len(idle)} idle sessions. Memory: {mem_mb:.0f}MB")

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[cleanup] Error: {e}")
