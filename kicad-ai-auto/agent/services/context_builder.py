# -*- coding: utf-8 -*-
"""
Context Builder - AI 上下文构建器

为 AI 对话构建项目上下文，使其能够理解当前设计状态。

功能:
- 从原理图数据构建上下文描述
- 从 PCB 数据构建上下文描述
- 提取关键元件和网络信息
- 生成结构化的上下文提示
"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class ContextBuilder:
    """AI 上下文构建器"""

    def __init__(self):
        self.max_components_shown = 10  # 最多显示的元件数量
        self.max_nets_shown = 15       # 最多显示的网络数量
        self.max_wires_shown = 20     # 最多显示的导线数量

    def build_schematic_context(
        self,
        schematic_data: Dict[str, Any],
        project_name: str = "未知项目",
    ) -> str:
        """
        从原理图数据构建上下文描述

        Args:
            schematic_data: 原理图数据字典
            project_name: 项目名称

        Returns:
            结构化的上下文描述字符串
        """
        context_parts = []

        # 项目基本信息
        context_parts.append(f"项目：{project_name}")

        # 元件统计
        components = schematic_data.get("components", [])
        if components:
            context_parts.append(f"元件总数：{len(components)}")

            # 关键元件列表（按类型分组）
            component_types: Dict[str, List[str]] = {}
            for comp in components:
                comp_type = comp.get("name", "Unknown")
                ref = comp.get("reference", "?")
                if comp_type not in component_types:
                    component_types[comp_type] = []
                component_types[comp_type].append(ref)

            # 显示前几个类型
            type_summary = []
            for comp_type, refs in list(component_types.items())[:5]:
                type_summary.append(f"{comp_type}({', '.join(refs[:3])})")
            if type_summary:
                context_parts.append(f"主要元件：{', '.join(type_summary)}")

        # 网络统计
        nets = schematic_data.get("nets", [])
        if nets:
            context_parts.append(f"网络总数：{len(nets)}")

            # 列出关键网络
            power_nets = [n.get("name", "") for n in nets if self._is_power_net(n)]
            if power_nets:
                context_parts.append(f"电源网络：{', '.join(power_nets[:5])}")

        # 导线统计
        wires = schematic_data.get("wires", [])
        if wires:
            context_parts.append(f"导线总数：{len(wires)}")

        return "\n".join(context_parts)

    def build_pcb_context(
        self,
        pcb_data: Dict[str, Any],
        project_name: str = "未知项目",
    ) -> str:
        """
        从 PCB 数据构建上下文描述

        Args:
            pcb_data: PCB 数据字典
            project_name: 项目名称

        Returns:
            结构化的上下文描述字符串
        """
        context_parts = []

        # 项目基本信息
        context_parts.append(f"项目：{project_name}")

        # PCB 参数
        if pcb_data.get("layer_count"):
            context_parts.append(f"PCB层数：{pcb_data['layer_count']}")

        if pcb_data.get("board_width") and pcb_data.get("board_height"):
            context_parts.append(
                f"板子尺寸：{pcb_data['board_width']}mm x {pcb_data['board_height']}mm"
            )

        # 元件封装
        footprints = pcb_data.get("footprints", [])
        if footprints:
            context_parts.append(f"封装总数：{len(footprints)}")

            # 按封装类型分组
            footprint_types: Dict[str, int] = {}
            for fp in footprints:
                fp_type = fp.get("footprint", "Unknown")
                footprint_types[fp_type] = footprint_types.get(fp_type, 0) + 1

            # 显示前几个封装类型
            type_summary = [
                f"{fp_type}({count})"
                for fp_type, count in list(footprint_types.items())[:3]
            ]
            if type_summary:
                context_parts.append(f"主要封装：{', '.join(type_summary)}")

        # 网络
        nets = pcb_data.get("nets", [])
        if nets:
            context_parts.append(f"网络总数：{len(nets)}")

        # 布线率（如果有）
        if pcb_data.get("routing_completion"):
            context_parts.append(
                f"布线完成率：{pcb_data['routing_completion']}%"
            )

        return "\n".join(context_parts)

    def build_full_context(
        self,
        project_id: str,
        schematic_data: Optional[Dict[str, Any]] = None,
        pcb_data: Optional[Dict[str, Any]] = None,
        project_name: str = "未知项目",
        drc_state: Optional[Dict[str, Any]] = None,
        layout_state: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        构建完整的项目上下文

        Args:
            project_id: 项目ID
            schematic_data: 原理图数据
            pcb_data: PCB 数据
            project_name: 项目名称
            drc_state: DRC检查结果状态
            layout_state: 布局优化状态

        Returns:
            完整的上下文描述字符串
        """
        context_parts = [
            f"=== 项目上下文 ===",
            f"项目ID：{project_id}",
            f"项目名称：{project_name}",
        ]

        if schematic_data:
            schematic_context = self.build_schematic_context(
                schematic_data, project_name
            )
            context_parts.append("")
            context_parts.append("【原理图信息】")
            context_parts.append(schematic_context)

        if pcb_data:
            pcb_context = self.build_pcb_context(pcb_data, project_name)
            context_parts.append("")
            context_parts.append("【PCB信息】")
            context_parts.append(pcb_context)

        # Phase 10C: DRC state context
        if drc_state:
            context_parts.append("")
            context_parts.append("【DRC状态】")
            errors = drc_state.get("error_count", 0)
            warnings = drc_state.get("warning_count", 0)
            context_parts.append(f"DRC错误: {errors}, 警告: {warnings}")
            passed = drc_state.get("passed", errors == 0 and warnings == 0)
            context_parts.append(f"检查结果: {'通过' if passed else '未通过'}")
            top_violations = drc_state.get("top_violations", [])
            if top_violations:
                context_parts.append("主要违规:")
                for v in top_violations[:5]:
                    context_parts.append(f"  - {v}")

        # Phase 10C: Layout optimization state
        if layout_state:
            context_parts.append("")
            context_parts.append("【布局状态】")
            density = layout_state.get("density")
            if density:
                context_parts.append(f"布局密度: {density}")
            routing_pct = layout_state.get("routing_pct")
            if routing_pct is not None:
                context_parts.append(f"布线完成率: {routing_pct}%")
            score = layout_state.get("score")
            if score is not None:
                context_parts.append(f"布局评分: {score}/100")
            hotspot_components = layout_state.get("hotspot_components", [])
            if hotspot_components:
                context_parts.append(f"需要关注的元件: {', '.join(hotspot_components[:5])}")

        context_parts.append("")
        context_parts.append("请根据以上上下文信息，帮助用户进行电路设计。")

        return "\n".join(context_parts)

    def build_conversation_context(
        self,
        conversation_messages: List[Dict[str, Any]],
        max_messages: int = 10,
    ) -> str:
        """
        从对话历史构建上下文

        Args:
            conversation_messages: 对话消息列表
            max_messages: 最多包含的消息数

        Returns:
            对话上下文描述字符串
        """
        if not conversation_messages:
            return ""

        # 取最近的消息
        recent = conversation_messages[-max_messages:]

        context_parts = ["=== 对话历史 ==="]
        for msg in recent:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            # 截断过长的消息
            if len(content) > 200:
                content = content[:200] + "..."
            role_label = "用户" if role == "user" else "助手"
            context_parts.append(f"{role_label}：{content}")

        return "\n".join(context_parts)

    def _is_power_net(self, net: Dict[str, Any]) -> bool:
        """判断是否为电源网络"""
        net_name = net.get("name", "").lower()
        power_keywords = ["vcc", "vdd", "gnd", "vss", "power", "avdd", "dvdd"]
        return any(kw in net_name for kw in power_keywords)


# 全局实例
_context_builder: Optional[ContextBuilder] = None


def get_context_builder() -> ContextBuilder:
    """获取全局上下文构建器实例"""
    global _context_builder
    if _context_builder is None:
        _context_builder = ContextBuilder()
    return _context_builder


def build_project_context(
    project_id: str,
    schematic_data: Optional[Dict[str, Any]] = None,
    pcb_data: Optional[Dict[str, Any]] = None,
    project_name: str = "未知项目",
    drc_state: Optional[Dict[str, Any]] = None,
    layout_state: Optional[Dict[str, Any]] = None,
) -> str:
    """
    便捷函数：构建项目上下文

    Args:
        project_id: 项目ID
        schematic_data: 原理图数据
        pcb_data: PCB 数据
        project_name: 项目名称
        drc_state: DRC检查结果
        layout_state: 布局状态

    Returns:
        项目上下文描述字符串
    """
    builder = get_context_builder()
    return builder.build_full_context(
        project_id=project_id,
        schematic_data=schematic_data,
        pcb_data=pcb_data,
        project_name=project_name,
        drc_state=drc_state,
        layout_state=layout_state,
    )
