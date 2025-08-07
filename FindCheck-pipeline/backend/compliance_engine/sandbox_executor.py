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
import tokenize
import logging

logger = logging.getLogger(__name__)

class SandboxExecutor:
    DEFAULT_EXECUTION_TIMEOUT = 60 # 默认执行超时时间（秒）
    TEMP_SCRIPT_DIR = "temp_scripts_execution" # 临时脚本目录名

    def __init__(self, execution_timeout: Optional[int] = None):
        self.execution_timeout = execution_timeout if execution_timeout is not None else self.DEFAULT_EXECUTION_TIMEOUT
        self.scripts_output_path = os.path.join(os.getcwd(), self.TEMP_SCRIPT_DIR)
        os.makedirs(self.scripts_output_path, exist_ok=True)
        logger.info(f"临时执行脚本将保存在：{self.scripts_output_path}")

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

# --- 哑日志记录器定义 ---
class DummyLogger:
    def _log(self, level, msg, *args, **kwargs):
        # 这个哑日志记录器什么也不做，只是为了防止代码崩溃
        pass
    
    def info(self, msg, *args, **kwargs):
        self._log('INFO', msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self._log('DEBUG', msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self._log('WARNING', msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self._log('ERROR', msg, *args, **kwargs)
        
    def exception(self, msg, *args, **kwargs):
        self._log('EXCEPTION', msg, *args, **kwargs)

# 实例化哑日志记录器
logger = DummyLogger()

def logger_print_fn_in_script(level, message):
    # 沙盒脚本内部使用的日志打印函数
    level_str = str(level)
    print(f"[子进程_{{level_str.upper()}}] {{message}}")

result_df_pickle_b64 = None
logger_print_fn_in_script("信息", "沙盒脚本执行开始。")

try:
    logger_print_fn_in_script("信息", f"子进程当前工作目录: {{os.getcwd()}}")
    logger_print_fn_in_script("信息", "--- 环境代码块执行开始 ---")
    
    # 环境代码在其自己的局部作用域中执行
    # 我们将把数据帧注入到这个作用域中
    env_code_globals = {{
        'pd': pd, 
        'np': np, 
        'os': os, 
        'logger_print_fn_in_script': logger_print_fn_in_script
    }}
    env_code_locals = {{}}
    
    # 反序列化输入数据帧
    b64_decoded_df = base64.b64decode("{df_pickle_b64}")
    df = pickle.loads(b64_decoded_df)
    
    env_code_locals['df'] = df
    
    logger_print_fn_in_script("信息", "--- 环境代码块执行结束 ---")

    if 'df' not in env_code_locals or not isinstance(env_code_locals['df'], pd.DataFrame):
        logger_print_fn_in_script("错误", f"环境数据帧未能正确加载。")
        initial_df_copy = pd.DataFrame()
    else:
        logger_print_fn_in_script("信息", f"初始DataFrame 'df' 已加载。形状: {{env_code_locals['df'].shape}}")
        initial_df_copy = env_code_locals['df'].copy()

    target_function_name = "{func_name}"
    logger_print_fn_in_script("信息", f"--- 用户代码函数 '{{target_function_name}}' 定义开始 ---")
    
    # 用户代码可用的全局变量
    user_code_exec_globals = {{
        'pd': pd,
        'np': np,
        'logger': logger,  # 注入哑日志记录器
        'logger_print_fn_in_script': logger_print_fn_in_script,
        'os': os,
        'bisect_left': bisect_left,
        'bisect_right': bisect_right,
        'bisect': bisect
    }} 
    user_code_locals = {{}} # 用户代码在其自己的局部作用域中执行定义

    # user_code_str 应包含函数定义
    exec(\"\"\"{user_code_str}\"\"\", user_code_exec_globals, user_code_locals)
    user_function = user_code_locals.get(target_function_name)

    if not user_function or not callable(user_function):
        raise NameError(f"用户函数 '{{target_function_name}}' 定义失败。")

    logger_print_fn_in_script("信息", f"用户函数 '{{target_function_name}}' 已定义，准备执行。")
    processed_df = user_function(initial_df_copy) # 调用用户函数
    logger_print_fn_in_script("信息", f"--- 用户代码函数 '{{target_function_name}}' 执行结束 ---")

    if not isinstance(processed_df, pd.DataFrame):
        logger_print_fn_in_script("警告", f"用户函数 '{{target_function_name}}' 未返回DataFrame。返回类型: {{type(processed_df)}}。将视为空DataFrame处理。")
        processed_df = None

    if processed_df is not None:
        logger_print_fn_in_script("信息", f"用户函数返回了DataFrame。形状: {{processed_df.shape}}")
        pickled_df = pickle.dumps(processed_df)
        result_df_pickle_b64 = base64.b64encode(pickled_df).decode('utf-8')
    else:
        logger_print_fn_in_script("信息", "处理后的DataFrame为None。")
        result_df_pickle_b64 = "EMPTY_DATAFRAME_MARKER"

except Exception as e_script:
    logger_print_fn_in_script("错误", f"沙盒脚本顶层错误: {{str(e_script)}} \\n----- 沙盒内部回溯开始 -----\\n{{traceback.format_exc()}}\\n----- 沙盒内部回溯结束 -----")
    result_df_pickle_b64 = "ERROR_DATAFRAME_MARKER"

if result_df_pickle_b64 is not None:
    sys.stdout.write(result_df_pickle_b64 + '\\n')
else:
    sys.stdout.write("UNEXPECTED_EMPTY_RESULT\\n")

"""

    def execute_code(self, user_code_str: str, func_name: str, company_data: pd.DataFrame, unit_id: str) -> Optional[pd.DataFrame]:
        
        # 序列化输入数据
        try:
            df_pickle_b64 = base64.b64encode(pickle.dumps(company_data)).decode('utf-8')
        except Exception as e:
            logger.error(f"无法序列化输入的 company_data for unit {unit_id}: {e}")
            raise

        script_content = self._get_sandbox_script_template().format(
            df_pickle_b64=df_pickle_b64,
            user_code_str=user_code_str,
            func_name=func_name
        )
        safe_unit_id = "".join(c if c.isalnum() else "_" for c in unit_id)
        script_file_name = f"exec_{safe_unit_id}_{os.getpid()}.py"
        script_save_path = os.path.join(self.scripts_output_path, script_file_name)
        
        should_delete_script = True

        try:
            with open(script_save_path, 'w', encoding='utf-8') as tmp_script_file:
                tmp_script_file.write(script_content)

            logger.debug(f"单元 {unit_id}: 正在执行临时脚本：{script_save_path}")
            
            process = subprocess.run(
                [sys.executable, script_save_path],
                capture_output=True,
                text=True,
                timeout=self.execution_timeout,
                cwd=os.getcwd()
            )

            if process.returncode != 0:
                logger.error(f"单元 {unit_id}: 子进程执行失败 (返回码: {process.returncode})")
                logger.error(f"子进程 STDERR:\n{process.stderr}")
                raise RuntimeError(f"子进程执行失败。查看日志获取详情。")

            # 处理标准输出
            output = process.stdout.strip()
            
            # 分离日志和真正的输出
            output_lines = output.splitlines()
            real_output = ""
            for line in output_lines:
                if line.startswith("[子进程_"):
                    logger.info(line) # 打印子进程日志
                else:
                    real_output = line
            
            if real_output == "ERROR_DATAFRAME_MARKER":
                logger.error(f"单元 {unit_id}: 脚本在执行期间遇到内部错误。")
                raise RuntimeError("脚本执行时发生内部错误。")

            if real_output == "EMPTY_DATAFRAME_MARKER":
                logger.info(f"单元 {unit_id}: 脚本执行成功并返回一个空的DataFrame。")
                return None
            
            if real_output == "UNEXPECTED_EMPTY_RESULT":
                 logger.error(f"单元 {unit_id}: 脚本返回了意外的空结果。")
                 raise ValueError("脚本返回了意外的空结果。")

            try:
                pickled_df = base64.b64decode(real_output.encode('utf-8'))
                deserialized_object = pickle.loads(pickled_df)
                
                if isinstance(deserialized_object, pd.DataFrame):
                    logger.info(f"单元 {unit_id}: DataFrame已成功反序列化。形状: {deserialized_object.shape}")
                    return deserialized_object
                else:
                    logger.error(f"单元 {unit_id}: 反序列化的对象不是DataFrame。类型: {type(deserialized_object)}。")
                    raise TypeError(f"执行结果不是预期的DataFrame。")
            except Exception as e_deserialize:
                logger.error(f"单元 {unit_id}: 无法反序列化结果: {e_deserialize}。Base64数据 (前100字符): '{real_output[:100]}'")
                raise

        except subprocess.TimeoutExpired:
            logger.error(f"单元 {unit_id}: 在 {self.execution_timeout} 秒后执行超时。")
            should_delete_script = False # 超时后可能无法清理，保留脚本用于调试
            raise TimeoutError(f"执行超时")
        except Exception as e:
            logger.error(f"单元 {unit_id}: 执行代码时发生未知错误: {e}")
            raise
        finally:
            if should_delete_script and os.path.exists(script_save_path):
                try:
                    os.remove(script_save_path)
                except OSError as e:
                    logger.warning(f"无法删除临时脚本 {script_save_path}: {e}") 