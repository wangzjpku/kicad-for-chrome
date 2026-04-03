"""
Custom DRC Rules Engine

Provides:
- User-defined DRC rules with Python-like expressions
- Rule templates for common checks
- Rule CRUD and execution
- Custom severity levels (error, warning, info)
- Rule categories (electrical, mechanical, manufacturing)

Rules are expressed as condition expressions evaluated against PCB items.
Safe evaluation using AST parsing (no arbitrary code execution).
"""

from __future__ import annotations

import ast
import json
import logging
import operator
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ---- Data Models ----

@dataclass
class DRCRule:
    """A custom DRC rule definition."""
    id: str
    name: str
    description: str
    category: str  # electrical, mechanical, manufacturing, signal_integrity
    severity: str  # error, warning, info
    condition: str  # Python-like expression
    item_types: List[str]  # component, track, via, pad, zone
    check_function: str  # built-in check name or custom
    parameters: Dict[str, Any] = field(default_factory=dict)
    author_id: str = ""
    is_public: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class DRCViolation:
    """A DRC violation found by a custom rule."""
    rule_id: str
    rule_name: str
    severity: str
    category: str
    message: str
    item_ids: List[str]
    location: Optional[Dict[str, float]] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DRCReport:
    """Result of running custom DRC checks."""
    total_rules: int
    violations: List[DRCViolation]
    run_time_ms: float
    timestamp: float = field(default_factory=time.time)

    @property
    def error_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "warning")

    @property
    def info_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "info")


# ---- Safe Expression Evaluator ----

SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.And: lambda a, b: a and b,
    ast.Or: lambda a, b: a or b,
    ast.Not: operator.not_,
    ast.USub: operator.neg,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
}

SAFE_FUNCTIONS = {
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
    "len": len,
    "sqrt": lambda x: x**0.5,
    "hypot": lambda a, b: (a**2 + b**2)**0.5,
}


