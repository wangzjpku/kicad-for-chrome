"""
Phase 12B-2: Project Sharing API Routes

REST endpoints for managing project access:
- POST /projects/{id}/share - Share project with user
- DELETE /projects/{id}/share/{user_id} - Revoke access
- GET /projects/{id}/members - List project members
- GET /my/projects - List user's accessible projects
- POST /share-links - Create shareable link
- GET /shared/{token} - Access via share link
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from services.sharing_service import get_sharing_service
from routes.auth_v2_routes import get_current_user

router = APIRouter(prefix="/api/v1", tags=["sharing"])


# ---- Models ----

class ShareRequest(BaseModel):
    user_id: str
    role: str  # editor or viewer

class ShareLinkRequest(BaseModel):
    project_id: str
    role: str = "viewer"
    expires_hours: Optional[float] = None
    max_uses: Optional[int] = None


# ---- Endpoints ----

@router.post("/projects/{project_id}/share", summary="Share project with a user")
async def share_project(
    project_id: str,
    req: ShareRequest,
    user: dict = Depends(get_current_user),
):
    svc = get_sharing_service()
    result = svc.share_project(
        project_id=project_id,
        target_user_id=req.user_id,
        role=req.role,
        granted_by=user["user_id"],
    )
    if "error" in result:
        raise HTTPException(status_code=403, detail=result["error"])
    return result


@router.delete("/projects/{project_id}/share/{target_user_id}", summary="Revoke user access")
async def unshare_project(
    project_id: str,
    target_user_id: str,
    user: dict = Depends(get_current_user),
):
    svc = get_sharing_service()
    result = svc.unshare_project(
        project_id=project_id,
        target_user_id=target_user_id,
        requested_by=user["user_id"],
    )
    if "error" in result:
        raise HTTPException(status_code=403, detail=result["error"])
    return result


@router.get("/projects/{project_id}/members", summary="List project members")
async def list_members(
    project_id: str,
    user: dict = Depends(get_current_user),
):
    svc = get_sharing_service()
    # Check user has access
    role = svc.get_user_role(project_id, user["user_id"])
    if not role:
        raise HTTPException(status_code=403, detail="No access to project")
    return {"members": svc.get_project_members(project_id)}


@router.get("/my/projects", summary="List projects accessible to current user")
async def my_projects(user: dict = Depends(get_current_user)):
    svc = get_sharing_service()
    projects = svc.get_user_projects(user["user_id"])
    return {"projects": projects}


@router.post("/share-links", summary="Create shareable link")
async def create_share_link(
    req: ShareLinkRequest,
    user: dict = Depends(get_current_user),
):
    svc = get_sharing_service()
    result = svc.create_share_link(
        project_id=req.project_id,
        role=req.role,
        created_by=user["user_id"],
        expires_hours=req.expires_hours,
        max_uses=req.max_uses,
    )
    if "error" in result:
        raise HTTPException(status_code=403, detail=result["error"])
    return result


@router.get("/shared/{token}", summary="Access project via share link")
async def access_shared(token: str):
    svc = get_sharing_service()
    result = svc.verify_share_link(token)
    if not result:
        raise HTTPException(status_code=404, detail="Invalid or expired share link")
    return result


@router.delete("/share-links/{token}", summary="Revoke share link")
async def revoke_share_link(
    token: str,
    user: dict = Depends(get_current_user),
):
    svc = get_sharing_service()
    result = svc.revoke_share_link(token, requested_by=user["user_id"])
    if "error" in result:
        raise HTTPException(status_code=403, detail=result["error"])
    return result
