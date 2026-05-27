# -*- coding: utf-8 -*-
"""
ReAct Agent —— Demo 06: Thought → Action → Observation 循环
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from demos_all.config import SYSTEM_PROMPT, LLM_CONFIG


class ReActAgent:
    """
    ReAct 循环引擎。
    知识点: Demo 06 — 多步推理, Thought→Action→Observation
    """

    def __init__(self, llm, tools, max_rounds: int = 5, verbose: bool = True):
        self.llm = llm
        self.tools = tools
        self.max_rounds = max_rounds
        self.verbose = verbose

    def run(self, user_input: str) -> tuple[str, list[dict]]:
        """返回 (最终回答, 追踪信息)"""
        trace = []
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ]

        for rnd in range(1, self.max_rounds + 1):
            openai_tools = self.tools.to_openai()
            resp = self._call_llm_with_tools(messages, openai_tools)
            msg = resp.choices[0].message

            if not msg.tool_calls:
                if self.verbose:
                    print(f"  [ReAct R{rnd}] → 最终回答")
                return msg.content, trace

            # 执行工具
            messages.append(msg)  # 先追加 assistant 消息（含 tool_calls）
            for tc in msg.tool_calls:
                name = tc.function.name
                args = json.loads(tc.function.arguments)
                result = self.tools.call(name, **args)
                if self.verbose:
                    print(f"  [ReAct R{rnd}] {name}({args}) → {result[:60]}...")
                trace.append({"round": rnd, "tool": name,
                              "args": args, "result": result[:100]})
                messages.append({"role": "tool", "tool_call_id": tc.id,
                                 "content": result})

        final = self.llm.chat(messages, profile="standard")
        return final, trace

    def _call_llm_with_tools(self, messages, tools):
        """调用 LLM（带 tools）"""
        params = {
            "model": LLM_CONFIG["model"],
            "messages": messages,
            "tools": tools,
            "temperature": 0.1,
        }
        return self.llm.client.chat.completions.create(**params)
