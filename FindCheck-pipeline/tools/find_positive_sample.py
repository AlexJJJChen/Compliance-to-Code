#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一个用于在数据集中寻找第一个“阳性样本”（即违规案例）的工具。

该脚本会自动遍历指定法规下的所有公司，并执行合规检查，
直到找到第一个出现违规的公司为止。
"""

import logging
import sys
import os

# 将项目根目录添加到Python路径中，以便导入其他模块
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from tools.compliance_checker import check_compliance
from tools.data_fetcher import DataFetcher

# 配置一个简单的日志记录器
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def find_positive_sample(regulation_id: str):
    """
    遍历给定法规下的所有公司，寻找第一个违规案例。

    参数:
        regulation_id: 要检查的法规ID (例如, 'regulation_04')。
    """
    logger.info(f"开始为法规 '{regulation_id}' 搜索阳性样本...")

    # 1. 获取该法规下的所有公司列表
    try:
        data_fetcher = DataFetcher()
        companies = data_fetcher.get_available_companies(regulation_id)
        if not companies:
            logger.warning(f"在 {regulation_id} 的数据文件中没有找到任何公司。")
            return
        logger.info(f"将在 {len(companies)} 家公司中进行搜索: {', '.join(companies)}")
    except FileNotFoundError:
        logger.error(f"未找到法规 '{regulation_id}' 对应的数据文件。请检查 `data/` 目录。")
        return
    except Exception as e:
        logger.error(f"获取公司列表时出错: {e}")
        return

    # 2. 遍历每个公司并进行检查
    for i, company_name in enumerate(companies, 1):
        logger.info(f"--- [{i}/{len(companies)}] 正在检查公司: {company_name} ---")
        try:
            # 调用核心检查逻辑，关闭详细日志以保持输出简洁
            result = check_compliance(
                company_name=company_name,
                regulation_id=regulation_id,
                verbose=False 
            )

            # 检查结果中是否有违规
            summary = result.get("summary", {})
            if summary.get("total_violations", 0) > 0:
                logger.info("=" * 80)
                logger.info(f"🎉 找到阳性样本！")
                logger.info(f"公司: {company_name}")
                logger.info(f"法规: {regulation_id}")
                logger.info(f"违规总数: {summary.get('total_violations')}")
                logger.info("-" * 80)
                logger.info("您可以使用以下命令以详细模式复现此案例:")
                # 使用引号确保公司名称正确处理
                reproduce_cmd = f'python main.py check --company "{company_name}" --regulation {regulation_id} --verbose'
                print("\n" + reproduce_cmd + "\n")
                logger.info("=" * 80)
                return  # 找到后即退出

        except Exception as e:
            logger.error(f"检查公司 '{company_name}' 时发生意外错误: {e}")

    # 3. 如果循环完成仍未找到
    logger.info("=" * 80)
    logger.info(f"搜索完成。未在所有公司中发现针对法规 '{regulation_id}' 的违规案例。")
    logger.info("=" * 80)


if __name__ == "__main__":
    # 当前任务是专注于股份回购，因此将法规ID硬编码为 'regulation_04'
    find_positive_sample("regulation_04") 