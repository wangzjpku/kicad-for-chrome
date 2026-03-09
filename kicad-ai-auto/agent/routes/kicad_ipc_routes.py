"""
KiCad IPC API 路由
提供 REST API 和 WebSocket 接口给浏览器使用
"""

import os
import tempfile

from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import asyncio
import logging
import json

from kicad_ipc_manager import KiCadIPCManager, get_kicad_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/kicad-ipc", tags=["KiCad IPC"])


# ========== Pydantic 模型 ==========


class Position(BaseModel):
    x: float
    y: float


class CreateFootprintRequest(BaseModel):
    footprint_name: str
    position: Position
    layer: str = "F.Cu"


class ExecuteActionRequest(BaseModel):
    action_name: str
    params: Optional[Dict[str, Any]] = None


class CreateTrackRequest(BaseModel):
    start: Position
    end: Position
    layer: str = "F.Cu"
    width: float = 0.25  # mm


# ========== REST API 端点 ==========


@router.post("/start")
async def start_kicad(
    pcb_file: Optional[str] = None,
    manager: KiCadIPCManager = Depends(get_kicad_manager),
):
    """启动 KiCad 并建立 IPC 连接"""
    try:
        success = manager.start_kicad(pcb_file)
        if success:
            return {
                "success": True,
                "message": "KiCad started and connected",
                "connected": True,
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to start KiCad")
    except Exception as e:
        logger.error(f"Error starting KiCad: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_kicad(manager: KiCadIPCManager = Depends(get_kicad_manager)):
    """关闭 KiCad 连接"""
    try:
        manager.cleanup()
        return {"success": True, "message": "KiCad connection closed"}
    except Exception as e:
        logger.error(f"Error stopping KiCad: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status(manager: KiCadIPCManager = Depends(get_kicad_manager)):
    """获取 KiCad 连接状态和板子信息"""
    try:
        if not manager.is_connected():
            return {"connected": False, "message": "KiCad not connected"}

        status = manager.get_board_status()
        return {"connected": True, **status}
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/action")
async def execute_action(
    request: ExecuteActionRequest, manager: KiCadIPCManager = Depends(get_kicad_manager)
):
    """执行 KiCad 动作"""
    if not manager.is_connected():
        return {"success": False, "connected": False, "message": "KiCad not connected. Please start KiCad with IPC server."}
    
    try:
        result = manager.execute_action(request.action_name, request.params)
        return {"success": True, "connected": True, **result} if isinstance(result, dict) else {"success": True, "connected": True, "result": str(result)}
    except Exception as e:
        logger.error(f"Error executing action: {e}")
        return {"success": False, "connected": True, "message": str(e)}


@router.post("/footprint")
async def create_footprint(
    request: CreateFootprintRequest,
    manager: KiCadIPCManager = Depends(get_kicad_manager),
):
    """在指定位置创建封装"""
    try:
        if not manager.is_connected():
            raise HTTPException(status_code=400, detail="KiCad not connected")

        result = manager.create_footprint(
            footprint_name=request.footprint_name,
            position=(request.position.x, request.position.y),
            layer=request.layer,
        )
        return result
    except Exception as e:
        logger.error(f"Error creating footprint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/items")
async def get_items(
    item_type: Optional[str] = None,
    layer: Optional[str] = None,
    manager: KiCadIPCManager = Depends(get_kicad_manager),
):
    """获取 PCB 上的项目列表"""
    # 如果未连接，返回友好错误而不是500
    if not manager.is_connected():
        return {"success": False, "connected": False, "message": "KiCad not connected. Please start KiCad with IPC server.", "items": []}
    
    try:
        status = manager.get_board_status()
        items = status.get("items", [])

        # 过滤
        if item_type:
            items = [item for item in items if item.get("type") == item_type]
        if layer:
            items = [item for item in items if item.get("layer") == layer]

        return {"success": True, "connected": True, "count": len(items), "items": items}
    except Exception as e:
        logger.error(f"Error getting items: {e}")
        return {"success": False, "connected": False, "message": str(e), "items": []}


@router.get("/selection")
async def get_selection(manager: KiCadIPCManager = Depends(get_kicad_manager)):
    """获取当前选中的项目"""
    if not manager.is_connected():
        return {"success": False, "connected": False, "message": "KiCad not connected", "selection": []}
    
    try:
        status = manager.get_board_status()
        return {"success": True, "connected": True, "selection": status.get("selection", [])}
    except Exception as e:
        logger.error(f"Error getting selection: {e}")
        return {"success": False, "connected": False, "message": str(e), "selection": []}


@router.post("/screenshot")
async def take_screenshot(
    manager: KiCadIPCManager = Depends(get_kicad_manager),
):
    """使用 KiCad CLI 导出截图"""
    if not manager.is_connected():
        return {"success": False, "connected": False, "message": "KiCad not connected"}
    
    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as temp_file:
            temp_file_path = temp_file.name
        output_path = temp_file_path

        success = manager.get_screenshot_via_cli(output_path)
        if success:
            return {"success": True, "connected": True, "path": output_path, "message": "Screenshot saved"}
        else:
            return {"success": False, "connected": True, "message": "Screenshot generation failed"}
    except Exception as e:
        logger.error(f"Error taking screenshot: {e}")
        return {"success": False, "connected": True, "message": str(e)}
    finally:
        # 仅当操作失败且是我们创建的临时文件时，才清理它
        if temp_file_path and not operation_success:
            try:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    logger.debug(f"Cleaned up temp file: {temp_file_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp file: {cleanup_error}")


@router.delete("/item/{item_id}")
async def delete_item(
    item_id: str, manager: KiCadIPCManager = Depends(get_kicad_manager)
):
    """删除项目"""
    try:
        if not manager.is_connected():
            raise HTTPException(status_code=400, detail="KiCad not connected")

        result = manager.delete_item(item_id)
        return result
    except Exception as e:
        logger.error(f"Error deleting item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/item/{item_id}/move")
async def move_item(
    item_id: str,
    position: Position,
    manager: KiCadIPCManager = Depends(get_kicad_manager),
):
    """移动项目"""
    try:
        if not manager.is_connected():
            raise HTTPException(status_code=400, detail="KiCad not connected")

        result = manager.move_item(item_id, (position.x, position.y))
        return result
    except Exception as e:
        logger.error(f"Error moving item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/track")
async def create_track(
    request: CreateTrackRequest, manager: KiCadIPCManager = Depends(get_kicad_manager)
):
    """创建走线"""
    try:
        if not manager.is_connected():
            raise HTTPException(status_code=400, detail="KiCad not connected")

        result = manager.create_track(
            start=(request.start.x, request.start.y),
            end=(request.end.x, request.end.y),
            layer=request.layer,
            width=request.width,
        )
        return result
    except Exception as e:
        logger.error(f"Error creating track: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/via")
async def create_via(
    position: Position,
    size: float = 0.8,
    drill: float = 0.4,
    manager: KiCadIPCManager = Depends(get_kicad_manager),
):
    """创建过孔"""
    try:
        if not manager.is_connected():
            raise HTTPException(status_code=400, detail="KiCad not connected")

        result = manager.create_via(
            position=(position.x, position.y), size=size, drill=drill
        )
        return result
    except Exception as e:
        logger.error(f"Error creating via: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save")
async def save_board(manager: KiCadIPCManager = Depends(get_kicad_manager)):
    """保存板子"""
    try:
        if not manager.is_connected():
            raise HTTPException(status_code=400, detail="KiCad not connected")

        result = manager.save_board()
        return result
    except Exception as e:
        logger.error(f"Error saving board: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(manager: KiCadIPCManager = Depends(get_kicad_manager)):
    """获取板子统计信息"""
    if not manager.is_connected():
        return {"success": False, "connected": False, "message": "KiCad not connected", "tracks": 0, "footprints": 0}
    
    try:
        result = manager.get_board_statistics()
        return {"success": True, "connected": True, **result}
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return {"success": False, "connected": False, "message": str(e)}


class SelectItemsRequest(BaseModel):
    item_ids: List[str]

@router.post("/select")
async def select_items(
    request: SelectItemsRequest, manager: KiCadIPCManager = Depends(get_kicad_manager)
):
    """选择项目"""
    if not manager.is_connected():
        return {"success": False, "connected": False, "message": "KiCad not connected"}
    
    try:
        result = manager.select_items(request.item_ids)
        return {"success": True, **result} if isinstance(result, dict) else {"success": True, "result": str(result)}
    except Exception as e:
        logger.error(f"Error selecting items: {e}")
        return {"success": False, "message": str(e)}


@router.post("/clear-selection")
async def clear_selection(manager: KiCadIPCManager = Depends(get_kicad_manager)):
    """清除选择"""
    if not manager.is_connected():
        return {"success": False, "connected": False, "message": "KiCad not connected"}
    
    try:
        result = manager.clear_selection()
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"Error clearing selection: {e}")
        return {"success": False, "message": str(e)}


# ========== WebSocket 实时通信 ==========


class WebSocketManager:
    """WebSocket 连接管理器 - 线程安全版本"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """广播消息给所有连接"""
        async with self._lock:
            # 复制列表以避免在迭代时修改
            connections = list(self.active_connections)

        disconnected = []
        for conn in connections:
            try:
                await conn.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send message to connection: {e}")
                disconnected.append(conn)

        # 清理断开的连接
        for conn in disconnected:
            await self.disconnect(conn)


ws_manager = WebSocketManager()


@router.websocket("/ws")
async def kicad_websocket(
    websocket: WebSocket, manager: KiCadIPCManager = Depends(get_kicad_manager)
):
    """WebSocket 实时通信端点"""
    await ws_manager.connect(websocket)

    try:
        # 发送初始状态
        if manager.is_connected():
            status = manager.get_board_status()
            await websocket.send_json({"type": "status", "data": status})
        else:
            await websocket.send_json({"type": "status", "data": {"connected": False}})

        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            message = json.loads(data)

            msg_type = message.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "get_status":
                status = (
                    manager.get_board_status()
                    if manager.is_connected()
                    else {"connected": False}
                )
                await websocket.send_json({"type": "status", "data": status})

            elif msg_type == "execute_action":
                if not manager.is_connected():
                    await websocket.send_json(
                        {"type": "error", "message": "KiCad not connected"}
                    )
                    continue

                action_name = message.get("action")
                params = message.get("params", {})
                result = manager.execute_action(action_name, params)
                await websocket.send_json({"type": "action_result", "data": result})

            elif msg_type == "create_footprint":
                if not manager.is_connected():
                    await websocket.send_json(
                        {"type": "error", "message": "KiCad not connected"}
                    )
                    continue

                footprint_name = message.get("footprint_name")
                pos = message.get("position", {})
                layer = message.get("layer", "F.Cu")

                result = manager.create_footprint(
                    footprint_name=footprint_name,
                    position=(pos.get("x", 0), pos.get("y", 0)),
                    layer=layer,
                )
                await websocket.send_json({"type": "creation_result", "data": result})

            else:
                await websocket.send_json(
                    {"type": "error", "message": f"Unknown message type: {msg_type}"}
                )

    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await ws_manager.disconnect(websocket)


# ========== 状态广播任务 ==========


async def broadcast_status_task(manager: KiCadIPCManager):
    """后台任务：定期广播 KiCad 状态"""
    while True:
        try:
            if manager.is_connected():
                status = manager.get_board_status()
                await ws_manager.broadcast(
                    {
                        "type": "status_update",
                        "data": status,
                        "timestamp": asyncio.get_event_loop().time(),
                    }
                )
            await asyncio.sleep(1.0)  # 1秒更新一次
        except Exception as e:
            logger.error(f"Broadcast error: {e}")
            await asyncio.sleep(5.0)


# ========== 自动布线相关模型 ==========


class AutoRouteRequest(BaseModel):
    """自动布线请求"""
    net_class: str = "default"  # 网络类名称
    ripup_days: bool = False     # 是否允许拆线重布
    stability: int = 50          # 稳定性参数 (0-100)
    max_iterations: int = 100    # 最大迭代次数


class RoutingRule(BaseModel):
    """布线规则"""
    name: str
    description: str
    min_trace_width: float = 0.2  # 最小走线宽度 (mm)
    max_trace_width: float = 2.0   # 最大走线宽度 (mm)
    default_trace_width: float = 0.25  # 默认走线宽度 (mm)
    min_clearance: float = 0.2     # 最小间距 (mm)
    via_diameter: float = 0.8      # 过孔直径 (mm)
    via_drill: float = 0.4        # 过孔钻孔 (mm)
    impedance_controlled: bool = False  # 阻抗控制


# ========== 自动布线路由 ==========


@router.post("/auto-route")
async def auto_route(
    request: AutoRouteRequest,
    manager: KiCadIPCManager = Depends(get_kicad_manager),
):
    """
    执行自动布线
    
    使用KiCad内置的FreeRouting进行自动布线
    """
    try:
        if not manager.is_connected():
            raise HTTPException(status_code=400, detail="KiCad未连接，请先启动KiCad并启用IPC服务器")

        logger.info(f"Starting auto-routing with net_class={request.net_class}")
        
        # 执行自动布线
        result = manager.auto_route(
            net_class=request.net_class,
            ripup_days=request.ripup_days,
            stability=request.stability,
            max_iterations=request.max_iterations,
        )
        
        # 如果布线失败，返回错误信息
        if not result.get("success", False):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "自动布线失败")
            )
        
        return {
            "success": True,
            "message": result.get("message", "Auto-routing completed"),
            "result": result,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in auto-route: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/routing-rules")
async def get_routing_rules(
    manager: KiCadIPCManager = Depends(get_kicad_manager),
):
    """
    获取当前布线路由规则
    """
    # 先检查连接状态
    if not manager.is_connected():
        return {"success": False, "connected": False, "message": "KiCad not connected. Start KiCad with IPC server.", "rules": {}}
    
    try:
        # 尝试获取规则，如果方法不存在则返回默认值
        if hasattr(manager, 'get_routing_rules'):
            rules = manager.get_routing_rules()
            return {"success": True, "connected": True, "rules": rules}
        else:
            # 默认布线规则
            return {"success": True, "connected": True, "rules": {"default": "standard"}}
    except Exception as e:
        logger.error(f"Error getting routing rules: {e}")
        return {"success": False, "connected": True, "message": str(e), "rules": {}}


@router.post("/routing-rules")
async def set_routing_rules(
    rules: RoutingRule,
    manager: KiCadIPCManager = Depends(get_kicad_manager),
):
    """
    设置布线路由规则
    """
    try:
        if not manager.is_connected():
            raise HTTPException(status_code=400, detail="KiCad not connected")

        result = manager.set_routing_rules(
            name=rules.name,
            min_trace_width=rules.min_trace_width,
            max_trace_width=rules.max_trace_width,
            default_trace_width=rules.default_trace_width,
            min_clearance=rules.min_clearance,
            via_diameter=rules.via_diameter,
            via_drill=rules.via_drill,
            impedance_controlled=rules.impedance_controlled,
        )
        
        return {
            "success": True,
            "message": f"Routing rule '{rules.name}' updated",
            "result": result,
        }
    except Exception as e:
        logger.error(f"Error setting routing rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-tracks")
async def clear_all_tracks(
    manager: KiCadIPCManager = Depends(get_kicad_manager),
):
    """
    清除所有走线
    """
    if not manager.is_connected():
        return {"success": False, "connected": False, "message": "KiCad not connected"}
    
    try:
        result = manager.clear_all_tracks()
        return {"success": True, "connected": True, "message": "All tracks cleared", "result": str(result)}
    except Exception as e:
        logger.error(f"Error clearing tracks: {e}")
        return {"success": False, "connected": True, "message": str(e)}


@router.get("/ratsnest")
async def get_ratsnest(
    manager: KiCadIPCManager = Depends(get_kicad_manager),
):
    """
    获取鼠线(未布线连接)信息
    """
    if not manager.is_connected():
        return {"success": False, "connected": False, "message": "KiCad not connected", "ratsnest": []}
    
    try:
        result = manager.get_ratsnest()
        return {"success": True, "connected": True, "ratsnest": result}
    except Exception as e:
        logger.error(f"Error getting ratsnest: {e}")
        return {"success": False, "connected": True, "message": str(e), "ratsnest": []}


@router.post("/show-ratsnest")
async def show_ratsnest(
    show: bool = True,
    manager: KiCadIPCManager = Depends(get_kicad_manager),
):
    """
    显示/隐藏鼠线
    """
    if not manager.is_connected():
        return {"success": False, "connected": False, "message": "KiCad not connected"}
    
    try:
        result = manager.show_ratsnest(show)
        return {"success": True, "connected": True, "message": f"Ratsnest {'shown' if show else 'hidden'}"}
    except Exception as e:
        logger.error(f"Error showing ratsnest: {e}")
        return {"success": False, "connected": True, "message": str(e)}
