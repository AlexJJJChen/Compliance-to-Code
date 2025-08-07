"""
MockRelationHandler类

用于测试的模拟关系处理器。
"""

from typing import Dict, Any
import logging
from .compliance_graph import ComplianceGraph

logger = logging.getLogger("mock_relation_handler")

class MockRelationHandler:
    """
    模拟关系处理器类，用于测试。
    """
    
    def __init__(self):
        """初始化模拟关系处理器"""
        pass
    
    def process_relations(self, graph: ComplianceGraph, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理图中的所有关系。
        
        参数:
            graph: 合规图
            results: 节点执行结果字典，键为节点ID，值为执行结果
            
        返回:
            处理后的结果
        """
        logger.info("使用模拟关系处理器处理关系")
        processed_results = results.copy()
        
        # 模拟exclude关系：cu_2_1 -> cu_3_1
        if "cu_2_1" in processed_results and "cu_3_1" in processed_results:
            # 检查cu_2_1是否有违规
            cu_2_1_result = processed_results["cu_2_1"]
            has_violation = cu_2_1_result.get("execution_result", {}).get("output_analysis", {}).get("has_violation", False)
            
            if has_violation:
                # 如果cu_2_1有违规，排除cu_3_1
                if "relations" not in processed_results["cu_3_1"]:
                    processed_results["cu_3_1"]["relations"] = {}
                processed_results["cu_3_1"]["relations"]["excluded"] = True
                processed_results["cu_3_1"]["relations"]["excluded_by"] = "cu_2_1"
                logger.info("模拟exclude关系：cu_3_1被cu_2_1排除")
        
        # 模拟should_include关系：cu_4_1 -> cu_5_1
        if "cu_4_1" in processed_results and "cu_5_1" in processed_results:
            # 检查cu_4_1是否执行成功
            cu_4_1_result = processed_results["cu_4_1"]
            status = cu_4_1_result.get("execution_result", {}).get("status", "")
            
            if status == "executed":
                # 强制cu_5_1的condition为True
                cu_5_1_result = processed_results["cu_5_1"]
                exec_result = cu_5_1_result.get("execution_result", {})
                
                if "relations" not in cu_5_1_result:
                    cu_5_1_result["relations"] = {}
                cu_5_1_result["relations"]["forced_by"] = "cu_4_1"
                
                # 模拟强制condition为True后的违规
                exec_result["output_analysis"]["has_violation"] = True
                exec_result["output_analysis"]["violation_count"] = 1
                exec_result["output_analysis"]["violations"].append({
                    "row_index": 0,
                    "details": "被强制包含后发现违规"
                })
                logger.info("模拟should_include关系：cu_5_1被cu_4_1强制包含，并发现违规")
        
        return processed_results 