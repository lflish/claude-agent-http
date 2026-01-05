"""
Claude Agent HTTP REST API
基于 FastAPI 和 claude_agent_lib 构建
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import logging
import sys

# 添加项目根目录到路径
sys.path.insert(0, '.')

from claude_agent_lib import ClaudeAgentLibrary, LibraryConfig
from .dependencies import set_library_instance
from .routers import sessions, chat
from .schemas import HealthResponse

# 应用启动时间
_start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""

    # 启动时：初始化库实例
    print("🚀 启动 Claude Agent API...")

    # 从 YAML 配置加载（环境变量会自动覆盖）
    config = LibraryConfig.from_yaml()

    # 创建库实例
    library = ClaudeAgentLibrary(config)
    await library.__aenter__()

    # 设置全局实例
    set_library_instance(library)

    print(f"✅ 库实例已初始化")
    print(f"   - 存储类型: {config.session_storage}")
    print(f"   - 会话TTL: {config.session_ttl}秒")

    yield

    # 关闭时：清理资源
    print("🛑 关闭 Claude Agent API...")
    await library.__aexit__(None, None, None)
    print("✅ 资源已清理")


# 创建 FastAPI 应用
app = FastAPI(
    title="Claude Agent API",
    description="基于 Claude Agent SDK 的 HTTP REST API",
    version="0.2.0",
    lifespan=lifespan
)

# 从统一配置加载 CORS 和日志设置
try:
    from config_loader import get_config
    _cfg = get_config()
    _cors_origins = _cfg.api.cors_origins
    _log_level = _cfg.api.log_level
except Exception:
    _cors_origins = ["*"]
    _log_level = "INFO"

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置日志级别
logging.getLogger("claude_agent_api").setLevel(getattr(logging, _log_level.upper(), logging.INFO))


# 注册路由
app.include_router(sessions.router, prefix="/api/v1", tags=["Sessions"])
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])


# ============ 基础端点 ============

@app.get("/", summary="根路径")
async def root():
    """根路径"""
    return {
        "message": "Claude Agent API",
        "version": "0.2.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, summary="健康检查")
async def health_check():
    """健康检查"""
    from .dependencies import get_library

    try:
        library = get_library()
        active_sessions = await library.list_sessions()

        return HealthResponse(
            status="healthy",
            version="0.2.0",
            active_sessions=len(active_sessions),
            uptime_seconds=time.time() - _start_time
        )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "version": "0.2.0",
                "active_sessions": 0,
                "error": str(e)
            }
        )


# ============ 异常处理 ============

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn

    # 开发模式运行（关闭 reload 以便正确捕获日志）
    uvicorn.run(
        "claude_agent_api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
