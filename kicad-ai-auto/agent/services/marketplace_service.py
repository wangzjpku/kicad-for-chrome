"""
Template Marketplace Service

Provides:
- Template CRUD (create, read, update, delete)
- Category/tag based search
- Rating system (1-5 stars)
- Download tracking
- Featured templates
- Template versioning

Uses SQLite database with JSON file fallback.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from threading import local
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Template:
    """A marketplace template."""
    id: str
    name: str
    description: str
    author_id: str
    author_name: str
    category: str
    tags: List[str]
    board_layers: int = 2
    board_size: str = ""
    components_count: int = 0
    schematic_data: Dict[str, Any] = field(default_factory=dict)
    pcb_data: Dict[str, Any] = field(default_factory=dict)
    bom_data: List[Dict[str, Any]] = field(default_factory=list)
    thumbnail: str = ""
    rating_avg: float = 0.0
    rating_count: int = 0
    downloads: int = 0
    version: str = "1.0.0"
    is_public: bool = True
    is_featured: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class TemplateRating:
    """A user's rating of a template."""
    user_id: str
    template_id: str
    stars: int
    review: str = ""
    created_at: float = field(default_factory=time.time)


class MarketplaceService:
    """
    Template marketplace with search, rating, and download tracking.
    Uses SQLite for persistence with JSON file fallback.
    """

    CATEGORIES = [
        "mcu-board", "power-supply", "sensor-board", "usb-adapter",
        "wireless-module", "motor-driver", "audio-board", "led-controller",
        "io-expander", "development-board", "breakout-board", "other",
    ]

    def __init__(self, data_dir: Optional[str] = None, use_database: bool = True):
        self._data_dir = data_dir or os.path.join(
            os.path.dirname(__file__), "..", "data", "marketplace"
        )
        os.makedirs(self._data_dir, exist_ok=True)
        self._templates: Dict[str, Template] = {}
        self._ratings: Dict[str, Dict[str, TemplateRating]] = {}
        self._use_database = use_database
        self._db_path = os.path.join(self._data_dir, "marketplace.db")
        self._local = local()

        if use_database:
            try:
                self._init_database()
                logger.info("MarketplaceService using SQLite database")
            except Exception as e:
                logger.warning(f"Failed to init database, falling back to JSON: {e}")
                self._use_database = False

        if not self._use_database:
            self._load()

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
            CREATE TABLE IF NOT EXISTS templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                author_id TEXT,
                author_name TEXT,
                category TEXT NOT NULL,
                tags_json TEXT DEFAULT '[]',
                board_layers INTEGER DEFAULT 2,
                board_size TEXT,
                components_count INTEGER DEFAULT 0,
                schematic_json TEXT DEFAULT '{}',
                pcb_json TEXT DEFAULT '{}',
                bom_json TEXT DEFAULT '[]',
                thumbnail TEXT,
                rating_avg REAL DEFAULT 0,
                rating_count INTEGER DEFAULT 0,
                downloads INTEGER DEFAULT 0,
                version TEXT DEFAULT '1.0.0',
                is_public INTEGER DEFAULT 1,
                is_featured INTEGER DEFAULT 0,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                id TEXT PRIMARY KEY,
                template_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                stars INTEGER NOT NULL CHECK(stars >= 1 AND stars <= 5),
                review TEXT,
                created_at REAL NOT NULL,
                UNIQUE(template_id, user_id),
                FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_templates_category
            ON templates(category)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_templates_featured
            ON templates(is_featured, rating_avg DESC)
        """)

        conn.commit()

        # Load into memory
        cursor.execute("SELECT * FROM templates")
        for row in cursor.fetchall():
            self._templates[row["id"]] = Template(
                id=row["id"],
                name=row["name"],
                description=row["description"] or "",
                author_id=row["author_id"] or "",
                author_name=row["author_name"] or "",
                category=row["category"],
                tags=json.loads(row["tags_json"] or "[]"),
                board_layers=row["board_layers"] or 2,
                board_size=row["board_size"] or "",
                components_count=row["components_count"] or 0,
                schematic_data=json.loads(row["schematic_json"] or "{}"),
                pcb_data=json.loads(row["pcb_json"] or "{}"),
                bom_data=json.loads(row["bom_json"] or "[]"),
                thumbnail=row["thumbnail"] or "",
                rating_avg=row["rating_avg"] or 0.0,
                rating_count=row["rating_count"] or 0,
                downloads=row["downloads"] or 0,
                version=row["version"] or "1.0.0",
                is_public=bool(row["is_public"]),
                is_featured=bool(row["is_featured"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

        cursor.execute("SELECT * FROM ratings")
        for row in cursor.fetchall():
            tid = row["template_id"]
            uid = row["user_id"]
            if tid not in self._ratings:
                self._ratings[tid] = {}
            self._ratings[tid][uid] = TemplateRating(
                user_id=uid,
                template_id=tid,
                stars=row["stars"],
                review=row["review"] or "",
                created_at=row["created_at"],
            )

        logger.info(f"Loaded {len(self._templates)} templates from database")

    def _save_template_to_db(self, t: Template):
        """Save template to database."""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO templates
            (id, name, description, author_id, author_name, category, tags_json,
             board_layers, board_size, components_count, schematic_json, pcb_json,
             bom_json, thumbnail, rating_avg, rating_count, downloads, version,
             is_public, is_featured, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            t.id, t.name, t.description, t.author_id, t.author_name, t.category,
            json.dumps(t.tags), t.board_layers, t.board_size, t.components_count,
            json.dumps(t.schematic_data), json.dumps(t.pcb_data), json.dumps(t.bom_data),
            t.thumbnail, t.rating_avg, t.rating_count, t.downloads, t.version,
            int(t.is_public), int(t.is_featured), t.created_at, t.updated_at,
        ))
        conn.commit()

    def _delete_template_from_db(self, template_id: str):
        """Delete template from database."""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM templates WHERE id = ?", (template_id,))
        cursor.execute("DELETE FROM ratings WHERE template_id = ?", (template_id,))
        conn.commit()

    def _save_rating_to_db(self, r: TemplateRating):
        """Save rating to database."""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        rating_id = f"{r.template_id}_{r.user_id}"
        cursor.execute("""
            INSERT OR REPLACE INTO ratings
            (id, template_id, user_id, stars, review, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (rating_id, r.template_id, r.user_id, r.stars, r.review, r.created_at))
        conn.commit()

    def _update_template_stats_in_db(self, template_id: str, rating_avg: float, rating_count: int):
        """Update template rating stats in database."""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE templates SET rating_avg = ?, rating_count = ?, updated_at = ? WHERE id = ?",
            (rating_avg, rating_count, time.time(), template_id)
        )
        conn.commit()

    def _increment_downloads_in_db(self, template_id: str):
        """Increment download count in database."""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE templates SET downloads = downloads + 1, updated_at = ? WHERE id = ?",
            (time.time(), template_id)
        )
        conn.commit()

    # ---- JSON Fallback Methods ----

    def _data_file(self) -> str:
        return os.path.join(self._data_dir, "marketplace.json")

    def _load(self):
        """Load from JSON file (fallback mode)."""
        path = self._data_file()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r") as f:
                data = json.load(f)

            for tid, tdata in data.get("templates", {}).items():
                self._templates[tid] = Template(**tdata)

            for tid, ratings in data.get("ratings", {}).items():
                self._ratings[tid] = {}
                for uid, rdata in ratings.items():
                    self._ratings[tid][uid] = TemplateRating(**rdata)

            logger.info(f"Loaded {len(self._templates)} templates from JSON")
        except Exception as e:
            logger.warning(f"Failed to load marketplace: {e}")

    def _save(self):
        """Save to JSON file (fallback mode)."""
        path = self._data_file()
        try:
            data = {
                "templates": {
                    tid: {
                        "id": t.id, "name": t.name, "description": t.description,
                        "author_id": t.author_id, "author_name": t.author_name,
                        "category": t.category, "tags": t.tags,
                        "board_layers": t.board_layers, "board_size": t.board_size,
                        "components_count": t.components_count,
                        "schematic_data": t.schematic_data, "pcb_data": t.pcb_data,
                        "bom_data": t.bom_data, "thumbnail": t.thumbnail,
                        "rating_avg": t.rating_avg, "rating_count": t.rating_count,
                        "downloads": t.downloads, "version": t.version,
                        "is_public": t.is_public, "is_featured": t.is_featured,
                        "created_at": t.created_at, "updated_at": t.updated_at,
                    }
                    for tid, t in self._templates.items()
                },
                "ratings": {
                    tid: {
                        uid: {
                            "user_id": r.user_id, "template_id": r.template_id,
                            "stars": r.stars, "review": r.review,
                            "created_at": r.created_at,
                        }
                        for uid, r in ratings.items()
                    }
                    for tid, ratings in self._ratings.items()
                },
            }
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save marketplace: {e}")

    # ---- CRUD ----

    def create_template(
        self,
        name: str,
        description: str,
        author_id: str,
        author_name: str,
        category: str,
        tags: List[str],
        schematic_data: Dict[str, Any],
        pcb_data: Dict[str, Any],
        bom_data: List[Dict[str, Any]],
        board_layers: int = 2,
        board_size: str = "",
        thumbnail: str = "",
    ) -> Dict[str, Any]:
        template_id = str(uuid.uuid4())
        template = Template(
            id=template_id,
            name=name,
            description=description,
            author_id=author_id,
            author_name=author_name,
            category=category,
            tags=tags,
            board_layers=board_layers,
            board_size=board_size,
            components_count=len(bom_data),
            schematic_data=schematic_data,
            pcb_data=pcb_data,
            bom_data=bom_data,
            thumbnail=thumbnail,
        )
        self._templates[template_id] = template

        if self._use_database:
            self._save_template_to_db(template)
        else:
            self._save()

        logger.info(f"Template created: {name} by {author_name}")
        return {
            "id": template_id,
            "name": name,
            "status": "created",
        }

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        t = self._templates.get(template_id)
        if not t or not t.is_public:
            return None
        return self._template_to_dict(t)

    def update_template(
        self,
        template_id: str,
        author_id: str,
        **updates,
    ) -> Dict[str, Any]:
        t = self._templates.get(template_id)
        if not t:
            return {"error": "Template not found"}
        if t.author_id != author_id:
            return {"error": "Not the template author"}

        allowed = {
            "name", "description", "category", "tags",
            "board_layers", "board_size", "schematic_data",
            "pcb_data", "bom_data", "thumbnail", "is_public",
        }
        for key, value in updates.items():
            if key in allowed:
                setattr(t, key, value)
        t.updated_at = time.time()
        t.components_count = len(t.bom_data)

        if self._use_database:
            self._save_template_to_db(t)
        else:
            self._save()

        return {"status": "ok", "template_id": template_id}

    def delete_template(self, template_id: str, author_id: str) -> Dict[str, Any]:
        t = self._templates.get(template_id)
        if not t:
            return {"error": "Template not found"}
        if t.author_id != author_id:
            return {"error": "Not the template author"}

        del self._templates[template_id]
        self._ratings.pop(template_id, None)

        if self._use_database:
            self._delete_template_from_db(template_id)
        else:
            self._save()

        return {"status": "ok"}

    # ---- Search ----

    def search(
        self,
        query: str = "",
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        board_layers: Optional[int] = None,
        sort_by: str = "newest",
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        results = []
        for t in self._templates.values():
            if not t.is_public:
                continue

            if category and t.category != category:
                continue

            if board_layers and t.board_layers != board_layers:
                continue

            if tags:
                if not any(tag in t.tags for tag in tags):
                    continue

            if query:
                query_lower = query.lower()
                searchable = f"{t.name} {t.description} {' '.join(t.tags)} {t.category} {t.author_name}".lower()
                if query_lower not in searchable:
                    continue

            results.append(t)

        if sort_by == "popular":
            results.sort(key=lambda t: t.downloads, reverse=True)
        elif sort_by == "highest_rated":
            results.sort(key=lambda t: t.rating_avg, reverse=True)
        else:
            results.sort(key=lambda t: t.created_at, reverse=True)

        total = len(results)
        results = results[offset:offset + limit]

        return {
            "templates": [self._template_summary(t) for t in results],
            "total": total,
            "offset": offset,
            "limit": limit,
        }

    def get_featured(self, limit: int = 6) -> List[Dict[str, Any]]:
        featured = [
            t for t in self._templates.values()
            if t.is_public and t.is_featured
        ]
        featured.sort(key=lambda t: t.rating_avg, reverse=True)
        return [self._template_summary(t) for t in featured[:limit]]

    def get_categories(self) -> List[Dict[str, Any]]:
        counts = {}
        for t in self._templates.values():
            if t.is_public:
                counts[t.category] = counts.get(t.category, 0) + 1
        return [
            {"name": cat, "count": counts.get(cat, 0)}
            for cat in self.CATEGORIES
        ]

    # ---- Rating ----

    def rate_template(
        self,
        template_id: str,
        user_id: str,
        stars: int,
        review: str = "",
    ) -> Dict[str, Any]:
        if template_id not in self._templates:
            return {"error": "Template not found"}

        if not 1 <= stars <= 5:
            return {"error": "Stars must be 1-5"}

        if template_id not in self._ratings:
            self._ratings[template_id] = {}

        rating = TemplateRating(
            user_id=user_id,
            template_id=template_id,
            stars=stars,
            review=review,
        )
        self._ratings[template_id][user_id] = rating

        # Recalculate average
        ratings = list(self._ratings[template_id].values())
        avg = sum(r.stars for r in ratings) / len(ratings)
        self._templates[template_id].rating_avg = round(avg, 2)
        self._templates[template_id].rating_count = len(ratings)

        if self._use_database:
            self._save_rating_to_db(rating)
            self._update_template_stats_in_db(
                template_id,
                self._templates[template_id].rating_avg,
                self._templates[template_id].rating_count,
            )
        else:
            self._save()

        return {"status": "ok", "rating_avg": round(avg, 2)}

    # ---- Download ----

    def download_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        t = self._templates.get(template_id)
        if not t or not t.is_public:
            return None

        t.downloads += 1

        if self._use_database:
            self._increment_downloads_in_db(template_id)
        else:
            self._save()

        return {
            "id": t.id,
            "name": t.name,
            "version": t.version,
            "schematic_data": t.schematic_data,
            "pcb_data": t.pcb_data,
            "bom_data": t.bom_data,
        }

    # ---- Helpers ----

    def _template_to_dict(self, t: Template) -> Dict[str, Any]:
        return {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "author": t.author_name,
            "category": t.category,
            "tags": t.tags,
            "board_layers": t.board_layers,
            "board_size": t.board_size,
            "components_count": t.components_count,
            "thumbnail": t.thumbnail,
            "rating_avg": t.rating_avg,
            "rating_count": t.rating_count,
            "downloads": t.downloads,
            "version": t.version,
            "created_at": t.created_at,
            "updated_at": t.updated_at,
        }

    def _template_summary(self, t: Template) -> Dict[str, Any]:
        return {
            "id": t.id,
            "name": t.name,
            "description": t.description[:100] + "..." if len(t.description) > 100 else t.description,
            "author": t.author_name,
            "category": t.category,
            "tags": t.tags,
            "board_layers": t.board_layers,
            "components_count": t.components_count,
            "thumbnail": t.thumbnail,
            "rating_avg": t.rating_avg,
            "rating_count": t.rating_count,
            "downloads": t.downloads,
            "is_featured": t.is_featured,
        }


# Singleton
_marketplace: Optional[MarketplaceService] = None


def get_marketplace() -> MarketplaceService:
    global _marketplace
    if _marketplace is None:
        _marketplace = MarketplaceService()
    return _marketplace
