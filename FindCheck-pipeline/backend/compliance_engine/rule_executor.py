#!/usr/bin/env python3
"""
规则执行器模块

用于执行合规单元中的规则代码，并处理不同法规特定的数据格式。
"""

import os
import sys
import importlib
import inspect
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Union
import logging
from .sandbox_executor import SandboxExecutor
import textwrap
import re

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

logger = logging.getLogger(__name__)

# 用于从代码中提取函数名的正则表达式
# 匹配 'def function_name(df):' 或 'def function_name(data):'
FUNC_NAME_REGEX = re.compile(r"def\s+([a-zA-Z0-9_]+)\s*\((?:df|data)\s*:\s*pd\.DataFrame\s*\)\s*->\s*pd\.DataFrame:")
# 备用正则，以防类型提示不存在
FUNC_NAME_REGEX_SIMPLE = re.compile(r"def\s+([a-zA-Z0-9_]+)\s*\((?:df|data)\):")

class RuleExecutor:
    """
    规则执行器
    
    负责在沙箱环境中执行从合规单元提取的Python代码。
    """
    def __init__(self, execution_timeout: int = 10):
        """
        初始化规则执行器
        
        参数:
            execution_timeout: 沙箱执行的超时时间（秒）
        """
        self.sandbox = SandboxExecutor(execution_timeout=execution_timeout)

    def execute_rule(self, unit_id: str, code: str, company_data: pd.DataFrame, regulation_id: str) -> Dict[str, Any]:
        """
        在沙箱环境中安全地执行单个合规单元的规则代码。
        
        该方法现在会从提供的代码中解析函数名，直接执行，并在之后进行安全检查。
        """
        if not code:
            return {"status": "skipped", "result": None, "error": "代码为空"}

        logger.info(f"开始执行单元 {unit_id} 的规则...")

        try:
            # 1. 从代码中解析函数名
            match = FUNC_NAME_REGEX.search(code) or FUNC_NAME_REGEX_SIMPLE.search(code)
            if not match:
                error_message = f"在单元 {unit_id} 的代码中未找到格式为 'def function_name(df):' 的函数定义。"
                logger.error(error_message)
                return {"status": "error", "result": None, "error": error_message}
            func_name = match.group(1)
            logger.info(f"从单元 {unit_id} 的代码中解析到函数名: {func_name}")

            # 2. 数据预处理
            # 移除旧的数据处理器逻辑
            # processor = self.data_processors.get(regulation_id)
            # if processor:
            #     processed_data = processor(company_data)
            #     logger.info(f"使用 {regulation_id} 的处理器对数据进行了预处理。")
            # else:
            #     processed_data = company_data
            #     logger.warning(f"未找到法规 {regulation_id} 的数据处理器，将使用原始数据。")
            processed_data = company_data # 直接使用原始数据，不再进行预处理
            logger.info(f"单元 {unit_id}: 预处理后准备执行的数据，形状: {processed_data.shape}")

            # 3. 在沙箱中直接执行用户代码
            logger.info(f"在沙箱中执行函数 {func_name}...")
            result_df = self.sandbox.execute_code(
                user_code_str=code,  # 直接传入原始代码
                func_name=func_name, # 传入解析出的函数名
                company_data=processed_data,
                unit_id=unit_id
            )

            # 4. 处理执行结果
            if result_df is None:
                logger.warning(f"单元 {unit_id} 执行成功，但返回了 None。")
                return {"status": "success", "result": None, "error": None}
            
            if not isinstance(result_df, pd.DataFrame):
                 logger.warning(f"单元 {unit_id} 的执行结果不是一个DataFrame，类型为: {type(result_df)}")
                 return {"status": "error", "result": None, "error": f"执行结果不是一个DataFrame，而是 {type(result_df)}"}

            # 5. 安全包装：实现更灵活的列查找和错误填充
            for col_type in ['subject', 'condition', 'constraint']:
                # 优先查找cu_id风格的列名，然后是meu_id风格的列名
                cu_style_col = f"{unit_id}_{col_type}"
                meu_style_col = f"meu_{unit_id[3:]}_{col_type}" if unit_id.startswith("cu_") else None
                
                # 标准化后的内部列名
                standard_col = f"_{col_type}_passed" # 例如：_subject_passed

                found_col = None
                if cu_style_col in result_df.columns:
                    found_col = cu_style_col
                elif meu_style_col and meu_style_col in result_df.columns:
                    found_col = meu_style_col
                
                if found_col:
                    logger.debug(f"在单元 {unit_id} 的输出中找到列 '{found_col}'，将用作 '{standard_col}'。")
                    # 确保列是布尔类型
                    result_df[standard_col] = result_df[found_col].astype(bool)
                    # 可以选择删除原始列以保持整洁
                    if found_col != standard_col:
                        result_df.drop(columns=[found_col], inplace=True)
                else:
                    logger.warning(f"在单元 {unit_id} 的代码输出中未找到 '{cu_style_col}' 或 '{meu_style_col}'。将填充为 'error'。")
                    result_df[standard_col] = 'error'

            logger.info(f"单元 {unit_id} 执行成功，返回 {len(result_df)} 条记录。")
            logger.debug(f"单元 {unit_id}: 执行后返回的数据，形状: {result_df.shape}, 列: {result_df.columns.tolist()}")
            
            # 将DataFrame转换为JSON以便序列化
            result_json = result_df.to_dict(orient='records')

            return {"status": "success", "result": result_json, "error": None}

        except TimeoutError:
            error_message = f"执行超时 ({self.sandbox.execution_timeout} 秒)"
            logger.error(f"单元 {unit_id} 执行失败: {error_message}")
            return {"status": "error", "result": None, "error": error_message}
        except Exception as e:
            error_message = f"执行时发生未知错误: {str(e)}"
            logger.exception(f"执行单元 {unit_id} 的代码时发生异常") # 使用 logger.exception 记录堆栈信息
            return {"status": "error", "result": None, "error": error_message}


