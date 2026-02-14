"""
KiCad IPC API 路由
提供 REST API 和 WebSocket 接口给浏览器使用
"""

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
    try:
        if not manager.is_connected():
            raise HTTPException(status_code=400, detail="KiCad not connected")

        result = manager.execute_action(request.action_name, request.params)
        return result
    except Exception as e:
        logger.error(f"Error executing action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    try:
        if not manager.is_connected():
            raise HTTPException(status_code=400, detail="KiCad not connected")

        status = manager.get_board_status()
        items = status.get("items", [])

        # 过滤
        if item_type:
            items = [item for item in items if item.get("type") == item_type]
        if layer:
            items = [item for item in items if item.get("layer") == layer]

        return {"success": True, "count": len(items), "items": items}
    except Exception as e:
        logger.error(f"Error getting items: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/selection")
async def get_selection(manager: KiCadIPCManager = Depends(get_kicad_manager)):
    """获取当前选中的项目"""
    try:
        if not manager.is_connected():
            raise HTTPException(status_code=400, detail="KiCad not connected")

        status = manager.get_board_status()
        return {"success": True, "selection": status.get("selection", [])}
    except Exception as e:
        logger.error(f"Error getting selection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/screenshot")
async def take_screenshot(
    output_path: Optional[str] = None,
    manager: KiCadIPCManager = Depends(get_kicad_manager),
):
    """使用 KiCad CLI 导出截图"""
    try:
        if not output_path:
            import tempfile

            output_path = tempfile.mktemp(suffix=".svg")

        success = manager.get_screenshot_via_cli(output_path)
        if success:
            return {"success": True, "path": output_path, "message": "Screenshot saved"}
        else:
            raise HTTPException(status_code=500, detail="Screenshot failed")
    except Exception as e:
        logger.error(f"Error taking screenshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    try:
        if not manager.is_connected():
            raise HTTPException(status_code=400, detail="KiCad not connected")

        result = manager.get_board_statistics()
        return result
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/select")
async def select_items(
    item_ids: List[str], manager: KiCadIPCManager = Depends(get_kicad_manager)
):
    """选择项目"""
    try:
        if not manager.is_connected():
            raise HTTPException(status_code=400, detail="KiCad not connected")

        result = manager.select_items(item_ids)
        return result
    except Exception as e:
        logger.error(f"Error selecting items: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-selection")
async def clear_selection(manager: KiCadIPCManager = Depends(get_kicad_manager)):
    """清除选择"""
    try:
        if not manager.is_connected():
            raise HTTPException(status_code=400, detail="KiCad not connected")

        result = manager.clear_selection()
        return result
    except Exception as e:
        logger.error(f"Error clearing selection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== WebSocket 实时通信 ==========


class WebSocketManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """广播消息给所有连接"""
        disconnected = []
        for conn in self.active_connections:
            try:
                await conn.send_json(message)
            except:
                disconnected.append(conn)

        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)


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
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)


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
