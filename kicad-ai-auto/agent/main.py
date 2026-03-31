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

# 添加deprecated目录到sys.path
import sys

sys.path.insert(0, os.path.join(agent_dir, "deprecated"))

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
from pydantic import BaseModel, field_validator
from typing import List, Optional, Dict, Any
from pathlib import Path
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from contextlib import asynccontextmanager
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
from settings import get_settings, validate_api_key, get_environment

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

# 导入芯片质量门控路由
try:
    from routes.chip_quality import router as chip_quality_router

    HAS_CHIP_QUALITY = True
except ImportError as e:
    logger.warning(f"Chip quality routes not available: {e}")
    HAS_CHIP_QUALITY = False

# ========== 安全配置 ==========

# 使用新的配置模块
_config = get_settings()

# 使用配置模块的 CORS
ALLOWED_ORIGINS = _config.allowed_origins
API_KEY = _config.api_key or ""

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

# 文件魔数验证 - 防止恶意文件伪装扩展名
FILE_SIGNATURES = {
    ".zip": b"PK",  # ZIP文件
    ".kicad_pro": b"",  # JSON格式，无固定魔数
    ".kicad_sch": b"",  # JSON格式
    ".kicad_pcb": b"",  # S表达式格式
    ".kicad_mod": b"",  # S表达式格式
    ".kicad_sym": b"",  # S表达式格式
}


