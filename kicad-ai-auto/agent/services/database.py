"""
SQLite Database Service

Provides unified SQLite persistence for:
- User data (auth_service)
- Version snapshots (version_service)
- Marketplace templates (marketplace_service)

Usage:
    from services.database import db

    # User operations
    db.create_user(user_id, username, email, password_hash, role)
    user = db.get_user(user_id)
    db.update_user(user_id, {"last_login": time.time()})

    # Version operations
    db.create_snapshot(project_id, snapshot_id, data, label)
    snapshots = db.get_snapshots(project_id)

    # Template operations
    template = db.get_template(template_id)
    db.update_template_stats(template_id, download_count, rating)
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, fields, is_dataclass
from typing import Any, Dict, List, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar('T')


class DatabaseService:
    """
    Thread-safe SQLite database service with connection pooling.

    Features:
    - Automatic schema migration
    - Thread-safe connection handling
    - Context manager for transactions
    - Generic CRUD operations
    """

    _instance: Optional['DatabaseService'] = None
    _lock = threading.Lock()

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file.
                          Defaults to data/kicad_ai.db
        """
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            data_dir = os.path.join(base_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "kicad_ai.db")

        self._db_path = db_path
        self._local = threading.local()
        self._initialize_schema()
        logger.info(f"DatabaseService initialized: {db_path}")

    @classmethod
    def get_instance(cls) -> 'DatabaseService':
        """Get singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(self._db_path)
            self._local.conn.row_factory = sqlite3.Row
            # Enable foreign keys
            self._local.conn.execute("PRAGMA foreign_keys = ON")
        return self._local.conn

    @contextmanager
    def _transaction(self):
        """Context manager for database transactions."""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _initialize_schema(self):
        """Create database tables if they don't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'editor',
                is_active INTEGER DEFAULT 1,
                created_at REAL NOT NULL,
                last_login REAL,
                projects_json TEXT DEFAULT '[]'
            )
        """)

        # Refresh tokens table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                jti TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Project snapshots table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_snapshots (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                label TEXT,
                data_json TEXT NOT NULL,
                created_at REAL NOT NULL,
                parent_id TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)

        # Marketplace templates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS marketplace_templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT NOT NULL,
                author_id TEXT,
                author_name TEXT,
                schematic_json TEXT,
                pcb_json TEXT,
                tags_json TEXT DEFAULT '[]',
                downloads INTEGER DEFAULT 0,
                rating_sum INTEGER DEFAULT 0,
                rating_count INTEGER DEFAULT 0,
                is_featured INTEGER DEFAULT 0,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)

        # Template ratings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS template_ratings (
                id TEXT PRIMARY KEY,
                template_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
                created_at REAL NOT NULL,
                UNIQUE(template_id, user_id),
                FOREIGN KEY (template_id) REFERENCES marketplace_templates(id) ON DELETE CASCADE
            )
        """)

        # Collaboration rooms table (for Phase 12B)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collaboration_rooms (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                name TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at REAL NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        """)

        # Collaboration sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collaboration_sessions (
                id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                user_name TEXT NOT NULL,
                user_color TEXT,
                joined_at REAL NOT NULL,
                left_at REAL,
                FOREIGN KEY (room_id) REFERENCES collaboration_rooms(id) ON DELETE CASCADE
            )
        """)

        conn.commit()
        logger.debug("Database schema initialized")

    # ==================== User Operations ====================

    def create_user(
        self,
        user_id: str,
        username: str,
        email: str,
        password_hash: str,
        role: str = "editor"
    ) -> bool:
        """Create a new user."""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (id, username, email, password_hash, role, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, username, email, password_hash, role, time.time()))
                return True
        except sqlite3.IntegrityError as e:
            logger.warning(f"Failed to create user {username}: {e}")
            return False

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return self._row_to_dict(row) if row else None

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        return self._row_to_dict(row) if row else None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        return self._row_to_dict(row) if row else None

    def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user fields."""
        if not updates:
            return True

        allowed_fields = {'username', 'email', 'password_hash', 'role', 'is_active', 'last_login', 'projects'}
        filtered = {k: v for k, v in updates.items() if k in allowed_fields}

        if not filtered:
            return True

        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                set_clause = ", ".join(f"{k} = ?" for k in filtered.keys())
                if 'projects' in filtered:
                    filtered['projects_json'] = json.dumps(filtered.pop('projects'))

                values = list(filtered.values()) + [user_id]
                cursor.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to update user {user_id}: {e}")
            return False

    def delete_user(self, user_id: str) -> bool:
        """Delete user."""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {e}")
            return False

    def list_users(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List all users with pagination."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert database row to dictionary."""
        result = dict(row)
        if 'projects_json' in result:
            result['projects'] = json.loads(result.pop('projects_json'))
        return result

    # ==================== Token Operations ====================

    def store_refresh_token(self, jti: str, user_id: str, expires_at: float) -> bool:
        """Store refresh token."""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO refresh_tokens (jti, user_id, created_at, expires_at)
                    VALUES (?, ?, ?, ?)
                """, (jti, user_id, time.time(), expires_at))
                return True
        except Exception as e:
            logger.error(f"Failed to store refresh token: {e}")
            return False

    def get_refresh_token(self, jti: str) -> Optional[Dict[str, Any]]:
        """Get refresh token."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM refresh_tokens WHERE jti = ?", (jti,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def delete_refresh_token(self, jti: str) -> bool:
        """Delete refresh token."""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM refresh_tokens WHERE jti = ?", (jti,))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete refresh token: {e}")
            return False

    def cleanup_expired_tokens(self) -> int:
        """Remove expired refresh tokens. Returns count of deleted tokens."""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM refresh_tokens WHERE expires_at < ?", (time.time(),))
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to cleanup tokens: {e}")
            return 0

    # ==================== Snapshot Operations ====================

    def create_snapshot(
        self,
        snapshot_id: str,
        project_id: str,
        data: Dict[str, Any],
        label: Optional[str] = None,
        parent_id: Optional[str] = None
    ) -> bool:
        """Create project snapshot."""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO project_snapshots (id, project_id, label, data_json, created_at, parent_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (snapshot_id, project_id, label, json.dumps(data), time.time(), parent_id))
                return True
        except Exception as e:
            logger.error(f"Failed to create snapshot: {e}")
            return False

    def get_snapshot(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """Get snapshot by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM project_snapshots WHERE id = ?", (snapshot_id,))
        row = cursor.fetchone()
        if row:
            result = dict(row)
            result['data'] = json.loads(result.pop('data_json'))
            return result
        return None

    def get_snapshots_by_project(self, project_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all snapshots for a project."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM project_snapshots WHERE project_id = ? ORDER BY created_at DESC LIMIT ?",
            (project_id, limit)
        )
        results = []
        for row in cursor.fetchall():
            result = dict(row)
            result['data'] = json.loads(result.pop('data_json'))
            results.append(result)
        return results

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete snapshot."""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM project_snapshots WHERE id = ?", (snapshot_id,))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete snapshot: {e}")
            return False

    # ==================== Template Operations ====================

    def create_template(
        self,
        template_id: str,
        name: str,
        description: str,
        category: str,
        schematic: Dict[str, Any],
        pcb: Dict[str, Any],
        tags: List[str],
        author_id: Optional[str] = None,
        author_name: Optional[str] = None
    ) -> bool:
        """Create marketplace template."""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO marketplace_templates
                    (id, name, description, category, author_id, author_name, schematic_json, pcb_json, tags_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    template_id, name, description, category,
                    author_id, author_name,
                    json.dumps(schematic), json.dumps(pcb), json.dumps(tags),
                    time.time(), time.time()
                ))
                return True
        except Exception as e:
            logger.error(f"Failed to create template: {e}")
            return False

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get template by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM marketplace_templates WHERE id = ?", (template_id,))
        row = cursor.fetchone()
        if row:
            return self._template_row_to_dict(row)
        return None

    def list_templates(
        self,
        category: Optional[str] = None,
        featured_only: bool = False,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List templates with filters."""
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM marketplace_templates WHERE 1=1"
        params = []

        if category:
            query += " AND category = ?"
            params.append(category)
        if featured_only:
            query += " AND is_featured = 1"

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        return [self._template_row_to_dict(row) for row in cursor.fetchall()]

    def search_templates(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search templates by name or description."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM marketplace_templates
            WHERE name LIKE ? OR description LIKE ?
            ORDER BY created_at DESC LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit))
        return [self._template_row_to_dict(row) for row in cursor.fetchall()]

    def update_template_stats(
        self,
        template_id: str,
        download_increment: int = 0,
        rating: Optional[int] = None
    ) -> bool:
        """Update template download count and/or rating."""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                if download_increment:
                    cursor.execute(
                        "UPDATE marketplace_templates SET downloads = downloads + ?, updated_at = ? WHERE id = ?",
                        (download_increment, time.time(), template_id)
                    )
                if rating and 1 <= rating <= 5:
                    cursor.execute(
                        "UPDATE marketplace_templates SET rating_sum = rating_sum + ?, rating_count = rating_count + 1, updated_at = ? WHERE id = ?",
                        (rating, time.time(), template_id)
                    )
                return True
        except Exception as e:
            logger.error(f"Failed to update template stats: {e}")
            return False

    def rate_template(self, template_id: str, user_id: str, rating: int) -> bool:
        """Add user rating for template."""
        if not 1 <= rating <= 5:
            return False

        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                # Insert or replace rating
                cursor.execute("""
                    INSERT OR REPLACE INTO template_ratings (id, template_id, user_id, rating, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (f"{template_id}_{user_id}", template_id, user_id, rating, time.time()))

                # Recalculate aggregate rating
                cursor.execute("""
                    UPDATE marketplace_templates
                    SET rating_sum = (SELECT SUM(rating) FROM template_ratings WHERE template_id = ?),
                        rating_count = (SELECT COUNT(*) FROM template_ratings WHERE template_id = ?),
                        updated_at = ?
                    WHERE id = ?
                """, (template_id, template_id, time.time(), template_id))
                return True
        except Exception as e:
            logger.error(f"Failed to rate template: {e}")
            return False

    def _template_row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert template row to dictionary."""
        result = dict(row)
        result['schematic'] = json.loads(result.pop('schematic_json'))
        result['pcb'] = json.loads(result.pop('pcb_json'))
        result['tags'] = json.loads(result.pop('tags_json'))
        # Calculate average rating
        if result['rating_count'] > 0:
            result['average_rating'] = result['rating_sum'] / result['rating_count']
        else:
            result['average_rating'] = 0
        return result

    # ==================== Collaboration Operations ====================

    def create_collaboration_room(
        self,
        room_id: str,
        project_id: str,
        name: str,
        created_by: str
    ) -> bool:
        """Create collaboration room."""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO collaboration_rooms (id, project_id, name, created_by, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (room_id, project_id, name, created_by, time.time()))
                return True
        except Exception as e:
            logger.error(f"Failed to create collaboration room: {e}")
            return False

    def get_collaboration_room(self, room_id: str) -> Optional[Dict[str, Any]]:
        """Get collaboration room."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM collaboration_rooms WHERE id = ?", (room_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def join_collaboration_room(
        self,
        session_id: str,
        room_id: str,
        user_id: str,
        user_name: str,
        user_color: Optional[str] = None
    ) -> bool:
        """Join collaboration room."""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO collaboration_sessions (id, room_id, user_id, user_name, user_color, joined_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (session_id, room_id, user_id, user_name, user_color, time.time()))
                return True
        except Exception as e:
            logger.error(f"Failed to join collaboration room: {e}")
            return False

    def leave_collaboration_room(self, session_id: str) -> bool:
        """Leave collaboration room."""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE collaboration_sessions SET left_at = ? WHERE id = ?",
                    (time.time(), session_id)
                )
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to leave collaboration room: {e}")
            return False

    def get_active_sessions(self, room_id: str) -> List[Dict[str, Any]]:
        """Get active sessions in room."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM collaboration_sessions
            WHERE room_id = ? AND left_at IS NULL
            ORDER BY joined_at
        """, (room_id,))
        return [dict(row) for row in cursor.fetchall()]



    # ==================== Utility Methods ====================

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute raw SQL query."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'conn'):
            self._local.conn.close()
            delattr(self._local, 'conn')



    def migrate_from_json(self, json_file: str, data_type: str) -> int:
        """
        Migrate data from JSON file to SQLite.

        Args:
            json_file: Path to JSON file
            data_type: Type of data ('users', 'templates', etc.)

        Returns:
            Number of records migrated
        """
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)

            count = 0
            if data_type == 'users':
                for user_data in data.get('users', []):
                    if self.create_user(
                        user_data.get('id', str(uuid.uuid4())),
                        user_data.get('username', ''),
                        user_data.get('email', ''),
                        user_data.get('password_hash', ''),
                        user_data.get('role', 'editor')
                    ):
                        count += 1

            logger.info(f"Migrated {count} {data_type} records from {json_file}")
            return count
        except Exception as e:
            logger.error(f"Failed to migrate {data_type}: {e}")
            return 0


# Singleton instance
db: DatabaseService = DatabaseService.get_instance()
