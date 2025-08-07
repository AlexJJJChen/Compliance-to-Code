#!/usr/bin/env python3
"""
测试代码执行脚本

用于验证法规图中的合规单元代码是否可以正确执行。
"""

import os
import sys
import pandas as pd

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.compliance_engine.evaluator import Evaluator
from backend.compliance_engine.rule_executor import RuleExecutor, regulation_04_processor
from backend.database.compliance_unit_db import ComplianceUnitDB


def test_regulation_04():
    """测试股份回购法规的代码执行"""
    # 加载法规图
    db = ComplianceUnitDB()
    graph = db.load_graph_from_json('data/graphs/regulation_04.json')
    
    print(f'成功加载法规: {graph.regulation_name}')
    print(f'单元总数: {len(graph.units)}')
    print(f'有代码的单元: {sum(1 for unit in graph.units.values() if unit.code is not None)}')
    
    # 获取第一个有代码的单元
    test_unit = next((unit for unit in graph.units.values() if unit.code is not None), None)
    if not test_unit:
        print("没有找到可执行代码的单元！")
        return
    
    # 创建执行器
    executor = RuleExecutor()
    executor.register_data_processor('regulation_04', regulation_04_processor)
    
    # 创建测试数据
    fake_data = pd.DataFrame({
        '公司简称': ['测试公司'],
        '存在回购方案': [True],
        '回购方式': ['竞价回购'],
        '回购用途': ['维护公司价值及股东权益所必需'],
        '日期': [pd.Timestamp('2023-01-01')],
        '决议通过日': [pd.Timestamp('2023-01-01')],
        '收盘价': [10.0],
        '每股净资产': [12.0],  # 确保收盘价 < 每股净资产，满足条件1
        '总股本': [100000000],
        '累计回购数量': [1000000]
    })
    
    # 执行单元
    result = test_unit.execute(fake_data)
    
    # 显示结果
    print(f'\n单元ID: {test_unit.cu_id}')
    print(f'主体: {test_unit.subject}')
    print(f'条件: {test_unit.condition}')
    print(f'约束: {test_unit.constraint}')
    print(f'\n执行结果: {result}')
    

if __name__ == "__main__":
    test_regulation_04() 