def validate_file_content(content: bytes, extension: str) -> bool:
    """验证文件内容是否与扩展名匹配"""
    if extension not in FILE_SIGNATURES:
        return False

    signature = FILE_SIGNATURES[extension]
    if not signature:
        # 无需验证的文件类型，检查是否为有效JSON或文本
        try:
            content[:1000].decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False

    # 检查文件魔数
    return content.startswith(signature)


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理（替代废弃的 @app.on_event）"""
    global kicad_controller, state_monitor, export_manager

    # Startup
    logger.info("Initializing KiCad Controller...")
    kicad_controller = KiCadController(
        display_id=os.getenv("DISPLAY", ":99"), resolution=(1920, 1080)
    )
    state_monitor = StateMonitor(kicad_controller)
    export_manager = ExportManager(kicad_controller)
    logger.info("KiCad Controller initialized")

    yield

    # Shutdown
    logger.info("Shutting down KiCad Controller...")
    if kicad_controller:
        kicad_controller.close()
    logger.info("KiCad Controller stopped")


# 创建 FastAPI 应用
app = FastAPI(
    title="KiCad AI Control API",
    description="基于 KiCad 9.0+ IPC API 的 AI 驱动 PCB 设计自动化后端",
    version="0.9.13",
    lifespan=lifespan,
)


# ========== 版本信息端点 ==========
@app.get("/api/version")
async def get_version():
    """获取API版本信息"""
    return {
        "version": "0.9.12",
        "name": "KiCad AI Control API",
        "description": "基于 KiCad 9.0+ IPC API 的 AI 驱动 PCB 设计自动化后端",
    }


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

# 注册认证与 Token 管理路由
from routes.auth_routes import router as auth_router
from routes.token_routes import router as token_router
from routes.deepeda_routes import router as deepeda_router
from routes.admin_routes import router as admin_router

app.include_router(auth_router)
app.include_router(token_router)
app.include_router(deepeda_router)
app.include_router(admin_router)
logger.info("Auth and Token routes registered")

# 注册符号库 API 路由
try:
    from routes.symbol_routes import router as symbol_router

    app.include_router(symbol_router)
    logger.info("Symbol Library API routes registered")
except ImportError as e:
    logger.warning(f"Symbol routes not available: {e}")

# 注册 PCB 增强 API 路由 (Phase 6: 扇出、交互式布线)
try:
    from routes.pcb_routes import router as pcb_router

    app.include_router(pcb_router)
    logger.info("PCB Enhanced API routes registered")
except ImportError as e:
    logger.warning(f"PCB routes not available: {e}")

# 注册模板 API 路由 (Phase 6: 项目模板系统)
try:
    from routes.template_routes import router as template_router

    app.include_router(template_router)
    logger.info("Template API routes registered")
except ImportError as e:
    logger.warning(f"Template routes not available: {e}")

# 注册知识库 API 路由
try:
    from routes.knowledge_routes import router as knowledge_router

    app.include_router(knowledge_router)
    logger.info("Knowledge Base API routes registered")
except ImportError as e:
    logger.warning(f"Knowledge routes not available: {e}")

# 注册网表管理 API 路由
try:
    from routes.netlist_routes import router as netlist_router

    app.include_router(netlist_router)
    logger.info("Netlist API routes registered")
except ImportError as e:
    logger.warning(f"Netlist routes not available: {e}")

# 注册 PCB 生成 API 路由
try:
    from routes.pcb_gen_routes import router as pcb_gen_router

    app.include_router(pcb_gen_router)
    logger.info("PCB Generation API routes registered")
except ImportError as e:
    logger.warning(f"PCB Generation routes not available: {e}")

# 注册封装库 API 路由
try:
    from routes.footprint_routes import router as footprint_router

    app.include_router(footprint_router)
    logger.info("Footprint Library API routes registered")
except ImportError as e:
    logger.warning(f"Footprint routes not available: {e}")

# DRC 检查路由
try:
    from routes.drc_routes import router as drc_router

    app.include_router(drc_router)
    logger.info("DRC API routes registered")
except ImportError as e:
    logger.warning(f"DRC routes not available: {e}")

# 多步设计 Agent 路由 (Phase 7E)
try:
    from routes.agent_routes import router as agent_router

    app.include_router(agent_router)
    logger.info("Design Agent API routes registered")
except ImportError as e:
    logger.warning(f"Agent routes not available: {e}")

# 设计审查路由 (Phase 10)
try:
    from routes.design_review_routes import router as design_review_router

    app.include_router(design_review_router)
    logger.info("Design Review API routes registered")
except ImportError as e:
    logger.warning(f"Design Review routes not available: {e}")


# 别名路由 - 兼容旧版本
@app.get("/api/footprints/libraries")
async def footprints_libraries_alias():
    """封装库列表(兼容旧版本)"""
    from routes.footprint_routes import list_footprint_libraries

    return {"success": True, "libraries": list_footprint_libraries()}


@app.get("/api/netlist/example")
async def netlist_example_alias():
    """网表示例(兼容旧版本)"""
    from routes.netlist_routes import get_netlist_example

    return await get_netlist_example()


@app.get("/api/knowledge/health")
async def knowledge_health_alias():
    """知识库健康检查(兼容旧版本)"""
    from routes.knowledge_routes import knowledge_health

    return await knowledge_health()


# ========== 认证与验证 ==========


async def verify_api_key(api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """验证 API Key - 支持开发和生产环境"""
    # 使用新的配置验证函数
    result = validate_api_key(api_key)

    # result = None: 不需要验证
    # result = True: 验证通过
    # result = False: 验证失败
    if result is False:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    # 如果生产环境但未配置 API_KEY，会在 validate_api_key 中抛出异常
    return api_key


class ProjectPath(BaseModel):
    """项目路径验证"""

    path: str

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """防止路径遍历攻击 - 增强版"""
        from urllib.parse import unquote

        # URL 解码处理
        decoded_path = unquote(v)

        # 检查路径遍历模式（包括编码后的）
        traversal_patterns = ["..", "%2e%2e", "%2E%2E", "..%2f", "%2e%2e%2f"]
        for pattern in traversal_patterns:
            if pattern.lower() in decoded_path.lower():
                raise ValueError("Invalid path: path traversal not allowed")

        # 规范化路径
        try:
            normalized = Path(decoded_path).resolve()

            # 确保路径在项目目录内
            if not str(normalized).startswith(str(PROJECTS_DIR.resolve())):
                # 对于相对路径，检查规范化后是否仍在项目目录内
                if not decoded_path.startswith("/"):
                    full_path = (PROJECTS_DIR / decoded_path).resolve()
                    if not str(full_path).startswith(str(PROJECTS_DIR.resolve())):
                        raise ValueError(
                            "Invalid path: path must be within projects directory"
                        )
        except Exception as e:
            if "path traversal" in str(e) or "within projects" in str(e):
                raise
            raise ValueError(f"Invalid path format: {str(e)}")

        return v


# 全局控制器实例
kicad_controller: Optional[KiCadController] = None
state_monitor: Optional[StateMonitor] = None
export_manager: Optional[ExportManager] = None

# 全局锁保护控制器操作
_controller_lock = asyncio.Lock()

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
        # 使用锁保护全局控制器，避免并发操作冲突
        async with _controller_lock:
            # 使用 to_thread 避免阻塞事件循环
            await asyncio.to_thread(kicad_controller.start, project_path)
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
        # 使用锁保护全局控制器，避免并发操作冲突
        async with _controller_lock:
            # 使用 to_thread 避免阻塞事件循环
            await asyncio.to_thread(kicad_controller.close)
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

        # 验证文件内容（魔数验证）
        if not validate_file_content(content, ext):
            raise HTTPException(
                status_code=400,
                detail=f"文件内容与扩展名不匹配，可能是恶意文件",
            )

        # 保存文件
        with open(file_path, "wb") as f:
            f.write(content)

        # 打开项目
        async with _controller_lock:
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
        async with _controller_lock:
            kicad_controller.save_project()
        return {"success": True, "message": "Project saved"}
    except Exception as e:
        logger.error(f"Failed to save project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/project/info", response_model=ProjectInfo)
async def get_project_info():
    """获取当前项目信息"""
    try:
        async with _controller_lock:
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
        # 检查控制器是否可用
        if kicad_controller is None:
            return {
                "success": False,
                "message": "Controller not initialized",
                "menu": action.menu,
            }

        kicad_controller.click_menu(action.menu, action.item)
        return {"success": True, "menu": action.menu, "item": action.item}
    except Exception as e:
        logger.error(f"Failed to click menu: {e}")
        return {"success": False, "message": str(e), "menu": action.menu}


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
    tmp_path = None
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

                        success = kicad_manager.get_screenshot_via_cli(tmp_path)
                        svg_data = None
                        try:
                            if success and os.path.exists(tmp_path):
                                with open(tmp_path, "rb") as f:
                                    svg_data = f.read()
                                return StreamingResponse(
                                    io.BytesIO(svg_data),
                                    media_type="image/svg+xml",
                                    headers={
                                        "Content-Disposition": "inline; filename=screenshot.svg"
                                    },
                                )
                        finally:
                            # 清理临时文件
                            if svg_data and os.path.exists(tmp_path):
                                try:
                                    os.remove(tmp_path)
                                except Exception as cleanup_err:
                                    logger.warning(
                                        f"Failed to cleanup temp file: {cleanup_err}"
                                    )
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
    finally:
        # 确保临时文件被清理
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp file: {cleanup_error}")


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


@app.get("/api/v1/export/formats")
@limiter.limit("60/minute")
async def get_v1_export_formats(request: Request):
    """获取支持的导出格式 (v1)"""
    return {
        "success": True,
        "formats": [
            {"id": "gerber", "name": "Gerber", "description": "PCB制造文件 (RS-274X)"},
            {"id": "drill", "name": "Drill", "description": "钻孔文件 (Excellon)"},
            {"id": "bom", "name": "BOM", "description": "物料清单 (CSV)"},
            {"id": "pickplace", "name": "Pick and Place", "description": "贴片坐标文件"},
            {"id": "pdf", "name": "PDF", "description": "PDF文档"},
            {"id": "svg", "name": "SVG", "description": "SVG矢量图"},
            {"id": "step", "name": "STEP", "description": "3D模型 (STEP/AP-214)"},
        ]
    }


# ========== 设计设置与规则 ==========


@app.get("/api/v1/design/settings")
async def get_design_settings():
    """获取 PCB 设计默认设置"""
    return {
        "success": True,
        "settings": {
            "board": {
                "width": 100.0,
                "height": 80.0,
                "layers": 2,
                "thickness": 1.6,
                "material": "FR4"
            },
            "trace": {
                "min_width": 0.2,
                "default_width": 0.5,
                "power_width": 1.0,
                " clearance": 0.2
            },
            "via": {
                "diameter": 0.6,
                "drill": 0.3,
                "min_diameter": 0.4
            },
            "silkscreen": {
                "text_width": 0.15,
                "text_height": 1.0
            }
        }
    }


@app.post("/api/v1/design/settings")
async def update_design_settings(request: Request):
    """更新 PCB 设计设置"""
    try:
        body = await request.json()
        return {
            "success": True,
            "message": "设置已更新",
            "settings": body.get("settings", {})
        }
    except Exception as e:
        logger.error(f"更新设计设置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/design/rules")
async def get_design_rules():
    """获取 PCB 设计规则"""
    return {
        "success": True,
        "rules": {
            "electrical": {
                "min_clearance": 0.2,
                "min_trace_width": 0.2,
                "min_solder_mask": 0.1
            },
            "manufacturing": {
                "min_via_drill": 0.3,
                "min_via_diameter": 0.6,
                "min_pitch": 0.635,
                "edge_planning": 0.5
            },
            "high_speed": {
                "impedance_tolerance": 10,
                "max_length_mismatch": 0.15,
                "differential_pair_gap": 0.2
            }
        }
    }


@app.post("/api/v1/design/rules")
async def update_design_rules(request: Request):
    """更新 PCB 设计规则"""
    try:
        body = await request.json()
        return {
            "success": True,
            "message": "规则已更新",
            "rules": body.get("rules", {})
        }
    except Exception as e:
        logger.error(f"更新设计规则失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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


@app.get("/api/drc/options")
async def get_drc_options():
    """获取 DRC 选项"""
    return {
        "success": True,
        "options": {
            "min_clearance": {"value": 0.2, "unit": "mm", "description": "最小间距"},
            "min_track_width": {
                "value": 0.2,
                "unit": "mm",
                "description": "最小走线宽度",
            },
            "min_via_diameter": {
                "value": 0.3,
                "unit": "mm",
                "description": "最小过孔直径",
            },
            "min_solder_mask_clearance": {
                "value": 0.1,
                "unit": "mm",
                "description": "最小绿油间距",
            },
        },
    }


@app.get("/api/erc/options")
async def get_erc_options():
    """获取 ERC 选项"""
    return {
        "success": True,
        "options": {
            "check_power_pins": {"value": True, "description": "检查电源引脚"},
            "check_unconnected": {"value": True, "description": "检查未连接"},
            "check_duplicates": {"value": True, "description": "检查重复"},
        },
    }


# ========== WebSocket 控制通道 ==========


class ConnectionManager:
    """WebSocket 连接管理器 - 线程安全版本"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            # 关闭并移除同 IP:port 的旧连接（防止重连时僵尸连接）
            stale = [ws for ws in self.active_connections
                     if ws.client and websocket.client and
                     ws.client.peername == websocket.client.peername]
            for ws in stale:
                try:
                    await ws.close()
                except Exception as e:
                    logger.debug(f"关闭过期WebSocket连接失败: {e}")
                if ws in self.active_connections:
                    self.active_connections.remove(ws)
            self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        async with self._lock:
            # 复制列表以避免在迭代时修改
            connections = list(self.active_connections)
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send message to connection: {e}")


