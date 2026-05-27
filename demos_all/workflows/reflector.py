# -*- coding: utf-8 -*-
"""
Reflection Agent —— Demo 08: Generate → Reflect → Revise
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from demos_all.config import SYSTEM_PROMPT


class ReflectionAgent:
    """
    Reflection 循环：生成回答 → 自我审查 → 修正。
    知识点: Demo 08 — 自我反思 + 多轮修正 + 质检维度
    """

    def __init__(self, llm, max_rounds: int = 2, verbose: bool = True):
        self.llm = llm
        self.max_rounds = max_rounds
        self.verbose = verbose

    def run(self, user_input: str) -> dict:
        """返回 {"draft", "reflections": [...], "final"}"""
        # ─── 第 1 次生成 ──────────────────────
        draft = self.llm.chat([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ])
        if self.verbose:
            print(f"  [Draft] {draft[:80]}...")

        # ─── Reflection 循环 ──────────────────
        current = draft
        reflections = []
        for rnd in range(1, self.max_rounds + 1):
            critique = self._reflect(current)
            if self.verbose:
                print(f"  [Reflect R{rnd}] {critique[:80]}...")
            reflections.append(critique)
            if "NO_ISSUES" in critique.upper():
                break
            current = self._revise(user_input, current, critique)
            if self.verbose:
                print(f"  [Revise R{rnd}] {current[:80]}...")

        return {"draft": draft, "reflections": reflections, "final": current}

    def _reflect(self, answer: str) -> str:
        """审查回答，从 5 个维度检查"""
        return self.llm.chat([
            {"role": "system",
             "content": """审查以下客服回答，从准确性/完整性/清晰度/语气/合规性 5 维度检查。
输出具体问题。无问题输出 NO_ISSUES。"""},
            {"role": "user", "content": answer},
        ], profile="fast")

    def _revise(self, question: str, original: str, critique: str) -> str:
        """基于审查意见修正回答"""
        return self.llm.chat([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",
             "content": f"原问题: {question}\n原回答: {original}\n"
                        f"问题清单: {critique}\n请输出修正后的回答。"},
        ], profile="standard")
