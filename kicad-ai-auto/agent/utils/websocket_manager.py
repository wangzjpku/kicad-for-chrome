"""
WebSocket连接管理器 - 共享模块
"""

import asyncio
import logging
from typing import List
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """WebSocket连接管理器 - 线程安全版本"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        """接受新的WebSocket连接"""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
                logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def send_message(self, message: dict, websocket: WebSocket = None):
        """发送消息到指定连接或所有连接"""
        if websocket:
            # 发送到指定连接
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
        else:
            # 广播到所有连接
            disconnected = []
            async with self._lock:
                for connection in self.active_connections:
                    try:
                        await connection.send_json(message)
                    except Exception as e:
                        logger.error(f"Failed to broadcast: {e}")
                        disconnected.append(connection)

                # 清理断开的连接
                for conn in disconnected:
                    if conn in self.active_connections:
                        self.active_connections.remove(conn)

    async def broadcast(self, message: dict):
        """广播消息到所有连接"""
        await self.send_message(message, None)

    def get_connection_count(self) -> int:
        """获取当前连接数"""
        return len(self.active_connections)
