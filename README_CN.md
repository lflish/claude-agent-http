# Claude Agent HTTP

HTTP REST API 封装，基于 Claude Agent SDK，为 Claude Code 提供多用户会话管理。

[English](README.md) | 简体中文

## 特性

- **多用户支持**：每个用户拥有独立的工作目录
- **会话管理**：创建、恢复和关闭会话
- **流式响应**：基于 SSE 的流式输出，实时反馈
- **持久化存储**：SQLite（单实例）或 PostgreSQL（多实例）
- **灵活配置**：YAML 配置文件 + 环境变量覆盖

## 快速开始

### 安装

```bash
pip install -r requirements.txt
```

### 运行服务器

```bash
python -m claude_agent_http.main
```

或使用 uvicorn：

```bash
uvicorn claude_agent_http.main:app --host 0.0.0.0 --port 8000
```

### 配置

编辑 `config.yaml`：

```yaml
user:
  base_dir: "/home"          # 所有用户的基础目录
  auto_create_dir: true      # 自动创建用户目录

session:
  storage: "sqlite"          # memory | sqlite | postgresql
  ttl: 3600                  # 会话过期时间（秒）
  # SQLite 设置
  sqlite_path: "sessions.db"
  # PostgreSQL 设置（当 storage: postgresql）
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
  model: null                # 使用的模型（null = SDK 默认）
  max_turns: null            # 最大对话轮次（null = 无限制）
  max_budget_usd: null       # 最大预算（null = 无限制）

# 全局 MCP 服务器（应用于所有会话）
mcp_servers: {}

# 全局插件（应用于所有会话）
plugins: []
```

环境变量会覆盖配置文件：

```bash
# 必需：设置你的 Anthropic API Key
export ANTHROPIC_API_KEY="sk-ant-xxxxx"

# 可选：自定义 API 端点和模型
export ANTHROPIC_BASE_URL="https://your-custom-endpoint.com"
export ANTHROPIC_MODEL="claude-3-opus-20240229"

# 可选：覆盖配置设置
export CLAUDE_AGENT_USER_BASE_DIR="/data/users"
export CLAUDE_AGENT_SESSION_STORAGE="sqlite"
export CLAUDE_AGENT_API_PORT=8000
```

**重要**：你必须设置 `ANTHROPIC_API_KEY` 环境变量才能使服务正常工作。从 https://console.anthropic.com/ 获取你的 API 密钥。

**自定义端点**：如果使用自定义 API 端点或代理，请设置 `ANTHROPIC_BASE_URL`，并可选择使用 `ANTHROPIC_AUTH_TOKEN` 代替 `ANTHROPIC_API_KEY`。

## Docker 部署

详细的 Docker 部署指南请参考 [DOCKER_CN.md](DOCKER_CN.md)

```bash
# 1. 复制环境变量文件
cp .env.example .env

# 2. 编辑 .env 并设置你的 API Key
# ANTHROPIC_API_KEY=your_api_key_here

# 3. 启动服务
docker-compose up -d

# 4. 验证服务
curl http://localhost:8000/health
```

**故障排查**：如果在 Docker 部署过程中遇到任何问题，请参考 [DOCKER_CN.md 中的故障排查章节](DOCKER_CN.md#故障排查)，查看常见问题和解决方案。

## API 参考

> **Postman 集合**：导入 `postman_collection.json` 在 Postman 中测试所有 API。
>
> **详细示例**：查看 [docs/API_EXAMPLES.md](docs/API_EXAMPLES.md) 获取完整的 curl 测试示例。

### 会话管理

#### 创建会话

```bash
POST /api/v1/sessions
Content-Type: application/json

{
  "user_id": "zhangsan",           # 必需
  "subdir": "my-project",          # 可选，默认：用户根目录
  "metadata": {"env": "prod"}      # 可选，自定义业务数据
}
```

响应：

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

> **注意**：SDK 配置（system_prompt、mcp_servers、model、max_turns 等）从 `config.yaml` 读取。这简化了 API 的使用。

#### 列出会话

```bash
GET /api/v1/sessions?user_id=zhangsan
```

#### 获取会话信息

```bash
GET /api/v1/sessions/{session_id}
```

#### 恢复会话

```bash
POST /api/v1/sessions/{session_id}/resume
```

#### 关闭会话

```bash
DELETE /api/v1/sessions/{session_id}
```

### 聊天

#### 发送消息（同步）

```bash
POST /api/v1/chat
Content-Type: application/json

{
  "session_id": "abc123",
  "message": "Hello, what is 2+2?"
}
```

响应：

```json
{
  "session_id": "abc123",
  "text": "2 + 2 = 4",
  "tool_calls": [],
  "timestamp": "2024-01-01T00:00:00"
}
```

#### 发送消息（流式）

```bash
POST /api/v1/chat/stream
Content-Type: application/json

{
  "session_id": "abc123",
  "message": "Write a hello world program"
}
```

响应（SSE）：

```
data: {"type": "text_delta", "text": "Here"}
data: {"type": "text_delta", "text": " is"}
data: {"type": "tool_use", "tool_name": "Write", "tool_input": {...}}
data: {"type": "done"}
```

### 健康检查

```bash
GET /health
```

## 目录结构

```
claude_agent_http/
├── main.py           # FastAPI 入口
├── config.py         # 配置管理
├── models.py         # 数据模型
├── exceptions.py     # 自定义异常
├── security.py       # 路径验证
├── agent.py          # 核心 ClaudeAgent 类
├── storage/          # 会话存储
│   ├── base.py       # 抽象基类
│   ├── memory.py     # 内存存储（开发）
│   ├── sqlite.py     # SQLite（单实例）
│   └── postgresql.py # PostgreSQL（多实例）
└── routers/          # API 路由
    ├── sessions.py   # 会话端点
    └── chat.py       # 聊天端点
```

## 用户目录隔离

每个会话的工作目录由 `user_id` 和可选的 `subdir` 组成：

```
base_dir = /home
user_id = zhangsan
subdir = my-project

cwd = /home/zhangsan/my-project
```

安全性：
- 路径遍历（`..`）被阻止
- `subdir` 中的绝对路径被拒绝
- 所有路径都经过验证，确保在用户目录内

## 许可证

MIT
