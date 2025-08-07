from openai import OpenAI


def ask_deepseekv3(prompt):
    client = OpenAI(
        # 尽量确保有免费资金覆盖. 截至20250717凌晨还有121.24元
        base_url="https://api.siliconflow.cn/v1",
        api_key="sk-pipazuclriqkgqmsvynzchmydwoaihibokomyvlzttcddghb"
    )
    # 硅基流动的, 截至20250717, 这个是DeepSeek-V3-0324
    model_id = "deepseek-ai/DeepSeek-V3"

    if isinstance(prompt, str):
        messages = [{"role": "user", "content": prompt}]
        completion = client.chat.completions.create(model=model_id, messages=messages, temperature=0, seed=1024, max_tokens=1024)
        return [completion.choices[0].message.content]

    elif isinstance(prompt, list):
        responses = []
        conversation = []
        for user_msg in prompt:
            conversation.append(user_msg)
            messages = [{"role": "user" if i % 2 == 0 else "assistant", "content": m} for i, m in enumerate(conversation)]
            completion = client.chat.completions.create(model=model_id, messages=messages, temperature=0, seed=1024, max_tokens=1024)
            reply = completion.choices[0].message.content
            conversation.append(reply)
            responses.append(reply)
        return responses