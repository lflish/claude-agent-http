"""
数据模型
使用 Pydantic 定义所有数据结构
"""
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class SessionInfo(BaseModel):
    """会话信息"""
    session_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    last_active_at: datetime = Field(default_factory=datetime.now)
    message_count: int = 0
    system_prompt: Optional[str] = None
    mcp_servers: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Message(BaseModel):
    """完整消息响应"""
    session_id: str
    text: str
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class StreamChunk(BaseModel):
    """流式数据块"""
    type: Literal['text_delta', 'tool_use', 'done', 'error']
    text: Optional[str] = None
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    class Config:
        use_enum_values = True
