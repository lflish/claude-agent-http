"""
配置模型
定义库函数的配置选项
"""
from typing import Optional, Dict, List, Literal, Any
from pydantic import BaseModel, Field


class LibraryConfig(BaseModel):
    """库函数配置"""

    # 核心配置
    system_prompt: str = "你是一个有帮助的助手"
    mcp_servers: Dict[str, Any] = Field(default_factory=dict)
    permission_mode: str = "bypassPermissions"
    allowed_tools: List[str] = Field(
        default_factory=lambda: ["Bash", "Read", "Write", "Edit"]
    )

    # 会话配置
    session_storage: Literal['memory', 'redis', 'file', 'postgres'] = 'memory'
    session_ttl: int = 3600  # 会话过期时间（秒），0 表示不过期

    # 初始化配置
    init_message: str = "Hello"  # 创建新会话时的初始化消息

    # Redis 配置（当 session_storage='redis' 时需要）
    redis_url: Optional[str] = None
    redis_key_prefix: str = "claude_agent:"

    # 文件存储配置（当 session_storage='file' 时需要）
    file_storage_dir: str = ".sessions"

    # PostgreSQL 配置（当 session_storage='postgres' 时需要）
    postgres_url: Optional[str] = None
    postgres_table_name: str = "claude_agent_sessions"

    # 其他配置
    cwd: Optional[str] = None
    setting_sources: List[str] = Field(default_factory=lambda: ["project"])

    class Config:
        extra = "allow"

    @classmethod
    def from_yaml(cls, config_path: str = "config.yaml") -> "LibraryConfig":
        """从 YAML 配置文件加载"""
        import sys
        sys.path.insert(0, '.')
        from config_loader import get_config

        cfg = get_config(config_path)
        return cls(
            system_prompt=cfg.system_prompt,
            permission_mode=cfg.permission_mode,
            allowed_tools=cfg.allowed_tools,
            mcp_servers=cfg.mcp_servers,
            session_storage=cfg.session.storage,
            session_ttl=cfg.session.ttl,
            file_storage_dir=cfg.session.file_dir,
            redis_url=cfg.redis_url,
            redis_key_prefix=cfg.session.redis_prefix,
            postgres_url=cfg.postgres_url,
            postgres_table_name=cfg.session.postgres_table
        )
