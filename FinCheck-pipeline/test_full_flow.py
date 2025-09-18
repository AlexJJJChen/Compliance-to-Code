#!/usr/bin/env python3
"""
测试完整流程脚本

该脚本用于测试从数据获取、执行、关系后处理到结果保存的完整流程。
"""

import os
import sys
import json
import logging
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# 核心模块导入
from tools.execution_engine import ExecutionEngine

# 创建日志记录器
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger("test_full_flow")


def main():
    """主函数"""
    logger.info("开始测试完整流程")
    
    # 初始化执行引擎
    engine = ExecutionEngine()
    
    # 运行检查
    company_name = "祎煜环保"
    regulation_id = "regulation_04"
    
    logger.info(f"开始对公司 {company_name} 进行 {regulation_id} 的合规检查")
    result = engine.run_and_save(
        company_name=company_name,
        regulation_id=regulation_id
    )
    
    # 检查结果
    if "error" in result:
        logger.error(f"检查失败: {result['error']}")
        return
    
    # 打印最终合规状态
    final_status = result.get("final_compliance_status", {})
    logger.info(f"最终合规状态: {final_status.get('summary', '未知')}")
    logger.info(f"违规单元数量: {final_status.get('violation_count', 0)}")
    logger.info(f"被排除单元数量: {final_status.get('excluded_count', 0)}")
    logger.info(f"被强制包含单元数量: {final_status.get('forced_count', 0)}")
    
    logger.info("测试完整流程结束")


if __name__ == "__main__":
    main() 