"""
KiCad Web Editor - 后端核心
FastAPI + SQLAlchemy + PostgreSQL
"""

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.database import init_db, close_db
from app.api.v1.api import api_router
from app.core.websocket import WebSocketManager

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("Starting up KiCad Web Editor backend...")
    await init_db()

    yield

    # 关闭时
    logger.info("Shutting down KiCad Web Editor backend...")
    await close_db()


# 创建 FastAPI 应用
app = FastAPI(
    title="KiCad Web Editor API",
    description="浏览器版 KiCad 全功能编辑器后端 API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(api_router, prefix=settings.API_V1_STR)

# WebSocket 管理器
ws_manager = WebSocketManager()


@app.websocket("/ws/v1/realtime")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 实时通信端点"""
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await ws_manager.handle_message(websocket, data)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await ws_manager.disconnect(websocket)


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "KiCad Web Editor API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


@app.get("/api/v1/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "features": [
            "project_management",
            "schematic_viewer",
            "pcb_editor",
            "library_browser",
            "drc_erc",
            "export",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
