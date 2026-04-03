"""
Project Sharing & Permission Service

Provides:
- Project ACL management (owner/editor/viewer roles)
- Share/unshare projects with users
- Permission checking for API endpoints
- Share link generation for anonymous access
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# ---- Data Models ----

@dataclass
class ProjectPermission:
    """A single user's permission on a project."""
    user_id: str
    project_id: str
    role: str  # owner, editor, viewer
    granted_by: str  # user_id who granted
    granted_at: float = field(default_factory=time.time)


@dataclass
class ShareLink:
    """A shareable link for anonymous access."""
    token: str
    project_id: str
    role: str  # viewer or editor
    created_by: str
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    max_uses: Optional[int] = None
    uses: int = 0
    is_active: bool = True


class SharingService:
    """
    Manages project sharing and permissions.

    Persists ACL data to JSON file.
    """

    def __init__(self, data_dir: Optional[str] = None):
        self._data_dir = data_dir or os.path.join(
            os.path.dirname(__file__), "..", "data"
        )
        os.makedirs(self._data_dir, exist_ok=True)
        self._permissions: Dict[str, Dict[str, ProjectPermission]] = {}
        # project_id -> { user_id -> ProjectPermission }
        self._share_links: Dict[str, ShareLink] = {}
        # token -> ShareLink
        self._load()

    def _acl_file(self) -> str:
        return os.path.join(self._data_dir, "project_acls.json")

    def _load(self):
        path = self._acl_file()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r") as f:
                data = json.load(f)

            for pid, users in data.get("permissions", {}).items():
                self._permissions[pid] = {}
                for uid, pdata in users.items():
                    self._permissions[pid][uid] = ProjectPermission(**pdata)

            for token, sdata in data.get("share_links", {}).items():
                self._share_links[token] = ShareLink(**sdata)

            logger.info(f"Loaded sharing data: {len(self._permissions)} projects")
        except Exception as e:
            logger.warning(f"Failed to load sharing data: {e}")

    def _save(self):
        path = self._acl_file()
        try:
            data = {
                "permissions": {
                    pid: {
                        uid: {
                            "user_id": p.user_id,
                            "project_id": p.project_id,
                            "role": p.role,
                            "granted_by": p.granted_by,
                            "granted_at": p.granted_at,
                        }
                        for uid, p in users.items()
                    }
                    for pid, users in self._permissions.items()
                },
                "share_links": {
                    token: {
                        "token": s.token,
                        "project_id": s.project_id,
                        "role": s.role,
                        "created_by": s.created_by,
                        "created_at": s.created_at,
                        "expires_at": s.expires_at,
                        "max_uses": s.max_uses,
                        "uses": s.uses,
                        "is_active": s.is_active,
                    }
                    for token, s in self._share_links.items()
                },
            }
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save sharing data: {e}")

    # ---- Project Ownership ----

    def create_project(self, project_id: str, owner_id: str) -> Dict[str, Any]:
        """Set up ownership for a new project."""
        if project_id not in self._permissions:
            self._permissions[project_id] = {}

        self._permissions[project_id][owner_id] = ProjectPermission(
            user_id=owner_id,
            project_id=project_id,
            role="owner",
            granted_by=owner_id,
        )
        self._save()
        return {"status": "ok", "project_id": project_id, "owner": owner_id}

    # ---- Sharing ----

    def share_project(
        self,
        project_id: str,
        target_user_id: str,
        role: str,
        granted_by: str,
    ) -> Dict[str, Any]:
        """Share a project with another user."""
        if role not in ("editor", "viewer"):
            return {"error": "Role must be 'editor' or 'viewer'"}

        # Check granter has permission
        granter_role = self.get_user_role(project_id, granted_by)
        if granter_role not in ("owner", "editor"):
            return {"error": "Insufficient permissions to share"}

        if project_id not in self._permissions:
            self._permissions[project_id] = {}

        self._permissions[project_id][target_user_id] = ProjectPermission(
            user_id=target_user_id,
            project_id=project_id,
            role=role,
            granted_by=granted_by,
        )
        self._save()

        logger.info(f"Project {project_id} shared with {target_user_id} as {role}")
        return {
            "status": "ok",
            "project_id": project_id,
            "user_id": target_user_id,
            "role": role,
        }

    def unshare_project(
        self,
        project_id: str,
        target_user_id: str,
        requested_by: str,
    ) -> Dict[str, Any]:
        """Remove a user's access to a project."""
        requester_role = self.get_user_role(project_id, requested_by)
        if requester_role != "owner":
            return {"error": "Only owner can unshare"}

        if project_id not in self._permissions:
            return {"error": "Project not found"}

        if target_user_id not in self._permissions[project_id]:
            return {"error": "User does not have access"}

        target_perm = self._permissions[project_id][target_user_id]
        if target_perm.role == "owner":
            return {"error": "Cannot remove owner"}

        del self._permissions[project_id][target_user_id]
        self._save()
        return {"status": "ok"}

    # ---- Permission Queries ----

    def get_user_role(self, project_id: str, user_id: str) -> Optional[str]:
        """Get a user's role on a project (None = no access)."""
        project_perms = self._permissions.get(project_id, {})
        perm = project_perms.get(user_id)
        return perm.role if perm else None

    def check_permission(
        self,
        project_id: str,
        user_id: str,
        required_role: str,
    ) -> bool:
        """
        Check if user has sufficient permissions.
        Role hierarchy: owner > editor > viewer.
        """
        role_hierarchy = {"viewer": 0, "editor": 1, "owner": 2}
        user_role = self.get_user_role(project_id, user_id)
        if not user_role:
            return False
        return role_hierarchy.get(user_role, 0) >= role_hierarchy.get(required_role, 0)

    def get_project_members(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all members with access to a project."""
        project_perms = self._permissions.get(project_id, {})
        return [
            {
                "user_id": perm.user_id,
                "role": perm.role,
                "granted_by": perm.granted_by,
                "granted_at": perm.granted_at,
            }
            for perm in project_perms.values()
        ]

    def get_user_projects(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all projects a user has access to."""
        results = []
        for project_id, users in self._permissions.items():
            perm = users.get(user_id)
            if perm:
                results.append({
                    "project_id": project_id,
                    "role": perm.role,
                })
        return results

    # ---- Share Links ----

    def create_share_link(
        self,
        project_id: str,
        role: str,
        created_by: str,
        expires_hours: Optional[float] = None,
        max_uses: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a shareable link for anonymous access."""
        if role not in ("viewer", "editor"):
            return {"error": "Link role must be 'viewer' or 'editor'"}

        granter_role = self.get_user_role(project_id, created_by)
        if granter_role not in ("owner", "editor"):
            return {"error": "Insufficient permissions"}

        token = secrets.token_urlsafe(24)
        link = ShareLink(
            token=token,
            project_id=project_id,
            role=role,
            created_by=created_by,
            expires_at=time.time() + expires_hours * 3600 if expires_hours else None,
            max_uses=max_uses,
        )
        self._share_links[token] = link
        self._save()

        return {
            "share_link": f"/shared/{token}",
            "token": token,
            "role": role,
            "expires_at": link.expires_at,
        }

    def verify_share_link(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and consume a share link."""
        link = self._share_links.get(token)
        if not link or not link.is_active:
            return None

        if link.expires_at and link.expires_at < time.time():
            link.is_active = False
            self._save()
            return None

        if link.max_uses and link.uses >= link.max_uses:
            link.is_active = False
            self._save()
            return None

        link.uses += 1
        self._save()

        return {
            "project_id": link.project_id,
            "role": link.role,
            "share_token": token,
        }

    def revoke_share_link(self, token: str, requested_by: str) -> Dict[str, Any]:
        """Revoke a share link."""
        link = self._share_links.get(token)
        if not link:
            return {"error": "Share link not found"}

        granter_role = self.get_user_role(link.project_id, requested_by)
        if granter_role not in ("owner", "editor"):
            return {"error": "Insufficient permissions"}

        link.is_active = False
        self._save()
        return {"status": "ok"}

    def delete_project(self, project_id: str) -> None:
        """Remove all permissions for a deleted project."""
        self._permissions.pop(project_id, None)
        # Remove related share links
        to_remove = [
            token for token, link in self._share_links.items()
            if link.project_id == project_id
        ]
        for token in to_remove:
            del self._share_links[token]
        self._save()


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_sharing_service: Optional[SharingService] = None


def get_sharing_service() -> SharingService:
    global _sharing_service
    if _sharing_service is None:
        _sharing_service = SharingService()
    return _sharing_service
