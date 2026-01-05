# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Claude Agent is a Python wrapper around the Claude Agent SDK, providing two interfaces:
- **Library (`claude_agent_lib`)**: Async Python library for programmatic access
- **REST API (`claude_agent_api`)**: FastAPI-based HTTP service

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run REST API server
python -m claude_agent_api.main
```

## Architecture

### Configuration Flow
All modules share a unified configuration system:
```
config.yaml → config_loader.py → LibraryConfig.from_yaml()
                                      ↓
                              Environment variables override
                              (POSTGRES_URL, REDIS_URL, etc.)
```

### Library Module (`claude_agent_lib/`)
- `client.py`: Core `ClaudeAgentLibrary` class - wraps `ClaudeSDKClient` from `claude_agent_sdk`
- `session.py`: Session storage backends (memory/file/redis/postgres) with abstract `SessionStorage` base class
- `config.py`: `LibraryConfig` Pydantic model with `from_yaml()` class method
- `models.py`: Data models (`SessionInfo`, `Message`, `StreamChunk`)

Key pattern in `client.py`:
- Maintains `_clients` dict mapping session_id → ClaudeSDKClient
- Uses `_clients_lock` for concurrent access and `_session_locks` per-session to prevent message interleaving
- `_extract_session_id()` must fully consume the response stream to avoid response misalignment

### API Module (`claude_agent_api/`)
- `main.py`: FastAPI app with lifespan management
- `routers/sessions.py`: Session CRUD endpoints
- `routers/chat.py`: Message send endpoints (sync and SSE streaming)
- `dependencies.py`: Global library instance injection
- `schemas.py`: Pydantic request/response models

### Session Storage Options
| Type | Use Case |
|------|----------|
| `memory` | Development/testing |
| `file` | Single instance |
| `redis` | Multi-instance (requires REDIS_URL) |
| `postgres` | Production (requires POSTGRES_URL) |

## API Endpoints

- `POST /api/v1/sessions` - Create session
- `DELETE /api/v1/sessions/{id}` - Close session
- `POST /api/v1/chat` - Send message (sync)
- `POST /api/v1/chat/stream` - Send message (SSE)
- `GET /health` - Health check
