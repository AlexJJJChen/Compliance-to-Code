#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一个一次性工具脚本，用于清理合规图JSON文件中嵌入的规则代码。

该脚本会移除代码中所有对 `logger` 对象的调用，以确保代码能在
一个没有预定义 `logger` 的沙箱环境中纯净地执行。
"""

import json
import os
import re
import shutil
import sys

# 将项目根目录添加到Python路径中
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# 定义日志清理的正则表达式
# 匹配任何以可选空白符开头，后跟 "logger."，并持续到行尾的内容
LOGGER_REGEX = re.compile(r"^\s*logger\..*$", re.MULTILINE)

def clean_code(code: str) -> str:
    """
    使用正则表达式从给定的代码字符串中移除所有logger调用。

    参数:
        code: 包含潜在logger调用的代码字符串。

    返回:
        清理后的代码字符串。
    """
    if not code:
        return ""
    # 使用 re.sub 将所有匹配的行替换为空字符串
    cleaned_code = LOGGER_REGEX.sub("", code)
    # 移除可能由替换产生的多余空行
    return "\n".join(line for line in cleaned_code.split('\n') if line.strip())

def process_graph_file(file_path: str):
    """
    读取、清理并写回一个合规图JSON文件。

    该函数会创建一个原始文件的备份。

    参数:
        file_path: 合规图JSON文件的路径。
    """
    if not os.path.exists(file_path):
        print(f"错误: 文件不存在 -> {file_path}")
        return

    backup_path = f"{file_path}.bak"
    print(f"正在处理文件: {file_path}")

    # 1. 创建备份
    try:
        shutil.copy2(file_path, backup_path)
        print(f"已创建备份文件: {backup_path}")
    except Exception as e:
        print(f"创建备份失败: {e}")
        return

    # 2. 读取和解析JSON
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            graph_data = json.load(f)
    except Exception as e:
        print(f"读取或解析JSON文件失败: {e}")
        # 如果失败，从备份中恢复
        shutil.move(backup_path, file_path)
        return

    # 3. 遍历并清理代码
    cleaned_units_count = 0
    units = graph_data.get("units", {})
    for unit_id, unit_content in units.items():
        if "code" in unit_content and unit_content["code"]:
            original_code = unit_content["code"]
            cleaned_code = clean_code(original_code)
            
            if original_code != cleaned_code:
                unit_content["code"] = cleaned_code
                cleaned_units_count += 1
                print(f"  - 清理了单元 '{unit_id}' 的代码。")

    if cleaned_units_count == 0:
        print("未发现需要清理的代码。文件未被修改。")
        # 移除不必要的备份
        os.remove(backup_path)
        return

    # 4. 写回修改后的JSON
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, ensure_ascii=False, indent=4)
        print(f"\n成功清理了 {cleaned_units_count} 个单元的代码。")
        print(f"修改后的内容已写回: {file_path}")
    except Exception as e:
        print(f"写回JSON文件失败: {e}")
        # 尝试从备份中恢复
        shutil.move(backup_path, file_path)
        print("已从备份中恢复原始文件。")


if __name__ == "__main__":
    # 目标文件是 regulation_04.json
    target_file = os.path.join(project_root, "data", "graphs", "regulation_04.json")
    process_graph_file(target_file) 