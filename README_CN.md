<div align="center">

# 🤖 Claude Agent HTTP

**生产级 Claude Agent SDK 的 HTTP REST API 封装**

*为 Claude Code 提供多用户会话管理和 RESTful API*

[![许可证: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Release](https://img.shields.io/github/v/release/lflish/claude-agent-http)](https://github.com/lflish/claude-agent-http/releases)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)

[English](README.md) | [简体中文](README_CN.md)

[功能特性](#-功能特性) •
[快速开始](#-快速开始) •
[Docker](#-docker-部署) •
[API 文档](#-api-参考) •
[文档](#-文档)

</div>

---

## ✨ 功能特性

<table>
<tr>
<td width="50%">

### 👥 **多用户支持**
每个用户拥有独立的工作目录，自动路径验证和安全保护

</td>
<td width="50%">

### 🔄 **会话管理**
创建、恢复、关闭会话，支持持久化存储（SQLite/PostgreSQL）

</td>
</tr>
<tr>
<td width="50%">

### ⚡ **流式响应**
基于 SSE 的实时流式输出，提供响应式用户体验

</td>
<td width="50%">

### 🗄️ **灵活存储**
支持内存、SQLite（单实例）或 PostgreSQL（多实例）

</td>
</tr>
<tr>
<td width="50%">

### ⚙️ **高度可配置**
YAML 配置文件 + 环境变量覆盖，轻松部署

</td>
<td width="50%">

### 🐳 **Docker 就绪**
生产就绪的 Docker 配置，自动权限管理

</td>
</tr>
</table>

## 🎯 使用场景

- **🏢 企业部署**: 多用户 Claude Code 部署，集中管理
- **💼 团队协作**: 为开发团队提供共享的 Claude Code 服务
- **🔌 API 集成**: 将 Claude Code 集成到现有系统的 RESTful API
- **📊 使用追踪**: 集中化的会话和使用情况监控
- **🔒 安全隔离**: 用户环境隔离，路径验证保护

## 🚀 快速开始

### 方法 1: Docker（推荐）

最快的启动方式：

```bash
# 1. 克隆仓库
git clone https://github.com/lflish/claude-agent-http.git
cd claude-agent-http

# 2. 设置环境
cp .env.example .env
# 编辑 .env 并设置 ANTHROPIC_API_KEY=your_api_key_here

# 3. 启动服务
docker-compose up -d

# 4. 验证
curl http://localhost:8000/health
```

✅ **就这么简单！** 你的 API 现在运行在 `http://localhost:8000`

📖 详细的 Docker 部署说明，请参阅 [DOCKER_CN.md](DOCKER_CN.md) | [English](DOCKER.md)

### 方法 2: 手动安装

适用于开发或自定义设置：

```bash
# 安装依赖
pip install -r requirements.txt

# 设置 API Key
export ANTHROPIC_API_KEY="sk-ant-xxxxx"

# 运行服务器
python -m claude_agent_http.main

# 或使用 uvicorn（自动重载）
uvicorn claude_agent_http.main:app --reload --host 0.0.0.0 --port 8000
```

## 🐳 Docker 部署

我们提供三种部署模式：

| 模式 | 使用场景 | 命令 |
|------|----------|---------|
| **SQLite + 命名卷** | 生产环境（默认） | `docker-compose up -d` |
| **SQLite + 绑定挂载** | 开发环境 | `./docker-start.sh --bind-mounts` |
| **PostgreSQL** | 多实例部署 | `./docker-start.sh --postgres` |

### 快速部署

```bash
# SQLite 模式（默认）
docker-compose up -d

# PostgreSQL 模式
docker-compose -f docker-compose.yml -f docker-compose.postgres.yml up -d

# 检查健康状态
curl http://localhost:8000/health
```

### Docker 特性

- ✅ 自动卷权限管理
- ✅ 非 root 用户执行保证安全
- ✅ 内置健康检查
- ✅ 支持命名卷或绑定挂载
- ✅ PostgreSQL 支持多实例部署
- ✅ 容器内存限制（OOM 防护）

**故障排查**: 遇到问题？查看我们的[全面故障排查指南](DOCKER_CN.md#故障排查)，涵盖 6 个常见问题和解决方案。

## 📚 API 参考

### REST 端点

| 端点 | 方法 | 描述 |
|----------|--------|-------------|
| `/health` | GET | 服务健康检查 |
| `/api/v1/sessions` | POST | 创建新会话 |
| `/api/v1/sessions` | GET | 列出会话（可选 `?user_id=`） |
| `/api/v1/sessions/{id}` | GET | 获取会话详情 |
| `/api/v1/sessions/{id}` | DELETE | 关闭会话 |
| `/api/v1/sessions/{id}/resume` | POST | 恢复会话 |
| `/api/v1/chat` | POST | 发送消息（同步） |
| `/api/v1/chat/stream` | POST | 发送消息（流式 SSE） |

### 快速示例

```bash
# 创建会话
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_id": "zhangsan", "subdir": "my-project"}'

# 发送消息
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "your-session-id",
    "message": "写一个 Python hello world 程序"
  }'
```

### API 测试

- 📮 **Postman 集合**: 导入 [`postman_collection.json`](postman_collection.json) 测试所有 API
- 📖 **详细示例**: 查看 [docs/API_EXAMPLES.md](docs/API_EXAMPLES.md) 获取完整的 curl 示例
- 🌐 **交互式文档**: 启动服务器后访问 `http://localhost:8000/docs`

## ⚙️ 配置

### 环境变量

```bash
# 必需：Anthropic API 配置
ANTHROPIC_API_KEY=sk-ant-xxxxx         # 你的 API 密钥（必需）

# 可选：自定义端点或代理
ANTHROPIC_BASE_URL=https://api.anthropic.com
ANTHROPIC_AUTH_TOKEN=                   # API_KEY 的替代方案
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# 可选：服务配置
CLAUDE_AGENT_SESSION_STORAGE=sqlite     # memory | sqlite | postgresql
CLAUDE_AGENT_SESSION_TTL=3600           # 会话超时（秒）
CLAUDE_AGENT_USER_BASE_DIR=/data/users  # 用户文件目录
CLAUDE_AGENT_API_PORT=8000              # API 服务器端口

# 可选：内存保护
CLAUDE_AGENT_MEMORY_LIMIT_MB=7168      # 内存阈值（MB），超过后拒绝创建新会话
CLAUDE_AGENT_IDLE_SESSION_TIMEOUT=600  # 空闲会话驱逐时间（秒）
```

### 配置文件

编辑 `config.yaml` 进行高级设置：

```yaml
user:
  base_dir: "/home"          # 所有用户的基础目录
  auto_create_dir: true      # 自动创建用户目录

session:
  storage: "sqlite"          # memory | sqlite | postgresql
  ttl: 3600                  # 会话过期时间（秒）

defaults:
  system_prompt: "You are a helpful AI assistant."
  permission_mode: "bypassPermissions"
  allowed_tools: [Bash, Read, Write, Edit, Glob, Grep, Skill]
  setting_sources: [user, project]  # 加载 Skills 必需
  model: null                # null = SDK 默认
  max_turns: 50              # 每会话最大对话轮数
  max_budget_usd: null       # null = 无限制

api:
  max_sessions: 20           # 最大会话总数
  max_sessions_per_user: 5   # 每用户最大会话数
  max_concurrent_requests: 5 # 最大并发请求数
  memory_limit_mb: 7168      # 应用层内存阈值（MB），超过后拒绝新会话
  idle_session_timeout: 600  # 空闲会话自动驱逐时间（秒）

mcp_servers: {}              # 全局 MCP 服务器
plugins: []                  # 全局插件
```

**优先级**: 环境变量 > config.yaml > 默认值

## 🏗️ 架构

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

### 项目结构

```
claude_agent_http/
├── main.py              # FastAPI 入口
├── config.py            # 配置管理
├── models.py            # 数据模型
├── agent.py             # 核心 ClaudeAgent 类
├── security.py          # 路径验证和安全
├── storage/             # 会话存储后端
│   ├── base.py          # 抽象接口
│   ├── memory.py        # 内存存储
│   ├── sqlite.py        # SQLite 存储
│   └── postgresql.py    # PostgreSQL 存储
└── routers/             # API 路由处理
    ├── sessions.py      # 会话管理
    └── chat.py          # 聊天端点
```

## 🛡️ 内存保护

每个会话会启动一个独立的 Claude CLI 子进程（每个约 300MB）。如果不加限制，多个会话可能耗尽主机内存。我们提供多层 OOM 防护：

| 层级 | 机制 | 说明 |
|------|------|------|
| **Docker** | `mem_limit: 8g` | 容器内存硬限制，防止宿主机 OOM |
| **应用层** | `memory_limit_mb: 7168` | 软限制，超过阈值后拒绝创建新会话 |
| **空闲驱逐** | `idle_session_timeout: 600` | 10 分钟无活动自动释放内存中的客户端 |
| **压力回收** | LRU 驱逐 | 内存压力时按最近最少使用策略驱逐会话 |
| **OOM 优先级** | `oom_score_adj: -100` | 降低被 OOM Killer 选中的概率 |

> **重要提示**: Docker 的 `deploy.resources.limits` 仅在 Swarm 模式下生效。使用 `docker-compose up` 时必须用 `mem_limit`。

## 🔒 安全特性

- **路径验证**: 防止路径遍历攻击（阻止 `..`）
- **用户隔离**: 每个用户拥有独立的工作目录
- **非 root 执行**: Docker 容器以非 root 用户（claudeuser）运行
- **输入验证**: 所有 API 输入通过 Pydantic 验证
- **会话安全**: 唯一会话 ID，可配置 TTL

## 📖 文档

- 📗 **[DOCKER_CN.md](DOCKER_CN.md)**: Docker 部署指南（中文）
- 📘 **[DOCKER.md](DOCKER.md)**: Comprehensive Docker deployment guide (English)
- 📙 **[API_EXAMPLES.md](docs/API_EXAMPLES.md)**: 完整的 API 示例
- 📕 **[CLAUDE.md](CLAUDE.md)**: 项目架构和设计决策
- 📝 **[CHANGELOG.md](CHANGELOG.md)**: 版本历史和变更

## 🤝 贡献

欢迎贡献！请随时提交 Pull Request。

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- 基于 [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk) 构建
- 由 [Anthropic Claude API](https://www.anthropic.com/) 驱动
- Web 框架: [FastAPI](https://fastapi.tiangolo.com/)

## 📞 支持

- 🐛 **问题反馈**: [GitHub Issues](https://github.com/lflish/claude-agent-http/issues)
- 💬 **讨论**: [GitHub Discussions](https://github.com/lflish/claude-agent-http/discussions)
- 📧 **Email**: 创建 issue 获取支持

---

<div align="center">

**Made with ❤️ by the Claude Agent HTTP team**

⭐ 在 GitHub 上为我们点个星 — 这对我们很重要！

[报告 Bug](https://github.com/lflish/claude-agent-http/issues) •
[请求功能](https://github.com/lflish/claude-agent-http/issues) •
[查看版本](https://github.com/lflish/claude-agent-http/releases)

</div>
