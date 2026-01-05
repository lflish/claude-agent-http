"""
Claude Agent Library
Python 库函数封装，提供便捷的 Claude Agent 功能接口
"""

__version__ = "0.1.0"

# 导出核心类
from .client import ClaudeAgentLibrary

# 导出配置和模型
from .config import LibraryConfig
from .models import SessionInfo, Message, StreamChunk

# 导出会话管理器
from .session import SessionManager

# 导出异常类
from .exceptions import (
    ClaudeAgentLibraryError,
    SessionNotFoundError,
    SessionExpiredError,
    ClientCreationError,
    MessageSendError,
    SessionStorageError,
    ConfigurationError,
    SessionBusyError
)

# 导出工具函数
from .utils import (
    load_config_from_file,
    save_config_to_file,
    load_session_id_from_file,
    save_session_id_to_file
)

__all__ = [
    # 核心类
    'ClaudeAgentLibrary',

    # 配置和模型
    'LibraryConfig',
    'SessionInfo',
    'Message',
    'StreamChunk',

    # 会话管理
    'SessionManager',

    # 异常
    'ClaudeAgentLibraryError',
    'SessionNotFoundError',
    'SessionExpiredError',
    'ClientCreationError',
    'MessageSendError',
    'SessionStorageError',
    'ConfigurationError',
    'SessionBusyError',

    # 工具函数
    'load_config_from_file',
    'save_config_to_file',
    'load_session_id_from_file',
    'save_session_id_to_file',
]
