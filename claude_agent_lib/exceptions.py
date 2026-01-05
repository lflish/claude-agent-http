"""
自定义异常类
定义库函数使用的所有异常
"""


class ClaudeAgentLibraryError(Exception):
    """库函数基础异常类"""
    pass


class SessionNotFoundError(ClaudeAgentLibraryError):
    """会话不存在异常"""
    pass


class SessionExpiredError(ClaudeAgentLibraryError):
    """会话已过期异常"""
    pass


class ClientCreationError(ClaudeAgentLibraryError):
    """Client 创建失败异常"""
    pass


class MessageSendError(ClaudeAgentLibraryError):
    """消息发送失败异常"""
    pass


class SessionStorageError(ClaudeAgentLibraryError):
    """会话存储异常"""
    pass


class ConfigurationError(ClaudeAgentLibraryError):
    """配置错误异常"""
    pass


class SessionBusyError(ClaudeAgentLibraryError):
    """会话正忙异常（上一个请求未完成）"""
    pass
