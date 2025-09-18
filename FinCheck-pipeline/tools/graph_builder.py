#!/usr/bin/env python3
"""
图构建工具

用于构建和可视化ComplianceUnit图结构。
"""

import os
import sys
import argparse
import json
import networkx as nx
import matplotlib.pyplot as plt
from typing import Dict, List, Any, Optional, Set, Tuple

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from backend.database.compliance_unit_db import ComplianceUnitDB
from backend.compliance_engine.compliance_graph import ComplianceGraph
from backend.compliance_engine.relation_handler import RelationHandler


def visualize_graph(graph: ComplianceGraph, output_path: Optional[str] = None) -> None:
    """
    可视化合规图结构。
    
    参数:
        graph: 要可视化的合规图
        output_path: 输出文件路径，如果提供则保存图片
    """
    # 创建NetworkX图
    G = graph.graph.copy()
    
    # 设置节点标签
    labels = {}
    for node in G.nodes():
        unit = graph.get_unit(node)
        if unit:
            labels[node] = f"{node}\n{unit.subject[:10]}..."
    
    # 设置边标签
    edge_labels = {}
    for u, v, data in G.edges(data=True):
        relation = data.get('relation', '')
        edge_labels[(u, v)] = relation
    
    # 设置布局
    pos = nx.spring_layout(G, seed=42)
    
    # 绘制图
    plt.figure(figsize=(20, 15))
    nx.draw_networkx_nodes(G, pos, node_size=1500, node_color='lightblue')
    nx.draw_networkx_edges(G, pos, width=1, arrowsize=20)
    nx.draw_networkx_labels(G, pos, labels, font_size=10)
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)
    
    plt.title(f"{graph.regulation_name} ({graph.regulation_id})")
    plt.axis('off')
    
    if output_path:
        plt.savefig(output_path, format='png', dpi=300, bbox_inches='tight')
        print(f"图像已保存到 {output_path}")
    else:
        plt.show()


def analyze_graph(graph: ComplianceGraph) -> Dict[str, Any]:
    """
    分析合规图结构。
    
    参数:
        graph: 要分析的合规图
        
    返回:
        包含分析结果的字典
    """
    relation_handler = RelationHandler()
    
    # 检查循环
    cycles = relation_handler.check_relation_cycles(graph)
    
    # 统计各种关系类型
    relation_counts = {}
    for _, _, data in graph.graph.edges(data=True):
        relation = data.get('relation', 'unknown')
        relation_counts[relation] = relation_counts.get(relation, 0) + 1
    
    # 统计有代码的单元
    units_with_code = []
    for cu_id, unit in graph.units.items():
        if unit.code:
            units_with_code.append(cu_id)
    
    # 分析结果
    analysis = {
        "regulation_id": graph.regulation_id,
        "regulation_name": graph.regulation_name,
        "total_units": len(graph.units),
        "total_edges": graph.graph.number_of_edges(),
        "relation_counts": relation_counts,
        "cycles": cycles,
        "units_with_code": len(units_with_code),
        "units_with_code_ratio": len(units_with_code) / len(graph.units) if graph.units else 0,
        "has_cycles": len(cycles) > 0
    }
    
    return analysis


def build_graph_from_excel(excel_path: str, output_json_path: str, regulation_id: str, regulation_name: str) -> ComplianceGraph:
    """
    从Excel文件构建合规图。
    
    参数:
        excel_path: Excel文件路径
        output_json_path: 输出JSON文件路径
        regulation_id: 法规ID
        regulation_name: 法规名称
        
    返回:
        构建的合规图
    """
    db = ComplianceUnitDB()
    
    # 从Excel加载
    graph = db.load_from_excel(excel_path, regulation_id, regulation_name)
    
    # 保存为JSON
    db.save_graph_to_json(regulation_id, output_json_path)
    
    return graph


def load_graph_from_json(json_path: str) -> ComplianceGraph:
    """
    从JSON文件加载合规图。
    
    参数:
        json_path: JSON文件路径
        
    返回:
        加载的合规图
    """
    db = ComplianceUnitDB()
    return db.load_graph_from_json(json_path)


def build_graph_for_regulation(regulation_id: str) -> Optional[ComplianceGraph]:
    """
    为特定法规构建合规图。
    
    参数:
        regulation_id: 法规ID
        
    返回:
        构建的合规图，如果失败则返回None
    """
    # 定义路径
    if regulation_id == "regulation_04":
        excel_path = os.path.join(project_root, "old", "ComplianceUnitGraph", "human_format", 
                                 "北京证券交易所上市公司持续监管指引第4号——股份回购.xlsx")
        regulation_name = "北京证券交易所上市公司持续监管指引第4号——股份回购"
    elif regulation_id == "regulation_08":
        excel_path = os.path.join(project_root, "old", "ComplianceUnitGraph", "human_format", 
                                 "北京证券交易所上市公司持续监管指引第8号——股份减持和持股管理.xlsx")
        regulation_name = "北京证券交易所上市公司持续监管指引第8号——股份减持和持股管理"
    elif regulation_id == "regulation_10":
        excel_path = os.path.join(project_root, "old", "ComplianceUnitGraph", "human_format", 
                                 "北京证券交易所上市公司持续监管指引第10号——权益分派.xlsx")
        regulation_name = "北京证券交易所上市公司持续监管指引第10号——权益分派"
    else:
        print(f"未知的法规ID: {regulation_id}")
        return None
    
    # 检查Excel文件是否存在
    if not os.path.exists(excel_path):
        print(f"Excel文件不存在: {excel_path}")
        return None
    
    # 确保输出目录存在
    output_dir = os.path.join(project_root, "data", "graphs")
    os.makedirs(output_dir, exist_ok=True)
    
    # 构建图
    output_json = os.path.join(output_dir, f"{regulation_id}.json")
    
    try:
        graph = build_graph_from_excel(excel_path, output_json, regulation_id, regulation_name)
        print(f"成功构建图 {regulation_id} ({regulation_name})")
        return graph
    except Exception as e:
        print(f"构建图失败 {regulation_id}: {e}")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="合规图构建和可视化工具")
    parser.add_argument("--build", type=str, help="从Excel构建图的法规ID")
    parser.add_argument("--load", type=str, help="要加载的JSON文件路径")
    parser.add_argument("--visualize", action="store_true", help="可视化图")
    parser.add_argument("--analyze", action="store_true", help="分析图结构")
    parser.add_argument("--output", type=str, help="输出文件路径")
    
    args = parser.parse_args()
    
    graph = None
    
    # 构建或加载图
    if args.build:
        graph = build_graph_for_regulation(args.build)
    elif args.load and os.path.exists(args.load):
        graph = load_graph_from_json(args.load)
    else:
        parser.print_help()
        sys.exit(1)
    
    # 没有成功加载图
    if not graph:
        sys.exit(1)
    
    # 进行操作
    if args.analyze:
        analysis = analyze_graph(graph)
        print("\n图结构分析:")
        print(f"法规: {analysis['regulation_name']} ({analysis['regulation_id']})")
        print(f"总单元数: {analysis['total_units']}")
        print(f"总边数: {analysis['total_edges']}")
        print(f"关系类型统计: {analysis['relation_counts']}")
        print(f"有代码的单元: {analysis['units_with_code']} ({analysis['units_with_code_ratio']:.1%})")
        
        if analysis['has_cycles']:
            print("\n警告: 图中存在循环!")
            for i, cycle in enumerate(analysis['cycles'], 1):
                print(f"循环 {i}: {' -> '.join(cycle)}")
    
    if args.visualize:
        print("\n正在可视化图结构...")
        visualize_graph(graph, args.output) 