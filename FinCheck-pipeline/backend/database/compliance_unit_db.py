"""
ComplianceUnitDB 模块

提供合规单元数据库接口，用于从不同来源加载合规单元数据。
"""

import os
import pandas as pd
from typing import Dict, List, Any, Optional
import json
import re

from backend.compliance_engine.compliance_unit import ComplianceUnit
from backend.compliance_engine.compliance_graph import ComplianceGraph


class ComplianceUnitDB:
    """
    合规单元数据库，提供合规单元的存储和检索功能。
    
    属性:
        units: 存储所有合规单元的字典，键为cu_id
        graphs: 存储所有合规图的字典，键为regulation_id
    """
    
    def __init__(self):
        """初始化合规单元数据库"""
        self.units: Dict[str, ComplianceUnit] = {}
        self.graphs: Dict[str, ComplianceGraph] = {}
    
    def load_from_excel(self, file_path: str, regulation_id: str, regulation_name: str) -> ComplianceGraph:
        """
        从Excel文件加载合规单元数据。
        
        参数:
            file_path: Excel文件路径
            regulation_id: 法规ID，如 "regulation_04"
            regulation_name: 法规名称
            
        返回:
            包含加载单元的合规图
        """
        try:
            # 读取Excel文件
            df = pd.read_excel(file_path)
            
            # 创建合规图
            graph = ComplianceGraph(regulation_id, regulation_name)
            
            # 处理每个合规单元
            for _, row in df.iterrows():
                # 提取基本信息
                cu_id = row.get('cu_id', '')
                if not cu_id:
                    continue  # 跳过没有ID的行
                
                # 使用更安全的方法处理可能的NaN值
                subject = str(row.get('subject', '')) if row.get('subject') is not None and not isinstance(row.get('subject'), float) else ''
                condition = str(row.get('condition', '')) if row.get('condition') is not None and not isinstance(row.get('condition'), float) else ''
                constraint = str(row.get('constraint', '')) if row.get('constraint') is not None and not isinstance(row.get('constraint'), float) else ''
                contextual_info = str(row.get('contextual_info', '')) if row.get('contextual_info') is not None and not isinstance(row.get('contextual_info'), float) else None
                
                # 提取关系信息
                relation = []
                target = []
                
                # 安全地检查relation和target字段
                relation_value = row.get('relation')
                target_value = row.get('target')
                
                if relation_value is not None and target_value is not None and not isinstance(relation_value, float) and not isinstance(target_value, float):
                    relation_str = str(relation_value).strip()
                    target_str = str(target_value).strip()
                    
                    # 解析关系和目标
                    if relation_str:
                        relations = [r.strip() for r in relation_str.split(',')]
                        relation.extend(relations)
                    
                    if target_str:
                        targets = [t.strip() for t in target_str.split(',')]
                        target.extend(targets)
                
                # 提取代码
                code_value = row.get('code')
                code = str(code_value) if code_value is not None and not isinstance(code_value, float) else None
                
                # 创建合规单元
                unit = ComplianceUnit(
                    cu_id=cu_id,
                    subject=subject,
                    condition=condition,
                    constraint=constraint,
                    contextual_info=contextual_info,
                    relation=relation,
                    target=target,
                    code=code
                )
                
                # 添加到图中
                graph.add_unit(unit)
                
                # 存储到数据库
                self.units[cu_id] = unit
            
            # 存储图
            self.graphs[regulation_id] = graph
            
            return graph
        
        except Exception as e:
            raise ValueError(f"加载Excel文件失败: {e}")
    
    def save_graph_to_json(self, regulation_id: str, output_path: str) -> None:
        """
        将合规图保存为JSON文件。
        
        参数:
            regulation_id: 要保存的法规ID
            output_path: 输出路径
        """
        if regulation_id not in self.graphs:
            raise ValueError(f"未找到法规 {regulation_id}")
        
        graph = self.graphs[regulation_id]
        
        # 确保目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 保存为JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(graph.to_dict(), f, ensure_ascii=False, indent=2)
    
    def load_graph_from_json(self, json_path: str) -> ComplianceGraph:
        """
        从JSON文件加载合规图。
        
        参数:
            json_path: JSON文件路径
            
        返回:
            加载的合规图
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            graph = ComplianceGraph.from_dict(data)
            
            # 存储图和单元
            self.graphs[graph.regulation_id] = graph
            for cu_id, unit in graph.units.items():
                self.units[cu_id] = unit
            
            return graph
        
        except Exception as e:
            raise ValueError(f"加载JSON文件失败: {e}")
    
    def get_unit(self, cu_id: str) -> Optional[ComplianceUnit]:
        """
        获取指定ID的合规单元。
        
        参数:
            cu_id: 合规单元ID
            
        返回:
            找到的合规单元，如果不存在则返回None
        """
        return self.units.get(cu_id)
    
    def get_graph(self, regulation_id: str) -> Optional[ComplianceGraph]:
        """
        获取指定ID的合规图。
        
        参数:
            regulation_id: 法规ID
            
        返回:
            找到的合规图，如果不存在则返回None
        """
        return self.graphs.get(regulation_id)
    
    def extract_code_from_notebook(self, notebook_path: str) -> Dict[str, str]:
        """
        从Jupyter Notebook提取代码。
        
        参数:
            notebook_path: Notebook文件路径
            
        返回:
            包含代码的字典，键为cu_id
        """
        try:
            import json
            with open(notebook_path, 'r', encoding='utf-8') as f:
                notebook = json.load(f)
            
            code_dict = {}
            
            for cell in notebook.get('cells', []):
                if cell.get('cell_type') == 'code':
                    source = ''.join(cell.get('source', []))
                    
                    # 查找函数定义
                    match = re.search(r'def\s+check_meu_(\d+)_(\d+)', source)
                    if match:
                        section = match.group(1)
                        item = match.group(2)
                        cu_id = f"cu_{section}_{item}"
                        code_dict[cu_id] = source
            
            return code_dict
        
        except Exception as e:
            raise ValueError(f"从Notebook提取代码失败: {e}")
    
    def update_graph_with_code(self, regulation_id: str, code_dict: Dict[str, str]) -> None:
        """
        用提取的代码更新合规图。
        
        参数:
            regulation_id: 法规ID
            code_dict: 代码字典，键为cu_id
        """
        if regulation_id not in self.graphs:
            raise ValueError(f"未找到法规 {regulation_id}")
        
        graph = self.graphs[regulation_id]
        
        # 更新单元的代码
        for cu_id, code in code_dict.items():
            unit = graph.get_unit(cu_id)
            if unit:
                unit.code = code
                unit._compile_code()  # 重新编译代码
                
                # 更新数据库中的单元
                self.units[cu_id] = unit 