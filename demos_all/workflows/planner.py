# -*- coding: utf-8 -*-
"""
Plan & Execute Agent —— Demo 07: 先规划 → 再执行 → 汇总
"""

import sys, os, re, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from demos_all.config import SYSTEM_PROMPT


class PlanExecuteAgent:
    """
    Plan & Execute 引擎。
    知识点: Demo 07 — 规划阶段 + 执行阶段 + 汇总阶段
    """

    def __init__(self, llm, tools, verbose: bool = True):
        self.llm = llm
        self.tools = tools
        self.verbose = verbose

    def run(self, user_input: str) -> dict:
        """返回 {"plan": [...], "steps": [...], "answer": str}"""
        # ─── 阶段 1: 规划 ──────────────────────
        plan = self._plan(user_input)
        if self.verbose:
            print(f"  [Plan] {len(plan)} 步: {[p['tool'] for p in plan]}")

        # ─── 阶段 2: 执行 ──────────────────────
        steps = []
        context = {}
        for i, step in enumerate(plan):
            tool_name = step["tool"]
            args = step.get("arguments", {})
            # 从 context 中解析占位参数
            for k, v in list(args.items()):
                if isinstance(v, str) and ("需要" in v or "待填" in v):
                    if k in context:
                        args[k] = context[k]
            result = self.tools.call(tool_name, **args)
            if self.verbose:
                print(f"  [Exec {i+1}] {tool_name}({args}) → {result[:60]}...")
            steps.append({"tool": tool_name, "args": args, "result": result})
            try:
                parsed = json.loads(result)
                if isinstance(parsed, dict):
                    context.update(parsed)
            except Exception:
                pass

        # ─── 阶段 3: 汇总 ──────────────────────
        steps_text = "\n".join(
            f"[{s['tool']}] {s['result'][:200]}" for s in steps
        )
        answer = self.llm.chat([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",
             "content": f"用户问题: {user_input}\n执行结果:\n{steps_text}\n请汇总回答。"},
        ], profile="standard")

        return {"plan": plan, "steps": steps, "answer": answer}

    def _plan(self, user_input: str) -> list[dict]:
        """LLM 生成计划"""
        tools_desc = "\n".join(
            f"- {t['name']}: {t['description']} "
            f"参数:{list(t.get('inputSchema', t.get('input_schema', {})).get('properties', {}).keys())}"
            for t in self.tools.to_mcp_tools()
        )
        reply = self.llm.chat([
            {"role": "system",
             "content": f"你是任务规划器。根据用户需求列出执行计划。\n可用工具:\n{tools_desc}\n\n"
                        f"输出格式(每行一个步骤):\n"
                        f"STEP N: tool_name(param=value, ...) | 说明"},
            {"role": "user", "content": user_input},
        ], profile="fast")

        steps = []
        pattern = r"STEP\s*\d*:\s*(\w+)\(([^)]*)\)"
        for func_name, args_str in re.findall(pattern, reply):
            args = {}
            if args_str.strip():
                for part in args_str.split(","):
                    if "=" in part:
                        k, v = part.split("=", 1)
                        args[k.strip()] = v.strip().strip("'\"")
            steps.append({"tool": func_name, "arguments": args})
        return steps
