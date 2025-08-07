import re
import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Any
import bisect
from bisect import bisect_left, bisect_right
import io
import os
import sys
import subprocess
import tempfile
import pickle
import base64
import traceback
import tokenize # 用于Python代码分词
import logging


# 配置基础日志记录器
if not logging.getLogger().hasHandlers():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(process)d - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
logger = logging.getLogger(__name__)


class CodeExtractionUtils:
    @staticmethod
    def extract_from_markdown(text: str, language: str = "python") -> str:
        # 从Markdown代码块中提取代码
        pattern = re.compile(rf'```{language}\n(.*?)\n```', re.DOTALL)
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
        if language == "python": # 如果是Python，尝试匹配没有指定语言的块
            pattern_generic = re.compile(r'```\n(.*?)\n```', re.DOTALL)
            match_generic = pattern_generic.search(text)
            if match_generic:
                logger.debug("已从通用Markdown块中提取代码（未指定语言）。")
                return match_generic.group(1).strip()
        logger.debug(f"无法从文本中提取语言为 {language} 的Markdown代码：{text[:100]}...")
        return ""

    @staticmethod
    def extract_from_custom_tag(text: str, tag: str = "CODE") -> str: # 尽管此请求不直接用，但保留其工具性
        # 从自定义XML风格标签中提取代码
        pattern = re.compile(rf'<{tag}>(.*?)</{tag}>', re.DOTALL)
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
        logger.debug(f"无法从文本中提取自定义标签 <{tag}> 的代码：{text[:100]}...")
        return ""


