# Claude Agent HTTP

HTTP REST API wrapper for Claude Agent SDK, providing multi-user session management for Claude Code.

English | [简体中文](README_CN.md)

## Features

- **Multi-user Support**: Each user has isolated working directory
- **Session Management**: Create, resume, and close sessions
- **Streaming Response**: SSE-based streaming for real-time output
- **Persistent Storage**: SQLite (single-instance) or PostgreSQL (multi-instance)
- **Configurable**: YAML config with environment variable overrides

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Run Server

```bash
python -m claude_agent_http.main
```

Or with uvicorn:

```bash
uvicorn claude_agent_http.main:app --host 0.0.0.0 --port 8000
```

### Configuration

Edit `config.yaml`:

```yaml
user:
  base_dir: "/home"          # Base directory for all users
  auto_create_dir: true      # Auto-create user directories

session:
  storage: "sqlite"          # memory | sqlite | postgresql
  ttl: 3600                  # Session TTL in seconds
  # SQLite settings
  sqlite_path: "sessions.db"
  # PostgreSQL settings (when storage: postgresql)
  pg_host: "localhost"
  pg_port: 5432
  pg_database: "claude_agent"
  pg_user: "postgres"
  pg_password: "postgres"

defaults:
  system_prompt: "You are a helpful AI assistant."
  permission_mode: "bypassPermissions"
  allowed_tools:
    - "Bash"
    - "Read"
    - "Write"
    - "Edit"
    - "Glob"
    - "Grep"
  model: null                # Model to use (null = SDK default)
  max_turns: null            # Max turns (null = unlimited)
  max_budget_usd: null       # Max budget (null = unlimited)

# Global MCP servers (applied to all sessions)
mcp_servers: {}

# Global plugins (applied to all sessions)
plugins: []
```

Environment variables override config file:

```bash
# Required: Set your Anthropic API Key
export ANTHROPIC_API_KEY="sk-ant-xxxxx"

# Optional: Override config settings
export CLAUDE_AGENT_USER_BASE_DIR="/data/users"
export CLAUDE_AGENT_SESSION_STORAGE="sqlite"
export CLAUDE_AGENT_API_PORT=8000
```

**Important**: You must set `ANTHROPIC_API_KEY` environment variable for the service to work. Get your API key from https://console.anthropic.com/

## Docker Deployment

For detailed Docker deployment instructions, see [DOCKER.md](DOCKER.md) ([中文版](DOCKER_CN.md))

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Edit .env and set your API Key
# ANTHROPIC_API_KEY=your_api_key_here

# 3. Start services
docker-compose up -d

# 4. Verify service
curl http://localhost:8000/health
```

## API Reference

> **Postman Collection**: Import `postman_collection.json` to test all APIs in Postman.
>
> **详细示例**: 查看 [docs/API_EXAMPLES.md](docs/API_EXAMPLES.md) 获取完整的 curl 测试示例。

### Sessions

#### Create Session

```bash
POST /api/v1/sessions
Content-Type: application/json

{
  "user_id": "zhangsan",           # Required
  "subdir": "my-project",          # Optional, default: user root
  "metadata": {"env": "prod"}      # Optional, custom business data
}
```

Response:

```json
{
  "session_id": "a61c5358-c9ef-4eac-a85e-ad8f68b93b30",
  "user_id": "zhangsan",
  "cwd": "/home/zhangsan/my-project",
  "created_at": "2026-01-06T11:43:12.893524",
  "last_active_at": "2026-01-06T11:43:12.893533",
  "message_count": 0,
  "status": "active",
  "metadata": {"env": "prod"}
}
```

> **Note**: SDK configurations (system_prompt, mcp_servers, model, max_turns, etc.) are read from `config.yaml`. This simplifies API usage.

#### List Sessions

```bash
GET /api/v1/sessions?user_id=zhangsan
```

#### Get Session Info

```bash
GET /api/v1/sessions/{session_id}
```

#### Resume Session

```bash
POST /api/v1/sessions/{session_id}/resume
```

#### Close Session

```bash
DELETE /api/v1/sessions/{session_id}
```

### Chat

#### Send Message (Sync)

```bash
POST /api/v1/chat
Content-Type: application/json

{
  "session_id": "abc123",
  "message": "Hello, what is 2+2?"
}
```

Response:

```json
{
  "session_id": "abc123",
  "text": "2 + 2 = 4",
  "tool_calls": [],
  "timestamp": "2024-01-01T00:00:00"
}
```

#### Send Message (Streaming)

```bash
POST /api/v1/chat/stream
Content-Type: application/json

{
  "session_id": "abc123",
  "message": "Write a hello world program"
}
```

Response (SSE):

```
data: {"type": "text_delta", "text": "Here"}
data: {"type": "text_delta", "text": " is"}
data: {"type": "tool_use", "tool_name": "Write", "tool_input": {...}}
data: {"type": "done"}
```

### Health Check

```bash
GET /health
```

## Directory Structure

```
claude_agent_http/
├── main.py           # FastAPI entry point
├── config.py         # Configuration
├── models.py         # Data models
├── exceptions.py     # Custom exceptions
├── security.py       # Path validation
├── agent.py          # Core ClaudeAgent class
├── storage/          # Session storage
│   ├── base.py       # Abstract base
│   ├── memory.py     # In-memory (dev)
│   ├── sqlite.py     # SQLite (single-instance)
│   └── postgresql.py # PostgreSQL (multi-instance)
└── routers/          # API routes
    ├── sessions.py   # Session endpoints
    └── chat.py       # Chat endpoints
```

## User Directory Isolation

Each session's working directory is derived from `user_id` and optional `subdir`:

```
base_dir = /home
user_id = zhangsan
subdir = my-project

cwd = /home/zhangsan/my-project
```

Security:
- Path traversal (`..`) is blocked
- Absolute paths in `subdir` are rejected
- All paths validated to stay within user directory

## License

MIT
