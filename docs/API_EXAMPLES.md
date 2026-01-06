# API 使用示例

本文档提供 Claude Agent HTTP API 的完整 curl 测试示例。

## 前置条件

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量（必需）
export ANTHROPIC_API_KEY="your-api-key"

# 3. 启动服务
python -m claude_agent_http.main
# 或
uvicorn claude_agent_http.main:app --host 0.0.0.0 --port 8000
```

## 健康检查

```bash
# 检查服务状态
curl -s http://localhost:8000/health | jq

# 响应示例
{
  "status": "healthy",
  "version": "1.0.0",
  "active_sessions": 2,
  "storage_type": "sqlite",
  "uptime_seconds": 3600.5
}
```

## Session 管理

### 创建 Session

```bash
# 最简方式：只需 user_id
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "zhangsan"
  }'

# 指定子目录
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "zhangsan",
    "subdir": "my-project"
  }'

# 带业务元数据
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "zhangsan",
    "subdir": "my-project",
    "metadata": {
      "env": "production",
      "app_name": "myapp",
      "version": "1.0.0"
    }
  }'

# 响应示例
{
  "session_id": "a61c5358-c9ef-4eac-a85e-ad8f68b93b30",
  "user_id": "zhangsan",
  "cwd": "/home/zhangsan/my-project",
  "created_at": "2026-01-06T11:43:12.893524",
  "last_active_at": "2026-01-06T11:43:12.893533",
  "message_count": 0,
  "status": "active",
  "metadata": {"env": "production", "app_name": "myapp", "version": "1.0.0"}
}
```

### 列出 Sessions

```bash
# 列出所有 sessions
curl -s http://localhost:8000/api/v1/sessions | jq

# 响应示例
["a61c5358-c9ef-4eac-a85e-ad8f68b93b30", "b72d6a4f-..."]

# 按用户过滤
curl -s "http://localhost:8000/api/v1/sessions?user_id=zhangsan" | jq
```

### 获取 Session 详情

```bash
# 替换 {session_id} 为实际值
curl -s http://localhost:8000/api/v1/sessions/{session_id} | jq

# 响应示例
{
  "session_id": "a61c5358-c9ef-4eac-a85e-ad8f68b93b30",
  "user_id": "zhangsan",
  "cwd": "/home/zhangsan/my-project",
  "created_at": "2026-01-06T11:43:12.893524",
  "last_active_at": "2026-01-06T11:45:30.123456",
  "message_count": 5,
  "status": "active",
  "metadata": {}
}
```

### 恢复 Session

```bash
# 从存储中恢复已有的 session
curl -X POST http://localhost:8000/api/v1/sessions/{session_id}/resume | jq
```

### 删除 Session

```bash
# 关闭并删除 session
curl -X DELETE http://localhost:8000/api/v1/sessions/{session_id}

# 成功返回 204 No Content
```

## 对话 (Chat)

### 同步模式

等待完整响应后返回：

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "a61c5358-c9ef-4eac-a85e-ad8f68b93b30",
    "message": "你好，请介绍一下你自己"
  }'

# 响应示例
{
  "session_id": "a61c5358-c9ef-4eac-a85e-ad8f68b93b30",
  "text": "你好！我是 Claude，一个由 Anthropic 创建的 AI 助手...",
  "tool_calls": [],
  "timestamp": "2026-01-06T11:45:30.123456"
}
```

### 流式模式 (SSE)

实时返回响应片段：

```bash
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "session_id": "a61c5358-c9ef-4eac-a85e-ad8f68b93b30",
    "message": "写一个 Python hello world 程序"
  }'

# 响应示例 (SSE 格式)
data: {"type": "text_delta", "text": "好的"}
data: {"type": "text_delta", "text": "，我来"}
data: {"type": "text_delta", "text": "帮你写"}
data: {"type": "tool_use", "tool_name": "Write", "tool_input": {"file_path": "/home/zhangsan/hello.py", "content": "print('Hello, World!')"}}
data: {"type": "text_delta", "text": "我已经创建了..."}
data: {"type": "done"}
```

## 完整使用流程示例

```bash
#!/bin/bash
# 完整的 API 使用流程示例

BASE_URL="http://localhost:8000"

echo "=== 1. 健康检查 ==="
curl -s $BASE_URL/health | jq

echo -e "\n=== 2. 创建 Session ==="
RESPONSE=$(curl -s -X POST $BASE_URL/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_id": "demo_user", "subdir": "demo-project"}')
echo $RESPONSE | jq

# 提取 session_id
SESSION_ID=$(echo $RESPONSE | jq -r '.session_id')
echo "Session ID: $SESSION_ID"

echo -e "\n=== 3. 发送消息 ==="
curl -s -X POST $BASE_URL/api/v1/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"message\": \"请列出当前目录的文件\"
  }" | jq

echo -e "\n=== 4. 继续对话 ==="
curl -s -X POST $BASE_URL/api/v1/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"message\": \"创建一个 README.md 文件\"
  }" | jq

echo -e "\n=== 5. 查看 Session 状态 ==="
curl -s $BASE_URL/api/v1/sessions/$SESSION_ID | jq

echo -e "\n=== 6. 删除 Session ==="
curl -s -X DELETE $BASE_URL/api/v1/sessions/$SESSION_ID
echo "Session deleted"
```

## 错误响应

### Session 不存在

```bash
curl -s http://localhost:8000/api/v1/sessions/non-existent-id | jq

# 响应
{
  "detail": "Session not found"
}
```

### 参数验证错误

```bash
curl -s -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_id": "../invalid"}' | jq

# 响应
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "user_id"],
      "msg": "User ID can only contain alphanumeric characters, underscore, and hyphen"
    }
  ]
}
```

### Session 繁忙

```bash
# 当同一 session 正在处理消息时
{
  "detail": "Session a61c5358-... is busy"
}
```

## 使用 jq 处理响应

```bash
# 只获取 session_id
curl -s -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test"}' | jq -r '.session_id'

# 获取响应文本
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "xxx", "message": "hello"}' | jq -r '.text'

# 格式化输出
curl -s http://localhost:8000/api/v1/sessions | jq '.[]'
```

## Python 客户端示例

```python
import requests

BASE_URL = "http://localhost:8000"

# 创建 session
resp = requests.post(f"{BASE_URL}/api/v1/sessions", json={
    "user_id": "python_user",
    "subdir": "my-project"
})
session_id = resp.json()["session_id"]
print(f"Created session: {session_id}")

# 发送消息
resp = requests.post(f"{BASE_URL}/api/v1/chat", json={
    "session_id": session_id,
    "message": "你好"
})
print(f"Response: {resp.json()['text']}")

# 流式响应
resp = requests.post(
    f"{BASE_URL}/api/v1/chat/stream",
    json={"session_id": session_id, "message": "写个程序"},
    stream=True
)
for line in resp.iter_lines():
    if line:
        print(line.decode())

# 删除 session
requests.delete(f"{BASE_URL}/api/v1/sessions/{session_id}")
```

## 环境变量配置

```bash
# 覆盖配置文件中的设置
export CLAUDE_AGENT_USER_BASE_DIR="/data/users"
export CLAUDE_AGENT_SESSION_STORAGE="postgresql"
export CLAUDE_AGENT_SESSION_TTL="7200"
export CLAUDE_AGENT_API_PORT="9000"
```
