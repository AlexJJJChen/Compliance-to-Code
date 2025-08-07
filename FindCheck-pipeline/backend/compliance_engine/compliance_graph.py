"""
ComplianceGraph类

合规图表示一个完整法规文件的结构，包含多个ComplianceUnit以及它们之间的关系。
图结构使用有向图表示，节点是ComplianceUnit，边是单元间的关系。
"""

from typing import Dict, List, Any, Optional, Set, Tuple
import json
import networkx as nx
from .compliance_unit import ComplianceUnit


class ComplianceGraph:
    """
    合规图类，表示一个完整法规文件的结构。
    
    属性:
        regulation_id (str): 法规ID，如 "regulation_04"
        regulation_name (str): 法规名称，如 "北京证券交易所上市公司持续监管指引第4号——股份回购"
        graph (nx.DiGraph): 合规单元构成的有向图
    """
    
    def __init__(
        self,
        regulation_id: str,
        regulation_name: str,
        units: Optional[List[ComplianceUnit]] = None
    ):
        """
        初始化合规图。
        
        参数:
            regulation_id: 法规ID
            regulation_name: 法规名称
            units: 可选的ComplianceUnit列表，用于初始化图
        """
        self.regulation_id = regulation_id
        self.regulation_name = regulation_name
        self.graph = nx.DiGraph()
        
        # 存储所有单元的字典，便于快速查找
        self.units: Dict[str, ComplianceUnit] = {}
        
        # 添加初始单元
        if units:
            for unit in units:
                self.add_unit(unit)
    
    def add_unit(self, unit: ComplianceUnit) -> None:
        """
        向图中添加一个合规单元。
        
        参数:
            unit: 要添加的ComplianceUnit
        """
        self.units[unit.cu_id] = unit
        self.graph.add_node(unit.cu_id, unit=unit)
        
        # 添加边（关系）
        if unit.relation and unit.target:
            for i, relation in enumerate(unit.relation):
                if i < len(unit.target):
                    target = unit.target[i]
                    self.graph.add_edge(unit.cu_id, target, relation=relation)
    
    def remove_unit(self, cu_id: str) -> None:
        """
        从图中删除一个合规单元。
        
        参数:
            cu_id: 要删除的单元ID
        """
        if cu_id in self.units:
            del self.units[cu_id]
            self.graph.remove_node(cu_id)
    
    def get_unit(self, cu_id: str) -> Optional[ComplianceUnit]:
        """
        获取指定ID的合规单元。
        
        参数:
            cu_id: 单元ID
        
        返回:
            对应的ComplianceUnit，如果不存在则返回None
        """
        return self.units.get(cu_id)
    
    def get_related_units(self, cu_id: str, relation_type: Optional[str] = None) -> List[ComplianceUnit]:
        """
        获取与指定单元有关系的所有单元。
        
        参数:
            cu_id: 源单元ID
            relation_type: 可选的关系类型过滤
        
        返回:
            相关单元列表
        """
        if cu_id not in self.graph:
            return []
        
        related_units = []
        for _, target_id, edge_data in self.graph.out_edges(cu_id, data=True):
            if relation_type is None or edge_data.get('relation') == relation_type:
                target_unit = self.get_unit(target_id)
                if target_unit:
                    related_units.append(target_unit)
        
        return related_units
    
    def get_referencing_units(self, cu_id: str) -> List[ComplianceUnit]:
        """
        获取引用了指定单元的所有单元。
        
        参数:
            cu_id: 被引用单元ID
        
        返回:
            引用了该单元的单元列表
        """
        if cu_id not in self.graph:
            return []
        
        referencing_units = []
        for source_id, _, edge_data in self.graph.in_edges(cu_id, data=True):
            source_unit = self.get_unit(source_id)
            if source_unit:
                referencing_units.append(source_unit)
        
        return referencing_units
    
    def evaluate_compliance(self, company_data: Any) -> Dict[str, Any]:
        """
        评估企业对该法规的合规性。
        
        参数:
            company_data: 企业数据，通常是DataFrame
            
        返回:
            包含评估结果的字典
        """
        results = {}
        execution_order = self._determine_execution_order()
        
        # 执行所有有代码的合规单元
        for cu_id in execution_order:
            unit = self.get_unit(cu_id)
            if unit and unit.code_function:
                result = unit.execute(company_data)
                results[cu_id] = result
        
        # 处理关系影响
        processed_results = self._process_relations(results, company_data)
        
        return {
            "regulation_id": self.regulation_id,
            "regulation_name": self.regulation_name,
            "unit_results": processed_results,
            "summary": self._generate_summary(processed_results)
        }
    
    def _determine_execution_order(self) -> List[str]:
        """
        确定合规单元的执行顺序，优先执行无依赖的单元。
        
        返回:
            单元ID的执行顺序列表
        """
        # 简单实现：拓扑排序
        try:
            execution_order = list(nx.topological_sort(self.graph))
        except nx.NetworkXUnfeasible:
            # 如果图中有循环，则按ID排序
            execution_order = sorted(self.units.keys())
        
        return execution_order
    
    def _process_relations(self, raw_results: Dict[str, Any], company_data: Any) -> Dict[str, Any]:
        """
        处理合规单元之间的关系对结果的影响。
        
        参数:
            raw_results: 原始执行结果
            company_data: 企业数据
            
        返回:
            处理后的结果
        """
        processed_results = raw_results.copy()
        
        # 处理exclude关系
        for source_id, target_id, edge_data in self.graph.edges(data=True):
            relation = edge_data.get('relation')
            
            if relation == 'exclude':
                source_result = raw_results.get(source_id, {}).get('result')
                if source_result is not None:
                    # 检查source是否满足条件（subject和condition都为True）
                    if source_result.get(f'meu_{source_id.split("_")[1]}_{source_id.split("_")[2]}_subject', False) and \
                       source_result.get(f'meu_{source_id.split("_")[1]}_{source_id.split("_")[2]}_condition', False):
                        # 如果满足条件，则将target标记为免除
                        if target_id in processed_results:
                            processed_results[target_id]['excluded'] = True
                            processed_results[target_id]['excluded_by'] = source_id
                            
            # 处理only_include关系
            elif relation == 'only_include':
                source_result = raw_results.get(source_id, {}).get('result')
                if source_result is not None:
                    # 检查source是否满足条件
                    if source_result.get(f'meu_{source_id.split("_")[1]}_{source_id.split("_")[2]}_subject', False) and \
                       source_result.get(f'meu_{source_id.split("_")[1]}_{source_id.split("_")[2]}_condition', False):
                        # 如果满足条件，则只包含target
                        for cu_id in list(processed_results.keys()):
                            if cu_id != target_id and cu_id != source_id:
                                processed_results[cu_id]['excluded'] = True
                                processed_results[cu_id]['excluded_by'] = f"only_include:{source_id}->{target_id}"
        
        return processed_results
    
    def _generate_summary(self, processed_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成合规评估的总结。
        
        参数:
            processed_results: 处理后的结果
            
        返回:
            包含总结信息的字典
        """
        violations = []
        compliant_units = []
        excluded_units = []
        
        for cu_id, result in processed_results.items():
            if result.get('excluded', False):
                excluded_units.append(cu_id)
                continue
                
            if not result.get('executed', False):
                # 无法执行的单元忽略
                continue
                
            unit_result = result.get('result', {})
            unit = self.get_unit(cu_id)
            if not unit:
                continue
                
            # 提取subject、condition和constraint的结果
            prefix = f"meu_{cu_id.split('_')[1]}_{cu_id.split('_')[2]}"
            subject_result = unit_result.get(f"{prefix}_subject", None)
            condition_result = unit_result.get(f"{prefix}_condition", None)
            constraint_result = unit_result.get(f"{prefix}_constraint", None)
            
            # 只有当subject和condition都为True，且constraint为False时，才视为违规
            if subject_result == True and condition_result == True and constraint_result == False:
                violations.append({
                    "cu_id": cu_id,
                    "subject": unit.subject,
                    "condition": unit.condition,
                    "constraint": unit.constraint,
                    "contextual_info": unit.contextual_info
                })
            elif subject_result == True and condition_result == True and constraint_result == True:
                compliant_units.append(cu_id)
        
        return {
            "violation_count": len(violations),
            "violations": violations,
            "compliant_units": compliant_units,
            "excluded_units": excluded_units,
            "is_compliant": len(violations) == 0
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将ComplianceGraph转换为字典格式。
        
        返回:
            表示图的字典
        """
        nodes = []
        for cu_id, unit in self.units.items():
            nodes.append(unit.to_dict())
        
        edges = []
        for source, target, data in self.graph.edges(data=True):
            edges.append({
                "source": source,
                "target": target,
                "relation": data.get('relation', '')
            })
        
        return {
            "regulation_id": self.regulation_id,
            "regulation_name": self.regulation_name,
            "nodes": nodes,
            "edges": edges
        }
    
    def to_json(self) -> str:
        """
        将ComplianceGraph转换为JSON字符串。
        
        返回:
            表示图的JSON字符串
        """
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ComplianceGraph':
        """
        从字典创建ComplianceGraph实例。
        
        参数:
            data: 包含图数据的字典
            
        返回:
            新创建的ComplianceGraph实例
        """
        regulation_id = data.get("regulation_id", "")
        regulation_name = data.get("regulation_name", "")
        
        graph = cls(regulation_id, regulation_name)
        
        # 添加节点
        for node_data in data.get("nodes", []):
            unit = ComplianceUnit.from_dict(node_data)
            graph.add_unit(unit)
        
        # 添加边
        for edge_data in data.get("edges", []):
            source = edge_data.get("source", "")
            target = edge_data.get("target", "")
            relation = edge_data.get("relation", "")
            
            if source in graph.graph and target in graph.graph:
                graph.graph.add_edge(source, target, relation=relation)
                
                # 更新源单元的relation和target
                source_unit = graph.get_unit(source)
                if source_unit:
                    if relation not in source_unit.relation:
                        source_unit.relation.append(relation)
                    if target not in source_unit.target:
                        source_unit.target.append(target)
        
        return graph
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ComplianceGraph':
        """
        从JSON字符串创建ComplianceGraph实例。
        
        参数:
            json_str: 包含图数据的JSON字符串
            
        返回:
            新创建的ComplianceGraph实例
        """
        data = json.loads(json_str)
        return cls.from_dict(data) 