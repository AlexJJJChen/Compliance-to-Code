#!/usr/bin/env python3
"""
处理现有结果文件脚本

该脚本用于处理现有的结果文件，为它们添加基于关系的后处理结果。
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# 核心模块导入
from backend.database.compliance_unit_db import ComplianceUnitDB
from backend.compliance_engine.relation_processor import RelationProcessor

# 创建日志记录器
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger("process_existing_results")


def find_result_files(results_dir: str) -> List[str]:
    """
    查找所有结果文件
    
    参数:
        results_dir: 结果目录路径
        
    返回:
        结果文件路径列表
    """
    result_files = []
    for root, _, files in os.walk(results_dir):
        for file in files:
            if file == "result.json":
                result_files.append(os.path.join(root, file))
    
    return result_files


def process_result_file(file_path: str, db: ComplianceUnitDB, processor: RelationProcessor, graph_path: Optional[str] = None) -> bool:
    """
    处理单个结果文件
    
    参数:
        file_path: 结果文件路径
        db: 合规单元数据库实例
        processor: 关系后处理器实例
        graph_path: 可选的合规图路径，用于测试
        
    返回:
        处理是否成功
    """
    try:
        logger.info(f"处理结果文件: {file_path}")
        
        # 读取结果文件
        with open(file_path, 'r', encoding='utf-8') as f:
            result_data = json.load(f)
        
        # 获取法规ID
        regulation_id = result_data.get("metadata", {}).get("request_params", {}).get("regulation_id")
        if not regulation_id:
            logger.warning(f"未找到法规ID: {file_path}")
            return False
        
        # 加载合规图
        if not graph_path:
            graph_path = os.path.join(project_root, "data", "graphs", f"{regulation_id}.json")
        
        if not os.path.exists(graph_path):
            logger.error(f"合规图文件不存在: {graph_path}")
            return False
        
        graph = db.load_graph_from_json(graph_path)
        
        # 处理结果
        processed_results = processor.process_results(graph, result_data.get("results", {}))
        
        # 创建新的结果文件路径
        dir_path = os.path.dirname(file_path)
        new_file_path = os.path.join(dir_path, "processed_result.json")
        
        # 构建新的响应数据
        new_response_data = {
            "metadata": result_data.get("metadata", {}),
            "results": processed_results,
            "graph": result_data.get("graph", {})
        }
        
        # 保存新的结果文件
        with open(new_file_path, 'w', encoding='utf-8') as f:
            json.dump(new_response_data, f, ensure_ascii=False, indent=4)
        
        logger.info(f"处理完成，保存到: {new_file_path}")
        return True
        
    except Exception as e:
        logger.error(f"处理结果文件时出错: {e}")
        return False


def run_test():
    """运行测试"""
    logger.info("运行测试")
    
    # 测试文件路径
    test_result_path = os.path.join(project_root, "tests", "sample_result.json")
    test_graph_path = os.path.join(project_root, "tests", "sample_graph.json")
    
    # 检查测试文件是否存在
    if not os.path.exists(test_result_path) or not os.path.exists(test_graph_path):
        logger.error("测试文件不存在")
        return False
    
    # 创建测试目录
    test_output_dir = os.path.join(project_root, "tests", "output")
    os.makedirs(test_output_dir, exist_ok=True)
    
    # 复制测试结果文件到测试目录
    test_output_path = os.path.join(test_output_dir, "result.json")
    with open(test_result_path, 'r', encoding='utf-8') as f_in:
        with open(test_output_path, 'w', encoding='utf-8') as f_out:
            f_out.write(f_in.read())
    
    # 处理测试文件
    db = ComplianceUnitDB()
    processor = RelationProcessor(use_mock=True)  # 使用模拟关系处理器
    success = process_result_file(test_output_path, db, processor, test_graph_path)
    
    if success:
        logger.info("测试成功")
        # 读取处理后的结果文件
        processed_path = os.path.join(test_output_dir, "processed_result.json")
        with open(processed_path, 'r', encoding='utf-8') as f:
            processed_data = json.load(f)
        
        # 打印处理结果
        regulation_id = next(iter(processed_data.get("results", {}).get("regulations", {})), None)
        if regulation_id:
            final_status = processed_data["results"]["regulations"][regulation_id].get("final_compliance_status", {})
            logger.info(f"最终合规状态: {final_status.get('summary', '未知')}")
            logger.info(f"违规单元: {final_status.get('violation_units', [])}")
            logger.info(f"被排除单元: {final_status.get('excluded_units', [])}")
            logger.info(f"被强制包含单元: {final_status.get('forced_units', [])}")
    else:
        logger.error("测试失败")
    
    return success


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="处理现有的结果文件，为它们添加基于关系的后处理结果")
    parser.add_argument("--results-dir", default=os.path.join(project_root, "results"),
                        help="结果目录路径")
    parser.add_argument("--file", help="单个结果文件路径")
    parser.add_argument("--test", action="store_true", help="运行测试")
    args = parser.parse_args()
    
    if args.test:
        success = run_test()
        sys.exit(0 if success else 1)
    
    db = ComplianceUnitDB()
    processor = RelationProcessor()
    
    if args.file:
        # 处理单个文件
        if os.path.exists(args.file):
            success = process_result_file(args.file, db, processor)
            sys.exit(0 if success else 1)
        else:
            logger.error(f"结果文件不存在: {args.file}")
            sys.exit(1)
    else:
        # 处理所有文件
        result_files = find_result_files(args.results_dir)
        logger.info(f"找到 {len(result_files)} 个结果文件")
        
        success_count = 0
        for file_path in result_files:
            if process_result_file(file_path, db, processor):
                success_count += 1
        
        logger.info(f"处理完成，成功: {success_count}/{len(result_files)}")
        sys.exit(0 if success_count == len(result_files) else 1)


if __name__ == "__main__":
    main() 