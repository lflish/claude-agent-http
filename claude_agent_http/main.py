"""
Claude Agent HTTP REST API
FastAPI application entry point.
"""
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_config, Config
from .agent import ClaudeAgent
from .models import HealthResponse
from .routers import sessions, chat


# Global agent instance
_agent: Optional[ClaudeAgent] = None
_start_time = time.time()


def get_agent_instance() -> ClaudeAgent:
    """Get the global agent instance."""
    if _agent is None:
        raise RuntimeError("Agent not initialized")
    return _agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global _agent

    print("Starting Claude Agent HTTP API...")

    # Load configuration
    config = get_config()

    # Create agent instance
    _agent = ClaudeAgent(config)
    await _agent.__aenter__()

    print(f"Agent initialized:")
    print(f"  - User base dir: {config.user.base_dir}")
    print(f"  - Storage: {config.session.storage}")
    print(f"  - Session TTL: {config.session.ttl}s")

    yield

    # Cleanup
    print("Shutting down Claude Agent HTTP API...")
    if _agent:
        await _agent.__aexit__(None, None, None)
    print("Cleanup complete")


# Create FastAPI app
app = FastAPI(
    title="Claude Agent HTTP API",
    description="HTTP REST API for Claude Agent SDK",
    version="1.0.0",
    lifespan=lifespan,
)

# Load config for CORS
try:
    _cfg = get_config()
    _cors_origins = _cfg.api.cors_origins
except Exception:
    _cors_origins = ["*"]

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(sessions.router, prefix="/api/v1", tags=["Sessions"])
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])


# ============ Base Endpoints ============

@app.get("/", summary="Root")
async def root():
    """Root endpoint."""
    return {
        "name": "Claude Agent HTTP API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse, summary="Health check")
async def health_check():
    """Health check endpoint."""
    try:
        agent = get_agent_instance()
        sessions = await agent.list_sessions()

        return HealthResponse(
            status="healthy",
            version="1.0.0",
            active_sessions=len(sessions),
            storage_type=agent.config.session.storage,
            uptime_seconds=time.time() - _start_time,
        )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "version": "1.0.0",
                "active_sessions": 0,
                "storage_type": "unknown",
                "error": str(e),
            },
        )


# ============ Exception Handlers ============

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc),
        },
    )


# ============ Main Entry ============

if __name__ == "__main__":
    import uvicorn

    config = get_config()
    uvicorn.run(
        "claude_agent_http.main:app",
        host=config.api.host,
        port=config.api.port,
        reload=False,
    )
