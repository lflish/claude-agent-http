# MCP Servers and Skills Configuration Guide

This guide explains how to configure MCP (Model Context Protocol) servers and skills for Claude Agent HTTP.

## Overview

The service supports two types of extensions:
1. **MCP Servers**: External services that provide tools and resources (filesystem, GitHub, search, etc.)
2. **Skills/Plugins**: Custom functionality modules loaded into Claude Agent

## Configuration Location

All configurations are in `config.yaml`:
- `mcp_servers`: Dictionary of MCP server configurations
- `plugins`: List of skill/plugin configurations

## MCP Servers Configuration

### Structure

#### STDIO Type (Local Process)

```yaml
mcp_servers:
  <server-name>:
    type: "stdio"           # Connection type for local processes
    command: "<command>"    # Executable command (e.g., npx, python)
    args: [...]            # Command arguments
    env:                   # Optional environment variables
      KEY: "value"
```

#### SSE Type (Remote Server)

```yaml
mcp_servers:
  <server-name>:
    type: "sse"            # Connection type for remote servers
    url: "http://host:port/path"  # Server URL endpoint
```

### Common MCP Servers

#### 1. Playwright Server

Provides browser automation capabilities:

```yaml
mcp_servers:
  playwright:
    type: "stdio"
    command: "npx"
    args:
      - "@playwright/mcp@latest"
```

**Available Tools**:
- `playwright_navigate` - Navigate to URL
- `playwright_screenshot` - Take screenshot
- `playwright_click` - Click element
- `playwright_fill` - Fill form fields
- `playwright_evaluate` - Execute JavaScript

**Use Cases**:
- Web scraping
- UI testing
- Browser automation
- Screenshot capture

#### 2. Filesystem Server

Provides file system access within specified directories:

```yaml
mcp_servers:
  filesystem:
    type: "stdio"
    command: "npx"
    args:
      - "-y"
      - "@modelcontextprotocol/server-filesystem"
      - "/path/to/allowed/directory"  # Required: specify allowed path
```

**Available Tools**:
- `read_file` - Read file contents
- `write_file` - Write to file
- `list_directory` - List directory contents
- `search_files` - Search for files

#### 2. GitHub Server

Provides GitHub repository access:

```yaml
mcp_servers:
  github:
    type: "stdio"
    command: "npx"
    args:
      - "-y"
      - "@modelcontextprotocol/server-github"
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "ghp_xxxxxxxxxxxx"
```

**Available Tools**:
- `create_or_update_file` - Create/update files in repo
- `search_repositories` - Search GitHub repos
- `create_issue` - Create GitHub issues
- `create_pull_request` - Create PRs
- `fork_repository` - Fork repositories
- `push_files` - Push multiple files

#### 3. Brave Search Server

Provides web search capabilities:

```yaml
mcp_servers:
  brave-search:
    type: "stdio"
    command: "npx"
    args:
      - "-y"
      - "@modelcontextprotocol/server-brave-search"
    env:
      BRAVE_API_KEY: "BSA_xxxxxxxxxxxxx"
```

Get API key from: https://brave.com/search/api/

#### 4. Google Maps Server

Provides location and mapping services:

```yaml
mcp_servers:
  google-maps:
    type: "stdio"
    command: "npx"
    args:
      - "-y"
      - "@modelcontextprotocol/server-google-maps"
    env:
      GOOGLE_MAPS_API_KEY: "AIzaSy_xxxxxxxxxxxx"
```

#### 5. Postgres Database Server

Provides PostgreSQL database access:

```yaml
mcp_servers:
  postgres:
    type: "stdio"
    command: "npx"
    args:
      - "-y"
      - "@modelcontextprotocol/server-postgres"
      - "postgresql://user:password@localhost/dbname"
```

#### 6. Memory Server

Provides persistent knowledge graph storage:

```yaml
mcp_servers:
  memory:
    type: "stdio"
    command: "npx"
    args:
      - "-y"
      - "@modelcontextprotocol/server-memory"
```

