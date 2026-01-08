# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Claude Agent HTTP is a Python wrapper around the Claude Agent SDK, providing an HTTP REST API interface for multi-user session management with Claude Code.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run API server (development)
python -m claude_agent_http.main

# Or with uvicorn directly (with auto-reload)
uvicorn claude_agent_http.main:app --host 0.0.0.0 --port 8000 --reload

# Docker deployment (SQLite with named volumes - recommended)
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY
docker-compose up -d

# Docker deployment (SQLite with bind mounts - requires host permission setup)
docker-compose -f docker-compose.bindmounts.yml up -d

# Docker deployment (PostgreSQL)
docker-compose -f docker-compose.postgres.yml up -d

# Docker rebuild (no cache)
docker-compose build --no-cache

# Check service health
curl http://localhost:8000/health

# View Docker logs
docker-compose logs -f

# Test API (after server is running)
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_id": "testuser"}'
```

## Architecture

### Key Design Decisions

1. **User-based CWD**: Each session's working directory is derived from `user_id` + optional `subdir`
   - Default: `{base_dir}/{user_id}/`
   - With subdir: `{base_dir}/{user_id}/{subdir}/`

2. **Simplified API**: SDK configurations (system_prompt, mcp_servers, model, max_turns, etc.) are read from `config.yaml`, not passed via API. API only accepts:
   - `user_id` (required)
   - `subdir` (optional)
   - `metadata` (optional)

3. **Session Storage**: Memory (dev), SQLite (single-instance), or PostgreSQL (multi-instance)
   - Conversation history stored by Claude CLI (JSONL files)
   - Only session metadata stored in our database

4. **Concurrency**: Dual-lock pattern in `agent.py`
   - `_clients_lock`: Protects the `_clients` dict
   - `_session_locks[id]`: Prevents message interleaving per session

### Core Components

- **`agent.py`**: Core `ClaudeAgent` class - manages `ClaudeSDKClient` instances and sessions
- **`config.py`**: Pydantic config models, loads from `config.yaml` with env var overrides
- **`security.py`**: Path validation (`build_cwd`, `build_add_dirs`, `ensure_directory`)
- **`storage/`**: Session storage backends (Memory, SQLite, PostgreSQL)
- **`routers/`**: FastAPI routes for sessions and chat

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/sessions` | Create session (user_id required) |
| GET | `/api/v1/sessions` | List sessions (optional `?user_id=`) |
| GET | `/api/v1/sessions/{id}` | Get session info |
| DELETE | `/api/v1/sessions/{id}` | Close session |
| POST | `/api/v1/sessions/{id}/resume` | Resume session |
| POST | `/api/v1/chat` | Send message (sync) |
| POST | `/api/v1/chat/stream` | Send message (SSE streaming) |
| GET | `/health` | Health check |

### Configuration

All SDK settings are in `config.yaml`:

```yaml
user:
  base_dir: "/home"        # Base directory for all users
  auto_create_dir: true    # Auto-create directories

session:
  storage: "sqlite"        # memory | sqlite | postgresql
  ttl: 3600               # Session TTL in seconds
  # PostgreSQL settings (when storage: postgresql)
  pg_host: "localhost"
  pg_port: 5432
  pg_database: "claude_agent"
  pg_user: "postgres"
  pg_password: "postgres"

defaults:
  system_prompt: "..."
  permission_mode: "bypassPermissions"
  allowed_tools: [Bash, Read, Write, Edit, Glob, Grep]
  model: null             # null = SDK default
  max_turns: null
  max_budget_usd: null

mcp_servers: {}           # Global MCP servers for all sessions
plugins: []               # Global plugins for all sessions
```

