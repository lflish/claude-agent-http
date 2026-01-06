"""
Session management API routes.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..agent import ClaudeAgent
from ..models import (
    CreateSessionRequest,
    SessionResponse,
)
from ..exceptions import (
    SessionNotFoundError,
    ClientCreationError,
    PathSecurityError,
)

router = APIRouter()


def get_agent() -> ClaudeAgent:
    """Dependency to get agent instance (set in main.py)."""
    from ..main import get_agent_instance
    return get_agent_instance()


@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new session",
    description="Create a new Claude Agent session for a user",
)
async def create_session(
    request: CreateSessionRequest,
    agent: ClaudeAgent = Depends(get_agent),
):
    """Create a new session."""
    try:
        session_id = await agent.create_session(
            user_id=request.user_id,
            subdir=request.subdir,
            system_prompt=request.system_prompt,
            mcp_servers=request.mcp_servers,
            plugins=request.plugins,
            model=request.model,
            permission_mode=request.permission_mode,
            allowed_tools=request.allowed_tools,
            disallowed_tools=request.disallowed_tools,
            add_dirs=request.add_dirs,
            max_turns=request.max_turns,
            max_budget_usd=request.max_budget_usd,
            init_message=request.init_message,
            metadata=request.metadata,
        )

        session_info = await agent.get_session_info(session_id)

        return SessionResponse(
            session_id=session_info.session_id,
            user_id=session_info.user_id,
            cwd=session_info.cwd,
            created_at=session_info.created_at,
            last_active_at=session_info.last_active_at,
            message_count=session_info.message_count,
            status="active",
            metadata=session_info.metadata,
        )

    except PathSecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ClientCreationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {e}",
        )


@router.get(
    "/sessions",
    response_model=list[str],
    summary="List sessions",
    description="List all session IDs, optionally filtered by user_id",
)
async def list_sessions(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    agent: ClaudeAgent = Depends(get_agent),
):
    """List all sessions."""
    try:
        return await agent.list_sessions(user_id=user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {e}",
        )


@router.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    summary="Get session info",
    description="Get information about a specific session",
)
async def get_session(
    session_id: str,
    agent: ClaudeAgent = Depends(get_agent),
):
    """Get session information."""
    try:
        session_info = await agent.get_session_info(session_id)

        if not session_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        return SessionResponse(
            session_id=session_info.session_id,
            user_id=session_info.user_id,
            cwd=session_info.cwd,
            created_at=session_info.created_at,
            last_active_at=session_info.last_active_at,
            message_count=session_info.message_count,
            status="active",
            metadata=session_info.metadata,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {e}",
        )


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Close session",
    description="Close and delete a session",
)
async def delete_session(
    session_id: str,
    agent: ClaudeAgent = Depends(get_agent),
):
    """Close a session."""
    try:
        session_info = await agent.get_session_info(session_id)
        if not session_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        await agent.close_session(session_id)
        return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to close session: {e}",
        )


@router.post(
    "/sessions/{session_id}/resume",
    response_model=SessionResponse,
    summary="Resume session",
    description="Resume an existing session",
)
async def resume_session(
    session_id: str,
    agent: ClaudeAgent = Depends(get_agent),
):
    """Resume an existing session."""
    try:
        await agent.resume_session(session_id)
        session_info = await agent.get_session_info(session_id)

        return SessionResponse(
            session_id=session_info.session_id,
            user_id=session_info.user_id,
            cwd=session_info.cwd,
            created_at=session_info.created_at,
            last_active_at=session_info.last_active_at,
            message_count=session_info.message_count,
            status="active",
            metadata=session_info.metadata,
        )

    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or expired",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume session: {e}",
        )
