"""
RelationProcessor类

关系后处理器负责在执行引擎完成初步执行后，根据ComplianceUnit之间的关系进行后处理，
生成最终的违规情况判断。
"""

from typing import Dict, List, Any, Optional, Set, Tuple
import pandas as pd
import logging
from datetime import datetime
from .relation_handler import RelationHandler
from .mock_relation_handler import MockRelationHandler
from .compliance_graph import ComplianceGraph

# 创建后处理器的日志记录器
logger = logging.getLogger("relation_processor")

class RelationProcessor:
    """
    关系后处理器类，负责处理ComplianceUnit之间的关系并生成最终的违规情况判断。
    
    属性:
        relation_handler: 关系处理器实例
    """
    
    def __init__(self, use_mock: bool = False):
        """
        初始化关系后处理器
        
        参数:
            use_mock: 是否使用模拟关系处理器
        """
        if use_mock:
            self.relation_handler = MockRelationHandler()
            logger.info("使用模拟关系处理器")
        else:
            self.relation_handler = RelationHandler()
            logger.info("使用真实关系处理器")
    
    def process_results(self, graph: ComplianceGraph, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理执行结果，生成最终的违规情况判断。
        
        参数:
            graph: 合规图
            results: 执行引擎的原始结果
            
        返回:
            处理后的结果，包含最终违规情况判断
        """
        logger.info("开始进行关系后处理")
        start_time = datetime.now()
        
        # 深拷贝原始结果，避免修改原始数据
        processed_results = results.copy()
        
        # 获取法规ID和单元结果
        regulation_id = next(iter(results.get("regulations", {})), None)
        if not regulation_id:
            logger.warning("未找到有效的法规ID")
            return processed_results
        
        regulation_results = results["regulations"][regulation_id]
        unit_results = regulation_results.get("node_results", {})
        
        # 使用RelationHandler处理关系
        processed_unit_results = self.relation_handler.process_relations(graph, unit_results)
        
        # 计算最终违规状态
        final_compliance_status = self._calculate_final_status(processed_unit_results)
        
        # 构建最终结果
        final_results = {
            "company_name": results.get("company_name", ""),
            "evaluation_time": results.get("evaluation_time", datetime.now().isoformat()),
            "regulations": {
                regulation_id: {
                    "regulation_name": regulation_results.get("regulation_name", ""),
                    "is_compliant": final_compliance_status["is_compliant"],
                    "total_violations": regulation_results.get("total_violations", 0),
                    "total_errors": regulation_results.get("total_errors", 0),
                    "node_results": processed_unit_results,
                    "final_compliance_status": final_compliance_status
                }
            }
        }
        
        # 添加执行时间
        processing_time = (datetime.now() - start_time).total_seconds()
        final_results["relation_processing_time"] = processing_time
        logger.info(f"关系后处理完成，耗时 {processing_time:.2f} 秒")
        
        return final_results
    
    def _calculate_final_status(self, unit_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算最终的合规状态。
        
        参数:
            unit_results: 处理后的单元结果
            
        返回:
            最终合规状态字典
        """
        # 初始化计数器
        violation_count = 0
        excluded_count = 0
        forced_count = 0
        error_count = 0
        skipped_count = 0
        success_count = 0
        
        # 违规单元和被排除单元列表
        violation_units = []
        excluded_units = []
        forced_units = []
        
        # 遍历所有单元结果
        for cu_id, result in unit_results.items():
            # 检查是否被排除
            relations = result.get("relations", {})
            if relations.get("excluded", False):
                excluded_count += 1
                excluded_units.append({
                    "cu_id": cu_id,
                    "excluded_by": relations.get("excluded_by", "unknown")
                })
                continue
            
            # 检查是否被强制包含
            if relations.get("forced_by", None):
                forced_count += 1
                forced_units.append({
                    "cu_id": cu_id,
                    "forced_by": relations.get("forced_by", "unknown")
                })
            
            # 获取执行状态
            exec_result = result.get("execution_result", {})
            status = exec_result.get("status", "")
            
            # 统计各类状态
            if status == "executed":
                if exec_result.get("output_analysis", {}).get("has_violation", False):
                    violation_count += 1
                    violation_units.append(cu_id)
                else:
                    success_count += 1
            elif status == "error":
                error_count += 1
            else:
                skipped_count += 1
        
        # 判断最终合规状态
        is_compliant = violation_count == 0
        
        # 构建最终状态字典
        final_status = {
            "is_compliant": is_compliant,
            "violation_count": violation_count,
            "excluded_count": excluded_count,
            "forced_count": forced_count,
            "error_count": error_count,
            "skipped_count": skipped_count,
            "success_count": success_count,
            "violation_units": violation_units,
            "excluded_units": excluded_units,
            "forced_units": forced_units,
            "summary": self._generate_summary(is_compliant, violation_count, excluded_count, forced_count)
        }
        
        return final_status
    
    def _generate_summary(self, is_compliant: bool, violation_count: int, excluded_count: int, forced_count: int) -> str:
        """
        生成合规状态摘要。
        
        参数:
            is_compliant: 是否合规
            violation_count: 违规单元数量
            excluded_count: 被排除单元数量
            forced_count: 被强制包含单元数量
            
        返回:
            合规状态摘要
        """
        if is_compliant:
            summary = "合规"
            if excluded_count > 0:
                summary += f"（{excluded_count}个单元因关系被排除）"
        else:
            summary = f"不合规（发现{violation_count}个违规单元"
            if excluded_count > 0:
                summary += f"，{excluded_count}个单元因关系被排除"
            if forced_count > 0:
                summary += f"，{forced_count}个单元因关系被强制包含"
            summary += "）"
        
        return summary 