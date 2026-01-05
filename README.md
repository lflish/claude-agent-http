# Claude Agent

基于 Claude Agent SDK 的 Python 封装，提供 Library 和 REST API 两种使用方式。

## 安装

```bash
pip install -r requirements.txt
```

## 配置

编辑 `config.yaml`：

```yaml
# 通用配置
system_prompt: "你是一个有帮助的AI助手"
permission_mode: "bypassPermissions"
allowed_tools: ["Bash", "Read", "Write", "Edit"]

# 会话存储
session:
  storage: "memory"  # memory / file / redis / postgres
  ttl: 3600

# API 服务
api:
  host: "0.0.0.0"
  port: 8000

# MCP 服务器
mcp_servers: {}
```

敏感信息通过环境变量设置：

```bash
export POSTGRES_URL="postgresql://user:pass@host:5432/db"
export REDIS_URL="redis://localhost:6379"
```

## 使用方式

### 1. Library

```python
from claude_agent_lib import ClaudeAgentLibrary, LibraryConfig

# 从 YAML 加载配置
config = LibraryConfig.from_yaml()

async with ClaudeAgentLibrary(config) as lib:
    session_id = await lib.create_session()
    response = await lib.send_message(session_id, "你好")
    print(response.text)
```

### 2. REST API

```bash
# 启动
python -m claude_agent_api.main

# 创建会话
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"init_message": "Hello"}'

# 发送消息
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "xxx", "message": "你好"}'
```

## 项目结构

```
├── config.yaml           # 统一配置
├── config_loader.py      # 配置加载器
├── claude_agent_lib/     # Library 模块
└── claude_agent_api/     # REST API 模块
```
