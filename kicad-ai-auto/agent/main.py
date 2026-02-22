"""
KiCad AI Auto - Control Agent
FastAPI backend for controlling KiCad through browser
"""

# 加载环境变量
from dotenv import load_dotenv
import os

# 加载当前目录和上级目录的 .env 文件
agent_dir = os.path.dirname(__file__)
project_root = os.path.dirname(agent_dir)

# 优先加载 agent/.env，然后是 backend/.env
env_paths = [
    os.path.join(agent_dir, ".env"),
    os.path.join(project_root, "backend", ".env"),
]
for env_path in env_paths:
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)

from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    File,
    UploadFile,
    HTTPException,
    Depends,
    Header,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any
from pathlib import Path
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import asyncio
import io
import os
import json
import logging
import re
from datetime import datetime

from kicad_controller import KiCadController
from export_manager import ExportManager
from state_monitor import StateMonitor

from middleware import (
    RequestLoggingMiddleware,
    ErrorHandlingMiddleware,
    setup_logging,
    KiCadError,
    KiCadNotRunningError,
    KiCadTimeoutError,
    KiCadCommandError,
    ProjectNotFoundError,
    ExportError,
)

# 配置日志（从环境变量读取日志级别）
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
setup_logging(LOG_LEVEL)
logger = logging.getLogger(__name__)

# 导入 IPC API 路由（如果可用）
try:
    from routes.kicad_ipc_routes import router as kicad_ipc_router
    from routes.kicad_ipc_routes import broadcast_status_task
    from kicad_ipc_manager import get_kicad_manager

    HAS_KICAD_IPC = True
    logger.info("KiCad IPC module imported successfully")
except ImportError as e:
    logger.warning(f"KiCad IPC routes not available: {e}")
    HAS_KICAD_IPC = False

# 导入项目 API 路由
from routes.project_routes import router as project_router
from routes.ai_routes import router as ai_router

# ========== 安全配置 ==========

# CORS 允许的域名（从环境变量读取）
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001"
).split(",")

# API Key 认证（从环境变量读取）
API_KEY = os.getenv("API_KEY", "")

# 文件上传配置
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {
    ".kicad_pro",
    ".kicad_sch",
    ".kicad_pcb",
    ".kicad_mod",
    ".zip",
    ".kicad_sym",
}

# 项目目录
PROJECTS_DIR = Path(os.getenv("PROJECTS_DIR", "/projects"))
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

# ========== 速率限制配置 ==========

# 创建速率限制器
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],  # 默认每分钟 200 次请求
    storage_uri="memory://",  # 使用内存存储（单实例）
)

# 创建 FastAPI 应用
app = FastAPI(
    title="KiCad AI Control API",
    description="API for controlling KiCad through browser automation",
    version="1.0.0",
)

# 注册速率限制器
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 添加中间件
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# 配 CORS - 安全配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

# 注册 KiCad IPC API 路由（如果可用）
if HAS_KICAD_IPC:
    app.include_router(kicad_ipc_router)
    logger.info("KiCad IPC API routes registered")

# 注册项目 API 路由
app.include_router(project_router)
logger.info("Project API routes registered")

# 注册 AI API 路由
app.include_router(ai_router)
logger.info("AI API routes registered")

# 注册符号库 API 路由
try:
    from routes.symbol_routes import router as symbol_router

    app.include_router(symbol_router)
    logger.info("Symbol Library API routes registered")
except ImportError as e:
    logger.warning(f"Symbol routes not available: {e}")


# ========== 认证与验证 ==========


