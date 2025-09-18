#!/usr/bin/env python3
"""
合规检查主执行脚本

主要功能：
1. 获取特定公司在特定时间范围内的数据
2. 执行合规检查
3. 分析并输出结果报告
"""

import os
import sys
import json
import argparse
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# 导入自定义模块
from tools.data_fetcher import DataFetcher
from backend.compliance_engine.rule_executor import RuleExecutor, regulation_04_processor, regulation_08_processor, regulation_10_processor
from backend.compliance_engine.evaluator import Evaluator
from backend.database.compliance_unit_db import ComplianceUnitDB


# 设置日志记录器
def setup_logging(log_dir: str = "logs") -> logging.Logger:
    """设置日志记录器"""
    # 确保日志目录存在
    os.makedirs(log_dir, exist_ok=True)
    
    # 创建记录器
    logger = logging.getLogger("compliance_checker")
    logger.setLevel(logging.INFO)
    
    # 防止日志重复
    if logger.handlers:
        return logger
    
    # 文件处理器
    log_file = os.path.join(log_dir, f"compliance_checker_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 设置格式
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def check_compliance(
    company_name: str,
    regulation_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    detailed: bool = False,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    执行合规性检查
    
    参数:
        company_name: 公司名称
        regulation_id: 法规ID
        start_date: 开始日期，格式为"YYYY-MM-DD"
        end_date: 结束日期，格式为"YYYY-MM-DD"
        detailed: 是否生成详细报告
        verbose: 是否输出详细日志
    
    返回:
        合规检查结果
    """
    # 设置日志级别
    log_level = logging.DEBUG if verbose else logging.INFO
    logger = setup_logging()
    logger.setLevel(log_level)
    
    logger.info("="*80)
    logger.info(f"开始对 {company_name} 进行 {regulation_id} 合规检查")
    logger.info(f"时间范围: {start_date or '全部'} 到 {end_date or '全部'}")
    logger.info("="*80)
    
    # 初始化数据获取器、规则执行器和评估器
    data_fetcher = DataFetcher()
    rule_executor = RuleExecutor()
    evaluator = Evaluator(rule_executor)
    
    # 注册数据处理器
    rule_executor.register_data_processor("regulation_04", regulation_04_processor)
    rule_executor.register_data_processor("regulation_08", regulation_08_processor)
    rule_executor.register_data_processor("regulation_10", regulation_10_processor)
    
    # 步骤1: 获取公司数据
    logger.info("步骤1: 获取公司数据")
    company_data = data_fetcher.get_company_data(company_name, regulation_id, start_date, end_date)
    
    if company_data is None or len(company_data) == 0:
        logger.error("未找到公司数据，检查中止")
        return {
            "company_name": company_name,
            "regulation_id": regulation_id,
            "start_date": start_date,
            "end_date": end_date,
            "status": "failed",
            "reason": "未找到公司数据",
            "timestamp": datetime.now(),
        }
    
    logger.info(f"获取到 {len(company_data)} 条公司数据记录")
    
    # 步骤2: 预加载合规图
    logger.info("步骤2: 加载合规图")
    db = ComplianceUnitDB()
    graph_path = os.path.join(project_root, "data", "graphs", f"{regulation_id}.json")
    
    if not os.path.exists(graph_path):
        logger.error(f"合规图文件不存在: {graph_path}")
        return {
            "company_name": company_name,
            "regulation_id": regulation_id,
            "start_date": start_date,
            "end_date": end_date,
            "status": "failed",
            "reason": "加载合规图失败",
            "timestamp": datetime.now(),
        }
    
    try:
        graph = db.load_graph_from_json(graph_path)
        evaluator.register_graph(graph)
    except Exception as e:
        logger.error(f"加载合规图失败: {e}")
        return {
            "company_name": company_name,
            "regulation_id": regulation_id,
            "start_date": start_date,
            "end_date": end_date,
            "status": "failed",
            "reason": f"加载合规图失败: {e}",
            "timestamp": datetime.now(),
        }
    
    # 步骤3: 执行合规检查
    logger.info("步骤3: 执行合规检查")
    result = evaluator.evaluate_company(company_name, company_data, [regulation_id])
    
    # 分析节点执行情况
    total_nodes = 0
    executed_nodes = 0
    qualitative_nodes = 0
    error_nodes = 0
    violation_nodes = 0
    
    # 提取法规结果
    regulation_result = result["regulations"].get(regulation_id, {})
    
    # 如果有node_results字段，分析节点情况
    if "node_results" in regulation_result:
        node_results = regulation_result["node_results"]
        total_nodes = len(node_results)
        
        for node_id, node_data in node_results.items():
            exec_result = node_data.get("execution_result", {})
            status = exec_result.get("status", "unknown")
            
            if status == "executed":
                executed_nodes += 1
                if exec_result.get("has_violation", False):
                    violation_nodes += 1
            elif status == "qualitative":
                qualitative_nodes += 1
            elif status == "error":
                error_nodes += 1
        
        # 添加统计信息到结果
        regulation_result["stats"] = {
            "total_nodes": total_nodes,
            "executed_nodes": executed_nodes,
            "qualitative_nodes": qualitative_nodes,
            "error_nodes": error_nodes,
            "violation_nodes": violation_nodes
        }
    
    # 步骤4: 保存结果
    logger.info("步骤4: 保存结果")
    # 创建结果目录
    results_dir = os.path.join(project_root, "results")
    os.makedirs(results_dir, exist_ok=True)
    
    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = os.path.join(results_dir, f"{company_name}_{regulation_id}_{timestamp}.json")
    
    # 保存JSON结果
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    
    logger.info(f"结果已保存至: {result_file}")
    
    # 生成报告
    if detailed:
        # 生成HTML报告
        html_report = evaluator.generate_report(result, "html")
        html_file = os.path.join(results_dir, f"{company_name}_{regulation_id}_{timestamp}.html")
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_report)
        logger.info(f"HTML报告已保存至: {html_file}")
        
        # 生成文本报告
        text_report = evaluator.generate_report(result, "text")
        text_file = os.path.join(results_dir, f"{company_name}_{regulation_id}_{timestamp}.txt")
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(text_report)
        logger.info(f"文本报告已保存至: {text_file}")
    
    # 添加文件路径和统计信息到结果
    result['output_path'] = result_file
    result['node_stats'] = {
        "total_nodes": total_nodes,
        "executed_nodes": executed_nodes,
        "qualitative_nodes": qualitative_nodes,
        "error_nodes": error_nodes,
        "violation_nodes": violation_nodes,
        "execution_percentage": round(executed_nodes / total_nodes * 100, 2) if total_nodes > 0 else 0
    }
    
    logger.info("="*80)
    logger.info(f"合规检查完成，结果已保存至: {result_file}")
    logger.info(f"检查总结: {'合规' if result.get('summary', {}).get('overall_compliant', False) else '存在违规'}")
    logger.info(f"违规数: {result.get('summary', {}).get('total_violations', 0)}")
    logger.info(f"总节点数: {total_nodes}, 执行节点数: {executed_nodes}, 质性分析节点数: {qualitative_nodes}")
    logger.info(f"执行覆盖率: {round(executed_nodes / total_nodes * 100, 2)}% 如果总节点数大于0 else 0")
    logger.info("="*80)
    
    return result


def format_violations(violations: List[Dict[str, Any]]) -> str:
    """格式化违规信息，便于输出"""
    if not violations:
        return "未发现违规"
    
    formatted = []
    for i, violation in enumerate(violations, 1):
        formatted.append(f"违规 {i}:")
        formatted.append(f"  单元ID: {violation.get('cu_id', 'N/A')}")
        formatted.append(f"  适用主体: {violation.get('subject', 'N/A')}")
        formatted.append(f"  触发条件: {violation.get('condition', 'N/A')}")
        formatted.append(f"  约束条件: {violation.get('constraint', 'N/A')}")
        if violation.get('contextual_info'):
            formatted.append(f"  上下文信息: {violation.get('contextual_info', 'N/A')}")
        formatted.append(f"  违规描述: {violation.get('message', 'N/A')}")
        formatted.append("")
    
    return "\n".join(formatted)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="合规检查工具")
    parser.add_argument("--company", required=True, help="要检查的公司名称")
    parser.add_argument("--regulation", required=True, help="要使用的法规ID (regulation_04, regulation_08, regulation_10)")
    parser.add_argument("--start-date", help="数据开始日期 (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="数据结束日期 (YYYY-MM-DD)")
    parser.add_argument("--detailed", action="store_true", help="是否生成详细报告")
    parser.add_argument("--verbose", action="store_true", help="是否输出详细日志")
    
    args = parser.parse_args()
    
    # 执行合规检查
    result = check_compliance(
        company_name=args.company,
        regulation_id=args.regulation,
        start_date=args.start_date,
        end_date=args.end_date,
        detailed=args.detailed,
        verbose=args.verbose
    )
    
    # 输出简要报告
    print("\n" + "="*50)
    print(f"公司: {args.company}")
    print(f"法规: {args.regulation}")
    
    if result.get("status") == "failed":
        print(f"检查状态: 失败 - {result.get('reason', '未知原因')}")
    else:
        violations = result.get("summary", {}).get("all_violations", [])
        
        print(f"检查状态: {'合规' if result.get('summary', {}).get('overall_compliant', False) else '存在违规'}")
        print(f"违规数量: {len(violations)}")
        
        if violations:
            print("\n违规详情:")
            print(format_violations(violations))
            
    print("="*50)


if __name__ == "__main__":
    main() 