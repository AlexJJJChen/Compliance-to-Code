#!/usr/bin/env python3
"""
'祎煜环保'股份回购合规检查程序

该脚本针对"祎煜环保"公司在2022年到2023年间的股份回购行为进行合规检查，
使用的是第4号法规（股份回购）。
"""

import os
import sys
import json
import logging
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# 导入合规检查模块
from compliance_checker import check_compliance


def main():
    """主函数"""
    # 检查参数
    company_name = "祎煜环保"
    regulation_id = "regulation_04"  # 股份回购
    start_date = "2022-01-01"
    end_date = "2023-12-31"
    detailed = True
    verbose = True
    
    print(f"开始对 {company_name} 执行 {regulation_id} 合规检查")
    print(f"检查时间范围: {start_date} 到 {end_date}")
    
    # 执行合规检查
    result = check_compliance(
        company_name=company_name,
        regulation_id=regulation_id,
        start_date=start_date,
        end_date=end_date,
        detailed=detailed,
        verbose=verbose
    )
    
    # 检查结果状态
    if result.get("status") == "failed":
        print(f"\n检查失败: {result.get('reason', '未知原因')}")
        sys.exit(1)
    
    # 输出检查结果摘要
    print("\n" + "="*80)
    print(f"祎煜环保 - 股份回购合规检查结果摘要")
    print("="*80)
    
    # 合规状态
    compliant = result.get("summary", {}).get("overall_compliant", False)
    violations = result.get("summary", {}).get("all_violations", [])
    
    print(f"合规状态: {'合规' if compliant else '不合规'}")
    print(f"违规数量: {len(violations)}")
    print(f"检查时间: {result.get('evaluation_time', datetime.now())}")
    
    # 统计图表信息
    if regulation_id in result.get("regulations", {}):
        reg_info = result["regulations"][regulation_id]
        total_units = reg_info.get("total_units", 0)
        executed_units = reg_info.get("executed_units", 0)
        execution_time = reg_info.get("execution_time", 0)
        
        print(f"图中总单元数: {total_units}")
        print(f"执行的单元数: {executed_units}")
        print(f"执行时间: {execution_time:.2f} 秒")
    
    # 输出详细违规信息
    if violations:
        print("\n违规详情:")
        for i, violation in enumerate(violations, 1):
            print(f"\n违规 {i}:")
            print(f"  单元ID: {violation.get('cu_id', 'N/A')}")
            print(f"  适用主体: {violation.get('subject', 'N/A')}")
            print(f"  触发条件: {violation.get('condition', 'N/A')}")
            print(f"  约束条件: {violation.get('constraint', 'N/A')}")
            if violation.get('contextual_info'):
                print(f"  上下文信息: {violation.get('contextual_info', 'N/A')}")
            print(f"  违规描述: {violation.get('message', 'N/A')}")
            
            # 显示详细信息（如果有）
            details = violation.get('details', {})
            if details:
                print("  详细数据:")
                for key, value in details.items():
                    print(f"    - {key}: {value}")
    
    print("\n" + "="*80)
    print(f"结果文件保存路径: {result.get('output_path', '未知')}")
    print("="*80)


if __name__ == "__main__":
    main() 