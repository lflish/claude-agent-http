# Docker Deployment Guide

This document explains how to deploy Claude Agent HTTP service using Docker and Docker Compose.

English | [简体中文](DOCKER_CN.md)

## Overview

The service supports three deployment modes through a unified `docker-compose.yml` file:

1. **SQLite + Named Volumes** (Default, Recommended) - Production-ready, automatic permission management
2. **SQLite + Bind Mounts** (Development) - Direct file access for development
3. **PostgreSQL** (Enterprise) - Multi-instance capable with connection pooling

## Quick Start

### Using Helper Script (Recommended)

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Edit .env and set your API Key
# ANTHROPIC_API_KEY=your_api_key_here

# 3. Start with automatic configuration
./docker-start.sh

# Or specify deployment mode:
./docker-start.sh --bind-mounts  # Development mode
./docker-start.sh --postgres     # PostgreSQL mode
```

### Manual Deployment

#### 1. Prepare Environment File

```bash
cp .env.example .env
```

Edit the `.env` file and **must** configure your Anthropic API Key:

```bash
# ⚠️ Required: Your Anthropic API Key (Get from https://console.anthropic.com/)
ANTHROPIC_API_KEY=your_api_key_here
```

> **Warning**: If you don't configure `ANTHROPIC_API_KEY`, the service can start but all Claude-related features will fail.

#### 2. Choose Deployment Mode

**Mode 1: SQLite + Named Volumes (Default)**

```bash
# Docker manages permissions automatically
docker-compose up -d
```

**Mode 2: SQLite + Bind Mounts (Development)**

```bash
# Copy bind mounts override configuration
cp docker-compose.override.bindmounts.yml docker-compose.override.yml

# Start services
docker-compose up -d
```

**Mode 3: PostgreSQL (Enterprise)**

```bash
# Start with PostgreSQL profile
docker-compose --profile postgres up -d
```

### 3. Verify Service

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

### 4. Stop Services

```bash
# Stop services (keep data)
docker-compose stop

# Stop and remove containers (keep data)
docker-compose down

# Complete cleanup (including volumes)
docker-compose down -v
```

## Configuration

### Deployment Modes

#### Mode 1: SQLite + Named Volumes (Default)

**Best for**: Production, single-instance deployments

- Docker automatically manages volume permissions
- No manual directory creation needed
- Containers run as UID 1000 (claudeuser)

```bash
# .env configuration
UID=1000
GID=1000
CLAUDE_AGENT_SESSION_STORAGE=sqlite
```

```bash
# Start
docker-compose up -d
```

#### Mode 2: SQLite + Bind Mounts (Development)

**Best for**: Development, when you need direct file access

- Direct access to files on host filesystem
- Requires proper host directory permissions
- Set UID/GID to match your host user

```bash
# .env configuration
UID=$(id -u)
GID=$(id -g)
CLAUDE_AGENT_SESSION_STORAGE=sqlite
```

```bash
# Copy override configuration
cp docker-compose.override.bindmounts.yml docker-compose.override.yml

# Start (docker-start.sh handles permissions automatically)
./docker-start.sh --bind-mounts
```

#### Mode 3: PostgreSQL (Enterprise)

**Best for**: Production, multi-instance deployments

- Multi-instance capable with connection pooling
- Better for high-concurrency scenarios

```bash
# .env configuration
CLAUDE_AGENT_SESSION_STORAGE=postgresql
CLAUDE_AGENT_SESSION_PG_PASSWORD=your_secure_password
```

```bash
# Start with PostgreSQL profile
docker-compose --profile postgres up -d
```

#### Mode 4: Memory (Development/Testing)

**Best for**: Testing, temporary sessions

- No persistence, data lost on restart
- Fastest performance

```bash
# .env configuration
CLAUDE_AGENT_SESSION_STORAGE=memory
```

### Volume Management

**Named Volumes** (Default):
- `claude-users` - User working directories
- `claude-db` - SQLite database
- `postgres_data` - PostgreSQL data (when using PostgreSQL)

**Bind Mounts** (Development):
- Specified via `HOST_USER_DATA_DIR` and `HOST_DB_DIR` in .env
- Configured through `docker-compose.override.yml`

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

### Common Issues

#### 1. Permission Denied Error: `EACCES: permission denied, mkdir '/home/claudeuser'`

**Symptoms:**
- Session creation fails with 503 Service Unavailable
- Logs show: `EACCES: permission denied, mkdir '/home/claudeuser'`
- Health check returns error

**Root Cause:**
Using outdated Docker image that doesn't have `claudeuser` user configured.

**Solution:**
```bash
# Stop containers
docker-compose down

# Rebuild image from scratch (no cache)
docker-compose build --no-cache

# Start services
docker-compose up -d

# Verify user is created
docker exec claude-agent-http id
# Should show: uid=1000(claudeuser) gid=1000 groups=1000

# Verify home directory exists
docker exec claude-agent-http ls -la /home/
# Should show: drwx------ claudeuser claudeuser /home/claudeuser
```

**Prevention:**
Always rebuild the image after pulling updates:
```bash
git pull
docker-compose build --no-cache
docker-compose up -d
```

#### 2. Health Check Returns 503

**Symptoms:**
- `curl http://localhost:8000/health` returns 503
- Container keeps restarting
- Logs show "Fatal error in message reader"

**Possible Causes & Solutions:**

**a) Missing HOME environment variable:**
```bash
# Check if HOME is set correctly
docker exec claude-agent-http env | grep HOME
# Should show: HOME=/home/claudeuser

# If missing, verify docker-compose.yml has:
environment:
  HOME: /home/claudeuser
```