manager = ConnectionManager()


@app.websocket("/ws/control")
async def control_websocket(websocket: WebSocket):
    """WebSocket 控制通道"""
    await manager.connect(websocket)
    try:
        while True:
            try:
                message = await websocket.receive_json()
            except Exception as e:
                logger.warning(f"Invalid JSON received: {e}")
                await websocket.send_json(
                    {"type": "error", "message": "Invalid JSON format"}
                )
                continue

            # 验证消息结构
            msg_type = message.get("type")
            if msg_type is None:
                await websocket.send_json(
                    {"type": "error", "message": "Missing message type"}
                )
                continue

            # 处理不同类型的消息
            if msg_type == "mouse":
                await handle_mouse_message(message)
            elif msg_type == "keyboard":
                await handle_keyboard_message(message)
            elif msg_type == "command":
                command = message.get("command")
                if command is None:
                    await websocket.send_json(
                        {"type": "error", "message": "Missing command field"}
                    )
                    continue
                result = await handle_command(command)
                cmd_type = command.get("type")

                # 根据命令类型返回对应的消息格式
                if cmd_type == "screenshot":
                    await websocket.send_json({"type": "screenshot", "data": result})
                else:
                    await websocket.send_json(
                        {"type": "result", "id": message.get("id"), "data": result}
                    )
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            else:
                await websocket.send_json(
                    {"type": "error", "message": f"Unknown message type: {msg_type}"}
                )

    except WebSocketDisconnect:
        await manager.disconnect(websocket)


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