### Full List of Official MCP Servers

Visit: https://github.com/modelcontextprotocol/servers

## Skills/Plugins Configuration

### Structure

```yaml
plugins:
  - type: "local"           # Plugin type: local | remote
    path: "/path/to/skill"  # For local plugins
    # OR
  - type: "remote"
    url: "https://example.com/skill.json"  # For remote plugins
```

### Example: Local Skill

```yaml
plugins:
  - type: "local"
    path: "/app/skills/custom-skill"
```

### Example: Multiple Skills

```yaml
plugins:
  - type: "local"
    path: "/app/skills/data-analysis"
  - type: "local"
    path: "/app/skills/code-review"
  - type: "remote"
    url: "https://cdn.example.com/public-skill.json"
```

#### 7. Remote Exec Server (SSE)

Remote execution server via SSE connection:

```yaml
mcp_servers:
  remote_exec:
    type: "sse"
    url: "http://10.1.16.4:8000/mcp/sse"
```

**Features**:
- Remote command execution
- Server-Sent Events streaming
- Cross-machine operations

**Note**: Requires the remote server to implement MCP SSE protocol.

## Complete Configuration Example

Here's a full `config.yaml` example with MCP servers and skills:

```yaml
user:
  base_dir: "~/claude-agent-http/"
  auto_create_dir: true

session:
  storage: "sqlite"
  ttl: 3600
  sqlite_path: "sessions.db"

api:
  host: "0.0.0.0"
  port: 8000
  cors_origins:
    - "*"

defaults:
  system_prompt: "You are a helpful AI assistant with access to various tools."
  permission_mode: "bypassPermissions"
  allowed_tools:
    - "Bash"
    - "Read"
    - "Write"
    - "Edit"
    - "Glob"
    - "Grep"
  model: null
  max_turns: null
  max_budget_usd: null

# MCP Servers
mcp_servers:
  # Browser automation with Playwright
  playwright:
    type: "stdio"
    command: "npx"
    args:
      - "@playwright/mcp@latest"

  # File system access
  filesystem:
    type: "stdio"
    command: "npx"
    args:
      - "-y"
      - "@modelcontextprotocol/server-filesystem"
      - "/data/claude-users"

  # Remote execution via SSE
  remote_exec:
    type: "sse"
    url: "http://10.1.16.4:8000/mcp/sse"

# Skills/Plugins
plugins:
  - type: "local"
    path: "/app/skills/custom-analyzer"
```

## Docker Configuration

### Environment Variables

For sensitive data (API keys), use environment variables instead:

```yaml
# config.yaml - Use environment variable references
mcp_servers:
  github:
    type: "stdio"
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "${GITHUB_TOKEN}"
```

Then set in `.env`:
```bash
GITHUB_TOKEN=ghp_your_token_here
BRAVE_API_KEY=BSA_your_api_key_here
```

### Volume Mounting for Skills

If using local skills in Docker, mount the skills directory:

```yaml
# docker-compose.override.yml
services:
  app:
    volumes:
      - ./skills:/app/skills:ro  # Mount local skills directory
```

## Testing Configuration

After configuration, test your setup:

```bash
# 1. Create a session
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_id": "testuser"}'

# 2. Send a message that uses MCP tools
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "your-session-id",
    "message": "List files in the current directory"
  }'
```

## Troubleshooting

### MCP Server Not Working

1. Check if Node.js is installed: `node --version`
2. Verify npx can access the package: `npx -y @modelcontextprotocol/server-filesystem --version`
3. Check Docker logs: `docker-compose logs -f`
4. Ensure environment variables are properly set

### Skills Not Loading

1. Verify the plugin path exists and is accessible
2. Check the plugin structure follows Claude Agent SDK requirements
3. Review application logs for plugin loading errors

## Additional Resources

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [Official MCP Servers](https://github.com/modelcontextprotocol/servers)
- [Claude Agent SDK Documentation](https://github.com/anthropics/claude-agent-sdk)
