"""
数据库模块 - 支持 SQLite 存储
可选的持久化方案，比 JSON 更可靠
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# 数据库文件路径
DB_PATH = Path(__file__).parent.parent / "data" / "kicad_ai.db"


class Database:
    """SQLite 数据库管理"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self._ensure_db_dir()
        self._init_tables()

    def _ensure_db_dir(self):
        """确保数据库目录存在"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _init_tables(self):
        """初始化数据表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 项目表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT,
                updated_at TEXT,
                schematic_file TEXT,
                pcb_file TEXT
            )
        """)

        # PCB 数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pcb_data (
                project_id TEXT PRIMARY KEY,
                data TEXT,
                updated_at TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)

        # 原理图数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schematic_data (
                project_id TEXT PRIMARY KEY,
                data TEXT,
                updated_at TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)

        conn.commit()
        conn.close()
        logger.info(f"Database initialized: {self.db_path}")

    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)

    # ========== 项目操作 ==========

    def create_project(self, project: Dict[str, Any]) -> bool:
        """创建项目"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO projects (id, name, description, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    project.get("id"),
                    project.get("name"),
                    project.get("description", ""),
                    project.get("status", "active"),
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                )
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            return False

    def get_project(self, project_id: str) -> Optional[Dict]:
        """获取项目"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "status": row[3],
                    "createdAt": row[4],
                    "updatedAt": row[5],
                    "schematicFile": row[6],
                    "pcbFile": row[7],
                }
        except Exception as e:
            logger.error(f"Failed to get project: {e}")
        return None

    def list_projects(self, search: str = None) -> List[Dict]:
        """列出项目"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            if search:
                cursor.execute(
                    "SELECT * FROM projects WHERE name LIKE ? ORDER BY updated_at DESC",
                    (f"%{search}%",)
                )
            else:
                cursor.execute("SELECT * FROM projects ORDER BY updated_at DESC")

            rows = cursor.fetchall()
            conn.close()

            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "status": row[3],
                    "createdAt": row[4],
                    "updatedAt": row[5],
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Failed to list projects: {e}")
            return []

    def update_project(self, project_id: str, data: Dict) -> bool:
        """更新项目"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            fields = []
            values = []
            for key, value in data.items():
                fields.append(f"{key} = ?")
                values.append(value)

            fields.append("updated_at = ?")
            values.append(datetime.now().isoformat())
            values.append(project_id)

            cursor.execute(
                f"UPDATE projects SET {', '.join(fields)} WHERE id = ?",
                values
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to update project: {e}")
            return False

    def delete_project(self, project_id: str) -> bool:
        """删除项目"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            cursor.execute("DELETE FROM pcb_data WHERE project_id = ?", (project_id,))
            cursor.execute("DELETE FROM schematic_data WHERE project_id = ?", (project_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to delete project: {e}")
            return False

    # ========== PCB 数据操作 ==========

    def save_pcb_data(self, project_id: str, data: Dict) -> bool:
        """保存 PCB 数据"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """INSERT OR REPLACE INTO pcb_data (project_id, data, updated_at)
                   VALUES (?, ?, ?)""",
                (project_id, json.dumps(data), datetime.now().isoformat())
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to save PCB data: {e}")
            return False

    def get_pcb_data(self, project_id: str) -> Optional[Dict]:
        """获取 PCB 数据"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT data FROM pcb_data WHERE project_id = ?",
                (project_id,)
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                return json.loads(row[0])
        except Exception as e:
            logger.error(f"Failed to get PCB data: {e}")
        return None

    # ========== 原理图数据操作 ==========

    def save_schematic_data(self, project_id: str, data: Dict) -> bool:
        """保存原理图数据"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """INSERT OR REPLACE INTO schematic_data (project_id, data, updated_at)
                   VALUES (?, ?, ?)""",
                (project_id, json.dumps(data), datetime.now().isoformat())
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to save schematic data: {e}")
            return False

    def get_schematic_data(self, project_id: str) -> Optional[Dict]:
        """获取原理图数据"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT data FROM schematic_data WHERE project_id = ?",
                (project_id,)
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                return json.loads(row[0])
        except Exception as e:
            logger.error(f"Failed to get schematic data: {e}")
        return None


# 全局数据库实例
_db: Optional[Database] = None


def get_database() -> Database:
    """获取数据库实例"""
    global _db
    if _db is None:
        _db = Database()
    return _db


# 使用示例：
# from database import get_database
#
# db = get_database()
# db.create_project({"id": "123", "name": "Test"})
# projects = db.list_projects()
# db.save_pcb_data("123", {"footprints": [...]})
