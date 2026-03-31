# -*- coding: utf-8 -*-
"""
Conversation Model - 持久化对话模型

支持:
- 多轮对话持久化
- 对话历史搜索
- 用户/项目关联
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
CONVERSATIONS_DB = DATA_DIR / "conversations.db"


@dataclass
class ChatMessage:
    """聊天消息"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatMessage":
        return cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", ""),
        )


@dataclass
class Conversation:
    """对话"""
    id: str
    user_id: int
    project_id: Optional[str] = None
    title: str = "新对话"
    messages: List[ChatMessage] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    model: str = "kimi"  # 使用的AI模型

    def __post_init__(self):
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "title": self.title,
            "messages": [m.to_dict() for m in self.messages],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "model": self.model,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Conversation":
        messages = [ChatMessage.from_dict(m) for m in data.get("messages", [])]
        return cls(
            id=data.get("id", ""),
            user_id=data.get("user_id", 0),
            project_id=data.get("project_id"),
            title=data.get("title", "新对话"),
            messages=messages,
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            model=data.get("model", "kimi"),
        )


class ConversationDB:
    """对话数据库管理器"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(CONVERSATIONS_DB)
        self._ensure_db()

    def _ensure_db(self):
        """确保数据库和表存在"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                project_id TEXT,
                title TEXT NOT NULL DEFAULT '新对话',
                messages TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                model TEXT NOT NULL DEFAULT 'kimi'
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_user_id
            ON conversations(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_updated_at
            ON conversations(updated_at)
        """)
        conn.commit()
        conn.close()

    def _row_to_conversation(self, row: tuple) -> Conversation:
        """将数据库行转换为 Conversation 对象"""
        return Conversation(
            id=row[0],
            user_id=row[1],
            project_id=row[2],
            title=row[3],
            messages=[ChatMessage.from_dict(m) for m in json.loads(row[4])],
            created_at=row[5],
            updated_at=row[6],
            model=row[7],
        )

    def save_conversation(self, conv: Conversation) -> bool:
        """保存对话"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO conversations
                (id, user_id, project_id, title, messages, created_at, updated_at, model)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                conv.id,
                conv.user_id,
                conv.project_id,
                conv.title,
                json.dumps([m.to_dict() for m in conv.messages], ensure_ascii=False),
                conv.created_at,
                datetime.now().isoformat(),
                conv.model,
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"保存对话失败: {e}")
            return False

    def get_conversation(self, conv_id: str) -> Optional[Conversation]:
        """获取对话"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, user_id, project_id, title, messages, created_at, updated_at, model "
                "FROM conversations WHERE id = ?",
                (conv_id,)
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return self._row_to_conversation(row)
            return None
        except Exception as e:
            logger.error(f"获取对话失败: {e}")
            return None

    def list_conversations(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Conversation]:
        """列出用户的所有对话（按更新时间排序）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, project_id, title, messages, created_at, updated_at, model
                FROM conversations
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
            """, (user_id, limit, offset))
            rows = cursor.fetchall()
            conn.close()
            return [self._row_to_conversation(row) for row in rows]
        except Exception as e:
            logger.error(f"列出对话失败: {e}")
            return []

    def delete_conversation(self, conv_id: str) -> bool:
        """删除对话"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"删除对话失败: {e}")
            return False

    def search_conversations(
        self,
        user_id: int,
        keyword: str,
        limit: int = 20,
    ) -> List[Conversation]:
        """搜索对话"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, project_id, title, messages, created_at, updated_at, model
                FROM conversations
                WHERE user_id = ? AND (title LIKE ? OR messages LIKE ?)
                ORDER BY updated_at DESC
                LIMIT ?
            """, (user_id, f"%{keyword}%", f"%{keyword}%", limit))
            rows = cursor.fetchall()
            conn.close()
            return [self._row_to_conversation(row) for row in rows]
        except Exception as e:
            logger.error(f"搜索对话失败: {e}")
            return []


# 全局数据库实例
_db: Optional[ConversationDB] = None


def get_conversation_db() -> ConversationDB:
    """获取全局对话数据库实例"""
    global _db
    if _db is None:
        _db = ConversationDB()
    return _db


def generate_conv_id() -> str:
    """生成对话ID"""
    import uuid
    return str(uuid.uuid4())