**Environment Variables** (override config.yaml):
- `ANTHROPIC_API_KEY` (required) - Your Anthropic API key
- `ANTHROPIC_BASE_URL` - Custom API endpoint (e.g., for proxies)
- `ANTHROPIC_AUTH_TOKEN` - Alternative to API_KEY for custom endpoints
- `ANTHROPIC_MODEL` - Override default model
- `CLAUDE_AGENT_USER_BASE_DIR` - Override base directory
- `CLAUDE_AGENT_SESSION_STORAGE` - Override storage backend (memory|sqlite|postgresql)
- `CLAUDE_AGENT_SESSION_TTL` - Override session TTL (seconds)
- `CLAUDE_AGENT_SESSION_SQLITE_PATH` - Override SQLite database path
- `CLAUDE_AGENT_SESSION_PG_HOST` - PostgreSQL host
- `CLAUDE_AGENT_SESSION_PG_PORT` - PostgreSQL port
- `CLAUDE_AGENT_SESSION_PG_DATABASE` - PostgreSQL database name
- `CLAUDE_AGENT_SESSION_PG_USER` - PostgreSQL username
- `CLAUDE_AGENT_SESSION_PG_PASSWORD` - PostgreSQL password
- `CLAUDE_AGENT_API_PORT` - Override API port

**Priority**: Environment variables > config.yaml > defaults

### Security

- Path traversal (`..`) blocked in `security.py`
- `user_id` validated: alphanumeric, underscore, hyphen only
- `subdir` cannot be absolute or contain `..`
- `.env` file (contains secrets) excluded via `.gitignore`

## Important Implementation Notes

### Session Lifecycle
1. **Create**: `POST /api/v1/sessions` → returns session_id, creates ClaudeSDKClient instance
2. **Use**: `POST /api/v1/chat` or `/chat/stream` → acquires per-session lock, prevents concurrent messages
3. **Resume**: `POST /api/v1/sessions/{id}/resume` → reloads from storage, recreates ClaudeSDKClient
4. **Close**: `DELETE /api/v1/sessions/{id}` → removes from memory, keeps metadata in storage

### Dual-Lock Pattern (agent.py)
- `_clients_lock`: Protects the `_clients` dict during add/remove operations
- `_session_locks[id]`: Per-session lock prevents message interleaving within a session
- Always acquire session lock BEFORE sending messages via ClaudeSDKClient

### Storage Abstraction
All storage backends implement `SessionStorage` interface (storage/base.py):
- `save()`, `get()`, `delete()`, `touch()`, `list_sessions()`
- Memory: Dev/testing only, data lost on restart
- SQLite: Single-instance, file-based persistence
- PostgreSQL: Multi-instance, production-ready with proper connection pooling

### Path Security Flow
1. API receives `user_id` + optional `subdir`
2. `security.build_cwd()` validates and constructs: `{base_dir}/{user_id}/{subdir}`
3. `security.ensure_directory()` creates if needed (when `auto_create_dir=true`)
4. Path passed to ClaudeSDKClient as `cwd` option

### Docker Deployment Architecture

**Non-Root User Security**: Containers run as non-root user `claudeuser` (UID 1000) for security.

**Volume Strategies**:
1. **Named Volumes** (default `docker-compose.yml`): Docker manages permissions automatically
   - Use UID=1000, GID=1000 in .env (matches claudeuser)
   - Best for: Production deployments, portability
   - Database: `/data/db/sessions.db`
   - User files: `/data/claude-users/{user_id}/`

2. **Bind Mounts** (`docker-compose.bindmounts.yml`): Direct host filesystem access
   - Requires: `sudo chown -R $(id -u):$(id -g) /opt/claude-code-http/`
   - Set UID/GID in .env to match your host user
   - Best for: Development, when you need direct file access

**Entrypoint Script** (`docker-entrypoint.sh`):
- Validates write permissions on startup
- Provides clear error messages if permissions are wrong
- Tests `/data/claude-users` and `/data/db` directories

**Configuration Loading Order**:
1. Dockerfile builds with `config.yaml` defaults
2. docker-compose sets environment variables (highest priority)
3. Container starts with entrypoint checking permissions
4. Application loads config with env var overrides

## Documentation References

- Full API examples: `docs/API_EXAMPLES.md`
- Docker deployment: `DOCKER.md` (English), `DOCKER_CN.md` (中文)
- Postman collection: `postman_collection.json`
- User README: `README.md` (English), `README_CN.md` (中文)