class SandboxExecutor:
    DEFAULT_EXECUTION_TIMEOUT = 60 # 默认执行超时时间（秒）
    TEMP_SCRIPT_DIR = "temp_scripts_evaluation" # 临时脚本目录名

    def __init__(self, execution_timeout: Optional[int] = None):
        self.execution_timeout = execution_timeout if execution_timeout is not None else self.DEFAULT_EXECUTION_TIMEOUT
        self.scripts_output_path = os.path.join(os.getcwd(), self.TEMP_SCRIPT_DIR)
        os.makedirs(self.scripts_output_path, exist_ok=True)
        logger.info(f"临时评估脚本将保存在：{self.scripts_output_path}")

    @staticmethod
    def _get_sandbox_script_template() -> str:
        # 获取沙盒执行脚本的模板字符串
        return """
import bisect
from bisect import bisect_left, bisect_right
import pandas as pd
import numpy as np
import traceback
import os
import pickle
import base64
import sys

def logger_print_fn_in_script(level, message):
    # 沙盒脚本内部使用的日志打印函数
    level_str = str(level)
    print(f"[子进程_{{level_str.upper()}}] {{message}}")

result_df_pickle_b64 = None
logger_print_fn_in_script("信息", "沙盒脚本执行开始。")

try:
    logger_print_fn_in_script("信息", f"子进程当前工作目录: {{os.getcwd()}}")
    logger_print_fn_in_script("信息", "--- 环境代码块执行开始 ---")
    env_code_globals = {{'pd': pd, 'np': np, 'os': os, 'logger_print_fn_in_script': logger_print_fn_in_script}}
    env_code_locals = {{}} # 环境代码在其自己的局部作用域中执行
    exec(\"\"\"{env_code_str}\"\"\", env_code_globals, env_code_locals)
    df = env_code_locals.get('df', None) # 从局部作用域获取df
    if df is None and 'df' in env_code_globals: # 如果环境代码修改了全局df，则回退
         df = env_code_globals['df']
    logger_print_fn_in_script("信息", "--- 环境代码块执行结束 ---")

    if 'df' not in locals() or df is None: # 明确检查df在环境代码执行后是否未定义或为None
        logger_print_fn_in_script("警告", f"环境代码执行后，初始DataFrame 'df' 为 None 或未定义。类型: {{type(df if 'df' in locals() else '未定义')}}")

    # 检查 df 状态，如果环境代码未能正确创建 df，则提供一个空的 DataFrame
    if 'df' not in locals() or not isinstance(df, pd.DataFrame):
        logger_print_fn_in_script("错误", f"环境代码执行后，未找到初始DataFrame 'df' 或类型不正确。类型为: {{type(df if 'df' in locals() else None)}}。将提供空的DataFrame。")
        initial_df_copy = pd.DataFrame()
    else:
        logger_print_fn_in_script("信息", f"初始DataFrame 'df' 已加载。形状: {{df.shape}}")
        initial_df_copy = df.copy()

    target_function_name = "{func_name}"
    logger_print_fn_in_script("信息", f"--- 用户代码函数 '{{target_function_name}}' 定义开始 ---")
    
    # 用户代码可用的全局变量
    user_code_exec_globals = {{
        'pd': pd,
        'np': np,
        'logger_print_fn_in_script': logger_print_fn_in_script,
        'os': os,
        'bisect_left': bisect_left,     # 直接访问 bisect_left
        'bisect_right': bisect_right,   # 直接访问 bisect_right
        'bisect': bisect                # 通过 bisect. 模块访问所有 bisect 功能
    }} 
    user_code_locals = {{}} # 用户代码在其自己的局部作用域中执行定义

    # user_code_str 应包含函数定义
    exec(\"\"\"{user_code_str}\"\"\", user_code_exec_globals, user_code_locals)
    user_function = user_code_locals.get(target_function_name) # 从用户代码的局部作用域获取函数

    if not user_function or not callable(user_function):
        logger_print_fn_in_script("错误", f"用户代码函数 '{{target_function_name}}' 在 user_code_str 中未定义或不可调用。")
        raise NameError(f"用户函数 '{{target_function_name}}' 定义失败。")

    logger_print_fn_in_script("信息", f"用户函数 '{{target_function_name}}' 已定义。准备使用 initial_df_copy (类型: {{type(initial_df_copy)}}) 执行。")
    processed_df = user_function(initial_df_copy) # 调用用户函数
    logger_print_fn_in_script("信息", f"--- 用户代码函数 '{{target_function_name}}' 执行结束 ---")

    if not isinstance(processed_df, pd.DataFrame):
        logger_print_fn_in_script("警告", f"用户函数 '{{target_function_name}}' 未返回DataFrame。返回类型: {{type(processed_df)}}。将视为空DataFrame处理。")
        processed_df = None

    if processed_df is not None:
        logger_print_fn_in_script("信息", f"用户函数 '{{target_function_name}}' 返回了DataFrame。形状: {{processed_df.shape}}")
        pickled_df = pickle.dumps(processed_df)
        result_df_pickle_b64 = base64.b64encode(pickled_df).decode('utf-8')
        logger_print_fn_in_script("信息", "DataFrame已成功序列化 (pickle + base64)。")
    else:
        logger_print_fn_in_script("信息", "处理后的DataFrame为None。发送 '空数据帧标记'。") # 注意：标记已更改
        result_df_pickle_b64 = "空数据帧标记"

except Exception as e_script:
    logger_print_fn_in_script("错误", f"沙盒脚本顶层错误: {{str(e_script)}} \\n----- 沙盒内部回溯开始 -----\\n{{traceback.format_exc()}}\\n----- 沙盒内部回溯结束 -----")
    result_df_pickle_b64 = "错误数据帧标记" # 注意：标记已更改

if result_df_pickle_b64 is not None:
    sys.stdout.write(result_df_pickle_b64 + '\\n')
    logger_print_fn_in_script("信息", f"沙盒脚本执行完毕。结果已写入标准输出。")
else: # 由于初始化，此情况不应发生
    sys.stdout.write("意外的空结果\\n") # 注意：标记已更改
    logger_print_fn_in_script("错误", "沙盒脚本已结束，但 result_df_pickle_b64 为 None。这表明模板中存在逻辑缺陷。")
"""

    def execute_code_in_sandbox(self, env_code_str: str, user_code_str: str, func_name: str, item_id_for_log: str, code_type_for_log: str) -> Optional[pd.DataFrame]:
        script_content = self._get_sandbox_script_template().format(
            env_code_str=env_code_str,
            user_code_str=user_code_str,
            func_name=func_name
        )
        safe_item_id = "".join(c if c.isalnum() else "_" for c in item_id_for_log)
        safe_code_type = "".join(c if c.isalnum() else "_" for c in code_type_for_log)
        script_file_name = f"{safe_item_id}_{safe_code_type}_{os.getpid()}.py"
        script_save_path = os.path.join(self.scripts_output_path, script_file_name)

        processed_df: Optional[pd.DataFrame] = None
        subprocess_execution_failed = False
        script_internal_error_marker = False
        deserialization_error_occurred = False # 重命名以更精确
        result_is_not_dataframe = False # 新增：标记结果是否不是预期的DataFrame
        full_stdout_logged = False
        
        # MODIFICATION: Initialize should_delete_script to False
        should_delete_script = False

        try:
            with open(script_save_path, 'w', encoding='utf-8') as tmp_script_file:
                tmp_script_file.write(script_content)

            logger.debug(f"项目 {item_id_for_log} ({code_type_for_log}): 正在执行临时脚本：{script_save_path}")
            process_cwd = os.getcwd()

            process = subprocess.run(
                [sys.executable, script_save_path],
                capture_output=True,
                text=True,
                timeout=self.execution_timeout,
                cwd=process_cwd
            )
            logger.debug(f"项目 {item_id_for_log} ({code_type_for_log}): 脚本执行完毕。返回码: {process.returncode}")

            if process.returncode != 0:
                subprocess_execution_failed = True

            df_pickle_b64_from_script = ""
            subprocess_stdout_log_lines = []
            if process.stdout:
                all_stdout_lines = process.stdout.strip().splitlines()
                found_data_line = False
                for i in range(len(all_stdout_lines) - 1, -1, -1):
                    line = all_stdout_lines[i]
                    if not line.startswith("[子进程_"):
                        df_pickle_b64_from_script = line
                        subprocess_stdout_log_lines = all_stdout_lines[:i] + all_stdout_lines[i+1:]
                        found_data_line = True
                        break
                if not found_data_line:
                    subprocess_stdout_log_lines = all_stdout_lines
            
            # 检查脚本内部的错误标记
            if df_pickle_b64_from_script == "错误数据帧标记":
                script_internal_error_marker = True
                logger.error(f"项目 {item_id_for_log} ({code_type_for_log}): 脚本返回 '错误数据帧标记'。")
            # 检查是否是用户函数返回了非DataFrame类型
            elif df_pickle_b64_from_script == "空数据帧标记_非DataFrame":
                result_is_not_dataframe = True # 标记结果不是DataFrame
                logger.warning(f"项目 {item_id_for_log} ({code_type_for_log}): 脚本返回 '空数据帧标记_非DataFrame'，表示用户函数未返回DataFrame。结果是 None DataFrame。")
            # 检查是否是用户函数明确返回了None
            elif df_pickle_b64_from_script == "空数据帧标记":
                logger.info(f"项目 {item_id_for_log} ({code_type_for_log}): 脚本返回 '空数据帧标记'。结果是 None DataFrame。")
            # 其他情况：尝试反序列化
            elif df_pickle_b64_from_script and not subprocess_execution_failed: # 仅在没有子进程错误且有数据时尝试
                try:
                    pickled_df = base64.b64decode(df_pickle_b64_from_script.encode('utf-8'))
                    deserialized_object = pickle.loads(pickled_df)
                    if isinstance(deserialized_object, pd.DataFrame):
                        processed_df = deserialized_object
                        logger.info(f"项目 {item_id_for_log} ({code_type_for_log}): DataFrame已反序列化。形状: {processed_df.shape}")
                    else:
                        # MODIFICATION: 即使这里反序列化成功，但类型不对，也认为是“问题”
                        logger.error(f"项目 {item_id_for_log} ({code_type_for_log}): 反序列化的对象不是DataFrame。类型: {type(deserialized_object)}。")
                        result_is_not_dataframe = True # 标记结果不是DataFrame
                        # processed_df 保持为 None 或其他非DataFrame类型
                except Exception as e_deserialize:
                    logger.error(f"项目 {item_id_for_log} ({code_type_for_log}): 无法反序列化DataFrame: {e_deserialize}。Base64数据 (前100个字符): '{df_pickle_b64_from_script[:100]}'")
                    deserialization_error_occurred = True
            elif subprocess_execution_failed:
                 logger.warning(f"项目 {item_id_for_log} ({code_type_for_log}): 子进程执行失败 (返回码 != 0)。不进行反序列化。")
            else: # 没有数据行，没有错误标记，并且子进程未执行失败
                if process.returncode == 0:
                     logger.warning(f"项目 {item_id_for_log} ({code_type_for_log}): 脚本标准输出中没有有效的DataFrame输出行 (除去日志后为空)。")


            # 日志记录 (stderr 和 stdout 日志)
            if process.stderr:
                log_level = logging.ERROR if subprocess_execution_failed or script_internal_error_marker else logging.WARNING
                logger.log(log_level, f"项目 {item_id_for_log} ({code_type_for_log}): 子进程标准错误输出:\n{process.stderr.strip()}")

            if subprocess_stdout_log_lines:
                log_level_stdout = logging.DEBUG
                if subprocess_execution_failed or script_internal_error_marker:
                    log_level_stdout = logging.ERROR
                elif any("[子进程_错误]" in line or "[子进程_警告]" in line for line in subprocess_stdout_log_lines):
                    log_level_stdout = logging.WARNING
                
                if logger.isEnabledFor(log_level_stdout) or log_level_stdout >= logging.WARNING :
                    logger.log(log_level_stdout, f"项目 {item_id_for_log} ({code_type_for_log}): 子进程标准输出日志:\n" + "\n".join(subprocess_stdout_log_lines))
                    if log_level_stdout >= logging.ERROR : full_stdout_logged = True
            
            if (deserialization_error_occurred or result_is_not_dataframe) and not full_stdout_logged and process.stdout:
                 logger.error(f"项目 {item_id_for_log} ({code_type_for_log}): 由于后处理错误/类型不匹配，记录完整的子进程标准输出:\n{process.stdout.strip()}")
            
            # MODIFICATION: 决定是否删除脚本的逻辑
            # "GT代码程序顺利运行" 解释为：子进程未失败，脚本内部未报致命错，且最终得到了一个DataFrame
            if isinstance(processed_df, pd.DataFrame) and \
               not subprocess_execution_failed and \
               not script_internal_error_marker and \
               not deserialization_error_occurred and \
               not result_is_not_dataframe: # 确保确实是DataFrame且没有其他标记错误
                should_delete_script = True
            
            # 如果不删除，记录原因（已在上面各处日志中体现，这里总结性或可省略）

        except subprocess.TimeoutExpired:
            logger.error(f"项目 {item_id_for_log} ({code_type_for_log}): 脚本执行超时 ({self.execution_timeout}秒)。脚本: {script_save_path}")
            # should_delete_script 保持 False
        except Exception as e_outer:
            logger.error(f"项目 {item_id_for_log} ({code_type_for_log}): 沙盒执行期间发生意外的外部错误: {type(e_outer).__name__} - {e_outer}。脚本: {script_save_path}")
            logger.error(traceback.format_exc())
            # should_delete_script 保持 False
        finally:
            # MODIFICATION: 根据 should_delete_script 决定是否删除
            if os.path.exists(script_save_path):
                if should_delete_script:
                    try:
                        os.remove(script_save_path)
                        logger.info(f"项目 {item_id_for_log} ({code_type_for_log}): 执行成功且结果符合预期，临时脚本 {script_save_path} 已删除。")
                    except OSError as e_remove:
                        logger.warning(f"项目 {item_id_for_log} ({code_type_for_log}): 尝试删除临时脚本 {script_save_path} 失败: {e_remove}。脚本仍会保留。")
                else:
                    logger.warning(f"项目 {item_id_for_log} ({code_type_for_log}): 由于执行问题、结果非DataFrame或错误，临时脚本 {script_save_path} 已保留以供调试。")
                    # 可以根据具体标志位添加更详细的保留原因日志
                    if subprocess_execution_failed:
                        logger.warning(f"    保留原因: 子进程执行失败 (返回码: {process.returncode if 'process' in locals() and hasattr(process, 'returncode') else 'N/A'})。")
                    if script_internal_error_marker:
                        logger.warning(f"    保留原因: 脚本内部报告了错误标记。")
                    if deserialization_error_occurred:
                        logger.warning(f"    保留原因: DataFrame反序列化失败。")
                    if result_is_not_dataframe: # 包括反序列化对象不是DataFrame，或脚本明确标记返回了非DataFrame
                        logger.warning(f"    保留原因: 最终结果不是有效的DataFrame (实际类型: {type(processed_df if 'deserialized_object' not in locals() else deserialized_object)}, 脚本输出标记: {df_pickle_b64_from_script if df_pickle_b64_from_script else '无特定标记'})。")
                    elif not isinstance(processed_df, pd.DataFrame) and not (subprocess_execution_failed or script_internal_error_marker or deserialization_error_occurred):
                        # 这种情况是 processed_df 为 None，但没有其他特定错误标记（例如，脚本返回了 "空数据帧标记"）
                        logger.warning(f"    保留原因: 最终结果为 None DataFrame (脚本输出标记: {df_pickle_b64_from_script if df_pickle_b64_from_script else '无特定标记'})。")


        return processed_df

    @staticmethod
    def calculate_column_accuracy(gt_series: pd.Series, gen_series: pd.Series, col_name_for_log:str ="<未知列>", item_id_for_log: str = "N/A") -> float:
        # (此方法未修改)
        if not isinstance(gt_series, pd.Series) or not isinstance(gen_series, pd.Series):
            logger.error(f"项目 {item_id_for_log}: 列 '{col_name_for_log}' 的输入不是Pandas Series。基准类型: {type(gt_series)}，生成类型: {type(gen_series)}")
            return 0.0

        if len(gt_series) == 0:
            return 1.0 if len(gen_series) == 0 else 0.0

        if len(gt_series) != len(gen_series):
            logger.warning(f"项目 {item_id_for_log}: 列 '{col_name_for_log}' 的Series长度不匹配：基准长度={len(gt_series)}，生成长度={len(gen_series)}。此列的准确率设为0。")
            return 0.0

        matches = 0
        gt_list = gt_series.astype(object).where(pd.notna(gt_series), None).tolist()
        gen_list = gen_series.astype(object).where(pd.notna(gen_series), None).tolist()

        for i, (gt_val, gen_val_orig) in enumerate(zip(gt_list, gen_list)):
            gen_val = gen_val_orig
            is_gt_missing = gt_val is None

            if isinstance(gt_val, bool) or is_gt_missing:
                if isinstance(gen_val, str):
                    low_gen_val = gen_val.lower()
                    if low_gen_val == 'true': gen_val = True
                    elif low_gen_val == 'false': gen_val = False
                    elif low_gen_val in ['none', 'nan', 'null', 'na', '', 'undefined', '<na>']: gen_val = None
                elif isinstance(gen_val, (int, float)) and not isinstance(gen_val, bool):
                    if gen_val == 1 and isinstance(gt_val, bool): gen_val = True
                    elif gen_val == 0 and isinstance(gt_val, bool): gen_val = False
            
            is_gen_missing = gen_val is None

            match_this_pair = False
            if is_gt_missing:
                if is_gen_missing:
                    matches += 1; match_this_pair = True
            elif isinstance(gt_val, bool):
                if isinstance(gen_val, bool) and gt_val == gen_val:
                    matches += 1; match_this_pair = True
            elif isinstance(gt_val, pd.Timestamp) and isinstance(gen_val, pd.Timestamp):
                if gt_val == gen_val:
                    matches += 1; match_this_pair = True
            elif type(gt_val) == type(gen_val) or \
                 (isinstance(gt_val, (int, float, np.number)) and isinstance(gen_val, (int, float, np.number))):
                try:
                    if gt_val == gen_val:
                        matches += 1; match_this_pair = True
                    elif isinstance(gt_val, (float, np.floating)) and isinstance(gen_val, (float, np.floating)) and np.isclose(gt_val, gen_val, equal_nan=is_gt_missing):
                        matches +=1; match_this_pair = True
                except (TypeError, ValueError): pass

            if not match_this_pair and not is_gt_missing and not is_gen_missing:
                if str(gt_val) == str(gen_val):
                     matches += 1; match_this_pair = True
            
        accuracy = matches / len(gt_series) if len(gt_series) > 0 else 1.0
        logger.info(f"项目 {item_id_for_log}: 列 '{col_name_for_log}' 准确率: {matches}/{len(gt_series)} = {accuracy:.4f}")
        return accuracy