# Docker 部署指南

本文档说明如何使用 Docker 和 Docker Compose 部署 Claude Agent HTTP 服务。

[English](DOCKER.md) | 简体中文

## 快速开始

### 1. 创建数据目录

```bash
# 创建数据目录
sudo mkdir -p /opt/claude-code-http/{claude-users,db}

# 设置目录权限
sudo chown -R $USER:$USER /opt/claude-code-http
```

### 2. 准备环境文件

复制环境变量模板文件并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，**必须**配置你的 Anthropic API Key：

```bash
# ⚠️ 必须配置：你的 Anthropic API Key（从 https://console.anthropic.com/ 获取）
ANTHROPIC_API_KEY=your_api_key_here
```

> **警告**：如果不配置 `ANTHROPIC_API_KEY`，服务虽然能启动，但所有 Claude 相关功能都会失败。

### 3. 启动服务

默认使用 SQLite 存储（适合单实例部署）：

```bash
# 构建并启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 查看服务状态
docker-compose ps
```

### 4. 验证服务

```bash
# 健康检查
curl http://localhost:8000/health

# 创建会话
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_id": "testuser"}'

# 发送消息
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session_id_from_above",
    "message": "Hello, Claude!"
  }'
```

### 4. 停止服务

```bash
# 停止服务（保留数据）
docker-compose stop

# 停止并删除容器（保留数据）
docker-compose down

# 完全清理（包括数据）
docker-compose down
sudo rm -rf /opt/claude-code-http
```

## 配置说明

### 存储模式

#### SQLite（默认，推荐单实例）

默认配置，无需额外设置：

```bash
CLAUDE_AGENT_SESSION_STORAGE=sqlite
HOST_DB_DIR=/opt/claude-code-http/db
```

> **注意**：即使 `config.yaml` 中配置了其他存储方式（如 PostgreSQL），使用 Docker Compose 时会通过环境变量优先使用 SQLite。这是因为**环境变量的优先级高于配置文件**。

#### PostgreSQL（多实例/生产环境）

使用 PostgreSQL compose 文件：

```bash
# 启动 PostgreSQL 版本
docker-compose -f docker-compose.postgres.yml up -d

# 或者在 .env 中配置
CLAUDE_AGENT_SESSION_STORAGE=postgresql
CLAUDE_AGENT_SESSION_PG_PASSWORD=your_secure_password
```

#### Memory（开发/测试）

在 `.env` 中配置：

```bash
CLAUDE_AGENT_SESSION_STORAGE=memory
```

### 数据持久化

#### 用户工作目录

用户的工作文件存储在：

```bash
# 宿主机路径（默认）
/opt/claude-code-http/claude-users/{user_id}/

# 可在 .env 中修改
HOST_USER_DATA_DIR=/opt/claude-code-http/claude-users
```

#### 会话数据库

- **SQLite**: 存储在 `/opt/claude-code-http/db/sessions.db`
- **PostgreSQL**: 存储在 Docker volume `postgres_data`

### 端口配置

在 `.env` 文件中修改端口：

```bash
# API 服务端口
API_PORT=8000

# PostgreSQL 端口（仅 postgres 模式）
POSTGRES_PORT=5432
```

### 自定义配置文件

如果需要更高级的配置（如 MCP servers、插件等），可以挂载自定义 `config.yaml`：

```bash
# 在 .env 中配置
HOST_CONFIG_FILE=./config.yaml
```

然后编辑 `config.yaml` 文件。

## 仅使用 Docker（不使用 Docker Compose）

如果你只想运行 API 服务：

### 1. 构建镜像

```bash
docker build -t claude-agent-http .
```

### 2. 运行容器（SQLite 模式）

> **重要**：必须通过 `-e` 参数设置存储类型为 `sqlite`，否则容器会使用 `config.yaml` 中的默认配置（postgresql），导致启动失败。

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

### 3. 运行容器（外部 PostgreSQL）

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

## 生产部署建议

1. **安全性**
   - 妥善保管 `ANTHROPIC_API_KEY`
   - 如使用 PostgreSQL，修改默认密码
   - 使用 Docker secrets 或密钥管理工具
   - 限制 API 访问（防火墙、VPN）

