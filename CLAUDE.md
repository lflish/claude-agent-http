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

# Docker deployment - Quick start with helper script
cp .env.example .env
# Edit .env and configure API authentication (ANTHROPIC_API_KEY or ANTHROPIC_BASE_URL+TOKEN)
./docker-start.sh

# Docker deployment - Manual modes
# 1. SQLite + Named Volumes (default, recommended)
docker-compose up -d

# 2. SQLite + Bind Mounts (development mode)
./docker-start.sh --bind-mounts

# 3. PostgreSQL (enterprise mode)
docker-compose --profile postgres up -d
# Or: ./docker-start.sh --postgres

# Docker management
./docker-start.sh --build    # Rebuild images
./docker-start.sh --stop     # Stop containers
./docker-start.sh --down     # Stop and remove containers

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
  base_dir: "~/claude-agent-http/"  # Base directory for all users
  auto_create_dir: true             # Auto-create directories

session:
  storage: "memory"        # memory | sqlite | postgresql
  ttl: 3600               # Session TTL in seconds (0 = no expiration)
  sqlite_path: "sessions.db"       # SQLite database path
  # PostgreSQL settings (when storage: postgresql)
  pg_host: "localhost"
  pg_port: 5432
  pg_database: "claude_agent"
  pg_user: "postgres"
  pg_password: "postgres"

api:
  host: "0.0.0.0"
  port: 8000
  cors_origins:
    - "*"

defaults:
  system_prompt: "You are a helpful AI assistant."
  permission_mode: "bypassPermissions"
  allowed_tools: [Bash, Read, Write, Edit, Glob, Grep, Skill]  # Include "Skill" to enable Skills
  setting_sources: [user, project]  # CRITICAL: Required to load Skills from filesystem
  model: null             # null = SDK default
  max_turns: null         # null = unlimited
  max_budget_usd: null    # null = unlimited

mcp_servers: {}           # Global MCP servers for all sessions
plugins: []               # SDK-level plugins (NOT the same as Skills)
```

**Environment Variables** (override config.yaml):

API Authentication (choose ONE method):
- Method 1 - Standard: `ANTHROPIC_API_KEY` - Your Anthropic API key
- Method 2 - Custom: `ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN` - Custom API endpoint

Core configuration:
- `CLAUDE_AGENT_USER_BASE_DIR` - Base directory for user files (default: /data/claude-users)
- `CLAUDE_AGENT_SESSION_STORAGE` - Storage backend: memory|sqlite|postgresql (default: sqlite)
- `CLAUDE_AGENT_SESSION_SQLITE_PATH` - SQLite database path (default: ~/.claude/sessions.db)

Optional overrides:
- `ANTHROPIC_MODEL` - Override default model
- `CLAUDE_AGENT_SESSION_TTL` - Session TTL in seconds (0 = no expiration)
- `CLAUDE_AGENT_SESSION_PG_*` - PostgreSQL connection settings (host, port, database, user, password)

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

### Skills Configuration (CRITICAL)

**Skills vs Plugins** - Two different concepts:
- **Skills**: SKILL.md files in `~/.claude/skills/` or `.claude/skills/` - loaded via `setting_sources`
- **Plugins**: SDK-level JavaScript/TypeScript modules - configured via `plugins` array

**To enable Skills, you MUST configure both**:

1. **Add `setting_sources` to defaults** (in config.py and config.yaml):
   ```python
   setting_sources: List[str] = Field(default_factory=lambda: ["user", "project"])
   ```
   - `"user"`: Loads from `~/.claude/skills/` (container: `/home/claudeuser/.claude/skills/`)
   - `"project"`: Loads from `.claude/skills/` relative to session cwd

2. **Add "Skill" to allowed_tools**:
   ```yaml
   allowed_tools: ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "Skill"]
   ```

3. **Pass `setting_sources` to SDK** (in agent.py):
   ```python
   setting_sources = self.config.defaults.setting_sources
   options = self._build_options(..., setting_sources=setting_sources)
   options_dict['setting_sources'] = setting_sources
   ```

**Without `setting_sources`**: Skills will NOT be loaded from filesystem, even if files exist and `plugins` is configured.

**Skills Directory Structure**:
```
/home/claudeuser/.claude/skills/
├── skill-name/
│   └── SKILL.md          # Required: frontmatter + instructions
└── another-skill/
    └── SKILL.md
