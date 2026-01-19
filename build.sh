#!/bin/bash

# 读取版本号
if [ -f VERSION ]; then
  VERSION=$(cat VERSION | tr -d '[:space:]')
else
  echo "错误: VERSION 文件不存在"
  exit 1
fi

# 生成时间戳 (格式: YYYYMMDD)
TIMESTAMP=$(date +%Y%m%d)

# 镜像名称（腾讯云 CCR）
IMAGE_NAME="ccr.ccs.tencentyun.com/claude/claude-agent-http"

# 构建标签（只保留带时间戳的版本）
VERSION_TIME_TAG="v${VERSION}-${TIMESTAMP}"

echo "=========================================="
echo "构建 Claude Agent HTTP Docker 镜像"
echo "=========================================="
echo "版本: ${VERSION}"
echo "时间戳: ${TIMESTAMP}"
echo ""
echo "将创建以下标签:"
echo "  - ${IMAGE_NAME}:${VERSION_TIME_TAG}"
echo "=========================================="
echo ""

# 构建镜像
docker build \
  -t ${IMAGE_NAME}:${VERSION_TIME_TAG} \
  .

if [ $? -eq 0 ]; then
  echo ""
  echo "=========================================="
  echo "✅ 构建成功！"
  echo "=========================================="
  echo "镜像标签:"
  echo "  - ${IMAGE_NAME}:${VERSION_TIME_TAG}"
  echo ""
  echo "查看镜像: docker images ${IMAGE_NAME}"
  echo "推送镜像: docker push ${IMAGE_NAME}:${VERSION_TIME_TAG}"
  echo "运行容器: ./run.sh"
else
  echo ""
  echo "❌ 构建失败"
  exit 1
fi
