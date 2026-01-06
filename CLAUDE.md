# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

Claude Agent HTTP is a simplified Python wrapper around the Claude Agent SDK, providing an HTTP REST API interface to Claude Code.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run API server
python -m claude_agent_http.main

# Or with uvicorn directly
uvicorn claude_agent_http.main:app --host 0.0.0.0 --port 8000
```

## Architecture

### Directory Structure

```
claude_agent_http/
├── main.py           # FastAPI entry point, lifespan management
├── config.py         # Configuration models (Pydantic)
├── models.py         # Data models (SessionInfo, Request/Response)
├── exceptions.py     # Custom exceptions
├── security.py       # Path validation and security
├── agent.py          # Core ClaudeAgent class
├── storage/          # Session storage backends
│   ├── base.py       # Abstract SessionStorage class
│   ├── memory.py     # In-memory storage (dev/testing)
│   └── sqlite.py     # SQLite storage (production)
└── routers/          # API routes
    ├── sessions.py   # Session CRUD endpoints
    └── chat.py       # Chat endpoints (sync + SSE)
```

### Key Design Decisions

1. **User-based CWD**: Each session has a `cwd` derived from `user_id` + optional `subdir`
   - Default: `/home/{user_id}/`
   - With subdir: `/home/{user_id}/{subdir}/`

2. **Session Storage**: Memory (dev) or SQLite (production)
   - Conversation history stored by Claude CLI (JSONL)
   - Only metadata stored in our database

3. **Concurrency**: Dual-lock pattern
   - `_clients_lock`: Protects client dict
   - `_session_locks[id]`: Prevents message interleaving per session

### Configuration

```yaml
# config.yaml
user:
  base_dir: "/home"        # Base directory for all users
  auto_create_dir: true    # Auto-create directories

session:
  storage: "sqlite"        # memory | sqlite
  ttl: 3600               # Session TTL in seconds
  sqlite_path: "sessions.db"

defaults:
  system_prompt: "..."
  permission_mode: "bypassPermissions"
  allowed_tools: [...]
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/sessions` | Create session |
| GET | `/api/v1/sessions` | List sessions (optional `?user_id=`) |
| GET | `/api/v1/sessions/{id}` | Get session info |
| DELETE | `/api/v1/sessions/{id}` | Close session |
| POST | `/api/v1/sessions/{id}/resume` | Resume session |
| POST | `/api/v1/chat` | Send message (sync) |
| POST | `/api/v1/chat/stream` | Send message (SSE) |
| GET | `/health` | Health check |

### Session Creation Example

```json
POST /api/v1/sessions
{
  "user_id": "zhangsan",
  "subdir": "my-project",       // optional
  "system_prompt": "...",       // optional
  "mcp_servers": {...},         // optional
  "model": "...",               // optional
  "max_turns": 50,              // optional
  "max_budget_usd": 1.0         // optional
}
```

### Security

- Path traversal prevention in `security.py`
- `user_id` and `subdir` validated to prevent escape
- `add_dirs` must be relative paths under user directory