class SafeEvaluator:
    """
    Safely evaluate Python-like expressions for DRC rules.
    Uses AST parsing to prevent code injection.
    """

    def __init__(self, context: Dict[str, Any]):
        self.context = context

    def evaluate(self, expression: str) -> Any:
        try:
            tree = ast.parse(expression, mode="eval")
            return self._eval_node(tree.body)
        except Exception as e:
            logger.debug(f"Expression evaluation failed: {e}")
            return False

    def _eval_node(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            return self.context.get(node.id, None)
        elif isinstance(node, ast.Attribute):
            value = self._eval_node(node.value)
            return getattr(value, node.attr, None) if value else None
        elif isinstance(node, ast.Compare):
            left = self._eval_node(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator)
                op_type = type(op)
                if op_type in SAFE_OPERATORS:
                    if not SAFE_OPERATORS[op_type](left, right):
                        return False
                left = right
            return True
        elif isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(self._eval_node(v) for v in node.values)
            return any(self._eval_node(v) for v in node.values)
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            op_type = type(node.op)
            return SAFE_OPERATORS.get(op_type, lambda x: x)(operand)
        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            op_type = type(node.op)
            return SAFE_OPERATORS.get(op_type, lambda a, b: None)(left, right)
        elif isinstance(node, ast.Call):
            func_name = node.func.id if isinstance(node.func, ast.Name) else ""
            if func_name in SAFE_FUNCTIONS:
                args = [self._eval_node(a) for a in node.args]
                return SAFE_FUNCTIONS[func_name](*args)
            return None
        elif isinstance(node, ast.List):
            return [self._eval_node(e) for e in node.elts]
        elif isinstance(node, ast.Subscript):
            value = self._eval_node(node.value)
            index = self._eval_node(node.slice)
            try:
                return value[index] if value else None
            except (IndexError, KeyError, TypeError):
                return None
        return None


# ---- Built-in Check Functions ----

BUILTIN_CHECKS: Dict[str, Callable] = {}


def register_check(name: str):
    """Decorator to register a built-in DRC check function."""
    def decorator(fn):
        BUILTIN_CHECKS[name] = fn
        return fn
    return decorator


@register_check("min_clearance")
def check_min_clearance(items: List[Dict], params: Dict) -> List[DRCViolation]:
    """Check minimum clearance between items."""
    clearance = params.get("clearance", 0.25)  # mm
    violations = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a = items[i]
            b = items[j]
            # Skip items on different nets
            if a.get("net") and b.get("net") and a["net"] == b["net"]:
                continue
            # Calculate distance between bounding boxes
            bbox_a = a.get("bbox", {})
            bbox_b = b.get("bbox", {})
            dx = max(0, max(bbox_a.get("x1", 0), bbox_b.get("x1", 0)) -
                     min(bbox_a.get("x2", 0), bbox_b.get("x2", 0)))
            dy = max(0, max(bbox_a.get("y1", 0), bbox_b.get("y1", 0)) -
                     min(bbox_a.get("y2", 0), bbox_b.get("y2", 0)))
            dist = (dx**2 + dy**2)**0.5
            if dist < clearance and dist > 0:
                violations.append(DRCViolation(
                    rule_id="min_clearance",
                    rule_name="Minimum Clearance",
                    severity="error",
                    category="electrical",
                    message=f"Clearance {dist:.3f}mm < {clearance}mm between {a.get('id','?')} and {b.get('id','?')}",
                    item_ids=[a.get("id", ""), b.get("id", "")],
                ))
    return violations


@register_check("min_track_width")
def check_min_track_width(items: List[Dict], params: Dict) -> List[DRCViolation]:
    """Check minimum track width."""
    min_width = params.get("min_width", 0.15)
    violations = []
    for item in items:
        if item.get("type") != "track":
            continue
        width = item.get("width", 0)
        if width < min_width:
            violations.append(DRCViolation(
                rule_id="min_track_width",
                rule_name="Minimum Track Width",
                severity="error",
                category="manufacturing",
                message=f"Track {item.get('id','')} width {width}mm < {min_width}mm",
                item_ids=[item.get("id", "")],
            ))
    return violations


@register_check("min_drill_size")
def check_min_drill_size(items: List[Dict], params: Dict) -> List[DRCViolation]:
    """Check minimum drill hole size."""
    min_drill = params.get("min_drill", 0.3)
    violations = []
    for item in items:
        drill = item.get("drill", 0)
        if drill > 0 and drill < min_drill:
            violations.append(DRCViolation(
                rule_id="min_drill_size",
                rule_name="Minimum Drill Size",
                severity="error",
                category="manufacturing",
                message=f"Via {item.get('id','')} drill {drill}mm < {min_drill}mm",
                item_ids=[item.get("id", "")],
            ))
    return violations


@register_check("unconnected_net")
def check_unconnected_net(items: List[Dict], params: Dict) -> List[DRCViolation]:
    """Check for nets with only one connection."""
    net_items: Dict[str, List[str]] = {}
    for item in items:
        net = item.get("net", "")
        if net:
            net_items.setdefault(net, []).append(item.get("id", ""))

    violations = []
    for net, item_ids in net_items.items():
        if len(item_ids) == 1:
            violations.append(DRCViolation(
                rule_id="unconnected_net",
                rule_name="Unconnected Net",
                severity="warning",
                category="electrical",
                message=f"Net '{net}' has only 1 connection",
                item_ids=item_ids,
            ))
    return violations


@register_check("silk_over_pad")
def check_silk_over_pad(items: List[Dict], params: Dict) -> List[DRCViolation]:
    """Check for silkscreen overlapping pads."""
    violations = []
    pads = [i for i in items if i.get("type") == "pad"]
    silkscreen = [i for i in items if i.get("layer", "").startswith("F.SilkS")]

    for pad in pads:
        pad_bbox = pad.get("bbox", {})
        for silk in silkscreen:
            silk_bbox = silk.get("bbox", {})
            # Simple overlap check
            if (pad_bbox.get("x1", 0) < silk_bbox.get("x2", 0) and
                pad_bbox.get("x2", 0) > silk_bbox.get("x1", 0) and
                pad_bbox.get("y1", 0) < silk_bbox.get("y2", 0) and
                pad_bbox.get("y2", 0) > silk_bbox.get("y1", 0)):
                violations.append(DRCViolation(
                    rule_id="silk_over_pad",
                    rule_name="Silkscreen Over Pad",
                    severity="warning",
                    category="manufacturing",
                    message=f"Silkscreen overlaps pad {pad.get('id','')}",
                    item_ids=[pad.get("id", ""), silk.get("id", "")],
                ))
    return violations


# ---- Custom DRC Service ----

RULE_TEMPLATES = [
    {
        "name": "Minimum Clearance",
        "description": "Check minimum clearance between copper items",
        "category": "electrical",
        "severity": "error",
        "check_function": "min_clearance",
        "parameters": {"clearance": 0.25},
        "item_types": ["track", "pad", "via", "zone"],
    },
    {
        "name": "Minimum Track Width",
        "description": "Check minimum trace width for manufacturability",
        "category": "manufacturing",
        "severity": "error",
        "check_function": "min_track_width",
        "parameters": {"min_width": 0.15},
        "item_types": ["track"],
    },
    {
        "name": "Minimum Drill Size",
        "description": "Check minimum via/hole drill diameter",
        "category": "manufacturing",
        "severity": "error",
        "check_function": "min_drill_size",
        "parameters": {"min_drill": 0.3},
        "item_types": ["via", "pad"],
    },
    {
        "name": "Unconnected Nets",
        "description": "Find nets with only one connection",
        "category": "electrical",
        "severity": "warning",
        "check_function": "unconnected_net",
        "parameters": {},
        "item_types": ["track", "pad", "via"],
    },
    {
        "name": "Silkscreen Over Pad",
        "description": "Check for silkscreen overlapping solder pads",
        "category": "manufacturing",
        "severity": "warning",
        "check_function": "silk_over_pad",
        "parameters": {},
        "item_types": ["pad"],
    },
]


class CustomDRCService:
    """
    Custom DRC rules management and execution service.
    """

    def __init__(self, data_dir: Optional[str] = None):
        self._data_dir = data_dir or os.path.join(
            os.path.dirname(__file__), "..", "data", "drc_rules"
        )
        os.makedirs(self._data_dir, exist_ok=True)
        self._rules: Dict[str, DRCRule] = {}
        self._load()

    def _data_file(self) -> str:
        return os.path.join(self._data_dir, "custom_rules.json")

    def _load(self):
        path = self._data_file()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r") as f:
                data = json.load(f)
            for rid, rdata in data.items():
                self._rules[rid] = DRCRule(**rdata)
            logger.info(f"Loaded {len(self._rules)} custom DRC rules")
        except Exception as e:
            logger.warning(f"Failed to load custom DRC rules: {e}")

    def _save(self):
        path = self._data_file()
        try:
            data = {}
            for rid, rule in self._rules.items():
                data[rid] = {
                    "id": rule.id, "name": rule.name,
                    "description": rule.description,
                    "category": rule.category, "severity": rule.severity,
                    "condition": rule.condition,
                    "item_types": rule.item_types,
                    "check_function": rule.check_function,
                    "parameters": rule.parameters,
                    "author_id": rule.author_id,
                    "is_public": rule.is_public,
                    "created_at": rule.created_at,
                    "updated_at": rule.updated_at,
                }
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save custom DRC rules: {e}")

    # ---- CRUD ----

    def create_rule(
        self,
        name: str,
        description: str,
        category: str,
        severity: str,
        check_function: str,
        parameters: Dict[str, Any],
        item_types: List[str],
        condition: str = "",
        author_id: str = "",
        is_public: bool = False,
    ) -> Dict[str, Any]:
        rule_id = str(uuid.uuid4())
        rule = DRCRule(
            id=rule_id,
            name=name,
            description=description,
            category=category,
            severity=severity,
            condition=condition,
            item_types=item_types,
            check_function=check_function,
            parameters=parameters,
            author_id=author_id,
            is_public=is_public,
        )
        self._rules[rule_id] = rule
        self._save()
        return {"id": rule_id, "name": name, "status": "created"}

    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        rule = self._rules.get(rule_id)
        if not rule:
            return None
        return {
            "id": rule.id, "name": rule.name,
            "description": rule.description,
            "category": rule.category, "severity": rule.severity,
            "condition": rule.condition,
            "item_types": rule.item_types,
            "check_function": rule.check_function,
            "parameters": rule.parameters,
            "author_id": rule.author_id,
            "is_public": rule.is_public,
        }

    def list_rules(
        self,
        category: Optional[str] = None,
        include_public: bool = True,
    ) -> List[Dict[str, Any]]:
        results = []
        for rule in self._rules.values():
            if category and rule.category != category:
                continue
            results.append({
                "id": rule.id, "name": rule.name,
                "description": rule.description,
                "category": rule.category, "severity": rule.severity,
                "check_function": rule.check_function,
                "item_types": rule.item_types,
                "is_public": rule.is_public,
            })
        return results

    def delete_rule(self, rule_id: str) -> bool:
        if rule_id in self._rules:
            del self._rules[rule_id]
            self._save()
            return True
        return False

    def get_templates(self) -> List[Dict[str, Any]]:
        return RULE_TEMPLATES

    # ---- Execution ----

    def run_checks(
        self,
        pcb_items: List[Dict[str, Any]],
        rule_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Run custom DRC checks against PCB items."""
        start = time.time()
        all_violations: List[DRCViolation] = []
        rules_to_run = []

        if rule_ids:
            rules_to_run = [self._rules[rid] for rid in rule_ids if rid in self._rules]
        else:
            rules_to_run = list(self._rules.values())

        for rule in rules_to_run:
            # Filter items by type
            filtered = [
                item for item in pcb_items
                if item.get("type", "") in rule.item_types or not rule.item_types
            ]

            # Run built-in check
            check_fn = BUILTIN_CHECKS.get(rule.check_function)
            if check_fn:
                violations = check_fn(filtered, rule.parameters)
                for v in violations:
                    v.rule_id = rule.id
                    v.rule_name = rule.name
                    v.severity = rule.severity
                    v.category = rule.category
                all_violations.extend(violations)
            elif rule.condition:
                # Run expression-based check
                evaluator = SafeEvaluator({})
                for item in filtered:
                    ctx = {
                        "item": item,
                        "width": item.get("width", 0),
                        "drill": item.get("drill", 0),
                        "layer": item.get("layer", ""),
                        "net": item.get("net", ""),
                        **rule.parameters,
                    }
                    evaluator.context = ctx
                    if evaluator.evaluate(rule.condition):
                        all_violations.append(DRCViolation(
                            rule_id=rule.id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            category=rule.category,
                            message=f"Rule '{rule.name}' violated by {item.get('id', '?')}",
                            item_ids=[item.get("id", "")],
                            details=item,
                        ))

        run_time = (time.time() - start) * 1000

        report = DRCReport(
            total_rules=len(rules_to_run),
            violations=all_violations,
            run_time_ms=run_time,
        )

        return {
            "total_rules": report.total_rules,
            "violations": [
                {
                    "rule_id": v.rule_id,
                    "rule_name": v.rule_name,
                    "severity": v.severity,
                    "category": v.category,
                    "message": v.message,
                    "item_ids": v.item_ids,
                    "details": v.details,
                }
                for v in report.violations
            ],
            "summary": {
                "errors": report.error_count,
                "warnings": report.warning_count,
                "info": report.info_count,
            },
            "run_time_ms": round(run_time, 2),
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_custom_drc: Optional[CustomDRCService] = None


def get_custom_drc_service() -> CustomDRCService:
    global _custom_drc
    if _custom_drc is None:
        _custom_drc = CustomDRCService()
    return _custom_drc
