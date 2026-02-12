"""
Configuration module for Claude Agent HTTP service.
Supports YAML config file + environment variable overrides.
"""
import os
from pathlib import Path
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class UserConfig(BaseModel):
    """User directory configuration."""
    base_dir: str = "/home"
    auto_create_dir: bool = True


class SessionConfig(BaseModel):
    """Session storage configuration."""
    storage: Literal["memory", "sqlite", "postgresql"] = "memory"
    ttl: int = 3600  # Session TTL in seconds, 0 = no expiration
    sqlite_path: str = "sessions.db"
    # PostgreSQL settings
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_database: str = "claude_agent"
    pg_user: str = "postgresql"
    pg_password: str = "postgresql"


class ApiConfig(BaseModel):
    """API server configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])
    max_sessions: int = 20                  # Maximum total sessions
    max_sessions_per_user: int = 5          # Maximum sessions per user
    max_concurrent_requests: int = 5        # Maximum concurrent processing requests
    memory_limit_mb: int = 7168             # Memory threshold in MB, refuse new sessions above this
    idle_session_timeout: int = 300         # Close idle in-memory clients after N seconds


class DefaultsConfig(BaseModel):
    """Default values for sessions."""
    system_prompt: str = "You are a helpful AI assistant."
    permission_mode: str = "bypassPermissions"
    allowed_tools: List[str] = Field(
        default_factory=lambda: ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "Skill"]
    )
    setting_sources: List[str] = Field(
        default_factory=lambda: ["user", "project"]
    )
    cli_path: Optional[str] = None          # Path to claude CLI binary (None = SDK bundled)
    model: Optional[str] = None
    max_turns: Optional[int] = None
    max_budget_usd: Optional[float] = None


class Config(BaseSettings):
    """Main configuration class."""

    user: UserConfig = Field(default_factory=UserConfig)
    session: SessionConfig = Field(default_factory=SessionConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)
    defaults: DefaultsConfig = Field(default_factory=DefaultsConfig)

    # MCP servers (global default)
    mcp_servers: dict = Field(default_factory=dict)

    # Plugins (global default)
    plugins: List[dict] = Field(default_factory=list)

    class Config:
        env_prefix = "CLAUDE_AGENT_"
        env_nested_delimiter = "__"


def load_config(config_path: str = "config.yaml") -> Config:
    """
    Load configuration from YAML file with environment variable overrides.

    Priority: Environment variables > YAML file > Default values
    """
    config_data = {}

    # Load from YAML if exists
    path = Path(config_path)
    if path.exists():
        try:
            import yaml
            with open(path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f) or {}
        except ImportError:
            pass  # yaml not installed, use defaults

    # Create config with YAML data as base
    config = Config(**config_data)

    # Environment variable overrides
    if os.getenv("CLAUDE_AGENT_USER_BASE_DIR"):
        config.user.base_dir = os.getenv("CLAUDE_AGENT_USER_BASE_DIR")

    if os.getenv("CLAUDE_AGENT_SESSION_STORAGE"):
        config.session.storage = os.getenv("CLAUDE_AGENT_SESSION_STORAGE")

    if os.getenv("CLAUDE_AGENT_SESSION_TTL"):
        config.session.ttl = int(os.getenv("CLAUDE_AGENT_SESSION_TTL"))

    if os.getenv("CLAUDE_AGENT_SESSION_SQLITE_PATH"):
        config.session.sqlite_path = os.getenv("CLAUDE_AGENT_SESSION_SQLITE_PATH")

    # PostgreSQL settings
    if os.getenv("CLAUDE_AGENT_SESSION_PG_HOST"):
        config.session.pg_host = os.getenv("CLAUDE_AGENT_SESSION_PG_HOST")

    if os.getenv("CLAUDE_AGENT_SESSION_PG_PORT"):
        config.session.pg_port = int(os.getenv("CLAUDE_AGENT_SESSION_PG_PORT"))

    if os.getenv("CLAUDE_AGENT_SESSION_PG_DATABASE"):
        config.session.pg_database = os.getenv("CLAUDE_AGENT_SESSION_PG_DATABASE")

    if os.getenv("CLAUDE_AGENT_SESSION_PG_USER"):
        config.session.pg_user = os.getenv("CLAUDE_AGENT_SESSION_PG_USER")

    if os.getenv("CLAUDE_AGENT_SESSION_PG_PASSWORD"):
        config.session.pg_password = os.getenv("CLAUDE_AGENT_SESSION_PG_PASSWORD")

    if os.getenv("CLAUDE_AGENT_API_PORT"):
        config.api.port = int(os.getenv("CLAUDE_AGENT_API_PORT"))

    if os.getenv("CLAUDE_AGENT_MAX_SESSIONS"):
        config.api.max_sessions = int(os.getenv("CLAUDE_AGENT_MAX_SESSIONS"))
    if os.getenv("CLAUDE_AGENT_MAX_SESSIONS_PER_USER"):
        config.api.max_sessions_per_user = int(os.getenv("CLAUDE_AGENT_MAX_SESSIONS_PER_USER"))
    if os.getenv("CLAUDE_AGENT_MAX_CONCURRENT"):
        config.api.max_concurrent_requests = int(os.getenv("CLAUDE_AGENT_MAX_CONCURRENT"))

    if os.getenv("CLAUDE_AGENT_MEMORY_LIMIT_MB"):
        config.api.memory_limit_mb = int(os.getenv("CLAUDE_AGENT_MEMORY_LIMIT_MB"))

    if os.getenv("CLAUDE_AGENT_IDLE_SESSION_TIMEOUT"):
        config.api.idle_session_timeout = int(os.getenv("CLAUDE_AGENT_IDLE_SESSION_TIMEOUT"))

    if os.getenv("CLAUDE_AGENT_CLI_PATH"):
        config.defaults.cli_path = os.getenv("CLAUDE_AGENT_CLI_PATH")

    return config


# Global config instance
_config: Optional[Config] = None


def get_config(config_path: str = "config.yaml") -> Config:
    """Get global config instance (singleton)."""
    global _config
    if _config is None:
        _config = load_config(config_path)
    return _config


def reload_config(config_path: str = "config.yaml") -> Config:
    """Reload configuration."""
    global _config
    _config = load_config(config_path)
    return _config
