"""
Chat 聊天路由
处理消息发送（同步和流式）
"""
import time
from fastapi import APIRouter, Depends, HTTPException, status
from sse_starlette.sse import EventSourceResponse
from claude_agent_lib import ClaudeAgentLibrary
from claude_agent_lib.exceptions import SessionNotFoundError, MessageSendError, SessionBusyError
import json

from ..schemas import ChatRequest, ChatResponse, StreamChunkResponse
from ..dependencies import get_library
from ..middleware import log_request, log_response

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="发送消息（同步）",
    description="发送消息并等待完整响应"
)
async def send_message(
    request: ChatRequest,
    library: ClaudeAgentLibrary = Depends(get_library)
):
    """发送消息（同步模式）"""
    start_time = time.time()
    log_request("POST /chat", session_id=request.session_id, message=request.message)

    try:
        response = await library.send_message(
            session_id=request.session_id,
            message=request.message,
            timeout=request.timeout
        )

        elapsed_ms = (time.time() - start_time) * 1000
        log_response("POST /chat", session_id=request.session_id, time_ms=elapsed_ms,
                     text_len=len(response.text) if response.text else 0,
                     message=response.text)

        return ChatResponse(
            session_id=response.session_id,
            text=response.text,
            tool_calls=response.tool_calls,
            timestamp=response.timestamp
        )

    except SessionNotFoundError:
        elapsed_ms = (time.time() - start_time) * 1000
        log_response("POST /chat", session_id=request.session_id, status="NOT_FOUND", time_ms=elapsed_ms)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    except SessionBusyError:
        elapsed_ms = (time.time() - start_time) * 1000
        log_response("POST /chat", session_id=request.session_id, status="BUSY", time_ms=elapsed_ms)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Session is busy, please wait for the previous request to complete"
        )
    except MessageSendError as e:
        elapsed_ms = (time.time() - start_time) * 1000
        log_response("POST /chat", session_id=request.session_id, status="ERROR", time_ms=elapsed_ms, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        )
    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        log_response("POST /chat", session_id=request.session_id, status="ERROR", time_ms=elapsed_ms, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post(
    "/chat/stream",
    summary="发送消息（流式）",
    description="发送消息并以 SSE 流式返回响应"
)
async def send_message_stream(
    request: ChatRequest,
    library: ClaudeAgentLibrary = Depends(get_library)
):
    """发送消息（流式模式，SSE）"""
    start_time = time.time()
    log_request("POST /chat/stream", session_id=request.session_id, message=request.message)

    async def event_generator():
        """SSE 事件生成器"""
        nonlocal start_time
        full_text = ""  # 收集完整的回复文本
        try:
            async for chunk in library.send_message_stream(
                session_id=request.session_id,
                message=request.message
            ):
                # 收集文本
                if chunk.type == 'text_delta' and chunk.text:
                    full_text += chunk.text

                # 将 StreamChunk 转换为 JSON
                chunk_data = StreamChunkResponse(
                    type=chunk.type,
                    text=chunk.text,
                    tool_name=chunk.tool_name,
                    error=chunk.error
                )

                yield {
                    "event": "message",
                    "data": chunk_data.model_dump_json()
                }

                # 如果是 done 或 error，结束流并记录日志
                if chunk.type == 'done':
                    elapsed_ms = (time.time() - start_time) * 1000
                    log_response("POST /chat/stream", session_id=request.session_id, time_ms=elapsed_ms,
                                 text_len=len(full_text), message=full_text)
                    break
                elif chunk.type == 'error':
                    elapsed_ms = (time.time() - start_time) * 1000
                    log_response("POST /chat/stream", session_id=request.session_id, status="ERROR", time_ms=elapsed_ms, error=chunk.error)
                    break

        except SessionNotFoundError:
            elapsed_ms = (time.time() - start_time) * 1000
            log_response("POST /chat/stream", session_id=request.session_id, status="NOT_FOUND", time_ms=elapsed_ms)
            error_data = StreamChunkResponse(
                type="error",
                error="Session not found"
            )
            yield {
                "event": "error",
                "data": error_data.model_dump_json()
            }
        except SessionBusyError:
            elapsed_ms = (time.time() - start_time) * 1000
            log_response("POST /chat/stream", session_id=request.session_id, status="BUSY", time_ms=elapsed_ms)
            error_data = StreamChunkResponse(
                type="error",
                error="Session is busy, please wait for the previous request to complete"
            )
            yield {
                "event": "error",
                "data": error_data.model_dump_json()
            }
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            log_response("POST /chat/stream", session_id=request.session_id, status="ERROR", time_ms=elapsed_ms, error=str(e))
            error_data = StreamChunkResponse(
                type="error",
                error="Internal server error"
            )
            yield {
                "event": "error",
                "data": error_data.model_dump_json()
            }

    return EventSourceResponse(event_generator())
