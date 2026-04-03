# -*- coding: utf-8 -*-
"""
Project Snapshot Model - 项目快照模型

支持:
- 创建项目快照
- 列出项目快照
- 恢复快照
- 快照对比
"""

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

# 数据库路径
DATA_DIR = Path(__file__).parent.parent / "data"
SNAPSHOTS_DB = DATA_DIR / "snapshots.db"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"


@dataclass
class ProjectSnapshot:
    """项目快照"""
    id: str
    project_id: str
    version: int
    title: str
    description: str = ""
    schematic_data: str = ""  # JSON string
    pcb_data: str = ""       # JSON string
    created_at: str = ""
    created_by: int = 1      # user_id

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "version": self.version,
            "title": self.title,
            "description": self.description,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "has_schematic": bool(self.schematic_data),
            "has_pcb": bool(self.pcb_data),
        }

    def get_schematic_data(self) -> Optional[Dict[str, Any]]:
        """获取原理图数据"""
        if self.schematic_data:
            try:
                return json.loads(self.schematic_data)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    def get_pcb_data(self) -> Optional[Dict[str, Any]]:
        """获取PCB数据"""
        if self.pcb_data:
            try:
                return json.loads(self.pcb_data)
            except (json.JSONDecodeError, TypeError):
                return None
        return None


class SnapshotDB:
    """快照数据库管理器"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(SNAPSHOTS_DB)
        self._ensure_db()

    def _ensure_db(self):
        """确保数据库和表存在"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                schematic_data TEXT DEFAULT '',
                pcb_data TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                created_by INTEGER DEFAULT 1
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_snapshots_project_id
            ON snapshots(project_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_snapshots_created_at
            ON snapshots(created_at)
        """)
        conn.commit()
        conn.close()

    def _row_to_snapshot(self, row: tuple) -> ProjectSnapshot:
        """将数据库行转换为 ProjectSnapshot 对象"""
        return ProjectSnapshot(
            id=row[0],
            project_id=row[1],
            version=row[2],
            title=row[3],
            description=row[4] or "",
            schematic_data=row[5] or "",
            pcb_data=row[6] or "",
            created_at=row[7],
            created_by=row[8] or 1,
        )

    def create_snapshot(
        self,
        project_id: str,
        title: str,
        schematic_data: Dict[str, Any] = None,
        pcb_data: Dict[str, Any] = None,
        description: str = "",
        created_by: int = 1,
    ) -> Optional[ProjectSnapshot]:
        """创建快照"""
        try:
            # 获取下一个版本号
            version = self._get_next_version(project_id)

            # 生成快照ID
            import uuid
            snapshot_id = str(uuid.uuid4())

            # 序列化数据
            schematic_str = json.dumps(schematic_data, ensure_ascii=False) if schematic_data else ""
            pcb_str = json.dumps(pcb_data, ensure_ascii=False) if pcb_data else ""

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO snapshots
                (id, project_id, version, title, description, schematic_data, pcb_data, created_at, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot_id,
                project_id,
                version,
                title,
                description,
                schematic_str,
                pcb_str,
                datetime.now().isoformat(),
                created_by,
            ))
            conn.commit()
            conn.close()

            return ProjectSnapshot(
                id=snapshot_id,
                project_id=project_id,
                version=version,
                title=title,
                description=description,
                schematic_data=schematic_str,
                pcb_data=pcb_str,
                created_at=datetime.now().isoformat(),
                created_by=created_by,
            )
        except Exception as e:
            logger.error(f"创建快照失败: {e}")
            return None

    def _get_next_version(self, project_id: str) -> int:
        """获取下一个版本号"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT MAX(version) FROM snapshots WHERE project_id = ?",
                (project_id,)
            )
            row = cursor.fetchone()
            conn.close()
            return (row[0] or 0) + 1
        except Exception as e:
            logger.warning(f"获取版本号失败: {e}")
            return 1

    def get_snapshot(self, snapshot_id: str) -> Optional[ProjectSnapshot]:
        """获取快照"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, project_id, version, title, description, schematic_data, pcb_data, created_at, created_by
                FROM snapshots WHERE id = ?
            """, (snapshot_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                return self._row_to_snapshot(row)
            return None
        except Exception as e:
            logger.error(f"获取快照失败: {e}")
            return None

    def list_snapshots(
        self,
        project_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> List[ProjectSnapshot]:
        """列出项目的所有快照"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, project_id, version, title, description, schematic_data, pcb_data, created_at, created_by
                FROM snapshots
                WHERE project_id = ?
                ORDER BY version DESC
                LIMIT ? OFFSET ?
            """, (project_id, limit, offset))
            rows = cursor.fetchall()
            conn.close()
            return [self._row_to_snapshot(row) for row in rows]
        except Exception as e:
            logger.error(f"列出快照失败: {e}")
            return []

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """删除快照"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM snapshots WHERE id = ?", (snapshot_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"删除快照失败: {e}")
            return False

    def get_snapshot_count(self, project_id: str) -> int:
        """获取快照数量"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM snapshots WHERE project_id = ?",
                (project_id,)
            )
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else 0
        except Exception as e:
            logger.error(f"获取快照数量失败: {e}")
            return 0


# 全局数据库实例
_db: Optional[SnapshotDB] = None


def get_snapshot_db() -> SnapshotDB:
    """获取全局快照数据库实例"""
    global _db
    if _db is None:
        _db = SnapshotDB()
    return _db
