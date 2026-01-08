# Docker Deployment Guide

This document explains how to deploy Claude Agent HTTP service using Docker and Docker Compose.

English | [简体中文](DOCKER_CN.md)

## Quick Start

### 1. Create Data Directories

```bash
# Create data directories
sudo mkdir -p /opt/claude-code-http/{claude-users,db}

# Set directory permissions
sudo chown -R $USER:$USER /opt/claude-code-http
```

### 2. Prepare Environment File

Copy the environment variable template and configure it:

```bash
cp .env.example .env
```

Edit the `.env` file and **must** configure your Anthropic API Key:

```bash
# ⚠️ Required: Your Anthropic API Key (Get from https://console.anthropic.com/)
ANTHROPIC_API_KEY=your_api_key_here
```

> **Warning**: If you don't configure `ANTHROPIC_API_KEY`, the service can start but all Claude-related features will fail.

### 3. Start Services

Default uses SQLite storage (suitable for single-instance deployment):

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 4. Verify Service

```bash
# Health check
curl http://localhost:8000/health

# Create session
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_id": "testuser"}'

# Send message
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session_id_from_above",
    "message": "Hello, Claude!"
  }'
```

### 5. Stop Services

```bash
# Stop services (keep data)
docker-compose stop

# Stop and remove containers (keep data)
docker-compose down

# Complete cleanup (including data)
docker-compose down
sudo rm -rf /opt/claude-code-http
```

## Configuration

### Storage Modes

#### SQLite (Default, Recommended for Single Instance)

Default configuration, no additional setup needed:

```bash
CLAUDE_AGENT_SESSION_STORAGE=sqlite
HOST_DB_DIR=/opt/claude-code-http/db
```

> **Note**: Even if `config.yaml` configures other storage methods (like PostgreSQL), Docker Compose will prioritize SQLite via environment variables. This is because **environment variables have higher priority than config files**.

#### PostgreSQL (Multi-instance/Production)

Use PostgreSQL compose file:

```bash
# Start PostgreSQL version
docker-compose -f docker-compose.postgres.yml up -d

# Or configure in .env
CLAUDE_AGENT_SESSION_STORAGE=postgresql
CLAUDE_AGENT_SESSION_PG_PASSWORD=your_secure_password
```

#### Memory (Development/Testing)

Configure in `.env`:

```bash
CLAUDE_AGENT_SESSION_STORAGE=memory
```

### Data Persistence

#### User Working Directory

User work files are stored in:

```bash
# Host path (default)
/opt/claude-code-http/claude-users/{user_id}/

# Can be modified in .env
HOST_USER_DATA_DIR=/opt/claude-code-http/claude-users
```

#### Session Database

- **SQLite**: Stored in `/opt/claude-code-http/db/sessions.db`
- **PostgreSQL**: Stored in Docker volume `postgres_data`

### Port Configuration

Modify ports in `.env` file:

```bash
# API service port
API_PORT=8000

# PostgreSQL port (postgres mode only)
POSTGRES_PORT=5432
```

### Custom Configuration File

If you need advanced configuration (like MCP servers, plugins, etc.), you can mount a custom `config.yaml`:

```bash
# Configure in .env
HOST_CONFIG_FILE=./config.yaml
```

Then edit the `config.yaml` file.

## Docker Only (Without Docker Compose)

If you only want to run the API service:

### 1. Build Image

```bash
docker build -t claude-agent-http .
```

### 2. Run Container (SQLite Mode)

> **Important**: You must set the storage type to `sqlite` via `-e` parameter, otherwise the container will use the default configuration from `config.yaml` (postgresql), causing startup failure.

```bash
docker run -d \
  --name claude-agent-http \
  -p 8000:8000 \
  -e ANTHROPIC_API_KEY=your_api_key \
  -e CLAUDE_AGENT_SESSION_STORAGE=sqlite \
  -v /opt/claude-code-http/claude-users:/data/claude-users \
  -v /opt/claude-code-http/db:/data/db \
  claude-agent-http
```

### 3. Run Container (External PostgreSQL)

```bash
docker run -d \
  --name claude-agent-http \
  -p 8000:8000 \
  -e ANTHROPIC_API_KEY=your_api_key \
  -e CLAUDE_AGENT_SESSION_STORAGE=postgresql \
  -e CLAUDE_AGENT_SESSION_PG_HOST=your_postgres_host \
  -e CLAUDE_AGENT_SESSION_PG_PASSWORD=your_password \
  -v /opt/claude-code-http/claude-users:/data/claude-users \
  claude-agent-http
```

