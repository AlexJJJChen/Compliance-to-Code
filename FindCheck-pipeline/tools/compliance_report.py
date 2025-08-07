#!/usr/bin/env python3
"""
合规报告生成工具

主要功能：
1. 读取合规检查结果（result.json和processed_result.json）
2. 使用LLM生成Markdown格式的合规报告
3. 将报告保存到results目录中对应的检查结果文件夹
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# 导入LLM调用工具
from tools.call_gpt import ask_deepseekv3

# 设置日志记录器
logger = logging.getLogger("compliance_report")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def create_report_prompt(data: Dict[str, Any]) -> str:
    """
    创建用于生成合规报告的提示词
    
    参数:
        data: 处理后的合规检查结果数据
        
    返回:
        生成提示词
    """
    metadata = data.get("metadata", {})
    company_name = metadata.get("company_name", "未知公司")
    regulation_name = metadata.get("regulation_name", "未知法规")
    date_range = metadata.get("date_range", ["", ""])
    
    # 获取最终合规状态
    final_status = data.get("final_compliance_status", {})
    violation_count = final_status.get("violation_count", 0)
    success_count = final_status.get("success_count", 0)
    excluded_count = final_status.get("excluded_count", 0)
    
    # 获取违规单元的详细信息
    violations = []
    results = data.get("results", {})
    compliance_units = results.get("compliance_units", {})
    
    for unit_id, unit_data in compliance_units.items():
        if unit_data.get("final_status") == "violation":
            unit_info = {
                "id": unit_id,
                "subject": unit_data.get("subject", "未提供"),
                "condition": unit_data.get("condition", "未提供"),
                "constraint": unit_data.get("constraint", "未提供"),
                "details": unit_data.get("evaluation_details", [])
            }
            violations.append(unit_info)
    
    # 构建提示词
    current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
    prompt = f"""
你是一位专业的金融合规分析师。请根据以下金融合规检查的结果，生成一份详细的Markdown格式合规报告。

## 基本信息
- 公司名称: {company_name}
- 法规名称: {regulation_name}
- 检查时间范围: {date_range[0] or "无起始日期"} 至 {date_range[1] or "无结束日期"}
- 报告生成时间: {current_time}

## 检查结果摘要
- 违规数量: {violation_count}
- 合规数量: {success_count}
- 排除数量: {excluded_count}

## 违规详情
"""
    
    # 添加前三个违规单元的详细信息
    top_violations = violations[:3]
    for i, violation in enumerate(top_violations):
        prompt += f"""
### 违规 {i+1}: {violation['id']}

- **Subject (适用主体)**: {violation['subject']}
- **Condition (触发条件)**: {violation['condition']}
- **Constraint (约束条件)**: {violation['constraint']}

#### 违规记录:
"""
        # 添加前三条记录
        details = violation.get("details", [])
        for j, detail in enumerate(details[:3]):
            date_str = detail.get("日期", "未知日期")
            subject_passed = "是" if detail.get("_subject_passed", False) else "否"
            condition_passed = "是" if detail.get("_condition_passed", False) else "否"
            constraint_passed = "是" if detail.get("_constraint_passed", False) else "否"
            
            prompt += f"""
- **记录 {j+1}** (日期: {date_str})
  - Subject通过: {subject_passed}
  - Condition通过: {condition_passed}
  - Constraint通过: {constraint_passed}
"""
        
        if len(details) > 3:
            prompt += f"\n*注: 共有 {len(details)} 条违规记录，上面只显示前3条。*\n"
    
    prompt += """
## 请求任务
请基于上述信息生成一份专业的合规报告，包括以下部分：

1. **报告标题和摘要**：简明扼要地概述公司合规状况
2. **检查背景**：包括公司名称、适用法规和检查时间范围
3. **合规状况分析**：详细分析违规情况，包括违规单元数量和类型
4. **具体违规案例**：详细描述发现的前几个违规案例，分析违约原因
5. **建议和改进措施**：针对发现的问题提出具体的改进建议
6. **结论**：总结报告发现并提出合规管理的总体建议

请确保报告专业、客观、准确，并提供具体的分析而非泛泛而谈。使用Markdown格式，包括适当的标题层级、列表和强调。
"""
    
    return prompt


def generate_compliance_report(result_folder_path: str) -> Optional[str]:
    """
    为指定结果文件夹生成合规报告
    
    参数:
        result_folder_path: 结果文件夹路径
        
    返回:
        生成的报告内容，如果失败则返回None
    """
    try:
        # 构建processed_result.json路径
        processed_result_path = os.path.join(result_folder_path, "processed_result.json")
        
        # 如果processed_result.json不存在，尝试使用result.json
        if not os.path.exists(processed_result_path):
            processed_result_path = os.path.join(result_folder_path, "result.json")
            if not os.path.exists(processed_result_path):
                logger.error(f"无法找到结果文件: {result_folder_path}")
                return None
        
        # 读取结果数据
        with open(processed_result_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 创建提示词
        prompt = create_report_prompt(data)
        
        # 调用LLM生成报告
        logger.info(f"正在为 {os.path.basename(result_folder_path)} 生成合规报告...")
        response = ask_deepseekv3(prompt)
        
        if response and isinstance(response, list) and len(response) > 0:
            report_content = response[0]
            
            # 保存报告到文件
            report_path = os.path.join(result_folder_path, "compliance_report.md")
            # 确保report_content是字符串
            if report_content is not None:
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(report_content)
            
            logger.info(f"合规报告已生成并保存到: {report_path}")
            return report_content
        else:
            logger.error("LLM未返回有效响应")
            return None
    
    except Exception as e:
        logger.error(f"生成合规报告时出错: {e}")
        return None


def get_report_for_result(result_path: str) -> Optional[str]:
    """
    获取指定结果的报告内容，如果报告不存在则生成
    
    参数:
        result_path: 结果文件夹路径（相对于results目录）
        
    返回:
        报告内容，如果失败则返回None
    """
    try:
        # 构建完整路径
        full_result_path = os.path.join(project_root, "results", result_path)
        
        # 检查报告是否已存在
        report_path = os.path.join(full_result_path, "compliance_report.md")
        if os.path.exists(report_path):
            # 如果报告已存在，直接读取
            with open(report_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            # 如果报告不存在，生成新报告
            return generate_compliance_report(full_result_path)
    
    except Exception as e:
        logger.error(f"获取报告时出错: {e}")
        return None


if __name__ == "__main__":
    """
    命令行测试入口
    
    用法：python -m tools.compliance_report <result_folder_path>
    """
    if len(sys.argv) != 2:
        print("用法: python -m tools.compliance_report <result_folder_name>")
        sys.exit(1)
    
    result_folder = sys.argv[1]
    full_path = os.path.join(project_root, "results", result_folder)
    
    if not os.path.exists(full_path):
        print(f"错误: 结果文件夹不存在: {full_path}")
        sys.exit(1)
    
    report = generate_compliance_report(full_path)
    if report:
        print(f"报告生成成功！长度: {len(report)} 字符")
        print("前500个字符预览:")
        print(report[:500] + "...")
    else:
        print("报告生成失败。") 