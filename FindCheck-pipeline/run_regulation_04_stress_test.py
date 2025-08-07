import pandas as pd
import numpy as np
import os
import json
import logging
from datetime import datetime
from test_compliance_graph_execution import test_graph_execution, setup_logging

# --- 配置 ---
NUM_RUNS = 100
REGULATION_ID = "regulation_04"
COMPANY_NAME = "祎煜环保"
BASE_DATA_PATH = os.path.join("data", "company_data", "data_simulate_股份回购_04.csv")
VIOLATION_DIR = os.path.join("results", "stress_test_violations")
FUZZ_FACTOR = 0.2  # 数据变异幅度（20%）
FUZZ_RATIO = 0.05 # 每次变异的数据行数比例（5%）

def fuzz_data(df: pd.DataFrame, fuzz_factor: float = FUZZ_FACTOR) -> pd.DataFrame:
    """
    对DataFrame中的数据进行随机变异（Fuzzing）。
    
    参数:
        df: 要变异的数据
        fuzz_factor: 变异幅度（0-1之间），默认为FUZZ_FACTOR
        
    返回:
        变异后的数据
    """
    fuzzed_df = df.copy()
    
    # 确定要变异的行
    num_rows_to_fuzz = int(len(fuzzed_df) * FUZZ_RATIO)
    if num_rows_to_fuzz == 0:
        num_rows_to_fuzz = 1 # 至少变异一行
    fuzz_indices = np.random.choice(fuzzed_df.index, size=num_rows_to_fuzz, replace=False)
    
    # 对关键财务数据列进行变异
    columns_to_fuzz = ['收盘价', '每股净资产', '成交量']
    
    for col in columns_to_fuzz:
        if col in fuzzed_df.columns:
            # 生成随机扰动
            perturbation = 1 + (np.random.rand(len(fuzz_indices)) - 0.5) * 2 * fuzz_factor
            original_values = fuzzed_df.loc[fuzz_indices, col].astype(float)
            fuzzed_df.loc[fuzz_indices, col] = original_values * perturbation
            
    return fuzzed_df

def run_stress_test(num_runs: int = NUM_RUNS, fuzz_factor: float = FUZZ_FACTOR):
    """
    执行针对股份回购的压力测试，并使用统一的日志记录。
    
    参数:
        num_runs: 运行次数，默认为NUM_RUNS
        fuzz_factor: 变异幅度，默认为FUZZ_FACTOR
    """
    # 统一设置日志
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, f"stress_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    logger = setup_logging(log_filename=log_file_path)
    
    logger.info("--- 开始股份回购（regulation_04）压力测试 ---")
    logger.info(f"运行次数: {num_runs}, 变异幅度: {fuzz_factor}")
    
    # 确保违规结果目录存在
    os.makedirs(VIOLATION_DIR, exist_ok=True)
    print(f"违规案例将保存在: {VIOLATION_DIR}")
    
    # 加载基础数据
    try:
        base_df = pd.read_csv(BASE_DATA_PATH, encoding='utf-8')
    except Exception as e:
        print(f"错误：无法加载基础数据文件 '{BASE_DATA_PATH}'. 错误信息: {e}")
        return
        
    violations_found = 0
    for i in range(num_runs):
        logger.info(f"\n>>> 正在运行测试 {i + 1}/{num_runs}...")
        
        # 1. 生成变异数据
        fuzzed_df = fuzz_data(base_df, fuzz_factor)
        
        # 2. 执行合规检查，禁止保存常规报告
        results = test_graph_execution(
            regulation_id=REGULATION_ID,
            company_name=COMPANY_NAME,
            save_chart=False,
            input_data=fuzzed_df,
            save_report=False 
        )
        
        # 3. 检查和报告违规
        if results and results.get('regulations', {}).get(REGULATION_ID, {}).get('total_violations', 0) > 0:
            violations_found += 1
            logger.info(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            logger.info(f"!!! ==> 在测试 {i + 1} 中发现违规！ <== !!!")
            logger.info(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            
            # 保存触发违规的数据和报告
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            data_filename = os.path.join(VIOLATION_DIR, f"violating_data_run_{i+1}_{timestamp}.csv")
            report_filename = os.path.join(VIOLATION_DIR, f"violating_report_run_{i+1}_{timestamp}.json")
            
            fuzzed_df.to_csv(data_filename, index=False, encoding='utf-8-sig')
            with open(report_filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"已保存违规数据至: {data_filename}")
            logger.info(f"已保存违规报告至: {report_filename}")
        else:
            logger.info(f"测试 {i + 1} 未发现违规。")

    logger.info("\n--- 压力测试完成 ---")
    logger.info(f"总运行次数: {num_runs}")
    logger.info(f"发现违规的次数: {violations_found}")
    
    return {
        "total_runs": num_runs,
        "violations_found": violations_found,
        "violation_rate": violations_found / num_runs if num_runs > 0 else 0
    }

if __name__ == "__main__":
    run_stress_test() 