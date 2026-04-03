"""
Phase 12B-4: Version History API Routes

REST endpoints for project version management:
- POST /projects/{id}/snapshot - Create snapshot
- GET /projects/{id}/revisions - List revisions
- GET /projects/{id}/revisions/{rev} - Get specific revision
- GET /projects/{id}/diff?from=X&to=Y - Compare revisions
- POST /projects/{id}/rollback - Rollback to revision
- POST /projects/{id}/tag - Tag a revision
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from services.version_service import get_version_service
from routes.auth_v2_routes import get_current_user

router = APIRouter(prefix="/api/v1", tags=["version-history"])


# ---- Models ----

class SnapshotRequest(BaseModel):
    state: Dict[str, Any]
    message: str = ""
    tag: Optional[str] = None
    is_auto_save: bool = False

class RollbackRequest(BaseModel):
    target_revision: int

class TagRequest(BaseModel):
    revision: int
    tag: str


# ---- Endpoints ----

@router.post("/projects/{project_id}/snapshot", summary="Create project snapshot")
async def create_snapshot(
    project_id: str,
    req: SnapshotRequest,
    user: dict = Depends(get_current_user),
):
    svc = get_version_service()
    result = svc.create_snapshot(
        project_id=project_id,
        state=req.state,
        author_id=user["user_id"],
        author_name=user.get("username", "unknown"),
        message=req.message,
        tag=req.tag,
        is_auto_save=req.is_auto_save,
    )
    return result


@router.get("/projects/{project_id}/revisions", summary="List project revisions")
async def list_revisions(
    project_id: str,
    limit: int = Query(50, ge=1, le=200),
    include_auto_saves: bool = Query(True),
    user: dict = Depends(get_current_user),
):
    svc = get_version_service()
    revisions = svc.list_revisions(project_id, limit, include_auto_saves)
    return {"revisions": revisions}


@router.get("/projects/{project_id}/revisions/{revision}", summary="Get revision snapshot")
async def get_revision(
    project_id: str,
    revision: int,
    user: dict = Depends(get_current_user),
):
    svc = get_version_service()
    snapshot = svc.get_snapshot(project_id, revision)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Revision not found")
    return {"revision": revision, "snapshot": snapshot}


@router.get("/projects/{project_id}/latest", summary="Get latest revision")
async def get_latest(
    project_id: str,
    user: dict = Depends(get_current_user),
):
    svc = get_version_service()
    result = svc.get_latest(project_id)
    if not result:
        raise HTTPException(status_code=404, detail="No revisions found")
    return result


@router.get("/projects/{project_id}/diff", summary="Compare two revisions")
async def diff_revisions(
    project_id: str,
    from_rev: int = Query(...),
    to_rev: int = Query(...),
    user: dict = Depends(get_current_user),
):
    svc = get_version_service()
    result = svc.diff(project_id, from_rev, to_rev)
    if not result:
        raise HTTPException(status_code=404, detail="One or both revisions not found")
    return result


@router.post("/projects/{project_id}/rollback", summary="Rollback to a revision")
async def rollback(
    project_id: str,
    req: RollbackRequest,
    user: dict = Depends(get_current_user),
):
    svc = get_version_service()
    result = svc.rollback(
        project_id=project_id,
        target_revision=req.target_revision,
        author_id=user["user_id"],
        author_name=user.get("username", "unknown"),
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/projects/{project_id}/tag", summary="Tag a revision")
async def tag_revision(
    project_id: str,
    req: TagRequest,
    user: dict = Depends(get_current_user),
):
    svc = get_version_service()
    result = svc.tag_revision(project_id, req.revision, req.tag)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
