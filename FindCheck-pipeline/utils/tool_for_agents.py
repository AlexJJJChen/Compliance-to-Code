import pandas as pd
from utils.call_gpt import call_gpt
import re

def llm_content_check(
    announcement_text: str, 
    traget_content: str,
) -> bool:
    """
    使用LLM检查公告中是否包含特定内容. 
    这里只是一个示例函数, 会永远返回True. 在生产环境中, 你可以自己拓展这个工具. 
    
    参数:
        announcement_text: 公告全文
        traget_content: 需要检查的内容描述
    返回:
        bool: 公告中是否包含特定内容
    """

    return True

    # 构造提示词
    prompt = f"""
    你是一位合规检查专家. 你的任务是阅读一个**公告**, 并判断其中是否包含我们想要寻找的**内容**. 如果其中确实有我们要的内容, 就回复True, 否则为False. 用<ANSWER></ANSWER>包裹你的最终答案. 

    # example: 
    ## 公告:
    "..., 所以我们的权益分派计划不会影响偿债能力; 过去十二个月, 我们没有使用过募集资金补充流动资金; 未来十二个月内, 我们不计划使用募集资金补充流动资金......"

    ## 我们关注的内容:
    "请判断该公告是否披露了过去十二个月内是否使用过募集资金"

    ## 回复:
    <ANSWER>True</ANSWER>

    # 下面轮到你来处理:

    ## 公告:
    {announcement_text}

    ## 我们关注的内容:
    {traget_content}

    请你开始回答, 并用<ANSWER></ANSWER>包裹你的答案:
    """
    
    content, reasoning_content, api_usage = call_gpt(
        prompt,
        model='qwen2.5:14b'
    )
    
    # 使用正则表达式提取<ANSWER>标签中的内容
    answer_match = re.search(r'<ANSWER>(.*?)</ANSWER>', content, re.IGNORECASE)
    if answer_match:
        answer = answer_match.group(1).strip()
        # 将字符串形式的布尔值转换为真正的布尔值
        if answer.lower() == 'true':
            return True
        elif answer.lower() == 'false':
            return False
        else:
            # 如果模型返回的不是True/False，可以记录日志或抛出异常
            print(f"警告: 模型返回了非预期的答案: {answer}")
            return False
    else:
        # 如果没有找到<ANSWER>标签，可以记录日志或抛出异常
        print("警告: 未在模型回复中找到<ANSWER>标签")
        return False


def llm_content_check_qwen(
    announcement_text: str, 
    traget_content: str,
) -> bool:
    """
    使用LLM检查公告中是否包含特定内容
    
    参数:
        announcement_text: 公告全文
        traget_content: 需要检查的内容描述
    返回:
        bool: 公告中是否包含特定内容
    """

    # 构造提示词
    prompt = f"""
    你是一位合规检查专家. 你的任务是阅读一个**公告**, 并判断其中是否包含我们想要寻找的**内容**. 如果其中确实有我们要的内容, 就回复True, 否则为False. 用<ANSWER></ANSWER>包裹你的最终答案. 

    # example: 
    ## 公告:
    "..., 所以我们的权益分派计划不会影响偿债能力; 过去十二个月, 我们没有使用过募集资金补充流动资金; 未来十二个月内, 我们不计划使用募集资金补充流动资金......"

    ## 我们关注的内容:
    "请判断该公告是否披露了过去十二个月内是否使用过募集资金"

    ## 回复:
    <ANSWER>True</ANSWER>

    # 下面轮到你来处理:

    ## 公告:
    {announcement_text}

    ## 我们关注的内容:
    {traget_content}

    请你开始回答, 并用<ANSWER></ANSWER>包裹你的答案:
    """
    
    content, reasoning_content, api_usage = call_gpt(
        prompt,
        model='qwen2.5:14b'
    )
    
    # 使用正则表达式提取<ANSWER>标签中的内容
    answer_match = re.search(r'<ANSWER>(.*?)</ANSWER>', content, re.IGNORECASE)
    if answer_match:
        answer = answer_match.group(1).strip()
        # 将字符串形式的布尔值转换为真正的布尔值
        if answer.lower() == 'true':
            return True
        elif answer.lower() == 'false':
            return False
        else:
            # 如果模型返回的不是True/False，可以记录日志或抛出异常
            print(f"警告: 模型返回了非预期的答案: {answer}")
            return False
    else:
        # 如果没有找到<ANSWER>标签，可以记录日志或抛出异常
        print("警告: 未在模型回复中找到<ANSWER>标签")
        return False