```

**Docker Volume Mapping**:
- Host: `~/claude-users/lark/.claude/skills/`
- Container: `/home/claudeuser/.claude/skills/`
- Configured in docker-compose.yml volume: `claude-data`

### Docker Deployment Architecture

**Unified Configuration**: Single `docker-compose.yml` file supports multiple deployment modes through environment variables and profiles.

**Deployment Modes**:
1. **SQLite + Named Volumes** (default - production recommended)
   - Command: `docker-compose up -d` or `./docker-start.sh`
   - Docker manages permissions automatically
   - Best for: Production, single-instance deployments
   - Volumes:
     - `claude-data`: Claude SDK data (`~/.claude/`) - session history, cache
     - `claude-users`: User working directories (`/data/claude-users/{user_id}/`)

2. **SQLite + Bind Mounts** (development mode)
   - Command: `./docker-start.sh --bind-mounts`
   - Direct host filesystem access
   - Auto-creates directories and fixes permissions
   - Best for: Development, when you need direct file access

3. **PostgreSQL** (enterprise mode)
   - Command: `docker-compose --profile postgres up -d` or `./docker-start.sh --postgres`
   - Multi-instance capable with connection pooling
   - Best for: Production, multi-instance deployments

**Helper Script** (`docker-start.sh`):
- Validates configuration and environment variables
- Checks API authentication is configured (supports both standard and custom methods)
- Auto-creates and fixes permissions for bind mounts
- Provides clear error messages and suggestions
- Runs health checks after startup

**Volume Management**:
- **Named Volumes** (default):
  - `claude-data`: Claude SDK data (~/.claude/) - session history, cache, SQLite DB
  - `claude-users`: User working directories (/data/claude-users/)
  - Docker-managed, UID/GID defaults to 1000:1000
- **Bind Mounts**: Host-managed, use `docker-compose.override.yml` (auto-created by script)

**Configuration Priority**:
1. Environment variables (.env file) - highest priority
2. docker-compose.yml defaults
3. config.yaml defaults - lowest priority

## Code Modification Workflow

When making changes to Python code:

1. **Modify source files** in `claude_agent_http/`
2. **Rebuild Docker image**: `docker-compose build` (or `docker-compose build --no-cache` for clean build)
3. **Restart services**: `docker-compose down && docker-compose up -d`
4. **Verify changes**:
   ```bash
   # Check config loaded correctly
   docker exec claude-agent-http python3 -c "from claude_agent_http.config import get_config; print(get_config().defaults.setting_sources)"

   # Test API
   curl -X POST http://localhost:8000/api/v1/sessions -H "Content-Type: application/json" -d '{"user_id": "test"}'
   ```

**Note**: Changes to `config.yaml` do NOT require rebuild, only restart.

## Common Issues

### Skills Not Loading
**Symptom**: Claude reports "no skills available"

**Solution**: Verify all three requirements:
1. `setting_sources: ["user", "project"]` in config (not just `plugins`)
2. `"Skill"` in `allowed_tools`
3. Skills exist in `/home/claudeuser/.claude/skills/` with valid SKILL.md files

**Debug**:
```bash
docker exec claude-agent-http ls -la /home/claudeuser/.claude/skills/
docker exec claude-agent-http python3 -c "from claude_agent_http.config import get_config; print(get_config().defaults.setting_sources)"
```

### Docker Build Errors
If you get `KeyError: 'ContainerConfig'`:
```bash
docker-compose down
docker-compose build
docker-compose up -d
```

## Documentation References

- Full API examples: `docs/API_EXAMPLES.md`
- Docker deployment: `DOCKER.md` (English), `DOCKER_CN.md` (中文)
- MCP servers and skills: `MCP_AND_SKILLS.md`
- Skills investigation: `SKILLS_INVESTIGATION_FINAL.md` (troubleshooting reference)
- Postman collection: `postman_collection.json`
- User README: `README.md` (English), `README_CN.md` (中文)
