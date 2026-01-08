# Docker 部署指南

本文档说明如何使用 Docker 和 Docker Compose 部署 Claude Agent HTTP 服务。

[English](DOCKER.md) | 简体中文

## 概述

服务通过统一的 `docker-compose.yml` 文件支持三种部署模式：

1. **SQLite + 命名卷**（默认，推荐）- 生产就绪，自动权限管理
2. **SQLite + 绑定挂载**（开发）- 直接文件访问用于开发
3. **PostgreSQL**（企业）- 支持多实例和连接池

## 快速开始

### 使用辅助脚本（推荐）

```bash
# 1. 复制环境文件
cp .env.example .env

# 2. 编辑 .env 并设置你的 API Key
# ANTHROPIC_API_KEY=your_api_key_here

# 3. 使用自动配置启动
./docker-start.sh

# 或指定部署模式：
./docker-start.sh --bind-mounts  # 开发模式
./docker-start.sh --postgres     # PostgreSQL 模式
```

### 手动部署

#### 1. 准备环境文件

```bash
cp .env.example .env
```

编辑 `.env` 文件，**必须**配置你的 Anthropic API Key：

```bash
# ⚠️ 必须配置：你的 Anthropic API Key（从 https://console.anthropic.com/ 获取）
ANTHROPIC_API_KEY=your_api_key_here
```

> **警告**：如果不配置 `ANTHROPIC_API_KEY`，服务虽然能启动，但所有 Claude 相关功能都会失败。

#### 2. 选择部署模式

**模式 1：SQLite + 命名卷（默认）**

```bash
# Docker 自动管理权限
docker-compose up -d
```

**模式 2：SQLite + 绑定挂载（开发）**

```bash
# 复制绑定挂载覆盖配置
cp docker-compose.override.bindmounts.yml docker-compose.override.yml

# 启动服务
docker-compose up -d
```

**模式 3：PostgreSQL（企业）**

```bash
# 使用 PostgreSQL profile 启动
docker-compose --profile postgres up -d
```

### 3. 验证服务

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

# 完全清理（包括卷）
docker-compose down -v
```

## 配置说明

### 部署模式

#### 模式 1：SQLite + 命名卷（默认）

**适用于**：生产环境，单实例部署

- Docker 自动管理卷权限
- 无需手动创建目录
- 容器以 UID 1000（claudeuser）运行

```bash
# .env 配置
UID=1000
GID=1000
CLAUDE_AGENT_SESSION_STORAGE=sqlite
```

```bash
# 启动
docker-compose up -d
```

#### 模式 2：SQLite + 绑定挂载（开发）

**适用于**：开发环境，需要直接访问文件

- 直接访问宿主机文件系统
- 需要正确的宿主机目录权限
- 设置 UID/GID 以匹配你的宿主机用户

```bash
# .env 配置
UID=$(id -u)
GID=$(id -g)
CLAUDE_AGENT_SESSION_STORAGE=sqlite
```

```bash
# 复制覆盖配置
cp docker-compose.override.bindmounts.yml docker-compose.override.yml

# 启动（docker-start.sh 自动处理权限）
./docker-start.sh --bind-mounts
```

#### 模式 3：PostgreSQL（企业）

**适用于**：生产环境，多实例部署

- 支持多实例和连接池
- 更适合高并发场景

```bash
# .env 配置
CLAUDE_AGENT_SESSION_STORAGE=postgresql
CLAUDE_AGENT_SESSION_PG_PASSWORD=your_secure_password
```

```bash
# 使用 PostgreSQL profile 启动
docker-compose --profile postgres up -d
```

#### 模式 4：内存（开发/测试）

**适用于**：测试，临时会话

- 不持久化，重启后数据丢失
- 性能最快

```bash
# .env 配置
CLAUDE_AGENT_SESSION_STORAGE=memory
```

### 卷管理

**命名卷**（默认）：
- `claude-users` - 用户工作目录
- `claude-db` - SQLite 数据库
- `postgres_data` - PostgreSQL 数据（使用 PostgreSQL 时）

**绑定挂载**（开发）：
- 通过 .env 中的 `HOST_USER_DATA_DIR` 和 `HOST_DB_DIR` 指定
- 通过 `docker-compose.override.yml` 配置
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

### 常见问题

#### 1. 权限拒绝错误：`EACCES: permission denied, mkdir '/home/claudeuser'`

**症状：**
- 会话创建失败，返回 503 Service Unavailable
- 日志显示：`EACCES: permission denied, mkdir '/home/claudeuser'`
- 健康检查返回错误

**根本原因：**
使用了过期的 Docker 镜像，该镜像没有配置 `claudeuser` 用户。

**解决方案：**
```bash
# 停止容器
docker-compose down

