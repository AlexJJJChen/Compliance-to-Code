#!/usr/bin/env python3
"""
执行引擎模块

负责执行合规单元代码并收集结果。
"""

import os
import sys
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Set, Tuple

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# 核心模块导入
from backend.database.compliance_unit_db import ComplianceUnitDB
from backend.compliance_engine.compliance_graph import ComplianceGraph
from backend.compliance_engine.compliance_unit import ComplianceUnit
from backend.compliance_engine.rule_executor import RuleExecutor
from backend.compliance_engine.evaluator import Evaluator
from backend.compliance_engine.data_preprocessor import get_preprocessor
from backend.compliance_engine.relation_processor import RelationProcessor  # 导入关系后处理器
from tools.data_fetcher import DataFetcher # 引擎现在需要自己获取数据

# 创建执行引擎的日志记录器
logger = logging.getLogger("execution_engine")


class ExecutionEngine:
    """
    执行引擎类
    
    负责执行合规单元代码并收集结果。
    """
    
    def __init__(self, log_dir: str = "logs", log_level: int = logging.INFO):
        """
        初始化执行引擎
        """
        self.log_dir = os.path.join(project_root, log_dir)
        self.log_level = log_level
        self._setup_logging()
        
        self.db = ComplianceUnitDB()
        self.data_fetcher = DataFetcher()
        self.rule_executor = RuleExecutor()
        self.evaluator = Evaluator(self.rule_executor)
        self.relation_processor = RelationProcessor()  # 添加关系后处理器实例
        
        logger.info("执行引擎初始化完成")
    
    def _setup_logging(self) -> None:
        """配置日志记录器"""
        # 确保日志目录存在
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 获取根日志记录器并设置级别，以便从所有模块捕获日志
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level) # 设置最低捕获级别
        
        # 防止重复添加处理器
        if not root_logger.handlers:
            # 文件处理器
            log_file = os.path.join(self.log_dir, f"execution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(self.log_level)
            
            # 控制台处理器
            console_handler = logging.StreamHandler(sys.stdout) # 明确输出到 stdout
            console_handler.setLevel(self.log_level)
            
            # 设置格式 - 添加进程ID
            formatter = logging.Formatter('%(asctime)s - %(process)d - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            # 添加处理器到根记录器
            root_logger.addHandler(file_handler)
            root_logger.addHandler(console_handler)
            
            logger.info(f"日志系统已配置。日志级别: {logging.getLevelName(self.log_level)}，日志文件: {log_file}")
    
    def load_graph(self, regulation_id: str) -> Optional[ComplianceGraph]:
        """
        加载指定法规的合规图
        """
        try:
            # 构建图JSON路径
            graph_path = os.path.join(project_root, "data", "graphs", f"{regulation_id}.json")
            
            logger.info(f"正在加载 {regulation_id} 的合规图")
            
            if not os.path.exists(graph_path):
                logger.error(f"合规图文件不存在: {graph_path}")
                return None
            
            # 加载图
            graph = self.db.load_graph_from_json(graph_path)
            logger.info(f"成功加载合规图: {regulation_id} ({graph.regulation_name})")
            logger.info(f"图包含 {len(graph.units)} 个单元，其中 {sum(1 for unit in graph.units.values() if unit.code is not None)} 个有代码")
            
            return graph
            
        except Exception as e:
            logger.error(f"加载合规图时出错: {e}")
            return None

    def _internal_run(self, 
            company_name: str,
            company_data: pd.DataFrame,
            regulation_id: str) -> Tuple[Dict[str, Any], Optional[ComplianceGraph]]:
        """
        内部运行接口，仅负责加载图和执行。
        """
        logger.info(f"接收到对 {company_name} 关于 {regulation_id} 的检查请求")
        
        graph = self.load_graph(regulation_id)
        if not graph:
            return {"error": f"无法加载法规图: {regulation_id}"}, None
        
        results = self.execute_graph(graph, company_data, company_name)
        return results, graph

    def run_and_save(self, 
                     company_name: str, 
                     regulation_id: str,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None,
                     shareholder: Optional[str] = None) -> Dict[str, Any]:
        """
        完整的、统一的运行入口。
        负责获取数据、执行、构建响应、保存文件，并返回最终结果。
        
        参数:
            company_name: 公司名称
            regulation_id: 法规ID
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            shareholder: 股东名称（仅用于regulation_08，可选）
        """
        # 1. 获取数据
        company_data, actual_date_range = self.data_fetcher.get_company_data(
            regulation_id=regulation_id,
            company_name=company_name,
            start_date=start_date,
            end_date=end_date,
        )

        if company_data is None or company_data.empty:
            error_msg = f"未找到公司 '{company_name}' 在法规 '{regulation_id}' 下的数据。"
            logger.error(error_msg)
            return {"error": error_msg}
        
        # 如果是regulation_08且提供了股东参数，则过滤股东数据
        if regulation_id == "regulation_08" and shareholder:
            if "股东" in company_data.columns:
                original_len = len(company_data)
                company_data = company_data[company_data["股东"] == shareholder]
                filtered_len = len(company_data)
                
                if filtered_len == 0:
                    error_msg = f"未找到公司 '{company_name}' 中股东 '{shareholder}' 的数据。"
                    logger.error(error_msg)
                    return {"error": error_msg}
                
                logger.info(f"已过滤股东 '{shareholder}' 的数据，从 {original_len} 条记录中筛选出 {filtered_len} 条记录")
            else:
                logger.warning(f"公司 '{company_name}' 的数据中不包含'股东'列，无法过滤股东 '{shareholder}' 的数据")
        
        # 2. 运行核心引擎
        engine_output, compliance_graph = self._internal_run(
            company_name=company_name,
            company_data=company_data,
            regulation_id=regulation_id,
        )

        if not compliance_graph:
            error_msg = "执行引擎未能加载合规图。"
            logger.error(error_msg)
            return {"error": error_msg}
            
        # 2.1 进行关系后处理
        logger.info("开始进行关系后处理")
        processed_results = self.relation_processor.process_results(
            graph=compliance_graph,
            results=engine_output
        )
        
        # 添加股东信息到结果中（如果有）
        if regulation_id == "regulation_08" and shareholder:
            if "regulations" in processed_results and regulation_id in processed_results["regulations"]:
                processed_results["regulations"][regulation_id]["shareholder"] = shareholder

        # 3. 构建响应数据
        echarts_graph_data = self._build_hierarchical_echarts_graph(
            graph=compliance_graph,
            eval_results=processed_results,
            regulation_name=compliance_graph.regulation_name
        )
        
        response_data = {
            "metadata": {
                "company_name": company_name,
                "regulation_name": compliance_graph.regulation_name,
                "date_range": actual_date_range,
                "request_params": {
                    "regulation_id": regulation_id,
                    "company_name": company_name,
                    "start_date": start_date,
                    "end_date": end_date
                }
            },
            "results": processed_results,
            "graph": echarts_graph_data,
            "final_compliance_status": processed_results.get("regulations", {}).get(regulation_id, {}).get("final_compliance_status", {})
        }
        
        # 添加股东信息到请求参数中（如果有）
        if regulation_id == "regulation_08" and shareholder:
            response_data["metadata"]["request_params"]["shareholder"] = shareholder
        
        # 4. 在返回和保存之前，对整个响应数据进行一次性净化
        sanitized_response_data = self._sanitize_for_json(response_data)
        
        try:
            # 5. 保存文件 (使用净化后的数据)
            result_folder_name = self._save_run_output(sanitized_response_data)
            
            if result_folder_name:
                sanitized_response_data["result_path"] = result_folder_name
                logger.info(f"检查完成 - 结果已保存 到 {os.path.join(project_root, 'results', result_folder_name)}")
            else:
                logger.warning("检查完成 - 但结果保存失败")
        except Exception as e:
            logger.error(f"保存结果时出错: {e}")
            # 即使保存失败，也返回处理结果
        
        # 6. 返回数据 (使用净化后的数据)
        return sanitized_response_data

    def _save_run_output(self, response_data: Dict[str, Any]):
        """
        将单次检查的结果保存到带时间戳的文件夹中。
        传入的数据应已经是JSON兼容的。
        """
        try:
            # 使用响应数据中的元数据创建文件夹名称
            metadata = response_data.get('metadata', {}).get('request_params', {})
            run_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            company_name_safe = "".join(x for x in metadata.get('company_name', 'unknown') if x.isalnum())
            
            # 准备文件夹名称，如果是regulation_08且有股东参数，则包含股东信息
            shareholder_info = ""
            if metadata.get('regulation_id') == "regulation_08" and 'shareholder' in metadata:
                shareholder_safe = "".join(x for x in metadata['shareholder'] if x.isalnum())
                shareholder_info = f"_{shareholder_safe}"
                
            output_folder_name = f"{run_timestamp}_{company_name_safe}{shareholder_info}_{metadata.get('regulation_id', 'unknown')}"
            
            output_dir = os.path.join(project_root, "results", output_folder_name)
            os.makedirs(output_dir, exist_ok=True)

            # 保存请求元数据
            metadata_path = os.path.join(output_dir, "request_metadata.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=4)

            # 保存完整结果
            result_path = os.path.join(output_dir, "result.json")
            with open(result_path, 'w', encoding='utf-8') as f:
                json.dump(response_data, f, ensure_ascii=False, indent=4)
            
            # 同时保存一个processed_result.json
            processed_result_path = os.path.join(output_dir, "processed_result.json")
            with open(processed_result_path, 'w', encoding='utf-8') as f:
                json.dump(response_data, f, ensure_ascii=False, indent=4)
            
            # 尝试异步生成合规报告
            try:
                # 这里使用一个简单的线程来实现异步生成报告，避免阻塞主流程
                import threading
                from tools.compliance_report import generate_compliance_report
                
                def generate_report_async():
                    try:
                        generate_compliance_report(output_dir)
                    except Exception as e:
                        logger.error(f"异步生成合规报告时出错: {e}")
                
                # 启动异步生成报告的线程
                report_thread = threading.Thread(target=generate_report_async)
                report_thread.daemon = True  # 设置为守护线程，不阻止程序退出
                report_thread.start()
                
            except Exception as e:
                logger.warning(f"启动异步报告生成时出错: {e}")
                
            logger.info(f"检查结果已成功保存到: {output_dir}")
            return output_folder_name  # 返回文件夹名称

        except Exception as e:
            logger.error(f"错误: 未能保存检查结果文件: {e}")
            return None

    def _sanitize_for_json(self, data: Any) -> Any:
        # ... (这里是 sanitize_for_json 的完整实现) ...
        if isinstance(data, dict):
            # 特别处理 'results' 键，避免重复净化
            if 'results' in data and isinstance(data['results'], dict):
                 # 创建一个新的字典，避免在迭代时修改
                new_data = {}
                for k, v in data.items():
                    if k == 'results':
                        # 对于 results 字段，我们假设它已经是部分净化过的，或者将由下一个逻辑处理
                        # 为了避免无限递归或双重处理，这里可以直接赋值
                        new_data[k] = self._sanitize_for_json(v)
                    else:
                        new_data[k] = self._sanitize_for_json(v)
                return new_data
            return {k: self._sanitize_for_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_for_json(i) for i in data]
        elif isinstance(data, (datetime, date, pd.Timestamp)):
            return data.isoformat()
        elif isinstance(data, float):
            if np.isinf(data) or np.isnan(data):
                return None
            return data
        elif isinstance(data, np.bool_):
            return bool(data)
        elif isinstance(data, np.integer):
            return int(data)
        elif isinstance(data, np.floating):
            if np.isinf(data) or np.isnan(data):
                return None
            return float(data)
        else:
            return data

    def _build_hierarchical_echarts_graph(self, 
                                          graph: ComplianceGraph, 
                                          eval_results: Dict[str, Any],
                                          regulation_name: str) -> Dict[str, Any]:
        nodes, links, law_nodes = [], [], {}
        categories = [
            {"name": "合规", "itemStyle": {"color": "#67C23A"}},
            {"name": "违规", "itemStyle": {"color": "#F56C6C"}},
            {"name": "未执行", "itemStyle": {"color": "#A0CFFF"}},
            {"name": "执行错误", "itemStyle": {"color": "#E6A23C"}},
            {"name": "法条", "itemStyle": {"color": "#409EFF"}},
            {"name": "法规根节点", "itemStyle": {"color": "#6D8A7E"}},
            {"name": "被排除", "itemStyle": {"color": "#909399"}},
            {"name": "被强制包含", "itemStyle": {"color": "#E6A23C"}}
        ]
        relation_styles = {
            'refer_to': {'color': '#5B8DB6', 'type': 'dashed'},
            'exclude': {'color': '#B1443C', 'type': 'dashed'},
            'only_include': {'color': '#5F8EA9', 'type': 'solid'},
            'should_include': {'color': '#7CA17D', 'type': 'solid'},
            'default': {'color': '#9E9E9E', 'type': 'dotted'}
        }
        root_id = graph.regulation_id
        nodes.append({"id": root_id, "name": "Root", "symbolSize": 35, "category": 5})

        # 获取法规ID
        regulation_id = next(iter(eval_results.get("regulations", {})), None)
        if not regulation_id:
            logger.warning("未找到有效的法规ID，图表可能不完整")
            return {"nodes": nodes, "links": links, "categories": categories}
            
        # 获取单元结果
        unit_results = eval_results.get("regulations", {}).get(regulation_id, {}).get("node_results", {})
        
        # 如果node_results为空，尝试使用unit_results
        if not unit_results:
            unit_results = eval_results.get("regulations", {}).get(regulation_id, {}).get("unit_results", {})
            
        # 获取最终合规状态
        final_status = eval_results.get("regulations", {}).get(regulation_id, {}).get("final_compliance_status", {})
        excluded_units = {unit["cu_id"]: unit["excluded_by"] for unit in final_status.get("excluded_units", [])}
        forced_units = {unit["cu_id"]: unit["forced_by"] for unit in final_status.get("forced_units", [])}
        violation_units = set(final_status.get("violation_units", []))

        for cu_id, unit in graph.units.items():
            try:
                law_id = f"law_{unit.cu_id.split('_')[1]}"
                if law_id not in law_nodes:
                    law_nodes[law_id] = unit.source
                    nodes.append({"id": law_id, "name": f"法条 {unit.cu_id.split('_')[1]}", "symbolSize": 30, "category": 4})
                    links.append({"source": law_id, "target": root_id, "lineStyle": {"width": 1.5}})
            except IndexError:
                law_id = root_id
            
            # 获取单元状态信息
            unit_info = unit_results.get(cu_id, {})
            exec_result = unit_info.get("execution_result", {})
            relations = unit_info.get("relations", {})
            
            # 确定节点状态和类别
            status = "Unknown"
            category = 2  # 默认为"未执行"
            
            # 检查是否被排除
            if cu_id in excluded_units:
                status = f"被排除 (由 {excluded_units[cu_id]} 排除)"
                category = 6  # "被排除"类别
            # 检查是否被强制包含
            elif cu_id in forced_units:
                status = f"被强制包含 (由 {forced_units[cu_id]} 强制)"
                category = 7  # "被强制包含"类别
            # 检查是否有执行结果
            elif "status" in exec_result:
                exec_status = exec_result.get("status")
                if exec_status == "executed":
                    # 检查是否有违规
                    has_violation = exec_result.get("output_analysis", {}).get("has_violation", False)
                    if has_violation or cu_id in violation_units:
                        status = "Violation"
                        category = 1  # "违规"类别
                    else:
                        status = "Success"
                        category = 0  # "合规"类别
                elif exec_status == "error":
                    status = "Error"
                    category = 3  # "执行错误"类别
                else:
                    status = "Skipped"
                    category = 2  # "未执行"类别
            
            # 准备节点详情
            # 从执行结果中获取详细的违规信息列表
            violations_list = exec_result.get("output_analysis", {}).get("violations", [])
            evaluation_details = violations_list
            # 如果列表为空，但标记为违规，则提供一个通用消息
            if not violations_list and (exec_result.get("output_analysis", {}).get("has_violation") or cu_id in violation_units):
                violation_count = exec_result.get("output_analysis", {}).get("violation_count", '未知数量')
                evaluation_details = f"发现 {violation_count} 项违规 (无详细记录)"

            node_details = {
                "subject": unit.subject, 
                "condition": unit.condition, 
                "constraint": unit.constraint, 
                "contextual_info": unit.contextual_info, 
                "status": status,
                # 确保 evaluation_details 包含正确的违规详情列表
                "evaluation_details": evaluation_details
            }
            
            nodes.append({
                "id": cu_id, 
                "name": cu_id, 
                "value": node_details, 
                "symbolSize": 18, 
                "category": category
            })
            
            links.append({"source": cu_id, "target": law_id, "lineStyle": {"width": 1}})

        # 添加关系边
        for source, target, data in graph.graph.edges(data=True):
            relation = data.get('relation')
            if relation:
                style = relation_styles.get(relation, relation_styles['default'])
                links.append({
                    "source": source, 
                    "target": target, 
                    "value": relation, 
                    "lineStyle": {
                        "color": style['color'], 
                        "type": style['type'], 
                        "width": 1.5
                    }, 
                    "label": {
                        "show": True, 
                        "formatter": relation, 
                        "fontSize": 12
                    }
                })
        
        return {"nodes": nodes, "links": links, "categories": categories}


    def execute_graph(self, 
                     graph: ComplianceGraph, 
                     company_data: pd.DataFrame,
                     company_name: str) -> Dict[str, Any]:
        """
        执行合规图中的所有单元
        """
        logger.info(f"开始执行 {company_name} 的合规检查 ({graph.regulation_name})")
        start_time = datetime.now()
        
        preprocessor = get_preprocessor(graph.regulation_id)
        processed_data = preprocessor.preprocess(company_data) if preprocessor else company_data

        try:
            result = self.evaluator.evaluate_company(company_name, processed_data, [graph.regulation_id])
            result['execution_time'] = (datetime.now() - start_time).total_seconds()
            logger.info(f"合规检查完成，耗时 {result['execution_time']:.2f} 秒")
            return result
        except Exception as e:
            logger.error(f"执行合规检查时出错: {e}")
            return {"company_name": company_name, "error": str(e), "summary": {}}


if __name__ == "__main__":
    # 测试代码保持不变，但调用方式会更新
    logging.basicConfig(level=logging.INFO)
    engine = ExecutionEngine()
    engine.run_and_save(
        company_name="祎煜环保",
        regulation_id="regulation_04",
        start_date="2023-01-01",
        end_date="2023-12-31"
    ) 