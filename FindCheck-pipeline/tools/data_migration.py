#!/usr/bin/env python3
"""
数据迁移工具

用于将原始Excel和Jupyter Notebook文件转换为系统可用的格式。
"""

import os
import sys
import argparse
import json
from typing import Dict, List, Any

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from backend.database.compliance_unit_db import ComplianceUnitDB
from backend.compliance_engine.compliance_graph import ComplianceGraph


def migrate_excel_to_json(excel_path: str, output_path: str, regulation_id: str, regulation_name: str) -> None:
    """
    将Excel文件中的合规单元数据转换为JSON格式。
    
    参数:
        excel_path: Excel文件路径
        output_path: 输出JSON文件路径
        regulation_id: 法规ID，如 "regulation_04"
        regulation_name: 法规名称
    """
    print(f"正在迁移 {excel_path} -> {output_path}")
    
    db = ComplianceUnitDB()
    
    # 从Excel加载
    graph = db.load_from_excel(excel_path, regulation_id, regulation_name)
    
    # 保存为JSON
    db.save_graph_to_json(regulation_id, output_path)
    
    print(f"迁移完成，共 {len(graph.units)} 个合规单元")


def extract_code_from_notebook(notebook_path: str, graph_json_path: str, output_path: str) -> None:
    """
    从Jupyter Notebook提取代码并更新合规图。
    
    参数:
        notebook_path: Notebook文件路径
        graph_json_path: 合规图JSON文件路径
        output_path: 输出JSON文件路径
    """
    print(f"正在从 {notebook_path} 提取代码")
    
    db = ComplianceUnitDB()
    
    # 从JSON加载图
    graph = db.load_graph_from_json(graph_json_path)
    
    # 从Notebook提取代码
    code_dict = db.extract_code_from_notebook(notebook_path)
    
    # 更新图
    db.update_graph_with_code(graph.regulation_id, code_dict)
    
    # 保存更新后的图
    db.save_graph_to_json(graph.regulation_id, output_path)
    
    print(f"代码提取完成，更新了 {len(code_dict)} 个合规单元的代码")


def migrate_all() -> None:
    """迁移所有数据"""
    # 确保输出目录存在
    output_dir = os.path.join(project_root, "data", "graphs")
    os.makedirs(output_dir, exist_ok=True)
    
    # 法规定义
    regulations = [
        {
            "id": "regulation_04",
            "name": "北京证券交易所上市公司持续监管指引第4号——股份回购",
            "excel": os.path.join(project_root, "old", "ComplianceUnitGraph", "human_format", "北京证券交易所上市公司持续监管指引第4号——股份回购.xlsx"),
            "notebook": os.path.join(project_root, "old", "ComplianceUnitGraph", "human_format", "GT_第4号_股份回购.ipynb")
        },
        {
            "id": "regulation_08",
            "name": "北京证券交易所上市公司持续监管指引第8号——股份减持和持股管理",
            "excel": os.path.join(project_root, "old", "ComplianceUnitGraph", "human_format", "北京证券交易所上市公司持续监管指引第8号——股份减持和持股管理.xlsx"),
            "notebook": os.path.join(project_root, "old", "ComplianceUnitGraph", "human_format", "GT_第8号_股份减持和持股管理.ipynb")
        },
        {
            "id": "regulation_10",
            "name": "北京证券交易所上市公司持续监管指引第10号——权益分派",
            "excel": os.path.join(project_root, "old", "ComplianceUnitGraph", "human_format", "北京证券交易所上市公司持续监管指引第10号——权益分派.xlsx"),
            "notebook": os.path.join(project_root, "old", "ComplianceUnitGraph", "human_format", "GT_第10号_权益分派.ipynb")
        }
    ]
    
    # 迁移每个法规
    for reg in regulations:
        # 临时JSON文件
        temp_json = os.path.join(output_dir, f"{reg['id']}_temp.json")
        final_json = os.path.join(output_dir, f"{reg['id']}.json")
        
        # 迁移Excel到JSON
        if os.path.exists(reg["excel"]):
            migrate_excel_to_json(reg["excel"], temp_json, reg["id"], reg["name"])
        else:
            print(f"警告: Excel文件不存在 {reg['excel']}")
            continue
        
        # 提取代码
        if os.path.exists(reg["notebook"]):
            extract_code_from_notebook(reg["notebook"], temp_json, final_json)
        else:
            print(f"警告: Notebook文件不存在 {reg['notebook']}")
            # 如果没有notebook，直接使用临时文件
            if os.path.exists(temp_json):
                os.rename(temp_json, final_json)
        
        # 清理临时文件
        if os.path.exists(temp_json):
            try:
                os.remove(temp_json)
            except Exception:
                pass
    
    print("所有数据迁移完成")


def migrate_company_data() -> None:
    """迁移公司数据"""
    # 确保输出目录存在
    output_dir = os.path.join(project_root, "data", "company_data")
    os.makedirs(output_dir, exist_ok=True)
    
    # 定义数据文件
    data_files = [
        {
            "source": os.path.join(project_root, "company_database", "data_simulate_股份回购_04.csv"),
            "target": os.path.join(output_dir, "company_04.csv")
        },
        {
            "source": os.path.join(project_root, "company_database", "data_simulate_持股管理_08.csv"),
            "target": os.path.join(output_dir, "company_08.csv")
        },
        {
            "source": os.path.join(project_root, "company_database", "data_simulate_权益分派_10.csv"),
            "target": os.path.join(output_dir, "company_10.csv")
        }
    ]
    
    # 复制文件
    for file_info in data_files:
        source = file_info["source"]
        target = file_info["target"]
        
        if os.path.exists(source):
            print(f"正在复制 {source} -> {target}")
            import shutil
            shutil.copy2(source, target)
        else:
            print(f"警告: 源文件不存在 {source}")
    
    print("公司数据迁移完成")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="数据迁移工具")
    parser.add_argument("--all", action="store_true", help="迁移所有数据")
    parser.add_argument("--excel", type=str, help="Excel文件路径")
    parser.add_argument("--notebook", type=str, help="Notebook文件路径")
    parser.add_argument("--output", type=str, help="输出JSON文件路径")
    parser.add_argument("--regulation-id", type=str, help="法规ID")
    parser.add_argument("--regulation-name", type=str, help="法规名称")
    parser.add_argument("--company-data", action="store_true", help="迁移公司数据")
    
    args = parser.parse_args()
    
    if args.all:
        migrate_all()
    elif args.company_data:
        migrate_company_data()
    elif args.excel and args.output and args.regulation_id and args.regulation_name:
        migrate_excel_to_json(args.excel, args.output, args.regulation_id, args.regulation_name)
        
        # 如果提供了notebook，继续提取代码
        if args.notebook:
            temp_output = args.output + ".temp"
            os.rename(args.output, temp_output)
            extract_code_from_notebook(args.notebook, temp_output, args.output)
            # 清理临时文件
            try:
                os.remove(temp_output)
            except Exception:
                pass
    else:
        parser.print_help() 