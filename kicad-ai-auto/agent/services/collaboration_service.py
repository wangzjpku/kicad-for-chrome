"""
Real-time Collaboration Service

Provides:
- Multi-user WebSocket sessions per project
- Cursor/selection presence broadcasting
- Change broadcast with operational transform hints
- Conflict resolution (last-write-wins with revision tracking)
- User session management
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class Cursor:
    """A user's cursor position in the PCB canvas."""
    x: float
    y: float
    zoom: float = 1.0


@dataclass
class Selection:
    """A user's current selection state."""
    item_ids: List[str] = field(default_factory=list)
    bbox: Optional[Dict[str, float]] = None


@dataclass
class UserSession:
    """An active user session in a project room."""
    session_id: str
    user_id: str
    username: str
    project_id: str
    websocket: Optional[WebSocket] = None
    cursor: Optional[Cursor] = None
    selection: Optional[Selection] = None
    color: str = "#4CAF50"
    joined_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)


@dataclass
class ProjectRevision:
    """A revision of project state."""
    revision: int
    user_id: str
    timestamp: float
    changes: List[Dict[str, Any]]
    checksum: str = ""


class CollaborationRoom:
    """Manages a single project's collaboration session."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.sessions: Dict[str, UserSession] = {}
        self.revision = 0
        self.history: List[ProjectRevision] = []
        self.max_history = 100
        self._lock = asyncio.Lock()

    async def join(self, session: UserSession):
        async with self._lock:
            self.sessions[session.session_id] = session
            logger.info(f"User {session.username} joined room {self.project_id}")

    async def leave(self, session_id: str):
        async with self._lock:
            session = self.sessions.pop(session_id, None)
            if session:
                logger.info(f"User {session.username} left room {self.project_id}")

    async def update_cursor(self, session_id: str, cursor: Cursor):
        async with self._lock:
            session = self.sessions.get(session_id)
            if session:
                session.cursor = cursor
                session.last_active = time.time()

    async def update_selection(self, session_id: str, selection: Selection):
        async with self._lock:
            session = self.sessions.get(session_id)
            if session:
                session.selection = selection
                session.last_active = time.time()

    async def commit_changes(
        self,
        session_id: str,
        changes: List[Dict[str, Any]],
    ) -> int:
        """Commit changes and increment revision."""
        async with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return -1

            self.revision += 1
            revision = ProjectRevision(
                revision=self.revision,
                user_id=session.user_id,
                timestamp=time.time(),
                changes=changes,
            )
            self.history.append(revision)
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history:]
            return self.revision

    def get_presence(self) -> List[Dict[str, Any]]:
        """Get presence data for all active users."""
        now = time.time()
        presence = []
        for session in self.sessions.values():
            if now - session.last_active > 300:  # 5min timeout
                continue
            p: Dict[str, Any] = {
                "user_id": session.user_id,
                "username": session.username,
                "color": session.color,
                "joined_at": session.joined_at,
            }
            if session.cursor:
                p["cursor"] = {
                    "x": session.cursor.x,
                    "y": session.cursor.y,
                    "zoom": session.cursor.zoom,
                }
            if session.selection and session.selection.item_ids:
                p["selection"] = session.selection.item_ids
            presence.append(p)
        return presence

    def get_history(self, since_revision: int = 0) -> List[Dict[str, Any]]:
        """Get changes since a given revision."""
        return [
            {
                "revision": rev.revision,
                "user_id": rev.user_id,
                "timestamp": rev.timestamp,
                "changes": rev.changes,
            }
            for rev in self.history
            if rev.revision > since_revision
        ]

    @property
    def user_count(self) -> int:
        now = time.time()
        return sum(
            1 for s in self.sessions.values()
            if now - s.last_active < 300
        )


class CollaborationService:
    """
    Manages all collaboration rooms and WebSocket connections.
    """

    # User colors for presence indicators
    COLORS = [
        "#4CAF50", "#2196F3", "#FF9800", "#E91E63",
        "#9C27B0", "#00BCD4", "#FF5722", "#607D8B",
        "#795548", "#3F51B5", "#009688", "#CDDC39",
    ]

    def __init__(self):
        self.rooms: Dict[str, CollaborationRoom] = {}
        self._color_index = 0

    def _next_color(self) -> str:
        color = self.COLORS[self._color_index % len(self.COLORS)]
        self._color_index += 1
        return color

    def get_or_create_room(self, project_id: str) -> CollaborationRoom:
        if project_id not in self.rooms:
            self.rooms[project_id] = CollaborationRoom(project_id)
        return self.rooms[project_id]

    async def join_room(
        self,
        project_id: str,
        user_id: str,
        username: str,
        websocket: WebSocket,
    ) -> str:
        """Join a collaboration room. Returns session_id."""
        room = self.get_or_create_room(project_id)
        session_id = str(uuid.uuid4())
        session = UserSession(
            session_id=session_id,
            user_id=user_id,
            username=username,
            project_id=project_id,
            websocket=websocket,
            color=self._next_color(),
        )
        await room.join(session)

        # Notify others
        await self._broadcast(room, {
            "type": "user_joined",
            "user_id": user_id,
            "username": username,
            "color": session.color,
        }, exclude=session_id)

        return session_id

    async def leave_room(self, project_id: str, session_id: str):
        room = self.rooms.get(project_id)
        if not room:
            return

        session = room.sessions.get(session_id)
        user_id = session.user_id if session else ""
        username = session.username if session else ""

        await room.leave(session_id)

        # Notify others
        await self._broadcast(room, {
            "type": "user_left",
            "user_id": user_id,
            "username": username,
        })

        # Clean up empty rooms
        if not room.sessions:
            self.rooms.pop(project_id, None)

    async def handle_message(
        self,
        project_id: str,
        session_id: str,
        message: Dict[str, Any],
    ):
        """Process an incoming WebSocket message."""
        room = self.rooms.get(project_id)
        if not room:
            return

        msg_type = message.get("type", "")

        if msg_type == "cursor_move":
            cursor_data = message.get("cursor", {})
            cursor = Cursor(
                x=cursor_data.get("x", 0),
                y=cursor_data.get("y", 0),
                zoom=cursor_data.get("zoom", 1.0),
            )
            await room.update_cursor(session_id, cursor)

            session = room.sessions.get(session_id)
            if session:
                await self._broadcast(room, {
                    "type": "cursor_update",
                    "user_id": session.user_id,
                    "cursor": {"x": cursor.x, "y": cursor.y, "zoom": cursor.zoom},
                }, exclude=session_id)

        elif msg_type == "selection_change":
            sel_data = message.get("selection", {})
            selection = Selection(
                item_ids=sel_data.get("items", []),
            )
            await room.update_selection(session_id, selection)

            session = room.sessions.get(session_id)
            if session:
                await self._broadcast(room, {
                    "type": "selection_update",
                    "user_id": session.user_id,
                    "items": selection.item_ids,
                }, exclude=session_id)

        elif msg_type == "changes":
            changes = message.get("changes", [])
            rev = await room.commit_changes(session_id, changes)

            session = room.sessions.get(session_id)
            if session and rev >= 0:
                await self._broadcast(room, {
                    "type": "changes_applied",
                    "user_id": session.user_id,
                    "username": session.username,
                    "revision": rev,
                    "changes": changes,
                }, exclude=session_id)

        elif msg_type == "sync_request":
            since = message.get("since_revision", 0)
            session = room.sessions.get(session_id)
            if session and session.websocket:
                history = room.get_history(since)
                await self._send(session.websocket, {
                    "type": "sync_response",
                    "revision": room.revision,
                    "history": history,
                    "presence": room.get_presence(),
                })

    async def _broadcast(
        self,
        room: CollaborationRoom,
        message: Dict[str, Any],
        exclude: Optional[str] = None,
    ):
        """Send message to all sessions in room except excluded one."""
        dead_sessions = []
        for sid, session in room.sessions.items():
            if sid == exclude:
                continue
            if session.websocket:
                try:
                    await self._send(session.websocket, message)
                except Exception as e:
                    logger.warning(f"Room cleanup failed: {e}")
                    dead_sessions.append(sid)

        for sid in dead_sessions:
            await room.leave(sid)

    async def _send(self, ws: WebSocket, message: Dict[str, Any]):
        """Send a JSON message to a WebSocket."""
        try:
            await ws.send_json(message)
        except Exception as e:
            logger.debug(f"WebSocket send failed: {e}")

    def get_room_info(self, project_id: str) -> Optional[Dict[str, Any]]:
        room = self.rooms.get(project_id)
        if not room:
            return None
        return {
            "project_id": project_id,
            "user_count": room.user_count,
            "presence": room.get_presence(),
            "revision": room.revision,
        }

    def get_all_rooms(self) -> List[Dict[str, Any]]:
        return [
            {
                "project_id": pid,
                "user_count": room.user_count,
            }
            for pid, room in self.rooms.items()
        ]


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_collab_service: Optional[CollaborationService] = None


def get_collaboration_service() -> CollaborationService:
    global _collab_service
    if _collab_service is None:
        _collab_service = CollaborationService()
    return _collab_service