# 从头重新构建镜像（不使用缓存）
docker-compose build --no-cache

# 启动服务
docker-compose up -d

# 验证用户已创建
docker exec claude-agent-http id
# 应该显示：uid=1000(claudeuser) gid=1000 groups=1000

# 验证 home 目录存在
docker exec claude-agent-http ls -la /home/
# 应该显示：drwx------ claudeuser claudeuser /home/claudeuser
```

**预防措施：**
拉取更新后始终重新构建镜像：
```bash
git pull
docker-compose build --no-cache
docker-compose up -d
```

#### 2. 健康检查返回 503

**症状：**
- `curl http://localhost:8000/health` 返回 503
- 容器持续重启
- 日志显示 "Fatal error in message reader"

**可能原因及解决方案：**

**a) 缺少 HOME 环境变量：**
```bash
# 检查 HOME 是否正确设置
docker exec claude-agent-http env | grep HOME
# 应该显示：HOME=/home/claudeuser

# 如果缺失，验证 docker-compose.yml 中有：
environment:
  HOME: /home/claudeuser
```

**b) 未配置 ANTHROPIC_API_KEY：**
```bash
# 检查 API key 是否设置
docker exec claude-agent-http env | grep ANTHROPIC_API_KEY

# 在 .env 文件中配置
echo "ANTHROPIC_API_KEY=your_key_here" >> .env

# 重启
docker-compose restart
```

**c) 容器用户不匹配：**
```bash
# 检查容器用户
docker exec claude-agent-http id

# 应该是：uid=1000(claudeuser) gid=1000
# 如果不同，重新构建镜像（参见问题 #1）
```

#### 3. 端口已被占用

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

#### 4. 绑定挂载权限错误

**症状：**
- "Directory /data/claude-users is NOT writable"
- "Directory /data/db is NOT writable"

**绑定挂载解决方案：**
```bash
# 检查 .env 中的 UID/GID 是否匹配你的用户
id -u  # 获取你的 UID
id -g  # 获取你的 GID

# 更新 .env
echo "UID=$(id -u)" >> .env
echo "GID=$(id -g)" >> .env

# 创建并修复宿主机目录权限
mkdir -p ~/.claude-code-http/{claude-users,db}
chown -R $(id -u):$(id -g) ~/.claude-code-http/

# 或者使用系统级目录
sudo mkdir -p /opt/claude-code-http/{claude-users,db}
sudo chown -R $(id -u):$(id -g) /opt/claude-code-http/

# 重启
docker-compose restart
```

**命名卷解决方案（默认）：**
```bash
# 如果存在，删除绑定挂载覆盖文件
rm -f docker-compose.override.yml

# 确保 UID/GID 为 1000（默认）
echo "UID=1000" >> .env
echo "GID=1000" >> .env

# 重启
docker-compose down
docker-compose up -d
```

#### 5. 数据库连接失败（PostgreSQL）

**症状：**
- "could not connect to server"
- "Connection refused"

