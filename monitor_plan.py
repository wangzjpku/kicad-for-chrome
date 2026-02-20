#!/usr/bin/env python3
"""
计划进度监控循环脚本
功能:
1. 每60秒检查plan2.txt和todo2.txt
2. 分析「计划进度」，补充缺失的细节（如任务开始/结束时间）
3. 检查「逾期任务」，在plan2.txt中标记「需调整优先级」
4. 有修改才保存，无修改则跳过
5. 检测stop_loop.flag文件存在时停止循环
"""

import os
import re
import time
import hashlib
from datetime import datetime
from pathlib import Path

# 配置
INTERVAL = 60  # 秒
TARGET_FILES = ["plan2.txt", "todo2.txt"]
STOP_FLAG = "stop_loop.flag"
WORKDIR = Path(r"E:\0-007-MyAIOS\projects\1-kicad-for-chrome")


def get_file_hash(filepath: Path) -> str:
    """计算文件内容hash"""
    if not filepath.exists():
        return ""
    return hashlib.md5(filepath.read_text(encoding="utf-8").encode()).hexdigest()


def read_file(filepath: Path) -> str:
    """读取文件内容"""
    if not filepath.exists():
        return ""
    return filepath.read_text(encoding="utf-8")


def write_file(filepath: Path, content: str) -> str:
    """写入文件内容"""
    filepath.write_text(content, encoding="utf-8")


def get_current_timestamp() -> str:
    """获取当前时间戳"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def analyze_plan_progress(plan_content: str) -> tuple[str, bool]:
    """
    分析计划进度，补充缺失的细节
    1. 为没有开始时间的任务添加开始时间
    2. 根据任务状态推断结束时间
    返回: (修改后的内容, 是否有修改)
    """
    modified = False
    lines = plan_content.split("\n")
    new_lines = []

    # 匹配任务行的正则: □ Task X.X 或 ☑ Task X.X
    task_pattern = re.compile(r"^(\s*)(□|☑)\s+(Task\s+\d+\.\d+):(.+)$")

    # 当前时间
    current_time = get_current_timestamp()

    for line in lines:
        match = task_pattern.match(line)
        if match:
            indent, status, task_name, task_desc = match.groups()
            original_line = line

            # 如果没有时间戳，添加开始时间
            if "开始:" not in line and "结束:" not in line:
                if status == "☑":
                    # 已完成任务，添加开始和结束时间
                    line = f"{indent}{status} {task_name}:{task_desc} [开始: {current_time}] [结束: {current_time}]"
                elif status == "□":
                    # 未开始任务，只添加计划开始时间
                    line = f"{indent}{status} {task_name}:{task_desc} [计划开始: {current_time}]"
                modified = True

            # 如果只有开始时间没有结束时间，且任务已完成
            elif "开始:" in line and "结束:" not in line and status == "☑":
                line = f"{line.rstrip()} [结束: {current_time}]"
                modified = True

        new_lines.append(line)

    if modified:
        return "\n".join(new_lines), True
    return plan_content, False


def check_overdue_tasks(todo_content: str, plan_content: str) -> tuple[str, bool]:
    """
    检查todo2.txt中的逾期任务，在plan2.txt中标记「需调整优先级」
    返回: (修改后的plan内容, 是否有修改)
    """
    modified = False

    # 从todo中提取逾期任务
    # 查找类似 "□ Task X.X" 且超过预定时间的任务
    overdue_pattern = re.compile(
        r"□\s+(Task\s+\d+\.\d+):(.+?)(?=\n□|\n☑|\n---|\Z)", re.DOTALL
    )

    overdue_matches = overdue_pattern.findall(todo_content)
    overdue_tasks = [match[0].strip() for match in overdue_matches]

    if not overdue_tasks:
        return plan_content, False

    # 在plan中标记逾期任务
    lines = plan_content.split("\n")
    new_lines = []

    for line in lines:
        for task_name in overdue_tasks:
            if task_name in line and "需调整优先级" not in line:
                line = f"{line.rstrip()} [需调整优先级]"
                modified = True
        new_lines.append(line)

    if modified:
        return "\n".join(new_lines), True
    return plan_content, False


def main():
    """主循环"""
    print(f"[{get_current_timestamp()}] 计划监控循环启动")
    print(f"[{get_current_timestamp()}] 监控文件: {TARGET_FILES}")
    print(f"[{get_current_timestamp()}] 停止标志: {STOP_FLAG}")
    print(f"[{get_current_timestamp()}] 间隔: {INTERVAL}秒")
    print("-" * 60)

    # 记录文件初始hash
    file_hashes = {f: get_file_hash(WORKDIR / f) for f in TARGET_FILES}

    while True:
        # 检查停止标志
        if (WORKDIR / STOP_FLAG).exists():
            print(f"[{get_current_timestamp()}] 检测到停止标志，退出循环")
            break

        has_changes = False

        # 检查文件变化
        for filename in TARGET_FILES:
            filepath = WORKDIR / filename
            current_hash = get_file_hash(filepath)

            if current_hash != file_hashes.get(filename, ""):
                print(f"[{get_current_timestamp()}] 检测到 {filename} 变化")
                file_hashes[filename] = current_hash
                has_changes = True

        if has_changes:
            print(f"[{get_current_timestamp()}] 执行分析...")

            # 读取文件
            plan_content = read_file(WORKDIR / "plan2.txt")
            todo_content = read_file(WORKDIR / "todo2.txt")

            # 1. 分析计划进度
            new_plan, plan_modified = analyze_plan_progress(plan_content)

            # 2. 检查逾期任务
            new_plan, overdue_modified = check_overdue_tasks(todo_content, new_plan)

            # 3. 保存修改
            if plan_modified or overdue_modified:
                write_file(WORKDIR / "plan2.txt", new_plan)
                print(f"[{get_current_timestamp()}] 已保存plan2.txt的修改")
            else:
                print(f"[{get_current_timestamp()}] 无需修改")

        # 等待下次检查
        time.sleep(INTERVAL)

    print("-" * 60)
    print(f"[{get_current_timestamp()}] 监控循环已停止")


if __name__ == "__main__":
    main()
