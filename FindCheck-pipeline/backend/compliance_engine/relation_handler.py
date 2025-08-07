"""
RelationHandler类

关系处理器负责处理ComplianceUnit之间的关系，如refer_to、exclude、only_include和should_include。
"""

from typing import Dict, List, Any, Optional, Set, Tuple
import pandas as pd
import networkx as nx
from .compliance_unit import ComplianceUnit
from .compliance_graph import ComplianceGraph


class RelationHandler:
    """
    关系处理器类，负责处理ComplianceUnit之间的关系。
    
    属性:
        handlers: 关系处理函数的字典，键为关系类型
    """
    
    def __init__(self):
        """初始化关系处理器"""
        self.handlers = {
            'refer_to': self._handle_refer_to,
            'exclude': self._handle_exclude,
            'only_include': self._handle_only_include,
            'should_include': self._handle_should_include
        }
    
    def process_relations(self, graph: ComplianceGraph, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理图中的所有关系。
        
        参数:
            graph: 合规图
            results: 节点执行结果字典，键为节点ID，值为执行结果
            
        返回:
            处理后的结果
        """
        processed_results = results.copy()
        
        # 按关系类型分批处理
        for relation_type in ['refer_to', 'should_include', 'exclude', 'only_include']:
            # 获取该类型的所有边
            edges = [(s, t, data) for s, t, data in graph.graph.edges(data=True) 
                     if data.get('relation') == relation_type]
            
            # 处理该类型的所有关系
            for source, target, data in edges:
                handler = self.handlers.get(relation_type)
                if handler:
                    processed_results = handler(graph, source, target, processed_results)
        
        return processed_results
    
    def _handle_refer_to(self, graph: ComplianceGraph, source: str, target: str, 
                         results: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理refer_to关系。
        
        参数:
            graph: 合规图
            source: 源单元ID
            target: 目标单元ID
            results: 当前结果
        
        返回:
            处理后的结果
        """
        # refer_to关系：源单元需要结合目标单元的信息作为补充
        if source in results and target in results:
            source_result = results[source]
            
            # 标记refer_to关系
            if "relations" not in source_result:
                source_result["relations"] = {}
            
            if "refers_to" not in source_result["relations"]:
                source_result["relations"]["refers_to"] = []
                
            source_result["relations"]["refers_to"].append(target)
            
            # 更新结果
            results[source] = source_result
        
        return results
    
    def _handle_exclude(self, graph: ComplianceGraph, source: str, target: str, 
                        results: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理exclude关系。
        
        参数:
            graph: 合规图
            source: 源单元ID
            target: 目标单元ID
            results: 当前结果
        
        返回:
            处理后的结果
        """
        # exclude关系：当源单元条件满足时，目标单元被排除
        if source in results and target in results:
            source_result = results[source]
            exec_result = source_result.get("execution_result", {})
            status = exec_result.get("status", "")
            
            # 只处理已执行的节点
            if status == "executed":
                records = exec_result.get("records", {})
                source_unit = graph.get_unit(source)
                
                if source_unit:
                    # 获取prefix
                    prefix = f"meu_{source_unit.cu_id.split('_')[1]}_{source_unit.cu_id.split('_')[2]}"
                    
                    # 检查源单元的subject和condition是否都为True
                    subject_result = records.get(f"{prefix}_subject", False)
                    condition_result = records.get(f"{prefix}_condition", False)
                    
                    if subject_result and condition_result:
                        # 源单元条件满足，排除目标单元
                        if "relations" not in results[target]:
                            results[target]["relations"] = {}
                            
                        results[target]["relations"]["excluded"] = True
                        results[target]["relations"]["excluded_by"] = source
        
        return results
    
    def _handle_only_include(self, graph: ComplianceGraph, source: str, target: str, 
                             results: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理only_include关系。
        
        参数:
            graph: 合规图
            source: 源单元ID
            target: 目标单元ID
            results: 当前结果
        
        返回:
            处理后的结果
        """
        # only_include关系：当源单元条件满足时，只考虑目标单元
        if source in results:
            source_result = results[source]
            exec_result = source_result.get("execution_result", {})
            status = exec_result.get("status", "")
            
            # 只处理已执行的节点
            if status == "executed":
                records = exec_result.get("records", {})
                source_unit = graph.get_unit(source)
                
                if source_unit:
                    # 获取prefix
                    prefix = f"meu_{source_unit.cu_id.split('_')[1]}_{source_unit.cu_id.split('_')[2]}"
                    
                    # 检查源单元的subject和condition是否都为True
                    subject_result = records.get(f"{prefix}_subject", False)
                    condition_result = records.get(f"{prefix}_condition", False)
                    
                    if subject_result and condition_result:
                        # 源单元条件满足，排除除目标和源外的所有单元
                        for cu_id in list(results.keys()):
                            if cu_id != target and cu_id != source:
                                if "relations" not in results[cu_id]:
                                    results[cu_id]["relations"] = {}
                                    
                                results[cu_id]["relations"]["excluded"] = True
                                results[cu_id]["relations"]["excluded_by"] = f"only_include:{source}->{target}"
        
        return results
    
    def _handle_should_include(self, graph: ComplianceGraph, source: str, target: str, 
                               results: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理should_include关系。
        
        参数:
            graph: 合规图
            source: 源单元ID
            target: 目标单元ID
            results: 当前结果
        
        返回:
            处理后的结果
        """
        # should_include关系：当源单元条件满足时，强制纳入目标单元的要求
        if source in results and target in results:
            source_result = results[source]
            exec_source = source_result.get("execution_result", {})
            status_source = exec_source.get("status", "")
            
            # 只处理已执行的源节点
            if status_source == "executed":
                records_source = exec_source.get("records", {})
                source_unit = graph.get_unit(source)
                
                if source_unit:
                    # 获取source的prefix
                    prefix_source = f"meu_{source_unit.cu_id.split('_')[1]}_{source_unit.cu_id.split('_')[2]}"
                    
                    # 检查源单元的subject和condition是否都为True
                    subject_result = records_source.get(f"{prefix_source}_subject", False)
                    condition_result = records_source.get(f"{prefix_source}_condition", False)
                    
                    if subject_result and condition_result:
                        # 源单元条件满足，检查目标单元
                        target_result = results[target]
                        exec_target = target_result.get("execution_result", {})
                        status_target = exec_target.get("status", "")
                        
                        if status_target == "executed":
                            records_target = exec_target.get("records", {})
                            target_unit = graph.get_unit(target)
                            
                            if target_unit:
                                # 获取target的prefix
                                prefix_target = f"meu_{target_unit.cu_id.split('_')[1]}_{target_unit.cu_id.split('_')[2]}"
                                
                                # 强制目标单元的condition为True，保留constraint结果
                                if f"{prefix_target}_condition" in records_target:
                                    records_target[f"{prefix_target}_condition"] = True
                                    
                                    # 重新计算违规情况
                                    subject_value = records_target.get(f"{prefix_target}_subject", False)
                                    constraint_value = records_target.get(f"{prefix_target}_constraint", True)
                                    has_violation = (subject_value == True and True and constraint_value == False)
                                    
                                    # 更新执行结果
                                    exec_target["has_violation"] = has_violation
                                    exec_target["records"] = records_target
                                    
                                    # 标记为强制包含
                                    if "relations" not in target_result:
                                        target_result["relations"] = {}
                                        
                                    target_result["relations"]["forced_by"] = source
                                    results[target] = target_result
        
        return results
    
    @staticmethod
    def check_relation_cycles(graph: ComplianceGraph) -> List[List[str]]:
        """
        检查图中是否存在关系循环。
        
        参数:
            graph: 合规图
        
        返回:
            循环路径列表，每个路径是一个节点ID列表
        """
        # 使用NetworkX自带的循环检测算法
        try:
            cycles = list(nx.simple_cycles(graph.graph))
            return cycles
        except Exception:
            # 如果图不支持循环检测（如无向图），则返回空列表
            return [] 