2. **性能**
   - 配置适当的 `CLAUDE_AGENT_SESSION_TTL`
   - 定期清理过期会话
   - 监控磁盘空间使用

3. **监控**
   - 健康检查：`curl http://localhost:8000/health`
   - 查看日志：`docker-compose logs -f`
   - 监控容器状态：`docker-compose ps`

4. **备份**
   - 定期备份用户工作目录：`/opt/claude-code-http/claude-users/`
   - SQLite 模式：备份 `/opt/claude-code-http/db/sessions.db`
   - PostgreSQL 模式：备份 `postgres_data` volume
   - 保存配置文件：`.env` 和 `config.yaml`

5. **高可用性**
   - 多实例部署建议使用 PostgreSQL
   - 使用反向代理（Nginx/Traefik）进行负载均衡
   - 配置 HTTPS 证书

## 故障排查

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs

# 查看 API 服务日志
docker-compose logs app

# 查看 PostgreSQL 日志（如使用）
docker-compose -f docker-compose.postgres.yml logs postgres

# 实时跟踪日志
docker-compose logs -f app
```

### 重启服务

```bash
# 重启服务
docker-compose restart

# 重新构建并启动
docker-compose up -d --build
```

### 端口被占用

如果启动时遇到 `address already in use` 错误：

```bash
# 检查端口占用
netstat -tlnp | grep :8000
# 或
ss -tlnp | grep :8000

# 找到占用端口的进程 PID，然后停止它
kill <PID>

# 清理失败的容器
docker rm claude-agent-http

# 重新启动
docker-compose up -d

# 或者修改 .env 中的端口
API_PORT=8001
```

### 权限问题

如果遇到权限错误：

```bash
# 检查目录权限
ls -la /opt/claude-code-http/

# 修复权限
sudo chown -R $USER:$USER /opt/claude-code-http
```

### 数据库连接问题（PostgreSQL）

```bash
# 检查数据库是否就绪
docker-compose -f docker-compose.postgres.yml exec postgres pg_isready -U postgres

# 连接数据库
docker-compose -f docker-compose.postgres.yml exec postgres psql -U postgres -d claude_agent

# 查看数据库表
\dt
```

### 清理并重新构建

```bash
# 停止并删除所有容器
docker-compose down

# 删除镜像并重新构建
docker-compose build --no-cache

# 重新启动
docker-compose up -d
```

## 环境变量完整列表

查看 `.env.example` 文件获取所有可配置的环境变量说明。

### 核心配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ANTHROPIC_API_KEY` | Anthropic API 密钥 | **必填** |
| `CLAUDE_AGENT_SESSION_STORAGE` | 存储后端 | sqlite |
| `CLAUDE_AGENT_SESSION_TTL` | 会话过期时间（秒） | 3600 |
| `API_PORT` | API 服务端口 | 8000 |

### 数据目录

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `HOST_USER_DATA_DIR` | 用户数据目录（宿主机） | /opt/claude-code-http/claude-users |
| `HOST_DB_DIR` | SQLite 数据库目录（宿主机） | /opt/claude-code-http/db |

### PostgreSQL 配置（可选）

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `CLAUDE_AGENT_SESSION_PG_HOST` | PostgreSQL 主机 | postgres |
| `CLAUDE_AGENT_SESSION_PG_PORT` | PostgreSQL 端口 | 5432 |
| `CLAUDE_AGENT_SESSION_PG_DATABASE` | 数据库名称 | claude_agent |
| `CLAUDE_AGENT_SESSION_PG_USER` | 数据库用户名 | postgres |
| `CLAUDE_AGENT_SESSION_PG_PASSWORD` | 数据库密码 | postgres |
| `POSTGRES_PORT` | PostgreSQL 外部端口 | 5432 |

## 更多信息

- API 文档：启动服务后访问 `http://localhost:8000/docs`
- 项目文档：查看 [CLAUDE.md](CLAUDE.md) 和 [README_CN.md](README_CN.md)
- 问题反馈：提交 GitHub Issue
