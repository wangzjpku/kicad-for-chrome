"""
i18n (Internationalization) Service

Provides:
- Multi-language string management
- Translation key lookup with fallback
- Language detection from Accept-Language header
- Dynamic string interpolation
- Support for zh-CN, en-US, ja-JP

Used by both backend (API responses, error messages)
and frontend (UI labels, tooltips, notifications).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---- Translation Strings ----

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en-US": {
        # Common
        "app.title": "KiCad AI Auto",
        "app.tagline": "AI-Driven PCB Design Automation",
        "common.save": "Save",
        "common.cancel": "Cancel",
        "common.delete": "Delete",
        "common.close": "Close",
        "common.confirm": "Confirm",
        "common.loading": "Loading...",
        "common.error": "Error",
        "common.success": "Success",
        "common.warning": "Warning",
        "common.search": "Search",
        "common.filter": "Filter",
        "common.export": "Export",
        "common.import": "Import",
        "common.upload": "Upload",
        "common.download": "Download",
        "common.refresh": "Refresh",
        "common.apply": "Apply",
        "common.back": "Back",
        "common.next": "Next",
        "common.finish": "Finish",
        "common.yes": "Yes",
        "common.no": "No",
        # Auth
        "auth.login": "Login",
        "auth.register": "Register",
        "auth.logout": "Logout",
        "auth.username": "Username",
        "auth.password": "Password",
        "auth.email": "Email",
        "auth.confirm_password": "Confirm Password",
        "auth.forgot_password": "Forgot Password?",
        "auth.login_success": "Logged in successfully",
        "auth.login_failed": "Invalid credentials",
        "auth.register_success": "Account created successfully",
        "auth.register_failed": "Registration failed",
        "auth.token_expired": "Session expired, please login again",
        # Project
        "project.new": "New Project",
        "project.open": "Open Project",
        "project.save": "Save Project",
        "project.delete": "Delete Project",
        "project.share": "Share Project",
        "project.name": "Project Name",
        "project.description": "Description",
        "project.created": "Project created",
        "project.saved": "Project saved",
        "project.deleted": "Project deleted",
        # PCB Editor
        "pcb.title": "PCB Editor",
        "pcb.place_component": "Place Component",
        "pcb.route": "Route",
        "pcb.add_via": "Add Via",
        "pcb.add_zone": "Add Copper Zone",
        "pcb.run_drc": "Run DRC",
        "pcb.export_gerber": "Export Gerber",
        "pcb.zoom_in": "Zoom In",
        "pcb.zoom_out": "Zoom Out",
        "pcb.fit_view": "Fit to View",
        "pcb.select_all": "Select All",
        "pcb.delete_selected": "Delete Selected",
        "pcb.rotate_cw": "Rotate Clockwise",
        "pcb.rotate_ccw": "Rotate Counter-clockwise",
        "pcb.flip": "Flip to Other Side",
        "pcb.move": "Move",
        "pcb.copy": "Copy",
        "pcb.paste": "Paste",
        # Schematic
        "schematic.title": "Schematic Editor",
        "schematic.place_symbol": "Place Symbol",
        "schematic.add_wire": "Add Wire",
        "schematic.add_label": "Add Label",
        "schematic.annotate": "Annotate",
        "schematic.erc": "Run ERC",
        # DRC
        "drc.title": "Design Rule Check",
        "drc.running": "Running DRC...",
        "drc.complete": "DRC Complete",
        "drc.errors": "Errors",
        "drc.warnings": "Warnings",
        "drc.no_violations": "No violations found!",
        "drc.clearance": "Clearance Violation",
        "drc.short_circuit": "Short Circuit",
        "drc.unconnected": "Unconnected Net",
        "drc.width": "Track Width Violation",
        # Manufacturing
        "mfg.title": "Manufacturing",
        "mfg.generate": "Generate Manufacturing Files",
        "mfg.gerber": "Gerber Files",
        "mfg.bom": "Bill of Materials",
        "mfg.pnp": "Pick & Place",
        "mfg.order_package": "Order Package",
        "mfg.jlcpcb": "JLCPCB",
        "mfg.pcbway": "PCBWay",
        "mfg.cost_estimate": "Cost Estimate",
        "mfg.checking": "Checking manufacturability...",
        # Collaboration
        "collab.title": "Collaboration",
        "collab.share_link": "Share Link",
        "collab.users_online": "{count} users online",
        "collab.history": "Version History",
        "collab.rollback": "Rollback",
        "collab.snapshot": "Create Snapshot",
        # Marketplace
        "market.title": "Template Marketplace",
        "market.search": "Search templates...",
        "market.featured": "Featured",
        "market.categories": "Categories",
        "market.download": "Download",
        "market.rate": "Rate",
        "market.upload": "Upload Template",
        # AI
        "ai.title": "AI Assistant",
        "ai.generate": "Generate",
        "ai.analyzing": "Analyzing...",
        "ai.suggestion": "AI Suggestion",
        "ai.optimize": "Optimize",
        "ai.auto_route": "Auto Route",
        "ai.auto_place": "Auto Place",
    },
    "zh-CN": {
        # Common
        "app.title": "KiCad AI Auto",
        "app.tagline": "AI 驱动的 PCB 设计自动化",
        "common.save": "保存",
        "common.cancel": "取消",
        "common.delete": "删除",
        "common.close": "关闭",
        "common.confirm": "确认",
        "common.loading": "加载中...",
        "common.error": "错误",
        "common.success": "成功",
        "common.warning": "警告",
        "common.search": "搜索",
        "common.filter": "筛选",
        "common.export": "导出",
        "common.import": "导入",
        "common.upload": "上传",
        "common.download": "下载",
        "common.refresh": "刷新",
        "common.apply": "应用",
        "common.back": "返回",
        "common.next": "下一步",
        "common.finish": "完成",
        "common.yes": "是",
        "common.no": "否",
        # Auth
        "auth.login": "登录",
        "auth.register": "注册",
        "auth.logout": "退出",
        "auth.username": "用户名",
        "auth.password": "密码",
        "auth.email": "邮箱",
        "auth.confirm_password": "确认密码",
        "auth.forgot_password": "忘记密码？",
        "auth.login_success": "登录成功",
        "auth.login_failed": "用户名或密码错误",
        "auth.register_success": "注册成功",
        "auth.register_failed": "注册失败",
        "auth.token_expired": "会话已过期，请重新登录",
        # Project
        "project.new": "新建项目",
        "project.open": "打开项目",
        "project.save": "保存项目",
        "project.delete": "删除项目",
        "project.share": "分享项目",
        "project.name": "项目名称",
        "project.description": "描述",
        "project.created": "项目已创建",
        "project.saved": "项目已保存",
        "project.deleted": "项目已删除",
        # PCB Editor
        "pcb.title": "PCB 编辑器",
        "pcb.place_component": "放置元件",
        "pcb.route": "布线",
        "pcb.add_via": "添加过孔",
        "pcb.add_zone": "添加铺铜",
        "pcb.run_drc": "运行 DRC",
        "pcb.export_gerber": "导出 Gerber",
        "pcb.zoom_in": "放大",
        "pcb.zoom_out": "缩小",
        "pcb.fit_view": "适应视图",
        "pcb.select_all": "全选",
        "pcb.delete_selected": "删除选中",
        "pcb.rotate_cw": "顺时针旋转",
        "pcb.rotate_ccw": "逆时针旋转",
        "pcb.flip": "翻面",
        "pcb.move": "移动",
        "pcb.copy": "复制",
        "pcb.paste": "粘贴",
        # Schematic
        "schematic.title": "原理图编辑器",
        "schematic.place_symbol": "放置符号",
        "schematic.add_wire": "添加导线",
        "schematic.add_label": "添加标签",
        "schematic.annotate": "标注",
        "schematic.erc": "运行 ERC",
        # DRC
        "drc.title": "设计规则检查",
        "drc.running": "正在运行 DRC...",
        "drc.complete": "DRC 完成",
        "drc.errors": "错误",
        "drc.warnings": "警告",
        "drc.no_violations": "无违规！",
        "drc.clearance": "间距违规",
        "drc.short_circuit": "短路",
        "drc.unconnected": "未连接网络",
        "drc.width": "线宽违规",
        # Manufacturing
        "mfg.title": "制造",
        "mfg.generate": "生成制造文件",
        "mfg.gerber": "Gerber 文件",
        "mfg.bom": "物料清单",
        "mfg.pnp": "贴片文件",
        "mfg.order_package": "下单包",
        "mfg.jlcpcb": "嘉立创",
        "mfg.pcbway": "PCBWay",
        "mfg.cost_estimate": "成本估算",
        "mfg.checking": "正在检查可制造性...",
        # Collaboration
        "collab.title": "协作",
        "collab.share_link": "分享链接",
        "collab.users_online": "{count} 人在线",
        "collab.history": "版本历史",
        "collab.rollback": "回滚",
        "collab.snapshot": "创建快照",
        # Marketplace
        "market.title": "模板市场",
        "market.search": "搜索模板...",
        "market.featured": "精选",
        "market.categories": "分类",
        "market.download": "下载",
        "market.rate": "评分",
        "market.upload": "上传模板",
        # AI
        "ai.title": "AI 助手",
        "ai.generate": "生成",
        "ai.analyzing": "分析中...",
        "ai.suggestion": "AI 建议",
        "ai.optimize": "优化",
        "ai.auto_route": "自动布线",
        "ai.auto_place": "自动布局",
    },
    "ja-JP": {
        # Common
        "app.title": "KiCad AI Auto",
        "app.tagline": "AI駆動PCBデザイン自動化",
        "common.save": "保存",
        "common.cancel": "キャンセル",
        "common.delete": "削除",
        "common.close": "閉じる",
        "common.confirm": "確認",
        "common.loading": "読み込み中...",
        "common.error": "エラー",
        "common.success": "成功",
        "common.warning": "警告",
        "common.search": "検索",
        "common.filter": "フィルタ",
        "common.export": "エクスポート",
        "common.import": "インポート",
        "common.upload": "アップロード",
        "common.download": "ダウンロード",
        "common.refresh": "更新",
        "common.apply": "適用",
        "common.back": "戻る",
        "common.next": "次へ",
        "common.finish": "完了",
        "common.yes": "はい",
        "common.no": "いいえ",
        # Auth
        "auth.login": "ログイン",
        "auth.register": "新規登録",
        "auth.logout": "ログアウト",
        "auth.username": "ユーザー名",
        "auth.password": "パスワード",
        "auth.email": "メール",
        "auth.confirm_password": "パスワード確認",
        "auth.forgot_password": "パスワードをお忘れですか？",
        "auth.login_success": "ログインしました",
        "auth.login_failed": "認証に失敗しました",
        "auth.register_success": "登録しました",
        "auth.register_failed": "登録に失敗しました",
        "auth.token_expired": "セッションが期限切れです",
        # Project
        "project.new": "新規プロジェクト",
        "project.open": "プロジェクトを開く",
        "project.save": "保存",
        "project.delete": "削除",
        "project.share": "共有",
        "project.name": "プロジェクト名",
        "project.description": "説明",
        "project.created": "プロジェクトを作成しました",
        "project.saved": "保存しました",
        "project.deleted": "削除しました",
        # PCB Editor
        "pcb.title": "PCBエディタ",
        "pcb.place_component": "コンポーネント配置",
        "pcb.route": "配線",
        "pcb.add_via": "ビア追加",
        "pcb.add_zone": "銅箔追加",
        "pcb.run_drc": "DRC実行",
        "pcb.export_gerber": "Gerber出力",
        "pcb.zoom_in": "ズームイン",
        "pcb.zoom_out": "ズームアウト",
        "pcb.fit_view": "全体表示",
        "pcb.select_all": "全選択",
        "pcb.delete_selected": "選択削除",
        "pcb.rotate_cw": "時計回り回転",
        "pcb.rotate_ccw": "反時計回り回転",
        "pcb.flip": "裏面反転",
        "pcb.move": "移動",
        "pcb.copy": "コピー",
        "pcb.paste": "貼り付け",
        # DRC
        "drc.title": "設計ルールチェック",
        "drc.running": "DRC実行中...",
        "drc.complete": "DRC完了",
        "drc.errors": "エラー",
        "drc.warnings": "警告",
        "drc.no_violations": "違反なし！",
        # Manufacturing
        "mfg.title": "製造",
        "mfg.generate": "製造ファイル生成",
        "mfg.gerber": "Gerberファイル",
        "mfg.bom": "部品表",
        "mfg.order_package": "注文パッケージ",
        "mfg.cost_estimate": "コスト見積もり",
        # AI
        "ai.title": "AIアシスタント",
        "ai.generate": "生成",
        "ai.analyzing": "分析中...",
        "ai.auto_route": "自動配線",
        "ai.auto_place": "自動配置",
    },
}


class I18nService:
    """
    Internationalization service with string lookup and interpolation.
    """

    SUPPORTED_LANGUAGES = ["en-US", "zh-CN", "ja-JP"]
    DEFAULT_LANGUAGE = "en-US"

    def __init__(self):
        self._translations = TRANSLATIONS.copy()
        self._fallback_lang = self.DEFAULT_LANGUAGE

    def get(self, key: str, lang: str = "", **kwargs) -> str:
        """
        Get translated string by key.

        Falls back to default language if key not found in requested language.
        Supports interpolation: get("collab.users_online", lang, count=5)
        """
        lang = self._normalize_lang(lang or self._fallback_lang)
        strings = self._translations.get(lang, {})

        value = strings.get(key)
        if value is None:
            # Fallback to default language
            strings = self._translations.get(self._fallback_lang, {})
            value = strings.get(key, key)

        # Interpolate
        if kwargs:
            try:
                value = value.format(**kwargs)
            except (KeyError, IndexError):
                pass

        return value

    def get_all(self, lang: str = "") -> Dict[str, str]:
        """Get all translations for a language."""
        lang = self._normalize_lang(lang or self._fallback_lang)
        # Merge with fallback
        result = dict(self._translations.get(self._fallback_lang, {}))
        result.update(self._translations.get(lang, {}))
        return result

    def get_languages(self) -> List[Dict[str, str]]:
        """Get list of supported languages."""
        return [
            {"code": "en-US", "name": "English", "native": "English"},
            {"code": "zh-CN", "name": "Chinese (Simplified)", "native": "简体中文"},
            {"code": "ja-JP", "name": "Japanese", "native": "日本語"},
        ]

    def detect_language(self, accept_language: str) -> str:
        """
        Detect language from Accept-Language header.

        Example: "zh-CN,zh;q=0.9,en;q=0.8"
        """
        if not accept_language:
            return self._fallback_lang

        # Parse Accept-Language header
        languages = []
        for part in accept_language.split(","):
            part = part.strip()
            if ";q=" in part:
                lang, q = part.split(";q=")
                languages.append((lang.strip(), float(q)))
            else:
                languages.append((part, 1.0))

        # Sort by quality
        languages.sort(key=lambda x: x[1], reverse=True)

        for lang, _ in languages:
            normalized = self._normalize_lang(lang)
            if normalized in self._translations:
                return normalized

        return self._fallback_lang

    def add_translation(self, lang: str, key: str, value: str):
        """Add or update a translation string."""
        lang = self._normalize_lang(lang)
        if lang not in self._translations:
            self._translations[lang] = {}
        self._translations[lang][key] = value

    def _normalize_lang(self, lang: str) -> str:
        """Normalize language code (e.g., 'zh' -> 'zh-CN')."""
        lang = lang.strip()
        # Direct match
        if lang in self._translations:
            return lang
        # Prefix match (zh -> zh-CN)
        for supported in self.SUPPORTED_LANGUAGES:
            if supported.startswith(lang):
                return supported
        return self._fallback_lang


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_i18n_service: Optional[I18nService] = None


def get_i18n_service() -> I18nService:
    global _i18n_service
    if _i18n_service is None:
        _i18n_service = I18nService()
    return _i18n_service
