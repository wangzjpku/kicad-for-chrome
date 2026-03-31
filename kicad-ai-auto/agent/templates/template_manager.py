"""
Template Manager - 模板管理器

Phase 6: 项目模板系统

功能:
- 模板列表和搜索
- 自定义模板创建/保存
- 基于模板创建项目

Author: Claude Code
Date: 2026-03-30
"""

import json
import logging
import uuid
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

from .template_data import (
    ProjectTemplate,
    TemplateCategory,
    PREDEFINED_TEMPLATES,
    get_template_by_id,
    get_templates_by_category,
    search_templates,
)

logger = logging.getLogger(__name__)


@dataclass
class CustomTemplate:
    """自定义模板"""
    template_id: str
    name: str
    name_cn: str
    description: str
    category: str
    tags: List[str]
    schematic_data: Dict[str, Any]
    pcb_data: Dict[str, Any]
    author: str = "User"
    version: str = "1.0"
    created_at: str = ""
    updated_at: str = ""


class TemplateManager:
    """
    模板管理器

    支持:
    - 预定义模板获取
    - 自定义模板 CRUD
    - 基于模板创建项目
    """

    def __init__(self, templates_dir: str = "data/templates"):
        """
        Args:
            templates_dir: 自定义模板存储目录
        """
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self._custom_templates: Dict[str, CustomTemplate] = {}
        self._load_custom_templates()

    def _load_custom_templates(self):
        """加载自定义模板"""
        index_file = self.templates_dir / "index.json"
        if index_file.exists():
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for template_data in data.get("templates", []):
                        template = CustomTemplate(**template_data)
                        self._custom_templates[template.template_id] = template
                logger.info(f"Loaded {len(self._custom_templates)} custom templates")
            except Exception as e:
                logger.warning(f"Failed to load custom templates: {e}")

    def _save_custom_templates(self):
        """保存自定义模板索引"""
        index_file = self.templates_dir / "index.json"
        data = {
            "templates": [
                asdict(t) for t in self._custom_templates.values()
            ]
        }
        try:
            with open(index_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save custom templates: {e}")

    def list_templates(
        self,
        category: Optional[str] = None,
        include_predefined: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        列出模板

        Args:
            category: 类别过滤
            include_predefined: 是否包含预定义模板

        Returns:
            模板列表
        """
        results = []

        if include_predefined:
            templates = PREDEFINED_TEMPLATES
            if category:
                try:
                    cat = TemplateCategory(category)
                    templates = get_templates_by_category(cat)
                except ValueError:
                    pass

            for t in templates:
                results.append({
                    "template_id": t.template_id,
                    "name": t.name,
                    "name_cn": t.name_cn,
                    "description": t.description,
                    "category": t.category.value,
                    "tags": t.tags,
                    "author": t.author,
                    "is_predefined": True,
                })

        # 添加自定义模板
        for t in self._custom_templates.values():
            if category and t.category != category:
                continue
            results.append({
                "template_id": t.template_id,
                "name": t.name,
                "name_cn": t.name_cn,
                "description": t.description,
                "category": t.category,
                "tags": t.tags,
                "author": t.author,
                "is_predefined": False,
                "created_at": t.created_at,
            })

        return results

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        获取模板详情

        Args:
            template_id: 模板 ID

        Returns:
            模板详情
        """
        # 预定义模板
        template = get_template_by_id(template_id)
        if template:
            return {
                "template_id": template.template_id,
                "name": template.name,
                "name_cn": template.name_cn,
                "description": template.description,
                "category": template.category.value,
                "tags": template.tags,
                "schematic": asdict(template.schematic),
                "pcb": asdict(template.pcb),
                "author": template.author,
                "is_predefined": True,
            }

        # 自定义模板
        custom = self._custom_templates.get(template_id)
        if custom:
            return {
                "template_id": custom.template_id,
                "name": custom.name,
                "name_cn": custom.name_cn,
                "description": custom.description,
                "category": custom.category,
                "tags": custom.tags,
                "schematic": custom.schematic_data,
                "pcb": custom.pcb_data,
                "author": custom.author,
                "is_predefined": False,
                "created_at": custom.created_at,
            }

        return None

    def search_templates_api(
        self,
        keyword: str,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        搜索模板

        Args:
            keyword: 搜索关键词
            category: 类别过滤

        Returns:
            搜索结果
        """
        results = []

        # 搜索预定义模板
        predefined = search_templates(keyword)
        for t in predefined:
            if category and t.category.value != category:
                continue
            results.append({
                "template_id": t.template_id,
                "name": t.name,
                "name_cn": t.name_cn,
                "description": t.description,
                "category": t.category.value,
                "tags": t.tags,
                "author": t.author,
                "is_predefined": True,
            })

        # 搜索自定义模板
        keyword_lower = keyword.lower()
        for t in self._custom_templates.values():
            if category and t.category != category:
                continue
            if (keyword_lower in t.name.lower() or
                keyword_lower in t.name_cn.lower() or
                keyword_lower in t.description.lower() or
                any(keyword_lower in tag.lower() for tag in t.tags)):
                results.append({
                    "template_id": t.template_id,
                    "name": t.name,
                    "name_cn": t.name_cn,
                    "description": t.description,
                    "category": t.category,
                    "tags": t.tags,
                    "author": t.author,
                    "is_predefined": False,
                })

        return results

    def create_custom_template(
        self,
        name: str,
        name_cn: str,
        description: str,
        category: str,
        tags: List[str],
        schematic_data: Dict[str, Any],
        pcb_data: Dict[str, Any],
        author: str = "User",
    ) -> Dict[str, Any]:
        """
        创建自定义模板

        Args:
            name: 模板名称
            name_cn: 中文名称
            description: 描述
            category: 类别
            tags: 标签
            schematic_data: 原理图数据
            pcb_data: PCB 数据
            author: 作者

        Returns:
            创建的模板
        """
        from datetime import datetime

        template_id = f"custom_{uuid.uuid4().hex[:8]}"

        template = CustomTemplate(
            template_id=template_id,
            name=name,
            name_cn=name_cn,
            description=description,
            category=category,
            tags=tags,
            schematic_data=schematic_data,
            pcb_data=pcb_data,
            author=author,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )

        self._custom_templates[template_id] = template
        self._save_custom_templates()

        return {
            "template_id": template_id,
            "name": name,
            "message": "模板创建成功",
        }

    def update_custom_template(
        self,
        template_id: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        更新自定义模板

        Args:
            template_id: 模板 ID
            **kwargs: 要更新的字段

        Returns:
            更新结果
        """
        from datetime import datetime

        if template_id not in self._custom_templates:
            return {"success": False, "message": "模板不存在"}

        template = self._custom_templates[template_id]

        # 更新字段
        for key in ["name", "name_cn", "description", "category", "tags", "schematic_data", "pcb_data"]:
            if key in kwargs:
                setattr(template, key, kwargs[key])

        template.updated_at = datetime.now().isoformat()
        self._save_custom_templates()

        return {"success": True, "message": "模板更新成功"}

    def delete_custom_template(self, template_id: str) -> Dict[str, Any]:
        """
        删除自定义模板

        Args:
            template_id: 模板 ID

        Returns:
            删除结果
        """
        if template_id not in self._custom_templates:
            return {"success": False, "message": "模板不存在"}

        del self._custom_templates[template_id]
        self._save_custom_templates()

        return {"success": True, "message": "模板删除成功"}

    def create_project_from_template(
        self,
        template_id: str,
        project_name: str,
        **overrides,
    ) -> Dict[str, Any]:
        """
        基于模板创建项目

        Args:
            template_id: 模板 ID
            project_name: 项目名称
            **overrides: 可选的参数覆盖

        Returns:
            项目数据
        """
        template = self.get_template(template_id)
        if not template:
            return {"success": False, "message": "模板不存在"}

        # 生成项目 ID
        project_id = f"proj_{uuid.uuid4().hex[:12]}"

        # 合并覆盖参数
        schematic = template.get("schematic", {})
        pcb = template.get("pcb", {})

        if "schematic" in overrides:
            schematic.update(overrides["schematic"])
        if "pcb" in overrides:
            pcb.update(overrides["pcb"])

        return {
            "success": True,
            "project_id": project_id,
            "project_name": project_name,
            "template_id": template_id,
            "schematic": schematic,
            "pcb": pcb,
            "message": "项目创建成功",
        }


# 全局模板管理器实例
_template_manager: Optional[TemplateManager] = None


def get_template_manager() -> TemplateManager:
    """获取模板管理器单例"""
    global _template_manager
    if _template_manager is None:
        _template_manager = TemplateManager()
    return _template_manager
