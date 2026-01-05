"""
HTTP 日志工具
记录请求和响应信息，便于问题排查
"""
import time
import uuid
import logging
import json

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("claude_agent_api")


def log_request(endpoint: str, session_id: str = None, message: str = None, **kwargs):
    """记录请求信息"""
    parts = [f">>> {endpoint}"]

    if session_id:
        parts.append(f"session={session_id[:8]}...")

    if message:
        # 截断长消息
        msg = message[:100] + "..." if len(message) > 100 else message
        parts.append(f"msg={msg}")

    for key, value in kwargs.items():
        if value is not None:
            parts.append(f"{key}={value}")

    logger.info(" | ".join(parts))


def log_response(endpoint: str, session_id: str = None, status: str = "OK",
                 time_ms: float = None, text_len: int = None, message: str = None, **kwargs):
    """记录响应信息"""
    parts = [f"<<< {endpoint}"]

    if session_id:
        parts.append(f"session={session_id[:8]}...")

    parts.append(f"status={status}")

    if time_ms is not None:
        parts.append(f"time={time_ms:.0f}ms")

    if text_len is not None:
        parts.append(f"text_len={text_len}")

    if message:
        # 截断长消息，保留前200个字符
        msg = message[:200] + "..." if len(message) > 200 else message
        # 替换换行符为空格，保持日志单行
        msg = msg.replace('\n', ' ').replace('\r', '')
        parts.append(f"msg={msg}")

    for key, value in kwargs.items():
        if value is not None:
            parts.append(f"{key}={value}")

    if status == "OK":
        logger.info(" | ".join(parts))
    else:
        logger.warning(" | ".join(parts))
