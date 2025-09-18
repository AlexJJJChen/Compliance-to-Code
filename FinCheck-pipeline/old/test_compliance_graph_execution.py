#!/usr/bin/env python3
"""
合规图执行流程测试脚本

该脚本用于测试合规图的执行流程，确保所有节点（包括没有代码的节点）都能被正确遍历和处理。
"""

import os
import sys
import json
import logging
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import platform
import matplotlib.font_manager as fm
import argparse
from typing import Dict, Any, Optional, List

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# 导入自定义模块
from backend.compliance_engine.rule_executor import RuleExecutor, regulation_04_processor, regulation_08_processor, regulation_10_processor
from backend.compliance_engine.evaluator import Evaluator
from backend.database.compliance_unit_db import ComplianceUnitDB
from tools.data_fetcher import DataFetcher


def setup_logging(log_filename: Optional[str] = None) -> logging.Logger:
    """
    设置日志记录器。
    如果提供了log_filename，则使用它；否则，根据时间戳创建。
    """
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    if log_filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = os.path.join(log_dir, f"compliance_checker_{timestamp}.log")

    # 配置日志记录器
    # ... (the rest of the function remains the same, using the determined log_filename)
    
    # Check if handlers are already attached to the root logger
    if not logging.getLogger().handlers:
        # Basic configuration for the root logger
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
    logger = logging.getLogger(__name__)
    return logger


# 将辅助函数移到顶层，以便重用
def print_execution_summary(results: Dict[str, Any]):
    """打印执行摘要信息"""
    regulation_id = list(results['regulations'].keys())[0]
    summary = results['summary'].get(regulation_id, {})
    company_name = results.get("company_name", "N/A")
    
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info(f"节点执行统计 - {company_name} - {regulation_id}")
    logger.info(f"总节点数: {summary.get('total_units', 'N/A')}")
    logger.info(f"执行节点数: {summary.get('executed_units', 'N/A')}")
    logger.info(f"定性分析节点数: {summary.get('qualitative_units', 'N/A')}")
    logger.info(f"执行错误节点数: {summary.get('error_units', 'N/A')}")
    logger.info(f"违规节点数: {summary.get('violation_units', 'N/A')}")
    coverage = summary.get('coverage', 0) * 100
    logger.info(f"执行覆盖率: {coverage:.2f}%")
    logger.info("=" * 50)

def generate_and_save_chart(results: Dict[str, Any], company_name: str, regulation_id: str):
    """生成并保存执行统计图表"""
    # ... (function implementation remains the same)

def test_graph_execution(regulation_id: str, 
                         company_name: str, 
                         save_chart: bool = False, 
                         input_data: Optional[pd.DataFrame] = None,
                         save_report: bool = True) -> Dict[str, Any]:
    """
    测试合规图执行流程，增加了对报告保存的控制。
    """
    logger = setup_logging()
    
    logger.info(f"开始测试 {regulation_id} 合规图执行流程，公司：{company_name}")
    
    # 初始化组件
    rule_executor = RuleExecutor()
    evaluator = Evaluator(rule_executor)
    data_fetcher = DataFetcher()
    
    # 注册数据处理器
    rule_executor.register_data_processor("regulation_04", regulation_04_processor)
    rule_executor.register_data_processor("regulation_08", regulation_08_processor)
    rule_executor.register_data_processor("regulation_10", regulation_10_processor)
    
    # 如果没有提供输入数据，则从文件加载
    if input_data is None:
        logger.info("未提供输入数据，将从文件加载...")
        company_data = data_fetcher.get_company_data(company_name, regulation_id)
        if company_data is None or company_data.empty:
            logger.error(f"未找到公司 {company_name} 的数据。")
            return {}
        logger.info(f"从文件加载了 {len(company_data)} 条关于 {company_name} 的数据。")
    else:
        company_data = input_data
        logger.info(f"使用传入的DataFrame作为输入数据，共 {len(company_data)} 条记录。")
    
    # 加载合规图
    db = ComplianceUnitDB()
    graph_path = os.path.join(project_root, "data", "graphs", f"{regulation_id}.json")
    
    if not os.path.exists(graph_path):
        logger.error(f"合规图文件不存在: {graph_path}")
        return {}
    
    try:
        graph = db.load_graph_from_json(graph_path)
        logger.info(f"加载合规图成功: {graph.regulation_name}")
        logger.info(f"合规单元数量: {len(graph.units)}")
        
        # 统计有代码的单元数量
        units_with_code = sum(1 for unit in graph.units.values() if unit.code)
        logger.info(f"有代码的单元数量: {units_with_code} ({units_with_code/len(graph.units)*100:.2f}%)")
        
        # 注册合规图
        evaluator.register_graph(graph)
    except Exception as e:
        logger.error(f"加载合规图失败: {e}")
        return {}
    
    # 执行评估
    logger.info("开始执行合规图评估")
    result = evaluator.evaluate_company(company_name, company_data, [regulation_id])
    
    # 提取法规结果
    regulation_result = result["regulations"].get(regulation_id, {})
    
    # 分析节点结果
    if "node_results" in regulation_result:
        node_results = regulation_result["node_results"]
        
        # 统计节点状态
        status_counts = {"executed": 0, "qualitative": 0, "error": 0, "unknown": 0}
        violation_count = 0
        
        for node_id, node_data in node_results.items():
            exec_result = node_data.get("execution_result", {})
            status = exec_result.get("status", "unknown")
            
            if status in status_counts:
                status_counts[status] += 1
            else:
                status_counts["unknown"] += 1
                
            # 统计违规节点
            if status == "executed" and exec_result.get("has_violation", False):
                violation_count += 1
        
        # 输出统计结果
        logger.info("="*50)
        logger.info(f"节点执行统计 - {company_name} - {regulation_id}")
        logger.info(f"总节点数: {len(node_results)}")
        logger.info(f"执行节点数: {status_counts['executed']}")
        logger.info(f"定性分析节点数: {status_counts['qualitative']}")
        logger.info(f"执行错误节点数: {status_counts['error']}")
        logger.info(f"违规节点数: {violation_count}")
        logger.info(f"执行覆盖率: {status_counts['executed']/len(node_results)*100:.2f}%")
        logger.info("="*50)
        
        # 可选：生成可视化图表
        if save_chart:
            try:
                plot_graph_execution_stats(regulation_id, company_name, status_counts, violation_count, len(node_results))
            except Exception as e:
                logger.error(f"生成图表失败: {e}")
        
        # 保存结果
        save_path = os.path.join(project_root, "results", f"{company_name}_{regulation_id}_execution_test.json")
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"结果已保存至: {save_path}")
        
    else:
        logger.warning("未找到节点执行结果")
        
    # 评估完成
    logger.info(f"评估完成，耗时 {result['regulations'][regulation_id]['execution_time']:.2f} 秒")
    
    # 打印统计信息
    print_execution_summary(result)

    # 如果启用了图表保存，则生成并保存图表
    if save_chart:
        generate_and_save_chart(result, company_name, regulation_id)
        
    # 根据参数决定是否保存JSON报告
    if save_report:
        results_dir = "results"
        os.makedirs(results_dir, exist_ok=True)
        result_path = os.path.join(results_dir, f"{company_name}_{regulation_id}_execution_test.json")
        try:
            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            logger.info(f"结果已保存至: {result_path}")
        except Exception as e:
            logger.error(f"保存结果文件失败: {e}")

    return result


