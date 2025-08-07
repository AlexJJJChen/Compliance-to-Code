#!/usr/bin/env python3
"""
评估器模块

评估器负责综合分析一家公司的所有法规合规情况，生成最终的合规报告。
"""

from typing import Dict, List, Any, Optional, Union
import os
import sys
import pandas as pd
from datetime import datetime
import logging
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from .compliance_unit import ComplianceUnit
from .compliance_graph import ComplianceGraph
from .rule_executor import RuleExecutor

# 创建评估器的日志记录器
logger = logging.getLogger("evaluator")


class Evaluator:
    """
    评估器类，负责评估公司的合规性并生成报告。
    
    属性:
        executor: 规则执行器
        graphs: 法规图字典，键为regulation_id
    """
    
    def __init__(self, executor: Optional[RuleExecutor] = None):
        """
        初始化评估器。
        
        参数:
            executor: 可选的规则执行器，如果未提供则创建新的
        """
        self.executor = executor if executor else RuleExecutor()
        self.graphs: Dict[str, ComplianceGraph] = {}
    
    def register_graph(self, graph: ComplianceGraph) -> None:
        """
        注册一个法规图。
        
        参数:
            graph: 要注册的合规图
        """
        self.graphs[graph.regulation_id] = graph
    
    def evaluate_company(self, company_name: str, company_data: pd.DataFrame, regulation_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        评估一家公司对指定法规的合规性。
        
        参数:
            company_name: 公司名称
            company_data: 公司数据，可以是DataFrame或数据路径
            regulation_ids: 要评估的法规ID列表，如果为None则评估所有已注册的法规
            
        返回:
            包含评估结果的字典
        """
        logger.info(f"开始评估公司 {company_name} 的合规性")
        
        start_time = datetime.now()
        
        if regulation_ids is None:
            regulation_ids = list(self.graphs.keys())
        
        results = {
            "company_name": company_name,
            "evaluation_time": datetime.now().isoformat(),
            "regulations": {},
            "summary": {}
        }
        
        from backend.database.compliance_unit_db import ComplianceUnitDB
        db = ComplianceUnitDB()
        
        for regulation_id in regulation_ids:
            try:
                if regulation_id not in self.graphs:
                    graph_path = os.path.join(project_root, "data", "graphs", f"{regulation_id}.json")
                    if not os.path.exists(graph_path):
                        logger.error(f"法规图文件不存在: {graph_path}")
                        continue
                    logger.info(f"加载法规图: {regulation_id}")
                    graph = db.load_graph_from_json(graph_path)
                    self.register_graph(graph)
                
                graph = self.graphs[regulation_id]
                logger.info(f"评估 {company_name} 在 {graph.regulation_name} 下的合规性")
                regulation_result = self._evaluate_regulation(graph, company_data)
                results["regulations"][regulation_id] = regulation_result
                
            except Exception as e:
                logger.exception(f"评估法规 {regulation_id} 时出错")
                results["regulations"][regulation_id] = {
                    "error": str(e),
                    "is_compliant": None,
                    "violations": []
                }
        
        results["summary"] = self._generate_summary(results["regulations"])
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        results["execution_time"] = execution_time
        
        logger.info(f"评估完成，耗时 {execution_time:.2f} 秒")
        
        return results

    def _analyze_execution_output(self, unit_id: str, df_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析执行输出的DataFrame（以列表形式），检查是否存在违规。
        """
        if not df_list:
            return {"has_violation": False, "violation_count": 0, "violations": []}

        df = pd.DataFrame(df_list)
        
        # 定义标准化的列名
        subject_col = "_subject_passed"
        condition_col = "_condition_passed"
        constraint_col = "_constraint_passed"

        required_cols = {subject_col, condition_col, constraint_col}
        if not required_cols.issubset(df.columns):
            missing_cols = required_cols - set(df.columns)
            logger.warning(f"单元 {unit_id} 的输出缺少必要列: {missing_cols}")
            return {"has_violation": False, "violation_count": 0, "violations": [], "warning": f"缺少列: {missing_cols}"}

        # --- 更新：扩展违规和摘要的计算逻辑 ---

        # 分别计算布尔值和错误值
        s_passed = df[subject_col] == True
        c_passed = df[condition_col] == True
        constraint_failed = df[constraint_col] == False
        
        s_error = df[subject_col] == 'error'
        c_error = df[condition_col] == 'error'
        constraint_error = df[constraint_col] == 'error'

        # 1. 业务逻辑违规: S 和 C 通过，但 Constraint 失败
        logical_violations_df = df[s_passed & c_passed & constraint_failed]
        
        # 2. 程序执行错误导致的潜在违规
        # 如果 S 和 C 都满足，但约束无法计算（返回了error），也应视为一种需要关注的问题
        error_violations_df = df[s_passed & c_passed & constraint_error]

        logical_violation_count = len(logical_violations_df)
        error_violation_count = len(error_violations_df)
        
        all_problematic_df = pd.concat([logical_violations_df, error_violations_df])

        # 在DEBUG级别记录详细的统计摘要
        try:
            total_rows = len(df)
            subject_passed_count = s_passed.sum()
            condition_passed_count = c_passed.sum()
            constraint_passed_count = (df[constraint_col] == True).sum()
            subject_error_count = s_error.sum()
            condition_error_count = c_error.sum()
            
            log_summary = (
                f"\n--- [执行摘要] CU_ID: {unit_id} ---\n"
                f"  - 总行数              : {total_rows}\n"
                f"  - Subject (Pass/Error)    : {subject_passed_count} / {subject_error_count}\n"
                f"  - Condition (Pass/Error)  : {condition_passed_count} / {condition_error_count}\n"
                f"  - Constraint (Pass/Error) : {constraint_passed_count} / {constraint_error.sum()}\n"
                f"  - 适用行数 (S&C=Pass) : {(s_passed & c_passed).sum()}\n"
                f"  - 业务违规            : {logical_violation_count}\n"
                f"  - 程序错误 (约束)     : {error_violation_count}\n"
                f"  ------------------------------------"
            )
            logger.debug(log_summary)
        except Exception as e:
            logger.warning(f"为单元 {unit_id} 生成执行摘要日志时出错: {e}")

        has_violation = logical_violation_count > 0
        has_error = error_violation_count > 0

        # to_dict 方法的 'orient' 参数是有效的，linter的警告可以忽略
        violations_as_records = all_problematic_df.to_dict(orient='records') # type: ignore

        return {
            "has_violation": has_violation,
            "has_error": has_error,
            "violation_count": logical_violation_count,
            "error_count": error_violation_count,
            "violations": violations_as_records
        }

    def _evaluate_regulation(self, graph: ComplianceGraph, company_data: pd.DataFrame) -> Dict[str, Any]:
        """
        评估单个法规下的合规性，遍历所有节点并记录结果。
        """
        start_time = datetime.now()
        
        # The 'id' attribute exists on the ComplianceUnit class.
        # This might be a linter configuration issue, but the code is correct.
        node_results = {
            unit.cu_id: {
                "unit_info": unit.to_dict(),
                "execution_result": None
            }
            for unit in graph.units.values()
        }
        
        total_violations = 0
        total_errors = 0
        
        execution_order = graph._determine_execution_order()
        
        for cu_id in execution_order:
            unit = graph.get_unit(cu_id)
            if not unit:
                continue

            current_node_result = node_results[cu_id]
            logger.info(f"--- [开始评估单元] CU_ID: {cu_id} ---")
            
            try:
                if unit.code:
                    exec_result = self.executor.execute_rule(
                        unit_id=cu_id,
                        code=unit.code,
                        company_data=company_data,
                        regulation_id=graph.regulation_id
                    )
                    
                    current_node_result["execution_result"] = {
                        "status": "error" if exec_result["status"] == "error" else "executed",
                        "timestamp": datetime.now().isoformat(),
                        "details": exec_result.get("error")
                    }
                    
                    if exec_result["status"] == "success":
                        analysis = self._analyze_execution_output(cu_id, exec_result["result"])
                        current_node_result["execution_result"]["output_analysis"] = analysis
                        
                        # 将详细的检查结果添加到节点信息中
                        if analysis.get("has_violation"):
                            # 只选择包含标准化列的违规记录
                            violations_df = pd.DataFrame(analysis["violations"])[['_subject_passed', '_condition_passed', '_constraint_passed']]
                            current_node_result["execution_result"]["violation_details"] = violations_df.to_dict(orient='records') # type: ignore
                        
                        if analysis.get("has_violation"):
                            total_violations += analysis.get("violation_count", 0)
                        if analysis.get("has_error"):
                            total_errors += analysis.get("error_count", 0)
                    else:
                        total_errors += 1
                        
                else:
                    current_node_result["execution_result"] = {
                        "status": "qualitative",
                        "timestamp": datetime.now().isoformat(),
                        "message": "定性分析节点，无代码执行"
                    }
                    logger.info(f"[评估结果] CU_ID: {cu_id} - 跳过（定性节点）。")
            except Exception as e:
                logger.exception(f"在评估循环中执行单元 {cu_id} 时发生意外错误")
                current_node_result["execution_result"] = {
                    "status": "error",
                    "timestamp": datetime.now().isoformat(),
                    "error_message": f"评估器错误: {str(e)}"
                }
            logger.info(f"--- [结束评估单元] CU_ID: {cu_id} ---")

        # 关系处理暂时禁用，因为它可能与新格式不兼容，后续需要重新评估
        # from .relation_handler import RelationHandler
        # relation_handler = RelationHandler()
        # processed_node_results = relation_handler.process_relations(graph, node_results)
        
        regulation_summary = {
            "regulation_name": graph.regulation_name,
            "is_compliant": total_violations == 0 and total_errors == 0,
            "total_violations": total_violations,
            "total_errors": total_errors,
            "node_results": node_results,
            "execution_time": (datetime.now() - start_time).total_seconds()
        }
        
        return regulation_summary
    
    def _generate_summary(self, regulation_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据详细的法规评估结果生成摘要。
        """
        total_violations = 0
        compliant_regulations = 0
        non_compliant_regulations = 0
        
        for reg_id, result in regulation_results.items():
            if result.get("error"):
                continue
            
            if result.get("is_compliant"):
                compliant_regulations += 1
            else:
                non_compliant_regulations += 1
                total_violations += result.get("total_violations", 0)

        return {
            "total_violations": total_violations,
            "overall_compliant": non_compliant_regulations == 0,
            "compliant_regulations_count": compliant_regulations,
            "non_compliant_regulations_count": non_compliant_regulations,
        }
    
    def generate_report(self, evaluation_result: Dict[str, Any], format_type: str = "html") -> str:
        """
        生成合规评估报告。
        
        参数:
            evaluation_result: 评估结果
            format_type: 报告格式，可以是 "html", "text" 或 "json"
            
        返回:
            格式化的报告
        """
        company_name = evaluation_result.get("company_name", "未知公司")
        evaluation_time = evaluation_result.get("evaluation_time", datetime.now())
        summary = evaluation_result.get("summary", {})
        
        if format_type == "html":
            return self._generate_html_report(company_name, evaluation_time, summary, evaluation_result)
        elif format_type == "text":
            return self._generate_text_report(company_name, evaluation_time, summary, evaluation_result)
        else:
            # 默认返回JSON格式
            return json.dumps(evaluation_result, ensure_ascii=False, default=str, indent=2)
    
    def _generate_html_report(self, company_name: str, evaluation_time: datetime, 
                             summary: Dict[str, Any], full_result: Dict[str, Any]) -> str:
        """
        生成HTML格式的报告。
        
        参数:
            company_name: 公司名称
            evaluation_time: 评估时间
            summary: 评估摘要
            full_result: 完整评估结果
            
        返回:
            HTML格式的报告
        """
        # 简单HTML模板
        html = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>合规评估报告 - {company_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; }}
                h1, h2, h3 {{ color: #333; }}
                .report-header {{ text-align: center; margin-bottom: 30px; }}
                .summary {{ background-color: #f5f5f5; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
                .compliant {{ color: green; }}
                .non-compliant {{ color: red; }}
                .violation {{ margin-bottom: 10px; padding: 10px; background-color: #fff0f0; border-left: 3px solid #ff0000; }}
            </style>
        </head>
        <body>
            <div class="report-header">
                <h1>合规评估报告</h1>
                <p><strong>公司名称：</strong>{company_name}</p>
                <p><strong>评估时间：</strong>{evaluation_time}</p>
            </div>
            
            <div class="summary">
                <h2>评估摘要</h2>
                <p><strong>总体合规状态：</strong>
                    <span class="{'compliant' if summary.get('overall_compliant', False) else 'non-compliant'}">
                        {'合规' if summary.get('overall_compliant', False) else '不合规'}
                    </span>
                </p>
                <p><strong>违规总数：</strong>{summary.get('total_violations', 0)}</p>
                <p><strong>违规法规数：</strong>{len(summary.get('violated_regulations', []))}</p>
            </div>
        """
        
        # 如果有违规，显示违规详情
        if not summary.get('overall_compliant', False):
            html += """
            <h2>违规详情</h2>
            """
            
            # 按法规分组显示违规
            for regulation in summary.get('violated_regulations', []):
                regulation_id = regulation.get('regulation_id', '')
                regulation_name = regulation.get('regulation_name', '')
                
                html += f"""
                <h3>{regulation_name} ({regulation_id})</h3>
                """
                
                # 找出该法规的所有违规
                violations = [v for v in summary.get('all_violations', []) if v.get('regulation_id') == regulation_id]
                
                for violation in violations:
                    cu_id = violation.get('cu_id', '')
                    subject = violation.get('subject', '')
                    condition = violation.get('condition', '')
                    constraint = violation.get('constraint', '')
                    message = violation.get('message', '')
                    
                    html += f"""
                    <div class="violation">
                        <p><strong>违规单元：</strong>{cu_id}</p>
                        <p><strong>适用主体：</strong>{subject}</p>
                        <p><strong>触发条件：</strong>{condition}</p>
                        <p><strong>约束条件：</strong>{constraint}</p>
                        <p><strong>违规描述：</strong>{message}</p>
                    </div>
                    """
        
        # 报告结尾
        html += """
        </body>
        </html>
        """
        
        return html
    
    def _generate_text_report(self, company_name: str, evaluation_time: datetime, 
                             summary: Dict[str, Any], full_result: Dict[str, Any]) -> str:
        """
        生成纯文本格式的报告。
        
        参数:
            company_name: 公司名称
            evaluation_time: 评估时间
            summary: 评估摘要
            full_result: 完整评估结果
            
        返回:
            纯文本格式的报告
        """
        text = f"""
合规评估报告
==============================================
公司名称: {company_name}
评估时间: {evaluation_time}

评估摘要
----------------------------------------------
总体合规状态: {'合规' if summary.get('overall_compliant', False) else '不合规'}
违规总数: {summary.get('total_violations', 0)}
违规法规数: {len(summary.get('violated_regulations', []))}
        """
        
        # 如果有违规，显示违规详情
        if not summary.get('overall_compliant', False):
            text += """
违规详情
----------------------------------------------
"""
            
            # 按法规分组显示违规
            for regulation in summary.get('violated_regulations', []):
                regulation_id = regulation.get('regulation_id', '')
                regulation_name = regulation.get('regulation_name', '')
                
                text += f"""
{regulation_name} ({regulation_id})
"""
                
                # 找出该法规的所有违规
                violations = [v for v in summary.get('all_violations', []) if v.get('regulation_id') == regulation_id]
                
                for i, violation in enumerate(violations, 1):
                    cu_id = violation.get('cu_id', '')
                    subject = violation.get('subject', '')
                    condition = violation.get('condition', '')
                    constraint = violation.get('constraint', '')
                    message = violation.get('message', '')
                    
                    text += f"""
违规 {i}:
  - 违规单元: {cu_id}
  - 适用主体: {subject}
  - 触发条件: {condition}
  - 约束条件: {constraint}
  - 违规描述: {message}
"""
        
        return text


if __name__ == "__main__":
    # 该测试代码块已过时，依赖于旧的、已被移除的组件
    # (如 regulation_xx_processor, register_data_processor)
    # 为了避免linter错误和混淆，将其整个移除。
    pass 