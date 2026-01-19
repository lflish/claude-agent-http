#!/bin/bash

# 读取版本号和生成时间戳
if [ -f VERSION ]; then
  VERSION=$(cat VERSION | tr -d '[:space:]')
  TIMESTAMP=$(date +%Y%m%d)
  DEFAULT_TAG="v${VERSION}-${TIMESTAMP}"
else
  DEFAULT_TAG="latest"
fi

# 支持通过参数指定镜像标签
IMAGE_TAG=${1:-$DEFAULT_TAG}
# 支持通过环境变量指定镜像名（方便本地测试）
IMAGE_NAME=${DOCKER_IMAGE_NAME:-"ccr.ccs.tencentyun.com/claude/claude-agent-http"}

# 加载 .env 文件中的环境变量
if [ -f .env ]; then
  echo "正在加载 .env 文件..."
  export $(grep -v '^#' .env | xargs)
else
  echo "警告: .env 文件不存在，使用默认配置"
fi

# 停止并删除旧容器
docker stop claude-agent-http 2>/dev/null
docker rm claude-agent-http 2>/dev/null

# Anthropic API 配置（必填）
export ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-""}

# 用户目录配置
export CLAUDE_AGENT_USER_BASE_DIR=${CLAUDE_AGENT_USER_BASE_DIR:-"/data/claude-users"}
export CLAUDE_AGENT_USER_AUTO_CREATE_DIR=${CLAUDE_AGENT_USER_AUTO_CREATE_DIR:-"true"}

# Session 存储配置
export CLAUDE_AGENT_SESSION_STORAGE=${CLAUDE_AGENT_SESSION_STORAGE:-"memory"}
export CLAUDE_AGENT_SESSION_TTL=${CLAUDE_AGENT_SESSION_TTL:-3600}
export CLAUDE_AGENT_SESSION_SQLITE_PATH=${CLAUDE_AGENT_SESSION_SQLITE_PATH:-"/data/db/sessions.db"}

# API 服务器配置
export CLAUDE_AGENT_API_HOST=${CLAUDE_AGENT_API_HOST:-"127.0.0.1"}
export CLAUDE_AGENT_API_PORT=${CLAUDE_AGENT_API_PORT:-8000}
export API_PORT=${API_PORT:-8000}

# 本地存储目录
LOCAL_DATA_DIR=${LOCAL_DATA_DIR:-"~/.claude-agent-http"}
LOCAL_DATA_DIR="${LOCAL_DATA_DIR/#\~/$HOME}"

# 确保本地存储目录存在
mkdir -p ${LOCAL_DATA_DIR}/claude-users
mkdir -p ${LOCAL_DATA_DIR}/db

echo "=========================================="
echo "启动 Claude Agent HTTP 服务"
echo "=========================================="
echo "  镜像: ${IMAGE_NAME}:${IMAGE_TAG}"
echo "  API 端口: ${API_PORT}"
echo "  存储模式: ${CLAUDE_AGENT_SESSION_STORAGE}"
echo "  本地数据目录: ${LOCAL_DATA_DIR}"
echo "=========================================="
echo ""

# 检查 API Key
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "⚠️  警告: ANTHROPIC_API_KEY 未设置"
  echo "请在 .env 文件中设置或通过环境变量传入"
fi

# 检查镜像是否存在
if ! docker images ${IMAGE_NAME}:${IMAGE_TAG} | grep -q ${IMAGE_TAG}; then
  echo "❌ 错误: 镜像 ${IMAGE_NAME}:${IMAGE_TAG} 不存在"
  echo "请先运行: ./build.sh"
  echo "或拉取公共镜像: docker pull ${IMAGE_NAME}:${IMAGE_TAG}"
  exit 1
fi

docker run -d \
  --name claude-agent-http \
  --network host \
  -e HOME=/home/claudeuser \
  -e ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY} \
  -e CLAUDE_AGENT_USER_BASE_DIR=${CLAUDE_AGENT_USER_BASE_DIR} \
  -e CLAUDE_AGENT_USER_AUTO_CREATE_DIR=${CLAUDE_AGENT_USER_AUTO_CREATE_DIR} \
  -e CLAUDE_AGENT_SESSION_STORAGE=${CLAUDE_AGENT_SESSION_STORAGE} \
  -e CLAUDE_AGENT_SESSION_TTL=${CLAUDE_AGENT_SESSION_TTL} \
  -e CLAUDE_AGENT_SESSION_SQLITE_PATH=${CLAUDE_AGENT_SESSION_SQLITE_PATH} \
  -e CLAUDE_AGENT_API_HOST=${CLAUDE_AGENT_API_HOST} \
  -e CLAUDE_AGENT_API_PORT=${CLAUDE_AGENT_API_PORT} \
  -v ${LOCAL_DATA_DIR}/claude-users:/data/claude-users \
  -v ${LOCAL_DATA_DIR}/db:/data/db \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  --restart unless-stopped \
  ${IMAGE_NAME}:${IMAGE_TAG}

if [ $? -eq 0 ]; then
  echo ""
  echo "✅ 容器启动成功！"
  echo ""
  echo "查看日志: docker logs -f claude-agent-http"
  echo "健康检查: curl http://localhost:${API_PORT}/health"
  echo "停止容器: docker stop claude-agent-http"
else
  echo ""
  echo "❌ 容器启动失败"
  exit 1
fi
