"""
Phase 12B-3: Real-time Collaboration WebSocket Routes

WebSocket endpoint for real-time PCB collaboration:
- WS /api/v1/collab/{project_id} - Join project room
- GET /api/v1/collab/{project_id}/info - Room status
- GET /api/v1/collab/rooms - All active rooms
"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query

from services.collaboration_service import get_collaboration_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/collab", tags=["collaboration"])


@router.websocket("/{project_id}")
async def collaboration_websocket(
    websocket: WebSocket,
    project_id: str,
    user_id: str = Query(...),
    username: str = Query("anonymous"),
):
    """
    WebSocket endpoint for real-time collaboration.

    Query params:
    - user_id: User ID (from JWT)
    - username: Display name

    Message types (client → server):
    - cursor_move: { type: "cursor_move", cursor: { x, y, zoom } }
    - selection_change: { type: "selection_change", selection: { items: [...] } }
    - changes: { type: "changes", changes: [...] }
    - sync_request: { type: "sync_request", since_revision: N }

    Message types (server → client):
    - user_joined: { type, user_id, username, color }
    - user_left: { type, user_id, username }
    - cursor_update: { type, user_id, cursor: { x, y, zoom } }
    - selection_update: { type, user_id, items: [...] }
    - changes_applied: { type, user_id, revision, changes }
    - sync_response: { type, revision, history, presence }
    """
    collab = get_collaboration_service()

    await websocket.accept()
    session_id = await collab.join_room(
        project_id=project_id,
        user_id=user_id,
        username=username,
        websocket=websocket,
    )

    # Send initial state
    room_info = collab.get_room_info(project_id)
    if room_info:
        await websocket.send_json({
            "type": "room_state",
            "project_id": project_id,
            "presence": room_info["presence"],
            "revision": room_info["revision"],
            "session_id": session_id,
        })

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
                await collab.handle_message(project_id, session_id, message)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from session {session_id}")
            except Exception as e:
                logger.error(f"Error handling message: {e}")

    except WebSocketDisconnect:
        await collab.leave_room(project_id, session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await collab.leave_room(project_id, session_id)


@router.get("/{project_id}/info", summary="Get room info")
async def room_info(project_id: str):
    collab = get_collaboration_service()
    info = collab.get_room_info(project_id)
    if not info:
        return {"active": False, "project_id": project_id, "user_count": 0}
    return {"active": True, **info}


@router.get("/rooms", summary="List active collaboration rooms")
async def list_rooms():
    collab = get_collaboration_service()
    return {"rooms": collab.get_all_rooms()}
