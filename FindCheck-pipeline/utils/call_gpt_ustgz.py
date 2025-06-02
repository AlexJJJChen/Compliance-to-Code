import json
import re
import asyncio
import aiohttp
from typing import Tuple, Dict, Any
import requests
import pandas as pd
import os

# ==============================================================================
# 用户配置区域 START
# 请在此处填入您的 API Key 和 Base URL
# ==============================================================================
API_KEY = "YOUR_API_KEY_HERE"  # 请替换为您的 API Key
BASE_URL = "YOUR_BASE_URL_HERE"  # 例如: "https://api.example.com/v1/chat/completions"
# 确保URL是完整的，包括 "/v1/chat/completions" 或类似的端点路径
# ==============================================================================
# 用户配置区域 END
# ==============================================================================

# 检查用户是否已配置
if API_KEY == "YOUR_API_KEY_HERE" or BASE_URL == "YOUR_BASE_URL_HERE" or not BASE_URL.startswith("http"):
    print("错误：请先在脚本顶部正确配置您的 API_KEY 和 BASE_URL。")
    print("API_KEY 不应为 'YOUR_API_KEY_HERE'。")
    print("BASE_URL 不应为 'YOUR_BASE_URL_HERE' 且应以 http 或 https 开头。")
    exit()

def _split_reason_and_content(response_content: str) -> Tuple[str, str]:
    """
    从模型返回内容中分离思考过程 (reasoning_content) 和最终回复 (content)
    
    参数:
        response_content (str): 模型返回的原始字符串内容
        
    返回:
        Tuple[str, str]: 一个包含 (思考过程, 最终回复) 的元组
    """
    # 匹配 <think> 标签内容（支持跨行匹配）
    reason_match = re.search(r'<think>(.*?)</think>', response_content, re.DOTALL)
    
    reasoning_content = ""
    content = response_content
    
    if reason_match:
        # 提取思考内容并去除首尾空白
        reasoning_content = reason_match.group(1).strip()
        
        # 分离最终回复内容（排除 <think> 部分）
        content = re.sub(r'<think>.*?</think>', '', response_content, flags=re.DOTALL).strip()
    
    return reasoning_content, content


def call_gpt(prompt: str) -> Tuple[str, str, Dict[str, Any]]:
    """
    同步调用 GPT API 获取内容
    
    参数:
        prompt (str): 输入给模型的提示
        
    返回:
        Tuple[str, str, Dict[str, Any]]: 一个包含 (最终回复, 思考过程, API使用情况) 的元组
        
    异常:
        requests.exceptions.RequestException: 如果HTTP请求发生错误
        json.JSONDecodeError: 如果响应无法解析为JSON
        KeyError: 如果响应中缺少预期的键
    """
    headers = { 
        "Content-Type": "application/json", 
        "Authorization": f"Bearer {API_KEY}"
    }
    data = { 
        "model": "DeepSeek-R1-671B",  # 您可以根据需要修改或将其也设为可配置项
        "messages": [{"role": "user", "content": prompt}], 
        "temperature": 0,
    }
    response = requests.post(BASE_URL, headers=headers, data=json.dumps(data))
    response.raise_for_status()  # 如果请求失败 (状态码 4xx 或 5xx), 则抛出 HTTPError
    
    response_json = response.json()
    raw_content = response_json['choices'][0]['message']['content']
    reasoning_content, content = _split_reason_and_content(raw_content)
    api_usage = response_json['usage']

    return content, reasoning_content, api_usage


async def call_gpt_async(prompt: str) -> Tuple[str, str, Dict[str, Any]]:
    """
    异步调用 GPT API 获取内容
    
    参数:
        prompt (str): 输入给模型的提示
        
    返回:
        Tuple[str, str, Dict[str, Any]]: 一个包含 (最终回复, 思考过程, API使用情况) 的元组
        
    异常:
        aiohttp.ClientError: 如果HTTP请求发生错误
        json.JSONDecodeError: 如果响应无法解析为JSON
        KeyError: 如果响应中缺少预期的键
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    data = {
        "model": "DeepSeek-R1-671B",  # 您可以根据需要修改或将其也设为可配置项
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(BASE_URL, headers=headers, json=data) as response:
            response.raise_for_status() # 如果请求失败 (状态码 4xx 或 5xx), 则抛出 ClientResponseError
            
            response_json = await response.json()
            
            raw_content = response_json['choices'][0]['message']['content']
            reasoning_content, content = _split_reason_and_content(raw_content)
            api_usage = response_json['usage']
            
            return content, reasoning_content, api_usage

# 示例用法 (异步)
async def main_async_example():
    print("正在运行异步 API 调用示例...")
    try:
        content, reasoning, usage = await call_gpt_async("写一句赞美程序员的话，包含思考过程。例如：<think>我应该思考一下程序员的日常...</think> 最终回复内容。")
        print(f"\n--- 异步调用结果 ---")
        if reasoning:
            print(f"思考过程:\n{reasoning}")
        print(f"最终回复:\n{content}")
        print(f"API 使用情况: {usage}")
    except Exception as e:
        print(f"异步调用时发生错误: {e}")

# 示例用法 (同步)
def main_sync_example():
    print("\n正在运行同步 API 调用示例...")
    try:
        content, reasoning, usage = call_gpt("用Python写一个快速排序算法，包含思考过程。例如：<think>快速排序的关键是分区...</think> 最终代码。")
        print(f"\n--- 同步调用结果 ---")
        if reasoning:
            print(f"思考过程:\n{reasoning}")
        print(f"最终回复:\n{content}")
        print(f"API 使用情况: {usage}")
    except Exception as e:
        print(f"同步调用时发生错误: {e}")


def read_table_file(file_path: str) -> pd.DataFrame:
    """
    自动识别并读取Excel或CSV文件，返回pandas DataFrame
    
    参数:
        file_path (str): 文件的完整路径
        
    返回:
        pandas.DataFrame: 读取的数据表
        
    异常:
        ValueError: 当文件格式不支持时抛出
        FileNotFoundError: 当文件不存在时抛出
    """
    # 检查文件是否存在
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    # 获取文件扩展名（转换为小写以便比较）
    file_extension = os.path.splitext(file_path)[1].lower()
    
    try:
        # Excel文件 (.xlsx, .xls)
        if file_extension in ['.xlsx', '.xls']:
            return pd.read_excel(file_path)
            
        # CSV文件 (.csv)
        elif file_extension == '.csv':
            # 尝试不同的编码方式读取
            encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16']
            for encoding in encodings:
                try:
                    return pd.read_csv(file_path, encoding=encoding)
                except UnicodeDecodeError:
                    continue
            # 如果所有编码都失败，则抛出错误
            raise ValueError(f"无法以任何支持的编码方式（utf-8, gbk, gb2312, utf-16）读取CSV文件: {file_path}。请检查文件编码。")
            
        else:
            raise ValueError(f"不支持的文件格式: {file_extension}。仅支持 .xlsx, .xls, .csv 文件。")
            
    except Exception as e:
        # 避免捕获上面 ValueError 后再次包装，使得错误信息更清晰
        if isinstance(e, (FileNotFoundError, ValueError)):
            raise
        raise Exception(f"读取文件 '{file_path}' 时发生未知错误: {str(e)}")


if __name__ == "__main__":
    # 运行异步示例
    asyncio.run(main_async_example())
    
    # 分隔线，让输出更清晰
    print("\n" + "="*50 + "\n")
    
    # 运行同步示例
    main_sync_example()