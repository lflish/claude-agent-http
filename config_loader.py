"""
统一配置加载器
支持 YAML 配置文件 + 环境变量覆盖
"""
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

try:
    import yaml
except ImportError:
    yaml = None


@dataclass
class SessionConfig:
    """会话存储配置"""
    storage: str = "memory"
    ttl: int = 3600
    file_dir: str = ".sessions"
    redis_prefix: str = "claude_agent:"
    postgres_table: str = "claude_agent_sessions"


@dataclass
class ApiConfig:
    """API 服务配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    log_level: str = "INFO"


@dataclass
class Config:
    """统一配置"""
    system_prompt: str = "你是一个有帮助的AI助手"
    permission_mode: str = "bypassPermissions"
    allowed_tools: List[str] = field(default_factory=lambda: ["Bash", "Read", "Write", "Edit"])
    mcp_servers: Dict[str, Any] = field(default_factory=dict)
    session: SessionConfig = field(default_factory=SessionConfig)
    api: ApiConfig = field(default_factory=ApiConfig)

    # 环境变量加载的敏感配置
    postgres_url: Optional[str] = None
    redis_url: Optional[str] = None


def load_config(config_path: str = "config.yaml") -> Config:
    """
    加载配置，优先级: 环境变量 > YAML 文件 > 默认值
    """
    config = Config()

    # 1. 从 YAML 加载
    path = Path(config_path)
    if path.exists() and yaml:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}

        # 基础配置
        config.system_prompt = data.get('system_prompt', config.system_prompt)
        config.permission_mode = data.get('permission_mode', config.permission_mode)
        config.allowed_tools = data.get('allowed_tools', config.allowed_tools)
        config.mcp_servers = data.get('mcp_servers', config.mcp_servers) or {}

        # 会话配置
        if 'session' in data:
            s = data['session']
            config.session = SessionConfig(
                storage=s.get('storage', 'memory'),
                ttl=s.get('ttl', 3600),
                file_dir=s.get('file_dir', '.sessions'),
                redis_prefix=s.get('redis_prefix', 'claude_agent:'),
                postgres_table=s.get('postgres_table', 'claude_agent_sessions')
            )

        # API 配置
        if 'api' in data:
            a = data['api']
            config.api = ApiConfig(
                host=a.get('host', '0.0.0.0'),
                port=a.get('port', 8000),
                cors_origins=a.get('cors_origins', ['*']),
                log_level=a.get('log_level', 'INFO')
            )

    # 2. 环境变量覆盖
    config.system_prompt = os.getenv('SYSTEM_PROMPT', config.system_prompt)
    config.session.storage = os.getenv('SESSION_STORAGE', config.session.storage)
    config.session.ttl = int(os.getenv('SESSION_TTL', str(config.session.ttl)))
    config.api.port = int(os.getenv('API_PORT', str(config.api.port)))
    config.api.log_level = os.getenv('LOG_LEVEL', config.api.log_level)

    # 敏感配置只从环境变量加载
    config.postgres_url = os.getenv('POSTGRES_URL')
    config.redis_url = os.getenv('REDIS_URL')

    return config


# 全局配置实例
_config: Optional[Config] = None


def get_config(config_path: str = "config.yaml") -> Config:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = load_config(config_path)
    return _config


def reload_config(config_path: str = "config.yaml") -> Config:
    """重新加载配置"""
    global _config
    _config = load_config(config_path)
    return _config