if __name__ == "__main__":
    # 测试规则执行器
    executor = RuleExecutor()
    
    # 注册处理器
    # executor.register_data_processor("regulation_04", regulation_04_processor)
    
    # 创建测试数据
    test_data = pd.DataFrame({
        '公司简称': ['测试公司'] * 3,
        '日期': ['2022-01-01', '2022-01-02', '2022-01-03'],
        '收盘价': [10.0, 11.0, 9.0],
        '每股净资产': [12.0, 12.0, 12.0],
        '存在回购方案': [True, True, True],
        '回购方式': ['竞价回购', '竞价回购', '竞价回购'],
        '回购用途': ['维护公司价值及股东权益所必需', '维护公司价值及股东权益所必需', '维护公司价值及股东权益所必需']
    })
    
    # 测试代码
    test_code = """
# 检查是否存在回购方案
has_plan = data['存在回购方案'].any()

# 检查回购价格是否低于每股净资产
price_check = (data['收盘价'] < data['每股净资产']).all()

# 检查回购方式是否为竞价回购
method_check = (data['回购方式'] == '竞价回购').all()

# 检查回购用途是否合规
purpose_check = (data['回购用途'] == '维护公司价值及股东权益所必需').all()

# 综合判断
if has_plan and price_check and method_check and purpose_check:
    result['is_violation'] = False
    result['message'] = "回购方案符合规定"
else:
    result['is_violation'] = True
    result['message'] = "回购方案不符合规定"
    
# 添加详细信息
result['details'] = {
    'has_plan': has_plan,
    'price_check': price_check,
    'method_check': method_check,
    'purpose_check': purpose_check
}
"""
    
    # 执行代码
    result = executor.execute_rule(
        unit_id="CU_04_001",
        code=test_code, 
        company_data=test_data,
        regulation_id="regulation_04"
    )
    
    # 输出结果
    print(f"执行结果: {'成功' if result['status'] == 'success' else '失败'}")
    if result['status'] == 'success':
        print(f"是否违规: {'是' if result['result']['is_violation'] else '否'}")
        print(f"消息: {result['result']['message']}")
        print(f"详细信息: {result['result'].get('details', {})}")
    else:
        print(f"错误: {result['error']}") 