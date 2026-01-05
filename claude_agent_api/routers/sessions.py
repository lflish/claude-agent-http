"""
Session 管理路由
处理会话的创建、复用、查询、删除
"""
import time
from fastapi import APIRouter, Depends, HTTPException, status
from claude_agent_lib import ClaudeAgentLibrary
from claude_agent_lib.exceptions import SessionNotFoundError, ClientCreationError

from ..schemas import (
    CreateSessionRequest,
    ResumeSessionRequest,
    SessionResponse,
    ErrorResponse
)
from ..dependencies import get_library
from ..middleware import log_request, log_response

router = APIRouter()


@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建新会话",
    description="创建一个新的 Claude Agent 会话"
)
async def create_session(
    request: CreateSessionRequest,
    library: ClaudeAgentLibrary = Depends(get_library)
):
    """创建新会话"""
    start_time = time.time()
    log_request("POST /sessions", init_message=request.init_message)

    try:
        session_id = await library.create_session(
            system_prompt=request.system_prompt,
            mcp_servers=request.mcp_servers,
            metadata=request.metadata,
            init_message=request.init_message
        )

        session_info = await library.get_session_info(session_id)

        elapsed_ms = (time.time() - start_time) * 1000
        log_response("POST /sessions", session_id=session_id, time_ms=elapsed_ms)

        return SessionResponse(
            session_id=session_info.session_id,
            created_at=session_info.created_at,
            last_active_at=session_info.last_active_at,
            message_count=session_info.message_count,
            status="active",
            metadata=session_info.metadata
        )

    except ClientCreationError as e:
        elapsed_ms = (time.time() - start_time) * 1000
        log_response("POST /sessions", status="ERROR", time_ms=elapsed_ms, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create session"
        )
    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        log_response("POST /sessions", status="ERROR", time_ms=elapsed_ms, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post(
    "/sessions/resume",
    response_model=SessionResponse,
    summary="复用已有会话",
    description="复用一个已存在的会话，使用原始配置"
)
async def resume_session(
    request: ResumeSessionRequest,
    library: ClaudeAgentLibrary = Depends(get_library)
):
    """复用已有会话（使用原始 system_prompt 和 mcp_servers）"""
    try:
        success = await library.resume_session(session_id=request.session_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )

        session_info = await library.get_session_info(request.session_id)

        return SessionResponse(
            session_id=session_info.session_id,
            created_at=session_info.created_at,
            last_active_at=session_info.last_active_at,
            message_count=session_info.message_count,
            resumed=True,
            status="active",
            metadata=session_info.metadata
        )

    except HTTPException:
        raise
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or expired"
        )
    except Exception as e:
        print(f"Error resuming session {request.session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    summary="获取会话信息",
    description="获取指定会话的详细信息"
)
async def get_session(
    session_id: str,
    library: ClaudeAgentLibrary = Depends(get_library)
):
    """获取会话信息"""
    try:
        session_info = await library.get_session_info(session_id)

        if not session_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )

        return SessionResponse(
            session_id=session_info.session_id,
            created_at=session_info.created_at,
            last_active_at=session_info.last_active_at,
            message_count=session_info.message_count,
            status="active",
            metadata=session_info.metadata
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="关闭会话",
    description="关闭并删除指定的会话"
)
async def delete_session(
    session_id: str,
    library: ClaudeAgentLibrary = Depends(get_library)
):
    """关闭会话"""
    try:
        # 先检查会话是否存在
        session_info = await library.get_session_info(session_id)
        if not session_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found"
            )

        # 关闭会话
        await library.close_session(session_id)
        return None

    except HTTPException:
        # 重新抛出 HTTP 异常
        raise
    except Exception as e:
        # 记录错误但不暴露详细信息
        print(f"Error closing session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to close session"
        )


@router.get(
    "/sessions",
    response_model=list[str],
    summary="列出所有会话",
    description="获取当前所有活跃会话的 ID 列表"
)
async def list_sessions(
    library: ClaudeAgentLibrary = Depends(get_library)
):
    """列出所有会话"""
    try:
        sessions = await library.list_sessions()
        return sessions

    except Exception as e:
        print(f"Error listing sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