**b) ANTHROPIC_API_KEY not configured:**
```bash
# Check if API key is set
docker exec claude-agent-http env | grep ANTHROPIC_API_KEY

# Configure in .env file
echo "ANTHROPIC_API_KEY=your_key_here" >> .env

# Restart
docker-compose restart
```

**c) Container user mismatch:**
```bash
# Check container user
docker exec claude-agent-http id

# Should be: uid=1000(claudeuser) gid=1000
# If different, rebuild image (see issue #1)
```

#### 3. Port Already in Use

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

#### 4. Bind Mounts Permission Errors

**Symptoms:**
- "Directory /data/claude-users is NOT writable"
- "Directory /data/db is NOT writable"

**Solution for Bind Mounts:**
```bash
# Check UID/GID in .env matches your user
id -u  # Get your UID
id -g  # Get your GID

# Update .env
echo "UID=$(id -u)" >> .env
echo "GID=$(id -g)" >> .env

# Create and fix host directory permissions
mkdir -p ~/.claude-code-http/{claude-users,db}
chown -R $(id -u):$(id -g) ~/.claude-code-http/

# Or for system-wide directory
sudo mkdir -p /opt/claude-code-http/{claude-users,db}
sudo chown -R $(id -u):$(id -g) /opt/claude-code-http/

# Restart
docker-compose restart
```

**Solution for Named Volumes (Default):**
```bash
# Remove bind mounts override if exists
rm -f docker-compose.override.yml

# Ensure UID/GID is 1000 (default)
echo "UID=1000" >> .env
echo "GID=1000" >> .env

# Restart
docker-compose down
docker-compose up -d
```

#### 5. Database Connection Failed (PostgreSQL)

**Symptoms:**
- "could not connect to server"
- "Connection refused"

**Solution:**
```bash
# Check if PostgreSQL container is running
docker-compose -f docker-compose.yml -f docker-compose.postgres.yml ps

# Check if database is healthy
docker-compose -f docker-compose.yml -f docker-compose.postgres.yml exec postgres pg_isready -U postgres

# View PostgreSQL logs
docker-compose -f docker-compose.yml -f docker-compose.postgres.yml logs postgres

# Verify environment variables
docker exec claude-agent-http env | grep PG_

# Connect to database manually
docker-compose -f docker-compose.yml -f docker-compose.postgres.yml exec postgres psql -U postgres -d claude_agent

# View database tables
\dt
```

#### 6. Container Keeps Restarting

**Diagnosis:**
```bash
# Check container status
docker-compose ps

# View recent logs
docker-compose logs --tail=50

# Check container exit code
docker inspect claude-agent-http | grep ExitCode

# Common exit codes:
# 1 - Application error (check logs)
# 137 - Killed by system (OOM or manual kill)
# 139 - Segmentation fault
```

**Solutions:**
```bash
# Clear all and start fresh
docker-compose down
docker volume prune  # Careful: removes unused volumes
docker-compose build --no-cache
docker-compose up -d

# If OOM (Out of Memory), increase Docker memory limit
# Docker Desktop: Settings -> Resources -> Memory
```

### Debugging Commands

#### View Logs

```bash
# View all service logs
docker-compose logs

# View API service logs
docker-compose logs app

# View PostgreSQL logs (if used)
docker-compose -f docker-compose.yml -f docker-compose.postgres.yml logs postgres

# Follow logs in real-time
docker-compose logs -f app

# View last 50 lines
docker-compose logs --tail=50 app
```

#### Inspect Container

```bash
# Check container status
docker-compose ps

# Inspect container configuration
docker inspect claude-agent-http

# Check resource usage
docker stats claude-agent-http

# Check volumes
docker volume ls | grep claude

# Inspect volume
docker volume inspect claude-agent-http_claude-users
```

#### Debug Inside Container

```bash
# Open shell in running container
docker exec -it claude-agent-http bash

# Check user and permissions
id
env | grep HOME
ls -la /home/claudeuser/
ls -la /data/

# Check processes
ps aux

# Check network
netstat -tlnp
curl localhost:8000/health

# Exit shell
exit
```

### Complete Clean and Rebuild

If all else fails, perform a complete cleanup:

```bash
# 1. Stop all containers
docker-compose down

# 2. Remove containers and volumes
docker-compose down -v

# 3. Remove images
docker rmi claude-agent-http_app

# 4. Clean build cache (optional)
docker builder prune -a

# 5. Rebuild from scratch
docker-compose build --no-cache

# 6. Start services
docker-compose up -d

# 7. Check logs
docker-compose logs -f
```

### Getting Help

If the issue persists:

1. **Collect Information:**
   ```bash
   # System info
   docker version
   docker-compose version
   uname -a

   # Container logs
   docker-compose logs --tail=100 > logs.txt

   # Container status
   docker-compose ps

   # Volume info
   docker volume ls | grep claude
   ```

2. **Check Documentation:**
   - Project README: `README.md`
   - Configuration guide: `CLAUDE.md`
   - API examples: `docs/API_EXAMPLES.md`

3. **Report Issue:**
   - Create GitHub Issue with collected information
   - Include error messages and logs
   - Describe steps to reproduce



## Complete Environment Variable List

See `.env.example` file for all configurable environment variables.

### Core Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key | **Required** |
| `ANTHROPIC_AUTH_TOKEN` | Alternative to API_KEY (for custom endpoints) | - |
| `ANTHROPIC_BASE_URL` | Custom API endpoint URL | https://api.anthropic.com |
| `ANTHROPIC_MODEL` | Override default model | SDK default |
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
