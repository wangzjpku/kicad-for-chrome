"""
Version History Service

Provides:
- Project snapshot creation (manual and auto-save)
- Revision listing with timestamps and authors
- Revision comparison (diff)
- Rollback to previous revision
- Tagging / branching support (lightweight)

Stores snapshots in SQLite database with JSON file fallback.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass
from threading import local
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Revision:
    """A single project revision."""
    id: str
    project_id: str
    revision_number: int
    author_id: str
    author_name: str
    message: str
    timestamp: float
    tag: Optional[str] = None
    parent_id: Optional[str] = None
    snapshot_size: int = 0
    is_auto_save: bool = False


class VersionService:
    """
    Version history service for PCB projects.

    Stores project snapshots in SQLite database with JSON file fallback.
    """

    def __init__(self, data_dir: Optional[str] = None, use_database: bool = True):
        self._data_dir = data_dir or os.path.join(
            os.path.dirname(__file__), "..", "data", "versions"
        )
        os.makedirs(self._data_dir, exist_ok=True)
        self._revisions: Dict[str, Dict[int, Revision]] = {}
        self._use_database = use_database
        self._db_path = os.path.join(self._data_dir, "versions.db")
        self._local = local()

        if use_database:
            try:
                self._init_database()
                logger.info("VersionService using SQLite database")
            except Exception as e:
                logger.warning(f"Failed to init database, falling back to JSON: {e}")
                self._use_database = False

        if not self._use_database:
            self._load_index()

    # ---- Database Methods ----

    def _get_db_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self._db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_database(self):
        """Initialize SQLite database schema."""
        conn = self._get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS revisions (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                revision_number INTEGER NOT NULL,
                author_id TEXT,
                author_name TEXT,
                message TEXT,
                timestamp REAL NOT NULL,
                tag TEXT,
                parent_id TEXT,
                snapshot_size INTEGER DEFAULT 0,
                is_auto_save INTEGER DEFAULT 0,
                snapshot_json TEXT,
                UNIQUE(project_id, revision_number)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_revisions_project
            ON revisions(project_id, revision_number DESC)
        """)

        conn.commit()

        # Load existing revisions into memory
        cursor.execute("SELECT * FROM revisions ORDER BY project_id, revision_number")
        for row in cursor.fetchall():
            pid = row["project_id"]
            if pid not in self._revisions:
                self._revisions[pid] = {}
            self._revisions[pid][row["revision_number"]] = Revision(
                id=row["id"],
                project_id=pid,
                revision_number=row["revision_number"],
                author_id=row["author_id"] or "",
                author_name=row["author_name"] or "",
                message=row["message"] or "",
                timestamp=row["timestamp"],
                tag=row["tag"],
                parent_id=row["parent_id"],
                snapshot_size=row["snapshot_size"] or 0,
                is_auto_save=bool(row["is_auto_save"]),
            )

        total = sum(len(v) for v in self._revisions.values())
        logger.info(f"Loaded {total} revisions from database")

    def _save_to_database(self, revision: Revision, snapshot_json: str):
        """Save revision to database."""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO revisions
            (id, project_id, revision_number, author_id, author_name, message,
             timestamp, tag, parent_id, snapshot_size, is_auto_save, snapshot_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            revision.id,
            revision.project_id,
            revision.revision_number,
            revision.author_id,
            revision.author_name,
            revision.message,
            revision.timestamp,
            revision.tag,
            revision.parent_id,
            revision.snapshot_size,
            int(revision.is_auto_save),
            snapshot_json,
        ))
        conn.commit()

    def _get_snapshot_from_db(self, project_id: str, revision_number: int) -> Optional[Dict[str, Any]]:
        """Load snapshot from database."""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT snapshot_json FROM revisions WHERE project_id = ? AND revision_number = ?",
            (project_id, revision_number)
        )
        row = cursor.fetchone()
        if row and row["snapshot_json"]:
            try:
                return json.loads(row["snapshot_json"])
            except json.JSONDecodeError:
                return None
        return None

    def _update_revision_in_db(self, project_id: str, revision_number: int, **updates):
        """Update revision fields in database."""
        if not updates:
            return
        conn = self._get_db_connection()
        cursor = conn.cursor()
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [project_id, revision_number]
        cursor.execute(
            f"UPDATE revisions SET {set_clause} WHERE project_id = ? AND revision_number = ?",
            values
        )
        conn.commit()

    def _delete_revision_from_db(self, project_id: str, revision_number: int):
        """Delete revision from database."""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM revisions WHERE project_id = ? AND revision_number = ?",
            (project_id, revision_number)
        )
        conn.commit()

    # ---- JSON Fallback Methods ----

    def _index_file(self) -> str:
        return os.path.join(self._data_dir, "revisions_index.json")

    def _snapshot_file(self, project_id: str, revision_number: int) -> str:
        path = os.path.join(self._data_dir, project_id)
        os.makedirs(path, exist_ok=True)
        return os.path.join(path, f"r{revision_number:06d}.json")

    def _load_index(self):
        """Load revision index from JSON file (fallback mode)."""
        path = self._index_file()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r") as f:
                data = json.load(f)

            for pid, revs in data.items():
                self._revisions[pid] = {}
                for rnum_str, rdata in revs.items():
                    self._revisions[pid][int(rnum_str)] = Revision(
                        id=rdata["id"],
                        project_id=rdata["project_id"],
                        revision_number=rdata["revision_number"],
                        author_id=rdata.get("author_id", ""),
                        author_name=rdata.get("author_name", ""),
                        message=rdata.get("message", ""),
                        timestamp=rdata["timestamp"],
                        tag=rdata.get("tag"),
                        parent_id=rdata.get("parent_id"),
                        snapshot_size=rdata.get("snapshot_size", 0),
                        is_auto_save=rdata.get("is_auto_save", False),
                    )

            total = sum(len(v) for v in self._revisions.values())
            logger.info(f"Loaded {total} revisions from JSON for {len(self._revisions)} projects")
        except Exception as e:
            logger.warning(f"Failed to load revision index: {e}")

    def _save_index(self):
        """Save revision index to JSON file (fallback mode)."""
        path = self._index_file()
        try:
            data = {}
            for pid, revs in self._revisions.items():
                data[pid] = {}
                for rnum, r in revs.items():
                    data[pid][str(rnum)] = {
                        "id": r.id,
                        "project_id": r.project_id,
                        "revision_number": r.revision_number,
                        "author_id": r.author_id,
                        "author_name": r.author_name,
                        "message": r.message,
                        "timestamp": r.timestamp,
                        "tag": r.tag,
                        "parent_id": r.parent_id,
                        "snapshot_size": r.snapshot_size,
                        "is_auto_save": r.is_auto_save,
                    }
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save revision index: {e}")

    # ---- Create Snapshot ----

    def create_snapshot(
        self,
        project_id: str,
        state: Dict[str, Any],
        author_id: str,
        author_name: str,
        message: str = "",
        tag: Optional[str] = None,
        is_auto_save: bool = False,
    ) -> Dict[str, Any]:
        """Create a new version snapshot."""
        if project_id not in self._revisions:
            self._revisions[project_id] = {}

        revs = self._revisions[project_id]
        next_rev = max(revs.keys(), default=0) + 1

        # Find parent (previous revision)
        parent_id = None
        if revs:
            parent_rev = max(revs.keys())
            parent_id = revs[parent_rev].id

        rev_id = str(uuid.uuid4())
        revision = Revision(
            id=rev_id,
            project_id=project_id,
            revision_number=next_rev,
            author_id=author_id,
            author_name=author_name,
            message=message or f"Revision {next_rev}",
            timestamp=time.time(),
            tag=tag,
            parent_id=parent_id,
            is_auto_save=is_auto_save,
        )

        snapshot_json = json.dumps(state, indent=2, default=str)
        revision.snapshot_size = len(snapshot_json)

        if self._use_database:
            self._save_to_database(revision, snapshot_json)
        else:
            # Save to JSON file
            snapshot_path = self._snapshot_file(project_id, next_rev)
            with open(snapshot_path, "w") as f:
                f.write(snapshot_json)
            self._save_index()

        revs[next_rev] = revision

        logger.info(f"Created revision {next_rev} for project {project_id}")
        return {
            "id": rev_id,
            "revision": next_rev,
            "project_id": project_id,
            "timestamp": revision.timestamp,
            "snapshot_size": revision.snapshot_size,
        }

    # ---- Query ----

    def list_revisions(
        self,
        project_id: str,
        limit: int = 50,
        include_auto_saves: bool = True,
    ) -> List[Dict[str, Any]]:
        """List revisions for a project, newest first."""
        revs = self._revisions.get(project_id, {})
        sorted_revs = sorted(revs.values(), key=lambda r: r.revision_number, reverse=True)

        if not include_auto_saves:
            sorted_revs = [r for r in sorted_revs if not r.is_auto_save]

        sorted_revs = sorted_revs[:limit]
        return [
            {
                "id": r.id,
                "revision": r.revision_number,
                "author": r.author_name,
                "message": r.message,
                "timestamp": r.timestamp,
                "tag": r.tag,
                "snapshot_size": r.snapshot_size,
                "is_auto_save": r.is_auto_save,
            }
            for r in sorted_revs
        ]

    def get_snapshot(self, project_id: str, revision: int) -> Optional[Dict[str, Any]]:
        """Load a specific revision's snapshot."""
        if self._use_database:
            return self._get_snapshot_from_db(project_id, revision)
        else:
            path = self._snapshot_file(project_id, revision)
            if not os.path.exists(path):
                return None
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load snapshot: {e}")
                return None

    def get_latest(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest revision number and snapshot."""
        revs = self._revisions.get(project_id, {})
        if not revs:
            return None
        latest_rev = max(revs.keys())
        snapshot = self.get_snapshot(project_id, latest_rev)
        rev_info = revs[latest_rev]
        return {
            "revision": latest_rev,
            "snapshot": snapshot,
            "author": rev_info.author_name,
            "timestamp": rev_info.timestamp,
            "message": rev_info.message,
        }

    # ---- Comparison ----

    def diff(
        self,
        project_id: str,
        from_rev: int,
        to_rev: int,
    ) -> Optional[Dict[str, Any]]:
        """Compare two revisions."""
        from_state = self.get_snapshot(project_id, from_rev)
        to_state = self.get_snapshot(project_id, to_rev)
        if not from_state or not to_state:
            return None

        # Compare components
        from_comps = {c.get("ref", ""): c for c in from_state.get("components", [])}
        to_comps = {c.get("ref", ""): c for c in to_state.get("components", [])}

        added = [ref for ref in to_comps if ref not in from_comps]
        removed = [ref for ref in from_comps if ref not in to_comps]
        modified = []

        for ref in from_comps:
            if ref in to_comps:
                if from_comps[ref] != to_comps[ref]:
                    modified.append({
                        "ref": ref,
                        "from": from_comps[ref],
                        "to": to_comps[ref],
                    })

        # Compare tracks
        from_tracks = len(from_state.get("tracks", []))
        to_tracks = len(to_state.get("tracks", []))

        summary_parts = []
        if added:
            summary_parts.append(f"+{len(added)} components")
        if removed:
            summary_parts.append(f"-{len(removed)} components")
        if modified:
            summary_parts.append(f"~{len(modified)} modified")
        if from_tracks != to_tracks:
            summary_parts.append(f"tracks: {from_tracks} -> {to_tracks}")

        summary = ", ".join(summary_parts) or "No changes"

        return {
            "from_revision": from_rev,
            "to_revision": to_rev,
            "added": added,
            "removed": removed,
            "modified": modified,
            "tracks_changed": to_tracks - from_tracks,
            "summary": summary,
        }

    # ---- Tagging ----

    def tag_revision(
        self,
        project_id: str,
        revision: int,
        tag: str,
    ) -> Dict[str, Any]:
        """Add a tag to a revision."""
        revs = self._revisions.get(project_id, {})
        rev = revs.get(revision)
        if not rev:
            return {"error": "Revision not found"}

        rev.tag = tag

        if self._use_database:
            self._update_revision_in_db(project_id, revision, tag=tag)
        else:
            self._save_index()

        return {"status": "ok", "revision": revision, "tag": tag}

    # ---- Rollback ----

    def rollback(
        self,
        project_id: str,
        target_revision: int,
        author_id: str,
        author_name: str,
    ) -> Dict[str, Any]:
        """Rollback to a previous revision by creating a new revision with target state."""
        snapshot = self.get_snapshot(project_id, target_revision)
        if not snapshot:
            return {"error": "Target revision not found"}

        return self.create_snapshot(
            project_id=project_id,
            state=snapshot,
            author_id=author_id,
            author_name=author_name,
            message=f"Rollback to revision {target_revision}",
            tag=f"rollback-{target_revision}",
        )

    # ---- Cleanup ----

    def delete_old_auto_saves(
        self,
        project_id: str,
        keep: int = 10,
    ) -> int:
        """Delete old auto-save revisions, keeping the latest N."""
        revs = self._revisions.get(project_id, {})
        auto_saves = sorted(
            [r for r in revs.values() if r.is_auto_save],
            key=lambda r: r.revision_number,
        )

        if len(auto_saves) <= keep:
            return 0

        to_delete = auto_saves[:-keep]
        deleted = 0
        for rev in to_delete:
            if self._use_database:
                self._delete_revision_from_db(project_id, rev.revision_number)
            else:
                path = self._snapshot_file(project_id, rev.revision_number)
                if os.path.exists(path):
                    os.remove(path)
            del revs[rev.revision_number]
            deleted += 1

        if not self._use_database:
            self._save_index()

        return deleted


# Singleton
_version_service: Optional[VersionService] = None


def get_version_service() -> VersionService:
    global _version_service
    if _version_service is None:
        _version_service = VersionService()
    return _version_service
