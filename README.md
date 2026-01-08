<div align="center">

# 🤖 Claude Agent HTTP

**Production-ready HTTP REST API wrapper for Claude Agent SDK**

*Bring multi-user session management and RESTful APIs to Claude Code*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Release](https://img.shields.io/github/v/release/lflish/claude-agent-http)](https://github.com/lflish/claude-agent-http/releases)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)

[English](README.md) | [简体中文](README_CN.md)

[Features](#-features) •
[Quick Start](#-quick-start) •
[Docker](#-docker-deployment) •
[API Docs](#-api-reference) •
[Documentation](#-documentation)

</div>

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 👥 **Multi-User Support**
Isolated working directories for each user with automatic path validation and security

</td>
<td width="50%">

### 🔄 **Session Management**
Create, resume, close sessions with persistent storage (SQLite/PostgreSQL)

</td>
</tr>
<tr>
<td width="50%">

### ⚡ **Streaming Response**
Real-time SSE-based streaming for responsive user experience

</td>
<td width="50%">

### 🗄️ **Flexible Storage**
Choose from Memory, SQLite (single-instance), or PostgreSQL (multi-instance)

</td>
</tr>
<tr>
<td width="50%">

### ⚙️ **Highly Configurable**
YAML config with environment variable overrides for easy deployment

</td>
<td width="50%">

### 🐳 **Docker Ready**
Production-ready Docker setup with automatic permission management

</td>
</tr>
</table>

## 🎯 Use Cases

- **🏢 Enterprise Deployment**: Multi-user Claude Code deployment with centralized management
- **💼 Team Collaboration**: Shared Claude Code service for development teams
- **🔌 API Integration**: RESTful API for integrating Claude Code into existing systems
- **📊 Usage Tracking**: Centralized session and usage monitoring
- **🔒 Security**: Isolated user environments with path validation

## 🚀 Quick Start

### Method 1: Docker (Recommended)

The fastest way to get started:

```bash
# 1. Clone the repository
git clone https://github.com/lflish/claude-agent-http.git
cd claude-agent-http

# 2. Setup environment
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=your_api_key_here

# 3. Start services
docker-compose up -d

# 4. Verify
curl http://localhost:8000/health
```

✅ **That's it!** Your API is running at `http://localhost:8000`

📖 For detailed Docker deployment, see [DOCKER.md](DOCKER.md) | [中文版](DOCKER_CN.md)

### Method 2: Manual Installation

For development or custom setups:

```bash
# Install dependencies
pip install -r requirements.txt

# Set your API key
export ANTHROPIC_API_KEY="sk-ant-xxxxx"

# Run server
python -m claude_agent_http.main

# Or with uvicorn (auto-reload)
uvicorn claude_agent_http.main:app --reload --host 0.0.0.0 --port 8000
```

## 🐳 Docker Deployment

We provide three deployment modes:

| Mode | Use Case | Command |
|------|----------|---------|
| **SQLite + Named Volumes** | Production (default) | `docker-compose up -d` |
| **SQLite + Bind Mounts** | Development | `./docker-start.sh --bind-mounts` |
| **PostgreSQL** | Multi-instance | `./docker-start.sh --postgres` |

### Quick Deploy

```bash
# SQLite mode (default)
docker-compose up -d

# PostgreSQL mode
docker-compose -f docker-compose.yml -f docker-compose.postgres.yml up -d

# Check health
curl http://localhost:8000/health
```

### Docker Features

- ✅ Automatic volume permission management
- ✅ Non-root user execution for security
- ✅ Health checks built-in
- ✅ Named volumes or bind mounts support
- ✅ PostgreSQL for multi-instance deployments

**Troubleshooting**: Having issues? Check our [comprehensive troubleshooting guide](DOCKER.md#troubleshooting) covering 6 common problems and solutions.

## 📚 API Reference

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/api/v1/sessions` | POST | Create new session |
| `/api/v1/sessions` | GET | List sessions (optional `?user_id=`) |
| `/api/v1/sessions/{id}` | GET | Get session details |
| `/api/v1/sessions/{id}` | DELETE | Close session |
| `/api/v1/sessions/{id}/resume` | POST | Resume session |
| `/api/v1/chat` | POST | Send message (sync) |
| `/api/v1/chat/stream` | POST | Send message (streaming SSE) |

### Quick Example

```bash
# Create a session
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_id": "alice", "subdir": "my-project"}'

# Send a message
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "your-session-id",
    "message": "Write a Python hello world program"
  }'
```

### API Testing

- 📮 **Postman Collection**: Import [`postman_collection.json`](postman_collection.json) to test all APIs
- 📖 **Detailed Examples**: See [docs/API_EXAMPLES.md](docs/API_EXAMPLES.md) for complete curl examples
- 🌐 **Interactive Docs**: Visit `http://localhost:8000/docs` after starting the server

## ⚙️ Configuration

### Environment Variables

```bash
# Required: Anthropic API Configuration
ANTHROPIC_API_KEY=sk-ant-xxxxx         # Your API key (required)

# Optional: Custom endpoint or proxy
ANTHROPIC_BASE_URL=https://api.anthropic.com
ANTHROPIC_AUTH_TOKEN=                   # Alternative to API_KEY
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Optional: Service Configuration
CLAUDE_AGENT_SESSION_STORAGE=sqlite     # memory | sqlite | postgresql
CLAUDE_AGENT_SESSION_TTL=3600           # Session timeout (seconds)
CLAUDE_AGENT_USER_BASE_DIR=/data/users  # User files directory
CLAUDE_AGENT_API_PORT=8000              # API server port
```

### Configuration File

Edit `config.yaml` for advanced settings:

```yaml
user:
  base_dir: "/home"          # Base directory for all users
  auto_create_dir: true      # Auto-create user directories

session:
  storage: "sqlite"          # memory | sqlite | postgresql
  ttl: 3600                  # Session TTL in seconds

defaults:
  system_prompt: "You are a helpful AI assistant."
  permission_mode: "bypassPermissions"
  allowed_tools: [Bash, Read, Write, Edit, Glob, Grep]
  model: null                # null = SDK default
  max_turns: null            # null = unlimited
  max_budget_usd: null       # null = unlimited

mcp_servers: {}              # Global MCP servers
plugins: []                  # Global plugins
```

**Priority**: Environment Variables > config.yaml > Defaults

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Claude Agent HTTP                       │
│                                                             │
│  ┌───────────────┐      ┌──────────────┐                  │
│  │  FastAPI      │──────│   Routers    │                  │
│  │  HTTP Server  │      │ (REST APIs)  │                  │
│  └───────────────┘      └──────────────┘                  │
│                                │                            │
│                         ┌──────▼──────┐                    │
│                         │ ClaudeAgent │                    │
│                         │   Manager   │                    │
│                         └──────┬──────┘                    │
│                                │                            │
│         ┌──────────────────────┼──────────────────────┐    │
│         │                      │                      │    │
│    ┌────▼─────┐      ┌────────▼────────┐      ┌─────▼────┐│
│    │  Memory  │      │     SQLite      │      │PostgreSQL││
│    │ Storage  │      │    Storage      │      │ Storage  ││
│    └──────────┘      └─────────────────┘      └──────────┘│
│                                                             │
│                         ┌──────────────┐                   │
│                         │ Claude Agent │                   │
│                         │     SDK      │                   │
│                         └──────────────┘                   │
└─────────────────────────────────────────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Anthropic Claude API  │
                    └─────────────────────────┘
```

### Project Structure

```
claude_agent_http/
├── main.py              # FastAPI entry point
├── config.py            # Configuration management
├── models.py            # Data models
├── agent.py             # Core ClaudeAgent class
├── security.py          # Path validation & security
├── storage/             # Session storage backends
│   ├── base.py          # Abstract interface
│   ├── memory.py        # In-memory storage
│   ├── sqlite.py        # SQLite storage
│   └── postgresql.py    # PostgreSQL storage
└── routers/             # API route handlers
    ├── sessions.py      # Session management
    └── chat.py          # Chat endpoints
```

## 🔒 Security Features

- **Path Validation**: Prevents path traversal attacks (`..` blocked)
- **User Isolation**: Each user has isolated working directory
- **Non-root Execution**: Docker containers run as non-root user (claudeuser)
- **Input Validation**: All API inputs validated with Pydantic
- **Session Security**: Unique session IDs with configurable TTL

## 📖 Documentation

- 📘 **[DOCKER.md](DOCKER.md)**: Comprehensive Docker deployment guide (English)
- 📗 **[DOCKER_CN.md](DOCKER_CN.md)**: Docker 部署指南（中文）
- 📙 **[API_EXAMPLES.md](docs/API_EXAMPLES.md)**: Complete API examples
- 📕 **[CLAUDE.md](CLAUDE.md)**: Project architecture and design decisions
- 📝 **[CHANGELOG.md](CHANGELOG.md)**: Version history and changes

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk)
- Powered by [Anthropic Claude API](https://www.anthropic.com/)
- Web framework: [FastAPI](https://fastapi.tiangolo.com/)

## 📞 Support

- 🐛 **Issues**: [GitHub Issues](https://github.com/lflish/claude-agent-http/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/lflish/claude-agent-http/discussions)
- 📧 **Email**: Create an issue for support

---

<div align="center">

**Made with ❤️ by the Claude Agent HTTP team**

⭐ Star us on GitHub — it helps!

[Report Bug](https://github.com/lflish/claude-agent-http/issues) •
[Request Feature](https://github.com/lflish/claude-agent-http/issues) •
[View Releases](https://github.com/lflish/claude-agent-http/releases)

</div>
