#!/usr/bin/env python3
"""
'祎煜环保'股份回购合规检查程序

该脚本针对"祎煜环保"公司在2022年到2023年间的股份回购行为进行合规检查，
使用的是第4号法规（股份回购）。
"""

import os
import sys
import logging
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# 导入自定义模块
from tools.compliance_checker import check_compliance


def main():
    """主函数"""
    # 设置日志级别
    logging.basicConfig(level=logging.INFO)
    
    # 设置检查参数
    company_name = "祎煜环保"
    regulation_id = "regulation_04"  # 股份回购
    start_date = "2022-01-01"
    end_date = "2023-12-31"
    
    print(f"开始对 {company_name} 进行股份回购(04)合规检查")
    print(f"检查时间范围: {start_date} 到 {end_date}")
    
    # 执行检查，生成详细报告
    result = check_compliance(
        company_name=company_name,
        regulation_id=regulation_id,
        start_date=start_date,
        end_date=end_date,
        detailed=True,  # 生成详细报告
        verbose=True    # 输出详细日志
    )
    
    # 简要分析结果
    if result.get("status") == "failed":
        print(f"\n检查失败: {result.get('reason', '未知原因')}")
        sys.exit(1)
        
    # 获取统计数据
    summary_result = result.get("summary", {})
    violations = summary_result.get("summary", {}).get("all_violations", [])
    total_units = len(result.get("detailed", {}))
    units_with_code = sum(1 for r in result.get("detailed", {}).values() if r.get("executed") is True)
    
    # 输出分析报告
    print("\n" + "="*80)
    print("祎煜环保 - 股份回购合规检查报告")
    print("="*80)
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"检查范围: {start_date} 到 {end_date}")
    print(f"总计合规单元: {total_units}")
    print(f"执行的合规单元: {units_with_code}")
    print(f"违规数量: {len(violations)}")
    print(f"合规状态: {'合规' if summary_result.get('summary', {}).get('overall_compliant', False) else '存在违规'}")
    
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
    
    print("\n" + "="*80)
    print(f"结果已保存至: {result.get('output_path', '未知')}")
    print("="*80)


if __name__ == "__main__":
    main() 