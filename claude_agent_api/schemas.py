"""
API 请求和响应数据模型
使用 Pydantic 定义
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
import re


# ============ Session 相关模型 ============

class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    system_prompt: Optional[str] = Field(None, max_length=10000, description="系统提示词，最大10000字符")
    mcp_servers: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = Field(None, description="会话元数据")
    init_message: Optional[str] = Field("Hello", max_length=1000, description="初始化消息")

    @field_validator('metadata')
    @classmethod
    def validate_metadata_size(cls, v):
        """验证 metadata 大小不超过 100KB"""
        if v is not None:
            import json
            size = len(json.dumps(v).encode('utf-8'))
            if size > 102400:  # 100KB
                raise ValueError(f"metadata too large: {size} bytes (max 100KB)")
        return v


class ResumeSessionRequest(BaseModel):
    """复用会话请求"""
    session_id: str = Field(..., min_length=1, max_length=200, description="会话ID")

    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        """验证 session_id 格式（通常是 UUID 或类似格式）"""
        # 允许 UUID、字母数字和短横线
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Invalid session_id format")
        return v


class SessionResponse(BaseModel):
    """会话响应"""
    session_id: str
    created_at: datetime
    last_active_at: Optional[datetime] = None
    message_count: int = 0
    resumed: bool = False
    status: Literal["active", "closed"] = "active"
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============ Chat 相关模型 ============

class ChatRequest(BaseModel):
    """聊天请求"""
    session_id: str = Field(..., min_length=1, max_length=200, description="会话ID")
    message: str = Field(..., min_length=1, max_length=50000, description="用户消息，最大50000字符")
    timeout: Optional[int] = Field(default=60, ge=1, le=300, description="超时时间（秒）")

    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        """验证 session_id 格式"""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Invalid session_id format")
        return v

    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        """验证消息不为空白"""
        if not v or not v.strip():
            raise ValueError("Message cannot be empty or whitespace only")
        return v.strip()


class ChatResponse(BaseModel):
    """聊天响应"""
    session_id: str
    message_id: Optional[str] = None
    text: str
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class StreamChunkResponse(BaseModel):
    """流式响应块"""
    type: Literal["text_delta", "tool_use", "done", "error"]
    text: Optional[str] = None
    tool_name: Optional[str] = None
    error: Optional[str] = None


# ============ Config 相关模型 ============

class ConfigResponse(BaseModel):
    """配置响应"""
    system_prompt: str
    session_storage: str
    session_ttl: int
    mcp_servers: Dict[str, Any]


class UpdateSystemPromptRequest(BaseModel):
    """更新系统提示词请求"""
    system_prompt: str


# ============ Health Check ============

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    active_sessions: int
    uptime_seconds: Optional[float] = None


# ============ Error Response ============

class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    detail: Optional[str] = None
    session_id: Optional[str] = None
