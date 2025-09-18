# evaluate_models.py
import json
import os
import glob
import shutil
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, Any, Optional, List, Union
import pandas as pd
import sys
from tqdm import tqdm # 导入 tqdm

# 从 reward_utils.py 导入必要的类
# 确保 reward_utils.py 与此脚本在同一目录，或在 PYTHONPATH 中
from reward_utils import SandboxExecutor, CodeExtractionUtils

# 导入 CodeBLEU 计算函数
from codebleu import calc_codebleu

# 配置此脚本的日志记录器
logger = logging.getLogger(__name__)
if not logger.hasHandlers(): # 防止重复添加处理器
    handler = logging.StreamHandler(sys.stdout) # 显式输出到 stdout
    formatter = logging.Formatter('%(asctime)s - %(process)d - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO) # 设置日志级别


BASE_INPUT_DIR = 'model_output/infer_results_temp_0_no_sft/washed_data' # 基础输入目录
BASE_OUTPUT_DIR = 'model_output/infer_results_temp_0_no_sft/results' # 基础输出目录

# 全局 SandboxExecutor 实例。如果脚本直接运行，ProcessPoolExecutor 会正确处理它。
# 如果这是一个模块函数，则应显式传递。
sandbox_executor = SandboxExecutor(execution_timeout=120) # 超时时间（秒）

def preprocess_json_data(data: Any) -> Any:
    """
    递归地遍历JSON数据（列表或字典），并将所有字符串值和字典键中的 "meu_" 替换为 "cu_"。
    这个函数是历史遗留问题.
    """
    if isinstance(data, dict):
        new_dict = {}
        for key, value in data.items():
            new_key = key.replace("meu_", "cu_") if isinstance(key, str) else key
            new_dict[new_key] = preprocess_json_data(value)
        return new_dict
    elif isinstance(data, list):
        return [preprocess_json_data(item) for item in data]
    elif isinstance(data, str):
        return data.replace("meu_", "cu_")
    else:
        return data

def process_single_item(item_data: Dict[str, Any], model_name: str, item_idx: int) -> Dict[str, Any]:
    """
    处理 JSON 数据中的单个条目以评估生成的代码。
    """
    # 注意：由于预处理已在加载数据后完成，此处的 item_data 已经是 "cu_" 版本
    item_id_from_meta = item_data.get('metadata', {}).get('id', f'未知项目索引_{item_idx}')
    # 确保 item_id_from_meta 中的 "meu_" 也被替换（如果它最初包含）
    # 理论上，如果 'id' 是从原始数据来的，它已经在 preprocess_json_data 中被处理了
    # 但如果它是动态生成的且可能包含 "meu_"，则需要额外处理，不过此处场景下 'id' 似乎是元数据的一部分

    log_prefix = f"模型 '{model_name}', 项目 '{item_id_from_meta}':"
    # logger.info(f"{log_prefix} 开始处理。") # 此日志级别过于详细，可根据需要启用

    updated_item = item_data.copy() # item_data 已经是预处理过的
    evaluation_scores: Dict[str, Any] = {
        "subject_accuracy": 0.0,
        "condition_accuracy": 0.0,
        "constraint_accuracy": 0.0,
        "final_decision_accuracy": 0.0, # 新增：最终决策准确率
        "final_decision_pass_0.99": False, # 新增：最终决策是否通过0.99阈值
        "final_decision_pass_0.95": False, # 新增：最终决策是否通过0.95阈值
        "execution_status_gold": "未运行",
        "execution_status_gen": "未运行",
        "error_message_gold": None,
        "error_message_gen": None,
        "columns_found_gold": [],
        "columns_found_gen": [],
        "codebleu": 0.0,
        "ngram_match_score": 0.0,
        "weighted_ngram_match_score": 0.0,
        "syntax_match_score": 0.0,
        "dataflow_match_score": 0.0,
        "codebleu_error_message": None,
    }

    try:
        metadata = item_data.get('metadata', {})
        verification_info = item_data.get('verification_info', {})

        # cu_id 应该已经是 "cu_" 前缀了，因为它来自 item_data
        cu_id = metadata.get('compliance_unit_id')
        if not cu_id:
            # 即使经过预处理，如果原始字段名就是 'compliance_unit_id' 且其值为空，这里仍会触发
            # 如果原始字段名可能是 'compliance_meu_id'，预处理会将其键名改为 'compliance_cu_id'
            logger.error(f"{log_prefix} 元数据中缺少 'compliance_unit_id' (或其预处理前的形式)。")
            error_msg = "缺少 compliance_unit_id"
            evaluation_scores["error_message_gen"] = error_msg
            evaluation_scores["error_message_gold"] = error_msg
            evaluation_scores["codebleu_error_message"] = error_msg
            updated_item['evaluation_scores'] = evaluation_scores
            return updated_item

        # func_name 会使用已经是 "cu_" 的 cu_id
        func_name = f"check_{cu_id}"


        raw_env_code = verification_info.get('test_code', '')
        env_code_str: str
        if not raw_env_code: # raw_env_code 本身的内容如果含 "meu_" 已被预处理替换
            logger.warning(f"{log_prefix} verification_info中的 'test_code' (环境代码) 缺失或为空。将使用默认的空DataFrame。")
            env_code_str = "import pandas as pd\ndf = pd.DataFrame()"
        else:
            # raw_env_code 已经是预处理过的字符串
            extracted_md_code = CodeExtractionUtils.extract_from_markdown(raw_env_code)
            if extracted_md_code:
                env_code_str = extracted_md_code # extracted_md_code 也是基于预处理过的 raw_env_code
            else:
                env_code_str = raw_env_code
                logger.debug(f"{log_prefix} 未能从Markdown中提取环境代码，使用原始'test_code' (已预处理)。")

        # gold_user_code_str 和 gen_user_code_str 的内容如果含 "meu_" 已被预处理替换
        gold_user_code_str = item_data.get('runable_gold_code', '')
        if not gold_user_code_str:
            logger.error(f"{log_prefix} 'runable_gold_code' (基准可执行代码) 缺失或为空。")
            evaluation_scores["error_message_gold"] = "'runable_gold_code' 缺失"

        gen_user_code_str = item_data.get('runable_gen_code', '')
        if not gen_user_code_str:
            logger.warning(f"{log_prefix} 'runable_gen_code' (生成可执行代码) 缺失或为空。准确度将为0。")
            evaluation_scores["error_message_gen"] = "'runable_gen_code' 缺失"

        # --- 计算 CodeBLEU ---
        # 代码字符串已经是预处理过的
        if gold_user_code_str and gen_user_code_str:
            try:
                codebleu_results = calc_codebleu(
                    [gold_user_code_str],
                    [gen_user_code_str],
                    lang="python",
                    weights=(0.25, 0.25, 0.25, 0.25),
                    tokenizer=None
                )
                evaluation_scores["codebleu"] = codebleu_results.get('codebleu', 0.0)
                evaluation_scores["ngram_match_score"] = codebleu_results.get('ngram_match_score', 0.0)
                evaluation_scores["weighted_ngram_match_score"] = codebleu_results.get('weighted_ngram_match_score', 0.0)
                evaluation_scores["syntax_match_score"] = codebleu_results.get('syntax_match_score', 0.0)
                evaluation_scores["dataflow_match_score"] = codebleu_results.get('dataflow_match_score', 0.0)
            except Exception as e_codebleu:
                logger.error(f"{log_prefix} 计算 CodeBLEU 时出错: {e_codebleu}", exc_info=False) # exc_info=False 避免在日志中打印完整堆栈跟踪
                evaluation_scores["codebleu_error_message"] = f"CodeBLEU 计算错误: {str(e_codebleu)}"
        elif not gold_user_code_str:
            logger.warning(f"{log_prefix} 因 'runable_gold_code' 缺失或为空，无法计算 CodeBLEU。")
            evaluation_scores["codebleu_error_message"] = "用于 CodeBLEU 的基准代码 (gt_code) 缺失或为空。"
        elif not gen_user_code_str:
            logger.warning(f"{log_prefix} 因 'runable_gen_code' 缺失或为空，无法计算 CodeBLEU。")
            evaluation_scores["codebleu_error_message"] = "用于 CodeBLEU 的生成代码 (gen_code) 缺失或为空。"


        # --- 执行基准代码 ---
        gt_code_df: Optional[pd.DataFrame] = None
        if gold_user_code_str: # 字符串已预处理
            try:
                gt_code_df = sandbox_executor.execute_code_in_sandbox(
                    env_code_str=env_code_str, # 已预处理
                    user_code_str=gold_user_code_str, # 已预处理
                    func_name=func_name, # 基于已预处理的 cu_id
                    item_id_for_log=f"{model_name}_{item_id_from_meta}",
                    code_type_for_log="基准代码"
                )
                if gt_code_df is not None:
                    evaluation_scores["execution_status_gold"] = "成功"
                    evaluation_scores["columns_found_gold"] = list(gt_code_df.columns) # 列名本身是否需要替换取决于代码执行结果
                else:
                    evaluation_scores["execution_status_gold"] = "失败或空DataFrame"
                    evaluation_scores["error_message_gold"] = "基准 (GOLD) 代码执行结果为 None 或出错。"
                    logger.warning(f"{log_prefix} 基准 (GOLD) 代码执行失败或返回了 None DataFrame。")
            except Exception as e_gold_exec:
                logger.error(f"{log_prefix} 基准 (GOLD) 代码沙盒执行期间发生异常: {e_gold_exec}", exc_info=True)
                evaluation_scores["execution_status_gold"] = "执行异常"
                evaluation_scores["error_message_gold"] = str(e_gold_exec)
        else:
             evaluation_scores["execution_status_gold"] = "因空代码跳过"

        # --- 执行生成代码 ---
        gen_code_df: Optional[pd.DataFrame] = None
        if gen_user_code_str: # 字符串已预处理
            try:
                gen_code_df = sandbox_executor.execute_code_in_sandbox(
                    env_code_str=env_code_str, # 已预处理
                    user_code_str=gen_user_code_str, # 已预处理
                    func_name=func_name, # 基于已预处理的 cu_id
                    item_id_for_log=f"{model_name}_{item_id_from_meta}",
                    code_type_for_log="生成代码"
                )
                if gen_code_df is not None:
                    evaluation_scores["execution_status_gen"] = "成功"
                    evaluation_scores["columns_found_gen"] = list(gen_code_df.columns) # 列名本身是否需要替换取决于代码执行结果
                else:
                    evaluation_scores["execution_status_gen"] = "失败或空DataFrame"
                    evaluation_scores["error_message_gen"] = "生成 (GENERATED) 的代码执行结果为 None 或出错。"
                    logger.warning(f"{log_prefix} 生成 (GENERATED) 的代码执行失败或返回了 None DataFrame。")
            except Exception as e_gen_exec:
                logger.error(f"{log_prefix} 生成 (GENERATED) 的代码沙盒执行期间发生异常: {e_gen_exec}", exc_info=True)
                evaluation_scores["execution_status_gen"] = "执行异常"
                evaluation_scores["error_message_gen"] = str(e_gen_exec)
        else:
            evaluation_scores["execution_status_gen"] = "因空代码跳过"

        # --- 计算准确度 ---
        if gt_code_df is not None and gen_code_df is not None:
            target_col_categories = ["subject", "condition", "constraint"]
            for category in target_col_categories:
                # col_name 将使用已经是 "cu_" 的 cu_id
                col_name = f"{cu_id}_{category}" # 例如 cu_123_subject
                accuracy_key = f"{category}_accuracy"

                # DataFrame的列名是代码执行的结果，它们是否包含 "meu_" 或 "cu_" 取决于
                # 执行的代码如何生成这些列。如果代码本身生成了 "meu_" 前缀的列，
                # 那么这里的检查就需要对应。假设代码执行后列名与 `cu_id` 一致。
                if col_name in gt_code_df.columns and col_name in gen_code_df.columns:
                    try:
                        evaluation_scores[accuracy_key] = SandboxExecutor.calculate_column_accuracy(
                            gt_series=gt_code_df[col_name],
                            gen_series=gen_code_df[col_name],
                            col_name_for_log=col_name,
                            item_id_for_log=f"{model_name}_{item_id_from_meta}"
                        )
                    except Exception as e_acc: # 捕获计算准确率时可能发生的任何异常
                        logger.error(f"{log_prefix} 计算列 '{col_name}' 准确度时出错: {e_acc}")
                        evaluation_scores[accuracy_key] = 0.0 # 出错则准确率为0
                else:
                    missing_in = []
                    if col_name not in gt_code_df.columns: missing_in.append("基准DataFrame")
                    if col_name not in gen_code_df.columns: missing_in.append("生成DataFrame")
                    logger.warning(f"{log_prefix} 用于准确率计算的目标列 '{col_name}' 在 {', '.join(missing_in)} 中缺失。分类 '{category}' 的准确率设为0。")
                    evaluation_scores[accuracy_key] = 0.0

            # --- 新增: 计算 final_decision ---
            subject_col_name = f"{cu_id}_subject"
            condition_col_name = f"{cu_id}_condition"
            constraint_col_name = f"{cu_id}_constraint"
            final_decision_col_name = f"{cu_id}_final_decision"

            gt_final_decision_col_created = False
            gen_final_decision_col_created = False

            # 为 gt_code_df 计算 final_decision
            if all(col in gt_code_df.columns for col in [subject_col_name, condition_col_name, constraint_col_name]):
                try:
                    # 确保源列是布尔类型以进行逻辑运算
                    gt_code_df[final_decision_col_name] = (
                        gt_code_df[subject_col_name].astype(bool) &
                        gt_code_df[condition_col_name].astype(bool) &
                        (~gt_code_df[constraint_col_name].astype(bool))
                    )
                    gt_final_decision_col_created = True
                    if final_decision_col_name not in evaluation_scores["columns_found_gold"]: # 如果列被创建，添加到列表中
                        evaluation_scores["columns_found_gold"].append(final_decision_col_name)
                except Exception as e_gt_fd:
                    logger.warning(f"{log_prefix} 为基准DataFrame计算 '{final_decision_col_name}' 时出错: {e_gt_fd}")
            else:
                missing_cols_gt = [col for col in [subject_col_name, condition_col_name, constraint_col_name] if col not in gt_code_df.columns]
                if missing_cols_gt: # 仅当确实有列缺失时记录
                    logger.warning(f"{log_prefix} 基准DataFrame中缺少列 {missing_cols_gt}，无法计算 '{final_decision_col_name}'。")

            # 为 gen_code_df 计算 final_decision
            if all(col in gen_code_df.columns for col in [subject_col_name, condition_col_name, constraint_col_name]):
                try:
                    # 确保源列是布尔类型以进行逻辑运算
                    gen_code_df[final_decision_col_name] = (
                        gen_code_df[subject_col_name].astype(bool) &
                        gen_code_df[condition_col_name].astype(bool) &
                        (~gen_code_df[constraint_col_name].astype(bool))
                    )
                    gen_final_decision_col_created = True
                    if final_decision_col_name not in evaluation_scores["columns_found_gen"]: # 如果列被创建，添加到列表中
                        evaluation_scores["columns_found_gen"].append(final_decision_col_name)
                except Exception as e_gen_fd:
                    logger.warning(f"{log_prefix} 为生成DataFrame计算 '{final_decision_col_name}' 时出错: {e_gen_fd}")
            else:
                missing_cols_gen = [col for col in [subject_col_name, condition_col_name, constraint_col_name] if col not in gen_code_df.columns]
                if missing_cols_gen: # 仅当确实有列缺失时记录
                    logger.warning(f"{log_prefix} 生成DataFrame中缺少列 {missing_cols_gen}，无法计算 '{final_decision_col_name}'。")


            # 计算 final_decision_accuracy
            if gt_final_decision_col_created and gen_final_decision_col_created:
                try:
                    accuracy = SandboxExecutor.calculate_column_accuracy( 
                        gt_series=gt_code_df[final_decision_col_name],
                        gen_series=gen_code_df[final_decision_col_name],
                        col_name_for_log=final_decision_col_name,
                        item_id_for_log=f"{model_name}_{item_id_from_meta}"
                    )
                    evaluation_scores["final_decision_accuracy"] = accuracy
                    if accuracy >= 0.99:
                        evaluation_scores["final_decision_pass_0.99"] = True
                    if accuracy >= 0.95: # 注意：这里应该是 if, 而不是 elif，因为>=0.99也满足>=0.95
                        evaluation_scores["final_decision_pass_0.95"] = True
                except Exception as e_fd_acc: # 捕获计算准确率时可能发生的任何异常
                    logger.error(f"{log_prefix} 计算列 '{final_decision_col_name}' 准确度时出错: {e_fd_acc}")
                    evaluation_scores["final_decision_accuracy"] = 0.0 # 出错则准确率为0
            else:
                # 如果任一 final_decision 列未创建，则记录原因
                reason = []
                if not gt_final_decision_col_created: reason.append("基准DataFrame中未创建")
                if not gen_final_decision_col_created: reason.append("生成DataFrame中未创建")
                logger.warning(f"{log_prefix} 因 '{final_decision_col_name}' 未能在两个DataFrame中都成功创建 ({', '.join(reason)})，其准确率设为0。")
                evaluation_scores["final_decision_accuracy"] = 0.0 # 默认准确率为0，通过状态为False
            # --- 新增结束 ---

        elif gt_code_df is None:
             logger.warning(f"{log_prefix} 因基准DataFrame (gt_code_df) 为 None，无法计算准确率。")
        elif gen_code_df is None and gen_user_code_str: # 仅当生成代码存在但DataFrame为None时才记录此特定警告
             logger.warning(f"{log_prefix} 因生成DataFrame (gen_code_df) 为 None (且已提供生成代码)，无法计算准确率。")

    except Exception as e:
        logger.error(f"{log_prefix} process_single_item 中发生未处理的错误: {e}", exc_info=True)
        error_msg_outer = f"项目处理外部错误: {str(e)}"
        if evaluation_scores["error_message_gen"] is None : evaluation_scores["error_message_gen"] = error_msg_outer
        if evaluation_scores["error_message_gold"] is None : evaluation_scores["error_message_gold"] = error_msg_outer
        if evaluation_scores["codebleu_error_message"] is None : evaluation_scores["codebleu_error_message"] = error_msg_outer
        # 确保所有分数，包括新增的分数，在发生外部错误时也存在
        evaluation_scores.setdefault("subject_accuracy", 0.0)
        evaluation_scores.setdefault("condition_accuracy", 0.0)
        evaluation_scores.setdefault("constraint_accuracy", 0.0)
        evaluation_scores.setdefault("final_decision_accuracy", 0.0)
        evaluation_scores.setdefault("final_decision_pass_0.99", False)
        evaluation_scores.setdefault("final_decision_pass_0.95", False)
        evaluation_scores.setdefault("codebleu", 0.0)
        current_status_gen = evaluation_scores.get("execution_status_gen", "未运行")
        current_status_gold = evaluation_scores.get("execution_status_gold", "未运行")
        evaluation_scores["execution_status_gen"] = f"{current_status_gen}_外部错误"
        evaluation_scores["execution_status_gold"] = f"{current_status_gold}_外部错误"


    updated_item['evaluation_scores'] = evaluation_scores
    return updated_item


def main():
    os.makedirs(BASE_OUTPUT_DIR, exist_ok=True) # 创建输出目录，如果不存在
    json_files = glob.glob(os.path.join(BASE_INPUT_DIR, '*_washed.json')) # 查找所有清洗过的json文件

    if not json_files:
        logger.warning(f"在目录 {BASE_INPUT_DIR} 中未找到 '*_washed.json' 文件。")
        return

    for json_file_path in tqdm(json_files, desc="处理模型文件", unit="个文件"): # tqdm显示总体文件处理进度
        filename = os.path.basename(json_file_path)
        model_name = filename.replace('_washed.json', '')
        logger.info(f"开始处理模型: {model_name}，来自文件: {filename}")

        output_file_path = os.path.join(BASE_OUTPUT_DIR, filename) # 定义输出文件路径

        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data_items_raw = json.load(f) # 加载原始JSON数据
        except Exception as e:
            logger.error(f"无法从 '{json_file_path}' 读取或解析 JSON: {e}")
            continue # 跳过此文件

        # --- 新增预处理步骤 ---
        logger.info(f"对模型 '{model_name}' 的数据进行 'meu_' 到 'cu_' 的预处理...")
        data_items = preprocess_json_data(data_items_raw) # 对加载的数据进行预处理
        logger.info(f"模型 '{model_name}' 的数据预处理完成。")
        # -----------------------

        if not isinstance(data_items, list):
            logger.error(f"预处理后，'{json_file_path}' 中的 JSON 内容不是列表。正在跳过此文件。")
            # 如果原始数据就不是列表，preprocess_json_data 会保持其类型，所以这里检查是有效的
            continue

        # 我们直接在内存中预处理过的 data_items 上操作，并最后将结果写入 output_file_path。

        num_items = len(data_items)
        if num_items == 0:
            logger.info(f"模型 '{model_name}' 的文件 '{filename}' (预处理后) 为空，跳过处理。")
            # 如果预处理后列表为空，也需要写入一个空列表到输出文件
            try:
                with open(output_file_path, 'w', encoding='utf-8') as f:
                    json.dump(data_items, f, indent=4, ensure_ascii=False) # data_items此时是[]
                logger.info(f"已将空的预处理结果保存到 '{output_file_path}'")
            except Exception as e:
                logger.error(f"无法将空的预处理结果保存到 '{output_file_path}': {e}")
            continue


        max_workers = os.cpu_count() - 2 if os.cpu_count() and os.cpu_count() > 2 else 1 # 合理设置工作进程数
        logger.info(f"正在为模型 '{model_name}' 处理 {num_items} 个 (已预处理的) 项目，最多使用 {max_workers} 个工作进程。")

        futures_map = {} # 用于存储future对象和它们的原始索引
        # 注意：传递给 ProcessPoolExecutor 的 data_items 已经是预处理过的
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            for i, item in enumerate(data_items): # item 是预处理过的
                if not isinstance(item, dict):
                    logger.warning(f"正在跳过文件 '{output_file_path}' 中索引为 {i} 的项目 (预处理后)，因为它不是一个字典。")
                    # 为非字典项创建占位符，以保持顺序和结构一致性
                    processed_item_with_error_placeholder = {
                        "original_item_index": i, # 记录原始索引
                        "error_message": "项目在预处理后不是一个字典。",
                        "evaluation_scores": { # 提供默认的错误评估分数
                            "subject_accuracy": 0.0, "condition_accuracy": 0.0, "constraint_accuracy": 0.0,
                            "final_decision_accuracy": 0.0, # 新增
                            "final_decision_pass_0.99": False, # 新增
                            "final_decision_pass_0.95": False, # 新增
                            "codebleu": 0.0, "ngram_match_score": 0.0, "weighted_ngram_match_score": 0.0,
                            "syntax_match_score": 0.0, "dataflow_match_score": 0.0,
                            "execution_status_gold": "非字典项",
                            "execution_status_gen": "非字典项",
                            "error_message_gold": "项目不是一个字典。",
                            "error_message_gen": "项目不是一个字典。",
                            "codebleu_error_message": "项目不是一个字典，无法计算CodeBLEU。"
                        }
                    }
                    # 如果需要保留原始项目（即使不是字典），可能需要复制它，但那样它就不会有 evaluation_scores。
                    # 为了保持一致性，我们使用带有错误分数的占位符。
                    futures_map[i] = processed_item_with_error_placeholder # 使用索引作为键，值为预处理过的项目
                    continue
                # process_single_item 会接收预处理过的 item
                future = executor.submit(process_single_item, item, model_name, i)
                futures_map[future] = i # 使用future对象作为键，值为原始索引

            processed_items_ordered = [None] * num_items # 创建一个列表来按顺序存储处理结果

            # 分离出实际的future对象和那些直接存储结果的项（例如非字典项）
            actual_futures = {k: v for k, v in futures_map.items() if not isinstance(k, int)} # future对象作为键
            non_future_items_indices = {k:v for k,v in futures_map.items() if isinstance(k, int)} # 索引作为键

            # 首先填充那些不是future对象的项（例如，预处理后非字典的项）
            for original_idx, pre_processed_item_val in non_future_items_indices.items():
                 processed_items_ordered[original_idx] = pre_processed_item_val # pre_processed_item_val 是带有错误分数的占位符
                 logger.debug(f"模型 '{model_name}', 项目原始索引={original_idx} 不是future对象 (可能是非字典项目)，已保留其占位符。")

            progress_bar_desc = f"评估 {model_name} ({len(actual_futures)}/{num_items} 项)" # tqdm显示单个文件内项目处理进度
            for future_obj in tqdm(as_completed(actual_futures.keys()), total=len(actual_futures), desc=progress_bar_desc, unit="个项目"):
                original_idx = actual_futures[future_obj] # 获取原始索引
                try:
                    processed_item_result = future_obj.result() # result 基于预处理过的 item
                    processed_items_ordered[original_idx] = processed_item_result
                except Exception as e_future:
                    logger.error(f"模型 '{model_name}', 项目原始索引={original_idx} 的 future.result() 执行失败: {e_future}", exc_info=True)
                    # data_items[original_idx] 是预处理过的版本
                    original_item_with_error = data_items[original_idx].copy() if isinstance(data_items[original_idx], dict) else {"original_index": original_idx, "error": "原始项目 (预处理后) 不是一个字典"}

                    if isinstance(original_item_with_error, dict):
                        if 'evaluation_scores' not in original_item_with_error or not isinstance(original_item_with_error['evaluation_scores'], dict):
                            original_item_with_error['evaluation_scores'] = {}

                        # 确保在future处理错误时，所有分数都存在
                        original_item_with_error['evaluation_scores'].update({
                            "subject_accuracy": 0.0, "condition_accuracy": 0.0, "constraint_accuracy": 0.0,
                            "final_decision_accuracy": 0.0, # 新增
                            "final_decision_pass_0.99": False, # 新增
                            "final_decision_pass_0.95": False, # 新增
                            "codebleu": 0.0, "ngram_match_score": 0.0, "weighted_ngram_match_score": 0.0,
                            "syntax_match_score": 0.0, "dataflow_match_score": 0.0,
                            "execution_status_gold": "future处理错误",
                            "execution_status_gen": "future处理错误",
                            "error_message_gold": f"Future 处理错误: {str(e_future)}",
                            "error_message_gen": f"Future 处理错误: {str(e_future)}",
                            "codebleu_error_message": f"Future 处理错误导致无法计算 CodeBLEU: {str(e_future)}"
                        })
                    processed_items_ordered[original_idx] = original_item_with_error


            final_processed_items = processed_items_ordered # 这是评估了预处理数据后的结果
            # 检查是否有None占位符未被填充
            if any(item is None for item in final_processed_items):
                 logger.warning(f"模型 '{model_name}': 处理后的项目列表包含None值。这可能表示部分项目未能成功从future获取结果或被跳过。")
                 # 尝试用带有错误信息的原始预处理数据（如果可用）填充None值
                 for i, item_content in enumerate(final_processed_items):
                     if item_content is None:
                        logger.warning(f"模型 '{model_name}': 正在填充索引 {i} 处的 None 占位符。")
                        original_item_at_idx = data_items[i] if i < len(data_items) else {} # 获取预处理后的原始项
                        # 创建一个错误占位符结构
                        error_placeholder = original_item_at_idx.copy() if isinstance(original_item_at_idx, dict) else {"original_index": i, "error_message": "项目在最终收集中丢失或处理失败"}
                        if isinstance(error_placeholder, dict): # 确保是字典类型
                            if 'evaluation_scores' not in error_placeholder or not isinstance(error_placeholder['evaluation_scores'], dict):
                                error_placeholder['evaluation_scores'] = {} # 初始化评估分数
                            # 更新评估分数为错误状态
                            error_placeholder['evaluation_scores'].update({
                                "subject_accuracy": 0.0, "condition_accuracy": 0.0, "constraint_accuracy": 0.0,
                                "final_decision_accuracy": 0.0, "final_decision_pass_0.99": False, "final_decision_pass_0.95": False,
                                "codebleu": 0.0,
                                "execution_status_gold": "处理中丢失/失败",
                                "execution_status_gen": "处理中丢失/失败",
                                "error_message_gold": "项目在最终收集中丢失或处理失败",
                                "error_message_gen": "项目在最终收集中丢失或处理失败",
                                "codebleu_error_message": "项目在最终收集中丢失或处理失败"
                            })
                        final_processed_items[i] = error_placeholder


        try:
            # final_processed_items 包含了预处理和评估后的数据
            with open(output_file_path, 'w', encoding='utf-8') as f:
                json.dump(final_processed_items, f, indent=4, ensure_ascii=False) # 保存最终结果
            logger.info(f"已成功将预处理和评估后的结果保存到 '{output_file_path}'")
        except Exception as e:
            logger.error(f"无法将最终 JSON 保存到 '{output_file_path}': {e}")

    logger.info("所有模型均已处理完毕。")

if __name__ == '__main__':
    main()