async def verify_api_key(api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """验证 API Key"""
    if API_KEY and api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return api_key


class ProjectPath(BaseModel):
    """项目路径验证"""

    path: str

    @validator("path")
    def validate_path(cls, v):
        # 防止路径遍历攻击
        if ".." in v or not v.startswith("/"):
            raise ValueError("Invalid path: path traversal not allowed")
        return v


# 全局控制器实例
kicad_controller: Optional[KiCadController] = None
state_monitor: Optional[StateMonitor] = None
export_manager: Optional[ExportManager] = None

# ========== 数据模型 ==========


class ToolAction(BaseModel):
    tool: str
    params: Dict[str, Any] = {}


class MouseAction(BaseModel):
    action: str  # click, double_click, drag, move
    x: int
    y: int
    button: str = "left"
    duration: float = 0.5


class KeyboardAction(BaseModel):
    keys: List[str]
    text: Optional[str] = None


class MenuAction(BaseModel):
    menu: str
    item: Optional[str] = None


class ExportRequest(BaseModel):
    format: str  # gerber, drill, bom, pickplace, pdf, svg, step
    output_dir: str
    options: Dict[str, Any] = {}


class ProjectInfo(BaseModel):
    path: Optional[str] = None
    name: Optional[str] = None
    modified: Optional[datetime] = None
    running: bool = False


class StateResponse(BaseModel):
    tool: Optional[str]
    cursor: Dict[str, float]
    layer: Optional[str]
    zoom: Optional[float]
    errors: List[str]
    timestamp: datetime


# ========== 生命周期 ==========


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    global kicad_controller, state_monitor, export_manager

    logger.info("Initializing KiCad Controller...")
    kicad_controller = KiCadController(
        display_id=os.getenv("DISPLAY", ":99"), resolution=(1920, 1080)
    )

    state_monitor = StateMonitor(kicad_controller)
    export_manager = ExportManager(kicad_controller)

    logger.info("KiCad Controller initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理"""
    global kicad_controller

    logger.info("Shutting down KiCad Controller...")
    if kicad_controller:
        kicad_controller.close()
    logger.info("KiCad Controller stopped")


# ========== 健康检查 ==========


@app.get("/api/health")
@limiter.limit("60/minute")
async def health_check(request: Request):
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "kicad_running": kicad_controller.is_running() if kicad_controller else False,
    }


# ========== 项目操作 ==========


@app.post("/api/project/start")
@limiter.limit("10/minute")
async def start_kicad(request: Request, project_path: Optional[str] = None):
    """启动 KiCad"""
    try:
        kicad_controller.start(project_path)
        return {
            "success": True,
            "message": "KiCad started successfully",
            "project": project_path,
        }
    except Exception as e:
        logger.error(f"Failed to start KiCad: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/project/stop")
@limiter.limit("10/minute")
async def stop_kicad(request: Request):
    """停止 KiCad"""
    try:
        kicad_controller.close()
        return {"success": True, "message": "KiCad stopped"}
    except Exception as e:
        logger.error(f"Failed to stop KiCad: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/project/open")
@limiter.limit("20/minute")
async def open_project(
    request: Request, file: UploadFile, api_key: str = Depends(verify_api_key)
):
    """打开项目文件（带安全验证）"""
    try:
        # 验证文件扩展名
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {ext}。允许的类型: {', '.join(ALLOWED_EXTENSIONS)}",
            )

        # 安全路径处理 - 防止路径遍历
        safe_filename = os.path.basename(file.filename)
        file_path = PROJECTS_DIR / safe_filename

        # 读取并验证文件大小
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"文件过大，最大允许 {MAX_FILE_SIZE // (1024 * 1024)}MB",
            )

        # 保存文件
        with open(file_path, "wb") as f:
            f.write(content)

        # 打开项目
        kicad_controller.open_project(str(file_path))

        return {
            "success": True,
            "message": f"Project {safe_filename} opened",
            "path": str(file_path),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to open project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/project/save")
async def save_project():
    """保存当前项目"""
    try:
        kicad_controller.save_project()
        return {"success": True, "message": "Project saved"}
    except Exception as e:
        logger.error(f"Failed to save project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/project/info", response_model=ProjectInfo)
async def get_project_info():
    """获取当前项目信息"""
    try:
        info = kicad_controller.get_project_info()
        return info
    except Exception as e:
        logger.error(f"Failed to get project info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 菜单操作 ==========


@app.post("/api/menu/click")
async def click_menu(action: MenuAction):
    """点击菜单"""
    try:
        kicad_controller.click_menu(action.menu, action.item)
        return {"success": True, "menu": action.menu, "item": action.item}
    except Exception as e:
        logger.error(f"Failed to click menu: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 工具操作 ==========


@app.post("/api/tool/activate")
async def activate_tool(action: ToolAction):
    """激活工具"""
    try:
        kicad_controller.activate_tool(action.tool, action.params)
        return {"success": True, "tool": action.tool}
    except Exception as e:
        logger.error(f"Failed to activate tool: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 输入操作 ==========


@app.post("/api/input/mouse")
@limiter.limit("120/minute")
async def send_mouse_action(request: Request, action: MouseAction):
    """发送鼠标操作"""
    try:
        if action.action == "click":
            kicad_controller.mouse_click(action.x, action.y, action.button)
        elif action.action == "double_click":
            kicad_controller.mouse_double_click(action.x, action.y)
        elif action.action == "move":
            kicad_controller.mouse_move(action.x, action.y)
        elif action.action == "drag":
            kicad_controller.mouse_drag(action.x, action.y, action.duration)

        return {"success": True, "action": action.action, "x": action.x, "y": action.y}
    except Exception as e:
        logger.error(f"Failed to send mouse action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/input/keyboard")
@limiter.limit("120/minute")
async def send_keyboard_action(request: Request, action: KeyboardAction):
    """发送键盘操作"""
    try:
        if action.text:
            kicad_controller.type_text(action.text)
        else:
            kicad_controller.press_keys(action.keys)

        return {"success": True, "keys": action.keys, "text": action.text}
    except Exception as e:
        logger.error(f"Failed to send keyboard action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 状态查询 ==========


@app.get("/api/state/screenshot")
@limiter.limit("60/minute")
async def get_screenshot(request: Request):
    """获取屏幕截图 - 支持GUI截图和CLI导出"""
    try:
        # 首先尝试GUI截图
        screenshot = kicad_controller.get_screenshot()

        # 检查截图是否为空/白色（简单检查：如果截图非常小可能是空的）
        if len(screenshot) < 1000:
            logger.warning("GUI screenshot seems empty, trying CLI export...")
            # 尝试使用KiCad CLI导出（如果IPC模块可用）
            if HAS_KICAD_IPC:
                try:
                    kicad_manager = get_kicad_manager()
                    if (
                        kicad_manager.config.kicad_cli_path
                        and kicad_manager.config.pcb_file_path
                    ):
                        import tempfile

                        with tempfile.NamedTemporaryFile(
                            suffix=".svg", delete=False
                        ) as tmp:
                            tmp_path = tmp.name

                        try:
                            success = kicad_manager.get_screenshot_via_cli(tmp_path)
                            if success and os.path.exists(tmp_path):
                                with open(tmp_path, "rb") as f:
                                    svg_data = f.read()
                                os.unlink(tmp_path)
                                return StreamingResponse(
                                    io.BytesIO(svg_data),
                                    media_type="image/svg+xml",
                                    headers={
                                        "Content-Disposition": "inline; filename=screenshot.svg"
                                    },
                                )
                            else:
                                os.unlink(tmp_path)
                        except Exception as cli_error:
                            logger.error(f"CLI export failed: {cli_error}")
                            if os.path.exists(tmp_path):
                                os.unlink(tmp_path)
                except Exception as ipc_error:
                    logger.error(f"IPC manager error: {ipc_error}")

        return StreamingResponse(
            io.BytesIO(screenshot),
            media_type="image/png",
            headers={"Content-Disposition": "inline; filename=screenshot.png"},
        )
    except Exception as e:
        logger.error(f"Failed to get screenshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/state/full", response_model=StateResponse)
@limiter.limit("60/minute")
async def get_full_state(request: Request):
    """获取完整状态"""
    try:
        state = state_monitor.get_state()
        return state
    except Exception as e:
        logger.error(f"Failed to get state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/state/tool")
@limiter.limit("60/minute")
async def get_current_tool(request: Request):
    """获取当前工具"""
    try:
        tool = state_monitor.get_current_tool()
        return {"tool": tool}
    except Exception as e:
        logger.error(f"Failed to get tool: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/state/coords")
@limiter.limit("60/minute")
async def get_cursor_coords(request: Request):
    """获取光标坐标"""
    try:
        coords = state_monitor.get_cursor_coords()
        return coords
    except Exception as e:
        logger.error(f"Failed to get coords: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/state/errors")
@limiter.limit("60/minute")
async def get_errors(request: Request):
    """获取错误列表"""
    try:
        errors = state_monitor.get_errors()
        return {"errors": errors}
    except Exception as e:
        logger.error(f"Failed to get errors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 文件导出 ==========


@app.post("/api/export")
@limiter.limit("20/minute")
async def export_files(request: Request, export_request: ExportRequest):
    """导出文件"""
    try:
        result = await export_manager.export(
            export_request.format, export_request.output_dir, export_request.options
        )
        return result
    except Exception as e:
        logger.error(f"Failed to export: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/export/formats")
@limiter.limit("60/minute")
async def get_export_formats(request: Request):
    """获取支持的导出格式"""
    return {
        "formats": [
            {
                "id": "gerber",
                "name": "Gerber",
                "description": "PCB manufacturing files",
            },
            {"id": "drill", "name": "Drill", "description": "Excellon drill files"},
            {"id": "bom", "name": "BOM", "description": "Bill of Materials"},
            {
                "id": "pickplace",
                "name": "Pick & Place",
                "description": "Component placement file",
            },
            {"id": "pdf", "name": "PDF", "description": "PDF printout"},
            {"id": "svg", "name": "SVG", "description": "SVG vector graphics"},
            {"id": "step", "name": "STEP", "description": "3D STEP model"},
        ]
    }


# ========== DRC ==========


@app.post("/api/drc/run")
@limiter.limit("10/minute")
async def run_drc(request: Request):
    """运行 DRC 检查"""
    try:
        result = kicad_controller.run_drc()
        return result
    except Exception as e:
        logger.error(f"Failed to run DRC: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/drc/report")
@limiter.limit("30/minute")
async def get_drc_report(request: Request):
    """获取 DRC 报告"""
    try:
        report = kicad_controller.get_drc_report()
        return report
    except Exception as e:
        logger.error(f"Failed to get DRC report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== WebSocket 控制通道 ==========


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)


manager = ConnectionManager()


@app.websocket("/ws/control")
async def control_websocket(websocket: WebSocket):
    """WebSocket 控制通道"""
    await manager.connect(websocket)
    try:
        while True:
            message = await websocket.receive_json()

            # 处理不同类型的消息
            if message["type"] == "mouse":
                await handle_mouse_message(message)
            elif message["type"] == "keyboard":
                await handle_keyboard_message(message)
            elif message["type"] == "command":
                result = await handle_command(message["command"])
                cmd_type = message.get("command", {}).get("type")

                # 根据命令类型返回对应的消息格式
                if cmd_type == "screenshot":
                    await websocket.send_json({"type": "screenshot", "data": result})
                else:
                    await websocket.send_json(
                        {"type": "result", "id": message.get("id"), "data": result}
                    )
            elif message["type"] == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def handle_mouse_message(message: dict):
    """处理鼠标消息"""
    event_type = message.get("event")
    x = message.get("x")
    y = message.get("y")

    if event_type == "click":
        kicad_controller.mouse_click(x, y)
    elif event_type == "move":
        kicad_controller.mouse_move(x, y)
    elif event_type == "down":
        kicad_controller.mouse_down(x, y)
    elif event_type == "up":
        kicad_controller.mouse_up(x, y)


async def handle_keyboard_message(message: dict):
    """处理键盘消息"""
    keys = message.get("keys", [])
    kicad_controller.press_keys(keys)


async def handle_command(command: dict):
    """处理命令"""
    cmd_type = command.get("type")

    if cmd_type == "screenshot":
        return kicad_controller.get_screenshot_base64()
    elif cmd_type == "state":
        return state_monitor.get_state()
    elif cmd_type == "tool":
        return {"tool": state_monitor.get_current_tool()}

    return {"error": "Unknown command"}


# ========== 主入口 ==========

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