**解决方案：**
```bash
# 检查 PostgreSQL 容器是否运行
docker-compose -f docker-compose.yml -f docker-compose.postgres.yml ps

# 检查数据库是否健康
docker-compose -f docker-compose.yml -f docker-compose.postgres.yml exec postgres pg_isready -U postgres

# 查看 PostgreSQL 日志
docker-compose -f docker-compose.yml -f docker-compose.postgres.yml logs postgres

# 验证环境变量
docker exec claude-agent-http env | grep PG_

# 手动连接数据库
docker-compose -f docker-compose.yml -f docker-compose.postgres.yml exec postgres psql -U postgres -d claude_agent

# 查看数据库表
\dt
```

#### 6. 容器持续重启

**诊断：**
```bash
# 检查容器状态
docker-compose ps

# 查看最近的日志
docker-compose logs --tail=50

# 检查容器退出代码
docker inspect claude-agent-http | grep ExitCode

# 常见退出代码：
# 1 - 应用程序错误（检查日志）
# 137 - 被系统杀死（OOM 或手动 kill）
# 139 - 段错误
```

**解决方案：**
```bash
# 清理所有内容并重新开始
docker-compose down
docker volume prune  # 小心：会删除未使用的卷
docker-compose build --no-cache
docker-compose up -d

# 如果是 OOM（内存不足），增加 Docker 内存限制
# Docker Desktop：设置 -> 资源 -> 内存
```

### 调试命令

#### 查看日志

```bash
# 查看所有服务日志
docker-compose logs

# 查看 API 服务日志
docker-compose logs app

# 查看 PostgreSQL 日志（如使用）
docker-compose -f docker-compose.yml -f docker-compose.postgres.yml logs postgres

# 实时跟踪日志
docker-compose logs -f app

# 查看最后 50 行
docker-compose logs --tail=50 app
```

#### 检查容器

```bash
# 检查容器状态
docker-compose ps

# 检查容器配置
docker inspect claude-agent-http

# 检查资源使用
docker stats claude-agent-http

# 检查卷
docker volume ls | grep claude

# 检查卷详情
docker volume inspect claude-agent-http_claude-users
```

#### 容器内调试

```bash
# 在运行的容器中打开 shell
docker exec -it claude-agent-http bash

# 检查用户和权限
id
env | grep HOME
ls -la /home/claudeuser/
ls -la /data/

# 检查进程
ps aux

# 检查网络
netstat -tlnp
curl localhost:8000/health

# 退出 shell
exit
```

### 完全清理并重新构建

如果所有方法都失败，执行完全清理：

```bash
# 1. 停止所有容器
docker-compose down

# 2. 删除容器和卷
docker-compose down -v

# 3. 删除镜像
docker rmi claude-agent-http_app

# 4. 清理构建缓存（可选）
docker builder prune -a

# 5. 从头重新构建
docker-compose build --no-cache

# 6. 启动服务
docker-compose up -d

# 7. 检查日志
docker-compose logs -f
```

### 获取帮助

如果问题仍然存在：

1. **收集信息：**
   ```bash
   # 系统信息
   docker version
   docker-compose version
   uname -a

   # 容器日志
   docker-compose logs --tail=100 > logs.txt

   # 容器状态
   docker-compose ps

   # 卷信息
   docker volume ls | grep claude
   ```

2. **检查文档：**
   - 项目 README：`README_CN.md`
   - 配置指南：`CLAUDE.md`
   - API 示例：`docs/API_EXAMPLES.md`

3. **报告问题：**
   - 使用收集的信息创建 GitHub Issue
   - 包含错误消息和日志
   - 描述重现步骤

## 环境变量完整列表

查看 `.env.example` 文件获取所有可配置的环境变量说明。

### 核心配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ANTHROPIC_API_KEY` | Anthropic API 密钥 | **必填** |
| `ANTHROPIC_AUTH_TOKEN` | API_KEY 的替代方案（用于自定义端点） | - |
| `ANTHROPIC_BASE_URL` | 自定义 API 端点 URL | https://api.anthropic.com |
| `ANTHROPIC_MODEL` | 覆盖默认模型 | SDK 默认 |
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
