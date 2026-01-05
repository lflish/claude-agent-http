"""
依赖注入模块
提供全局库实例和配置
"""
from fastapi import Header, HTTPException, status
from typing import Optional
from claude_agent_lib import ClaudeAgentLibrary

# 全局库实例（在应用启动时初始化）
_library_instance: Optional[ClaudeAgentLibrary] = None


def set_library_instance(library: ClaudeAgentLibrary):
    """设置全局库实例"""
    global _library_instance
    _library_instance = library


def get_library() -> ClaudeAgentLibrary:
    """
    获取库实例（依赖注入）

    Raises:
        HTTPException: 如果库未初始化
    """
    if _library_instance is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized"
        )
    return _library_instance


async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """
    验证 API Key（可选的简单认证）

    Args:
        x_api_key: HTTP Header 中的 API Key

    Returns:
        str: 验证通过的 API Key

    Raises:
        HTTPException: API Key 无效
    """
    # 简单实现：环境变量中配置 API_KEY
    # 生产环境应使用更复杂的认证机制（JWT、OAuth 等）
    import os

    required_key = os.getenv("API_KEY")

    # 如果未配置 API_KEY，则不需要认证
    if not required_key:
        return "public"

    if not x_api_key or x_api_key != required_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return x_api_key
