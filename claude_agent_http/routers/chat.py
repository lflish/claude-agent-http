"""
Chat API routes.
"""
import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from ..agent import ClaudeAgent
from ..models import ChatRequest, ChatResponse
from ..exceptions import (
    SessionNotFoundError,
    SessionBusyError,
    MessageSendError,
)

router = APIRouter()


def get_agent() -> ClaudeAgent:
    """Dependency to get agent instance (set in main.py)."""
    from ..main import get_agent_instance
    return get_agent_instance()


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send message",
    description="Send a message and wait for complete response",
)
async def send_message(
    request: ChatRequest,
    agent: ClaudeAgent = Depends(get_agent),
):
    """Send a message (sync mode)."""
    try:
        response = await agent.send_message(
            session_id=request.session_id,
            message=request.message,
        )
        return response

    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or expired",
        )
    except SessionBusyError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Session is busy processing another request",
        )
    except MessageSendError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {e}",
        )


@router.post(
    "/chat/stream",
    summary="Send message (streaming)",
    description="Send a message and receive streaming response via SSE",
)
async def send_message_stream(
    request: ChatRequest,
    agent: ClaudeAgent = Depends(get_agent),
):
    """Send a message (streaming mode via SSE)."""

    async def event_generator():
        try:
            async for chunk in agent.send_message_stream(
                session_id=request.session_id,
                message=request.message,
            ):
                data = chunk.model_dump_json()
                yield f"data: {data}\n\n"

        except SessionNotFoundError:
            error_data = json.dumps({
                "type": "error",
                "error": "Session not found or expired"
            })
            yield f"data: {error_data}\n\n"

        except SessionBusyError:
            error_data = json.dumps({
                "type": "error",
                "error": "Session is busy processing another request"
            })
            yield f"data: {error_data}\n\n"

        except Exception as e:
            error_data = json.dumps({
                "type": "error",
                "error": str(e)
            })
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
