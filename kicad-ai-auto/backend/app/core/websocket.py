"""
WebSocket 管理器
处理实时通信
"""

from fastapi import WebSocket
from typing import List, Dict
import logging
import json

logger = logging.getLogger(__name__)


class WebSocketManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # 存储活跃的 WebSocket 连接
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """接受新的 WebSocket 连接"""
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
        self.active_connections[client_id].append(websocket)
        logger.info(
            f"Client {client_id} connected. Total connections: {len(self.active_connections[client_id])}"
        )

    def disconnect(self, websocket: WebSocket, client_id: str):
        """断开 WebSocket 连接"""
        if client_id in self.active_connections:
            if websocket in self.active_connections[client_id]:
                self.active_connections[client_id].remove(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
        logger.info(f"Client {client_id} disconnected")

    async def send_message(self, message: dict, websocket: WebSocket):
        """发送消息给特定客户端"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")

    async def broadcast(self, message: dict, client_id: str = None):
        """广播消息给所有或特定客户端"""
        if client_id:
            # 发送给特定客户端的所有连接
            if client_id in self.active_connections:
                for connection in self.active_connections[client_id]:
                    try:
                        await connection.send_json(message)
                    except Exception as e:
                        logger.error(f"Error broadcasting to {client_id}: {e}")
        else:
            # 广播给所有客户端
            for client_id, connections in self.active_connections.items():
                for connection in connections:
                    try:
                        await connection.send_json(message)
                    except Exception as e:
                        logger.error(f"Error broadcasting: {e}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """发送个人消息"""
        await websocket.send_text(message)


# 全局 WebSocket 管理器实例
ws_manager = WebSocketManager()
