#!/usr/bin/env python3
"""
检查JSON文件中的节点是否都有完整的核心元素
"""

import json
import sys

def check_json(filepath):
    """检查文件中的节点是否都有完整的核心元素"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    nodes = data.get('nodes', [])
    total_nodes = len(nodes)
    
    # 检查核心元素
    core_elements = ['subject', 'condition', 'constraint', 'contextual_info']
    missing_elements = {element: [] for element in core_elements}
    
    for node in nodes:
        cu_id = node.get('cu_id', 'unknown')
        for element in core_elements:
            if element not in node:
                missing_elements[element].append(cu_id)
    
    # 统计有代码的节点
    nodes_with_code = [node['cu_id'] for node in nodes if 'code' in node and node['code']]
    
    # 打印结果
    print(f"总节点数: {total_nodes}")
    print(f"有代码的节点数: {len(nodes_with_code)}")
    
    print("\n核心元素检查:")
    for element in core_elements:
        count = len(missing_elements[element])
        if count > 0:
            print(f"  缺少 {element} 的节点: {count}个")
            # 只显示前5个
            for cu_id in missing_elements[element][:5]:
                print(f"    - {cu_id}")
            if len(missing_elements[element]) > 5:
                print(f"    ... 等共{count}个节点")
        else:
            print(f"  所有节点都包含 {element} 字段")
    
    # 检查空值情况
    empty_elements = {element: 0 for element in core_elements}
    for node in nodes:
        for element in core_elements:
            if element in node and (node[element] == "" or node[element] is None):
                empty_elements[element] += 1
    
    print("\n空值检查:")
    for element, count in empty_elements.items():
        print(f"  {element} 为空的节点: {count}个 ({count/total_nodes*100:.1f}%)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python check_json.py <json_file>")
        sys.exit(1)
    
    check_json(sys.argv[1]) 