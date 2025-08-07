#!/usr/bin/env python3
"""
Compliance-to-Code 金融合规自动化系统主入口

主要功能：
1. 提供统一的命令行接口
2. 根据参数调用不同的工具
3. 简化用户交互体验
"""

import os
import sys
import argparse
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# 从tools导入功能模块
from tools.execution_engine import ExecutionEngine
from tools.data_fetcher import DataFetcher


def main():
    """主函数，处理命令行参数并调用相应的工具"""
    # 创建主解析器
    parser = argparse.ArgumentParser(
        description="Compliance-to-Code 金融合规自动化系统",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # 创建子命令解析器
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 1. 合规检查命令
    check_parser = subparsers.add_parser("check", help="执行合规检查")
    check_parser.add_argument("--company", required=True, help="要检查的公司名称")
    check_parser.add_argument("--regulation", required=True, help="要使用的法规ID (regulation_04, regulation_08, regulation_10)")
    check_parser.add_argument("--start-date", help="数据开始日期 (YYYY-MM-DD)")
    check_parser.add_argument("--end-date", help="数据结束日期 (YYYY-MM-DD)")
    check_parser.add_argument("--verbose", action="store_true", help="是否输出详细日志 (DEBUG 级别)")
    
    # 2. 压力测试命令
    stress_parser = subparsers.add_parser("stress-test", help="执行股份回购压力测试")
    stress_parser.add_argument("--runs", type=int, default=100, help="执行次数，默认100次")
    stress_parser.add_argument("--fuzz-factor", type=float, default=0.2, help="数据变异幅度，默认20%")
    
    # 3. 列出可用公司
    list_parser = subparsers.add_parser("list-companies", help="列出可用的公司")
    list_parser.add_argument("--regulation", required=True, help="法规ID (regulation_04, regulation_08, regulation_10)")
    
    # 解析参数
    args = parser.parse_args()
    
    # 如果没有指定命令，显示帮助信息
    if not args.command:
        parser.print_help()
        return
    
    # 执行相应的命令
    if args.command == "check":
        # 实例化统一的执行引擎
        engine = ExecutionEngine()
        
        # 执行合规检查并保存结果
        print(f"正在为公司 '{args.company}' 执行法规 '{args.regulation}' 的合规检查...")
        response = engine.run_and_save(
            company_name=args.company,
            regulation_id=args.regulation,
            start_date=args.start_date,
            end_date=args.end_date,
        )
        
        # 检查并输出简要报告
        print("\n" + "="*50)
        print(f"公司: {args.company}")
        print(f"法规: {args.regulation}")

        if "error" in response:
            print(f"检查状态: 失败 - {response['error']}")
        else:
            summary = response.get("results", {}).get("summary", {})
            overall_compliant = summary.get("overall_compliant", False)
            total_violations = summary.get("total_violations", 0)
            
            print(f"检查状态: {'合规' if overall_compliant else '存在违规'}")
            print(f"违规数量: {total_violations}")
            
        print("详细结果已保存到 results/ 目录下的最新文件夹中。")
        print("="*50)
        
    elif args.command == "stress-test":
        # 导入压力测试模块
        from run_regulation_04_stress_test import run_stress_test
        
        # 执行压力测试
        print(f"开始执行股份回购压力测试，将进行{args.runs}次随机变异测试...")
        run_stress_test(num_runs=args.runs, fuzz_factor=args.fuzz_factor)
        
    elif args.command == "list-companies":
        # 列出可用公司
        fetcher = DataFetcher()
        companies = fetcher.get_available_companies(args.regulation)
        
        print(f"\n法规 {args.regulation} 下的可用公司: {len(companies)}")
        if companies:
            for i, company in enumerate(companies, 1):
                print(f"{i}. {company}")
        else:
            print("未找到可用公司")


if __name__ == "__main__":
    main() 