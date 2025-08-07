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
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# 导入自定义模块
from tools.data_fetcher import DataFetcher
from tools.execution_engine import ExecutionEngine


# 设置日志记录器 - (此函数已由ExecutionEngine的根日志配置取代)
logger = logging.getLogger(__name__)


def check_compliance(
    company_name: str,
    regulation_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    执行合规性检查
    
    参数:
        company_name: 公司名称
        regulation_id: 法规ID
        start_date: 开始日期，格式为"YYYY-MM-DD"
        end_date: 结束日期，格式为"YYYY-MM-DD"
        verbose: 是否输出详细日志
    
    返回:
        合规检查结果
    """
    # 1. 设置日志级别并初始化引擎
    log_level = logging.DEBUG if verbose else logging.INFO
    # ExecutionEngine现在负责配置根日志记录器
    engine = ExecutionEngine(log_level=log_level)
    
    logger.info("="*80)
    logger.info(f"开始对 {company_name} 进行 {regulation_id} 合规检查")
    logger.info(f"时间范围: {start_date or '全部'} 到 {end_date or '全部'}")
    logger.info("="*80)
    
    # 初始化数据获取器
    data_fetcher = DataFetcher()
    
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
    
    # 步骤2: 加载合规图
    logger.info("步骤2: 加载合规图")
    graph = engine.load_graph(regulation_id)
    
    if graph is None:
        logger.error("加载合规图失败，检查中止")
        return {
            "company_name": company_name,
            "regulation_id": regulation_id,
            "start_date": start_date,
            "end_date": end_date,
            "status": "failed",
            "reason": "加载合规图失败",
            "timestamp": datetime.now(),
        }
    
    # 步骤3: 执行合规检查
    logger.info("步骤3: 执行合规检查")
    result = engine.execute_graph(graph, company_data, company_name)
    
    # 步骤4: 保存结果
    logger.info("步骤4: 保存结果")
    output_path = engine.save_results(result, regulation_id, company_name)
    
    logger.info("="*80)
    logger.info(f"合规检查完成，结果已保存至: {output_path}")
    summary = result.get("summary", {})
    logger.info(f"检查总结: {'合规' if summary.get('overall_compliant', False) else '存在违规'}")
    logger.info(f"违规数: {summary.get('total_violations', 0)}")
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
        formatted.append("")
    
    return "\n".join(formatted)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="合规检查工具")
    parser.add_argument("--company", required=True, help="要检查的公司名称")
    parser.add_argument("--regulation", required=True, help="要使用的法规ID (regulation_04, regulation_08, regulation_10)")
    parser.add_argument("--start-date", help="数据开始日期 (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="数据结束日期 (YYYY-MM-DD)")
    parser.add_argument("--verbose", action="store_true", help="是否输出详细日志")
    
    args = parser.parse_args()
    
    # 执行合规检查
    result = check_compliance(
        company_name=args.company,
        regulation_id=args.regulation,
        start_date=args.start_date,
        end_date=args.end_date,
        verbose=args.verbose
    )
    
    # 输出简要报告
    print("\n" + "="*50)
    print(f"公司: {args.company}")
    print(f"法规: {args.regulation}")
    
    if result.get("status") == "failed":
        print(f"检查状态: 失败 - {result.get('reason', '未知原因')}")
    else:
        summary = result.get("summary", {})
        violations = summary.get("all_violations", [])
        
        print(f"检查状态: {'合规' if summary.get('overall_compliant', False) else '存在违规'}")
        print(f"违规数量: {summary.get('total_violations', 0)}")
        
        if violations:
            print("\n违规详情:")
            print(format_violations(violations))
            
    print("="*50)


if __name__ == "__main__":
    main() 