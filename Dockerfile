# Dockerfile for Claude Agent API
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY claude_agent_lib/ ./claude_agent_lib/
COPY claude_agent_api/ ./claude_agent_api/

# 创建会话存储目录
RUN mkdir -p .sessions

# 暴露端口
EXPOSE 8000

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV SESSION_STORAGE=memory
ENV SESSION_TTL=3600
ENV SYSTEM_PROMPT="你是一个有帮助的助手"

# 启动命令
CMD ["uvicorn", "claude_agent_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
