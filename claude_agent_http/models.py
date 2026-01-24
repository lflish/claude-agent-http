"""
Data models for Claude Agent HTTP service.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field, field_validator
import re


# ============ Session Models ============

class SessionInfo(BaseModel):
    """Session information stored in database."""
    session_id: str
    user_id: str
    subdir: Optional[str] = None
    cwd: str  # Computed full path

    # SDK configuration
    system_prompt: Optional[str] = None
    mcp_servers: Dict[str, Any] = Field(default_factory=dict)
    plugins: List[Dict] = Field(default_factory=list)
    setting_sources: List[str] = Field(default_factory=lambda: ["user", "project"])
    model: Optional[str] = None
    permission_mode: str = "bypassPermissions"
    allowed_tools: List[str] = Field(default_factory=list)
    disallowed_tools: List[str] = Field(default_factory=list)
    add_dirs: List[str] = Field(default_factory=list)  # Relative paths
    max_turns: Optional[int] = None
    max_budget_usd: Optional[float] = None

    # Status
    created_at: datetime = Field(default_factory=datetime.now)
    last_active_at: datetime = Field(default_factory=datetime.now)
    message_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============ Request Models ============

class CreateSessionRequest(BaseModel):
    """Request to create a new session.

    Only user_id is required. All other configurations are read from config.yaml.
    """
    user_id: str = Field(..., min_length=1, max_length=64, description="User identifier")
    subdir: Optional[str] = Field(None, max_length=200, description="Subdirectory under user home")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Custom metadata for business use")

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("user_id must contain only alphanumeric, underscore, or hyphen")
        return v

    @field_validator('subdir')
    @classmethod
    def validate_subdir(cls, v):
        if v:
            if '..' in v:
                raise ValueError("Path traversal (..) not allowed in subdir")
            if v.startswith('/'):
                raise ValueError("Absolute path not allowed in subdir")
            return v.strip('/')
        return v


class ChatRequest(BaseModel):
    """Request to send a chat message."""
    session_id: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=100000)
    timeout: Optional[int] = Field(default=120, ge=1, le=600)

    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Invalid session_id format")
        return v

    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v


# ============ Response Models ============

class SessionResponse(BaseModel):
    """Response for session operations."""
    session_id: str
    user_id: str
    cwd: str
    created_at: datetime
    last_active_at: Optional[datetime] = None
    message_count: int = 0
    status: Literal["active", "closed"] = "active"
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ChatResponse(BaseModel):
    """Response for chat messages."""
    session_id: str
    text: str
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class StreamChunk(BaseModel):
    """Streaming response chunk."""
    type: Literal["text_delta", "tool_use", "done", "error"]
    text: Optional[str] = None
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    active_sessions: int
    storage_type: str
    uptime_seconds: Optional[float] = None


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None
    session_id: Optional[str] = None