## Production Deployment Recommendations

1. **Security**
   - Securely store `ANTHROPIC_API_KEY`
   - Change default PostgreSQL password
   - Use Docker secrets or key management tools
   - Restrict API access (firewall, VPN)

2. **Performance**
   - Configure appropriate `CLAUDE_AGENT_SESSION_TTL`
   - Regularly clean up expired sessions
   - Monitor disk space usage

3. **Monitoring**
   - Health check: `curl http://localhost:8000/health`
   - View logs: `docker-compose logs -f`
   - Monitor container status: `docker-compose ps`

4. **Backup**
   - Regularly backup user working directory: `/opt/claude-code-http/claude-users/`
   - SQLite mode: backup `/opt/claude-code-http/db/sessions.db`
   - PostgreSQL mode: backup `postgres_data` volume
   - Save configuration files: `.env` and `config.yaml`

5. **High Availability**
   - Multi-instance deployment recommends PostgreSQL
   - Use reverse proxy (Nginx/Traefik) for load balancing
   - Configure HTTPS certificates

## Troubleshooting

### View Logs

```bash
# View all service logs
docker-compose logs

# View API service logs
docker-compose logs app

# View PostgreSQL logs (if used)
docker-compose -f docker-compose.postgres.yml logs postgres

# Follow logs in real-time
docker-compose logs -f app
```

### Restart Services

```bash
# Restart services
docker-compose restart

# Rebuild and start
docker-compose up -d --build
```

### Port Already in Use

If you encounter `address already in use` error when starting:

```bash
# Check port usage
netstat -tlnp | grep :8000
# or
ss -tlnp | grep :8000

# Find the process PID using the port, then stop it
kill <PID>

# Clean up failed container
docker rm claude-agent-http

# Restart
docker-compose up -d

# Or modify port in .env
API_PORT=8001
```

### Permission Issues

If you encounter permission errors:

```bash
# Check directory permissions
ls -la /opt/claude-code-http/

# Fix permissions
sudo chown -R $USER:$USER /opt/claude-code-http
```

### Database Connection Issues (PostgreSQL)

```bash
# Check if database is ready
docker-compose -f docker-compose.postgres.yml exec postgres pg_isready -U postgres

# Connect to database
docker-compose -f docker-compose.postgres.yml exec postgres psql -U postgres -d claude_agent

# View database tables
\dt
```

### Clean and Rebuild

```bash
# Stop and remove all containers
docker-compose down

# Remove image and rebuild
docker-compose build --no-cache

# Restart
docker-compose up -d
```

## Complete Environment Variable List

See `.env.example` file for all configurable environment variables.

### Core Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key | **Required** |
| `CLAUDE_AGENT_SESSION_STORAGE` | Storage backend | sqlite |
| `CLAUDE_AGENT_SESSION_TTL` | Session expiration time (seconds) | 3600 |
| `API_PORT` | API service port | 8000 |

### Data Directories

| Variable | Description | Default |
|----------|-------------|---------|
| `HOST_USER_DATA_DIR` | User data directory (host) | /opt/claude-code-http/claude-users |
| `HOST_DB_DIR` | SQLite database directory (host) | /opt/claude-code-http/db |

### PostgreSQL Configuration (Optional)

| Variable | Description | Default |
|----------|-------------|---------|
| `CLAUDE_AGENT_SESSION_PG_HOST` | PostgreSQL host | postgres |
| `CLAUDE_AGENT_SESSION_PG_PORT` | PostgreSQL port | 5432 |
| `CLAUDE_AGENT_SESSION_PG_DATABASE` | Database name | claude_agent |
| `CLAUDE_AGENT_SESSION_PG_USER` | Database username | postgres |
| `CLAUDE_AGENT_SESSION_PG_PASSWORD` | Database password | postgres |
| `POSTGRES_PORT` | PostgreSQL external port | 5432 |

## More Information

- API Documentation: Visit `http://localhost:8000/docs` after starting the service
- Project Documentation: See `CLAUDE.md` and `README.md`
- Issue Reporting: Submit GitHub Issue