def plot_graph_execution_stats(regulation_id, company_name, status_counts, violation_count, total_nodes):
    """生成图表可视化执行统计"""
    # 检测操作系统类型并设置中文字体
    os_type = platform.system()
    chinese_font = None
    
    if os_type == "Darwin":  # macOS
        # 尝试找到常见的macOS中文字体
        font_paths = [
            "/System/Library/Fonts/PingFang.ttc",  # macOS上的PingFang字体
            "/System/Library/Fonts/STHeiti Light.ttc",  # macOS上的华文黑体
            "/System/Library/Fonts/Hiragino Sans GB.ttc"  # macOS上的冬青黑体
        ]
        for font_path in font_paths:
            try:
                if os.path.exists(font_path):
                    chinese_font = fm.FontProperties(fname=font_path)
                    break
            except:
                continue
    elif os_type == "Windows":  # Windows
        # 尝试找到常见的Windows中文字体
        font_paths = [
            "C:\\Windows\\Fonts\\msyh.ttc",  # Windows上的微软雅黑
            "C:\\Windows\\Fonts\\simsun.ttc",  # Windows上的宋体
            "C:\\Windows\\Fonts\\simhei.ttf"   # Windows上的黑体
        ]
        for font_path in font_paths:
            try:
                if os.path.exists(font_path):
                    chinese_font = fm.FontProperties(fname=font_path)
                    break
            except:
                continue
    
    if chinese_font is None:
        # 如果没有找到以上字体，尝试使用系统默认的一些字体
        for font_name in ["SimHei", "Microsoft YaHei", "SimSun", "STSong", "STFangsong", "AR PL UMing CN"]:
            try:
                chinese_font = fm.FontProperties(family=font_name)
                break
            except:
                continue
    
    # 创建饼图
    plt.figure(figsize=(10, 6))
    
    # 节点状态分布
    labels = ['已执行', '定性分析', '执行错误', '未知状态']
    sizes = [
        status_counts['executed'],
        status_counts['qualitative'],
        status_counts['error'],
        status_counts['unknown']
    ]
    colors = ['#4CAF50', '#2196F3', '#F44336', '#9E9E9E']
    
    plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90, 
            textprops={'fontproperties': chinese_font} if chinese_font else {})
    plt.axis('equal')
    
    title = f'{company_name} - {regulation_id} 合规图执行状态分析'
    plt.title(title, fontproperties=chinese_font if chinese_font else None)
    
    # 添加违规节点统计
    annotation_text = f"违规节点: {violation_count} ({violation_count/total_nodes*100:.1f}%)"
    plt.annotate(
        annotation_text,
        xy=(0.5, 0.04),
        xycoords='figure fraction',
        ha='center',
        fontproperties=chinese_font if chinese_font else None
    )
    
    # 添加总节点数
    annotation_text = f"总节点数: {total_nodes}"
    plt.annotate(
        annotation_text,
        xy=(0.5, 0.01),
        xycoords='figure fraction',
        ha='center',
        fontproperties=chinese_font if chinese_font else None
    )
    
    # 添加日期到图片名称
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存图表
    save_dir = os.path.join(project_root, "results")
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, f"{company_name}_{regulation_id}_execution_stats_{timestamp}.png")
    plt.savefig(save_path)
    
    print(f"统计图表已保存至: {save_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="合规图执行流程测试")
    parser.add_argument("--save-chart", action="store_true", help="是否保存统计图表")
    args = parser.parse_args()

    # 测试参数
    regulations_to_test = {
        "regulation_04": "祎煜环保",  # 股份回购
        "regulation_08": "钧璋机械",  # 股份减持
        "regulation_10": "曦祺电力"   # 权益分派
    }
    
    for regulation_id, company_name in regulations_to_test.items():
        print(f"\n--- 开始测试 {regulation_id} for {company_name} ---")
        test_graph_execution(regulation_id, company_name, save_chart=args.save_chart)
        print(f"--- 测试完成 {regulation_id} for {company_name} ---\n")
    
    print("所有测试已完成。") 