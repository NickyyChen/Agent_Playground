"""
统一 LLM 调用客户端。
为什么不直接用 openai.OpenAI()：封装后所有 demo 共享同一个调用入口，
方便后续统一加日志、重试、cost 统计等横切逻辑，demo 只需 import 这一个函数。
"""
from openai import OpenAI
from shared.config import LLM_CONFIG

# 全局单例，避免每个 demo 重复创建连接
_client = OpenAI(api_key=LLM_CONFIG["api_key"], base_url=LLM_CONFIG["base_url"])


def chat(messages: list[dict], **kwargs) -> str:
    """
    发送对话请求，返回模型文本回复。

    messages: [{"role": "system"|"user"|"assistant", "content": "..."}, ...]
    kwargs:   透传给 API 的参数，如 temperature, top_p, max_tokens
    """
    params = {"model": LLM_CONFIG["model"], "messages": messages}
    params.update(kwargs)
    response = _client.chat.completions.create(**params)
    return response.choices[0].message.content


def create_completion(messages: list[dict], tools: list[dict] = None, **kwargs):
    """
    返回原始 completion 对象，供 demo 自行处理 tool_calls。
    WHY: Function Calling 需要拿到 message.tool_calls 来判断
         模型是否想调用工具，而 chat() 只返回纯文本，不够用。
    """
    params = {"model": LLM_CONFIG["model"], "messages": messages}
    if tools:
        params["tools"] = tools
    params.update(kwargs)
    return _client.chat.completions.create(**params)
