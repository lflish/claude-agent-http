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
    """Request to create a new session."""
    user_id: str = Field(..., min_length=1, max_length=64)
    subdir: Optional[str] = Field(None, max_length=200)

    # SDK configuration (optional, use defaults if not provided)
    system_prompt: Optional[str] = Field(None, max_length=50000)
    mcp_servers: Optional[Dict[str, Any]] = None
    plugins: Optional[List[Dict]] = None
    model: Optional[str] = None
    permission_mode: Optional[str] = None
    allowed_tools: Optional[List[str]] = None
    disallowed_tools: Optional[List[str]] = None
    add_dirs: Optional[List[str]] = None
    max_turns: Optional[int] = Field(None, ge=1, le=1000)
    max_budget_usd: Optional[float] = Field(None, ge=0, le=100)

    # Init message to establish session
    init_message: str = Field(default="Hello", max_length=1000)

    # Custom metadata
    metadata: Optional[Dict[str, Any]] = None

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
            # Prevent path traversal
            if '..' in v:
                raise ValueError("Path traversal (..) not allowed in subdir")
            if v.startswith('/'):
                raise ValueError("Absolute path not allowed in subdir")
            return v.strip('/')
        return v

    @field_validator('add_dirs')
    @classmethod
    def validate_add_dirs(cls, v):
        if v:
            for d in v:
                if '..' in d:
                    raise ValueError("Path traversal (..) not allowed in add_dirs")
                if d.startswith('/'):
                    raise ValueError("Absolute path not allowed in add_dirs")
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
