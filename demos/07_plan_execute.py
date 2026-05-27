# -*- coding: utf-8 -*-
"""
07_plan_execute.py — Plan & Execute Agent：先规划，再执行
=========================================================

【概念】
Plan & Execute（规划-执行）是另一种 Agent 工作模式，与 ReAct 形成对比：

  ReAct（Demo 06）：一步一想，边走边看
                    思考→行动→观察→再思考→...
                    灵活，但可能绕弯路

  Plan & Execute：   先出完整计划，再逐条执行
                    规划→执行→汇总
                    清晰，适合已知步骤的复杂任务

类比：ReAct 是"走迷宫"，每步看前方再决定方向；
      Plan & Execute 是"看地图规划路线"，然后按路线走。

【在智能客服中解决什么问题】
用户经常一个对话里包含多个请求，比如：
"帮我查订单状态、确认能不能退货、再查一下优惠券——
哦对了，我上次反馈的问题有进展吗？"
P&E Agent 会先梳理出 4 个独立任务，列出执行计划，再逐一完成，
最后汇总成清晰的结构化回复——不会漏掉任何一个请求。

【核心流程】
1. 规划阶段（Planner）：LLM 分析用户输入，输出结构化的任务清单
2. 执行阶段（Executor）：按顺序执行每个任务，收集结果
3. 汇总阶段（Aggregator）：LLM 综合所有结果，生成最终回答

【pip install】
pip install openai

【ASCII 架构图】

   用户复杂请求（含多个子任务）
        │
        ▼
  ┌─────────────────────────────┐
  │       ① 规划阶段 (Planner)    │
  │                              │
  │  分析 → 拆解 → 输出计划清单:    │
  │  [STEP1: 查订单 ORD001]       │
  │  [STEP2: 查退货政策 耳机]      │
  │  [STEP3: 查物流 YT9876]       │
  │  [STEP4: 查优惠券]            │
  └──────────┬──────────────────┘
             │
             ▼
  ┌─────────────────────────────┐
  │      ② 执行阶段 (Executor)    │
  │                              │
  │  STEP1 → result1             │
  │  STEP2 → result2             │
  │  STEP3 → result3             │
  │  STEP4 → result4             │
  └──────────┬──────────────────┘
             │
             ▼
  ┌─────────────────────────────┐
  │     ③ 汇总阶段 (Aggregator)   │
  │                              │
  │  综合所有结果 → 结构化回答      │
  └─────────────────────────────┘

  对比 ReAct（06）：         本模式 P&E（07）：
  ┌────┐                    ┌────────────┐
  │思考│→行动→观察            │ 规划1,2,3,4 │
  │ ↑      │                │    ↓↓↓↓     │
  │ └──决策─┘                │  执行执行执行  │
  │ 每步决策                  │    ↓       │
  │ 灵活但不可预测             │  汇总回答    │
  └──────────┘              │ 清晰但灵活性低 │
                            └────────────┘
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import json, re
from shared.llm_client import chat, create_completion
from shared.mock_data import MOCK_ORDERS, MOCK_LOGISTICS, RETURN_POLICY


# ══════════════════════════════════════════════════════════════
# 工具集（与 Demo 06 共用同一套工具函数）
# ══════════════════════════════════════════════════════════════

def query_order(order_id: str) -> str:
    order = MOCK_ORDERS.get(order_id)
    if not order:
        return f"订单 {order_id} 不存在"
    return json.dumps(order, ensure_ascii=False, indent=2)


def query_logistics(tracking_no: str) -> str:
    info = MOCK_LOGISTICS.get(tracking_no)
    if not info:
        return f"快递 {tracking_no} 暂无物流记录"
    return json.dumps(info, ensure_ascii=False, indent=2)


def check_return_policy(category: str = "") -> str:
    if category:
        return f"'{category}'品类政策：\n{RETURN_POLICY}"
    return RETURN_POLICY


def query_coupons(user_name: str = "") -> str:
    """查询用户可用优惠券"""
    coupons = {
        "小明": [
            {"name": "首单9折券", "discount": "9折", "min_amount": 0,
             "expire": "2026-06-30"},
            {"name": "耳机专区满299减30", "discount": "减30元",
             "min_amount": 299, "expire": "2026-05-31"},
        ],
        "李总": [
            {"name": "会员专享8折券", "discount": "8折", "min_amount": 500,
             "expire": "2026-12-31"},
        ],
    }
    user_coupons = coupons.get(user_name, [])
    if not user_coupons:
        return f"用户 {user_name} 暂无可用优惠券"
    return json.dumps(user_coupons, ensure_ascii=False, indent=2)


TOOL_FUNCTIONS = {
    "query_order": query_order,
    "query_logistics": query_logistics,
    "check_return_policy": check_return_policy,
    "query_coupons": query_coupons,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_order",
            "description": "查询订单：参数 order_id",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_logistics",
            "description": "查询物流：参数 tracking_no",
            "parameters": {
                "type": "object",
                "properties": {"tracking_no": {"type": "string"}},
                "required": ["tracking_no"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_return_policy",
            "description": "查询退换货政策：可选参数 category",
            "parameters": {
                "type": "object",
                "properties": {"category": {"type": "string"}},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_coupons",
            "description": "查询用户可用优惠券：参数 user_name",
            "parameters": {
                "type": "object",
                "properties": {"user_name": {"type": "string"}},
                "required": ["user_name"]
            }
        }
    },
]


# ══════════════════════════════════════════════════════════════
# Plan & Execute 引擎
# ══════════════════════════════════════════════════════════════

PLANNER_SYSTEM = """你是智能客服的任务规划器。用户会提出一个或多个客服需求，
你需要将其拆解为可执行的任务清单。

输出格式（严格遵守）：
[PLAN]
STEP 1: function_name(param=value) | 这一步做什么
STEP 2: function_name(param=value) | 这一步做什么
...

可用工具：
- query_order(order_id) — 查订单
- query_logistics(tracking_no) — 查物流
- check_return_policy(category) — 查退换货政策
- query_coupons(user_name) — 查优惠券

规则：
- 每个 STEP 只能调用一个工具
- 如果用户没提供某个参数（如快递单号），不要自己编造，在说明中注明"需要用户提供"
- 按依赖关系排序：先查订单（可能得到用户名和快递单），再查其他
- 用户只闲聊不涉及工具时，输出 NO_PLAN"""

EXECUTOR_SYSTEM = """你是智能客服的回答汇总器。以下是用户的问题和各个工具的执行结果，
请综合所有信息，给出清晰的结构化回答。

要求：
- 每个任务的结果都要覆盖到，不要遗漏
- 用分段或小标题区分不同主题
- 工具查不到的信息诚实告知"""


def parse_plan(plan_text: str) -> list[dict]:
    """
    解析规划器输出的计划文本，提取每步的工具名和参数。
    WHY: 规划器输出的格式是 "STEP N: func(k=v) | 说明"，
         这里用正则提取函数名和参数字典，转为可执行的结构。
    """
    steps = []
    # WHY: 匹配 "STEP N: func(k=v, k2=v2)" 格式，
    #      捕获组1=函数名, 捕获组2=参数字符串
    pattern = r"STEP\s*\d+:\s*(\w+)\(([^)]*)\)"
    matches = re.findall(pattern, plan_text)
    for func_name, args_str in matches:
        args = {}
        if args_str.strip():
            for part in args_str.split(","):
                if "=" in part:
                    k, v = part.split("=", 1)
                    args[k.strip()] = v.strip().strip("'\"")
        steps.append({"function": func_name, "arguments": args})
    return steps


def plan_and_execute(user_question: str, verbose: bool = True):
    """
    Plan & Execute 的主流程：规划 → 执行 → 汇总。
    """
    # ─── 阶段1：规划 ─────────────────────────────────
    if verbose:
        print("╔══════════════════════════════════════════════╗")
        print("║  阶段1：规划 (Planner)                         ║")
        print("╚══════════════════════════════════════════════╝")

    plan_response = chat([
        {"role": "system", "content": PLANNER_SYSTEM},
        {"role": "user", "content": user_question},
    ])

    if verbose:
        print(f"  LLM 规划输出:\n{plan_response}\n")

    if "NO_PLAN" in plan_response:
        # WHY: 无需工具调用 → 直接让 LLM 聊天回答
        reply = chat([
            {"role": "system",
             "content": "你是小选，好买电商智能客服，回答简洁专业。"},
            {"role": "user", "content": user_question},
        ])
        print(f"  无需工具，直接回答: {reply}")
        return

    steps = parse_plan(plan_response)
    if not steps:
        print("  ⚠ 未能解析出有效计划，降级为直接回答")
        reply = chat([
            {"role": "system",
             "content": "你是小选，好买电商智能客服，回答简洁专业。"},
            {"role": "user", "content": user_question},
        ])
        print(f"  客服: {reply}")
        return

    # ─── 阶段2：执行 ─────────────────────────────────
    if verbose:
        print("╔══════════════════════════════════════════════╗")
        print("║  阶段2：执行 (Executor)                        ║")
        print("╚══════════════════════════════════════════════╝")

    execution_results = []
    # WHY: context 累积已执行步骤的结果，用于后续步骤的参数替换——
    #      例如 STEP1 查出订单里 user_name="小明"，
    #      STEP2 的 user_name 参数可以自动填入"小明"而非占位符
    context = {}

    for i, step in enumerate(steps):
        func_name = step["function"]
        args = step["arguments"]

        # WHY: 动态参数解析 —— Planner 输出的计划中，依赖上一步结果的参数
        #      会用占位符表示（如"需要用户提供"、"需要从上一步获取"），
        #      执行阶段自动从前面步骤的 JSON 结果中提取对应字段填入。
        for k, v in list(args.items()):
            if isinstance(v, str) and any(
                kw in v for kw in ["需要", "待填", "从上一步", "placeholder",
                                    "TODO", "待获取", "未知"]):
                # 从 context（扁平 dict）中按参数名直接查找匹配字段
                if k in context:
                    args[k] = str(context[k])
                    if verbose:
                        print(f"  [自动填充] {k}={args[k]}"
                              f" (来自上一步结果)")
                elif k.replace("user_", "") in context:
                    # 兼容 user_name → name 的变体
                    args[k] = str(context[k.replace("user_", "")])
                    if verbose:
                        print(f"  [自动填充] {k}={args[k]}"
                              f" (来自上一步结果)")

        fn = TOOL_FUNCTIONS.get(func_name)

        if fn:
            try:
                result = fn(**args)
            except Exception as e:
                result = f"执行失败: {e}"
        else:
            result = f"未知工具: {func_name}"

        # WHY: 解析 JSON 结果，把关键字段注入 context 供后续步骤使用
        try:
            parsed = json.loads(result)
            if isinstance(parsed, dict):
                context.update(parsed)
        except (json.JSONDecodeError, TypeError):
            pass

        if verbose:
            print(f"  [{i+1}/{len(steps)}] {func_name}({args})")
            short = result[:100].replace("\n", " ")
            print(f"        → {short}...\n")

        execution_results.append({
            "step": i + 1,
            "function": func_name,
            "args": args,
            "result": result,
        })

    # ─── 阶段3：汇总 ─────────────────────────────────
    if verbose:
        print("╔══════════════════════════════════════════════╗")
        print("║  阶段3：汇总 (Aggregator)                      ║")
        print("╚══════════════════════════════════════════════╝")

    results_text = "\n\n".join(
        f"[任务{r['step']}] {r['function']}({r['args']})\n结果: {r['result']}"
        for r in execution_results
    )

    final_reply = chat([
        {"role": "system", "content": EXECUTOR_SYSTEM},
        {"role": "user",
         "content": f"用户问题:\n{user_question}\n\n任务执行结果:\n{results_text}"},
    ])

    print(f"  汇总回答:\n{final_reply}\n")


# ══════════════════════════════════════════════════════════════
# 演示函数
# ══════════════════════════════════════════════════════════════

def demo_plan_execute_basic():
    """
    演示1：P&E 处理多任务复杂请求。
    WHY: 用户一次提出 3 个不相关的请求（订单状态+退货政策+物流），
         P&E 先列出 3 步计划，再逐一执行，最后汇总——
         保证每个请求都被处理，不会遗漏。
    """
    print("=" * 60)
    print(" 演示1：Plan & Execute 处理多任务请求")
    print("=" * 60)

    question = (
        "我有几个事想确认："
        "1) 订单 ORD20240001 是什么状态？"
        "2) 耳机能退货吗？"
        "3) 快递 SF1234567890 到哪了？"
    )
    print(f" 用户: {question}\n")
    plan_and_execute(question)


def demo_plan_execute_dependency():
    """
    演示2：P&E 处理有依赖关系的任务链。
    WHY: 查优惠券需要先知道用户名，用户名在订单信息里——
         P&E 规划时能识别这个依赖：先查订单拿到 user_name，
         再调 query_coupons(user_name=...)。
         如果规划阶段没识别到依赖，执行阶段的结果也会帮助调整。
    """
    print("=" * 60)
    print(" 演示2：P&E 处理依赖任务 —— 先查订单再查优惠券")
    print("=" * 60)

    question = "查一下订单 ORD20240001，顺便看看这个用户有什么优惠券可用"
    print(f" 用户: {question}\n")
    plan_and_execute(question)


def demo_compare_react():
    """
    演示3：同一问题，P&E 和 ReAct 的风格对比。
    WHY: 不做实际对比执行，而是用文字说明两种模式的设计哲学差异——
         P&E = 计划先行，适合已知结构的多任务（批量处理）；
         ReAct = 边走边看，适合探索性任务（需根据中间结果决定下一步）。
    """
    print("=" * 60)
    print(" 演示3：P&E vs ReAct 设计哲学对比")
    print("=" * 60)

    print("""
  场景: 用户说 "订单 ORD20240001 能退吗？能退多少钱？"

  【ReAct 风格（Demo 06）】
    Round 1: Thought="先查订单" → query_order → 得到订单信息
    Round 2: Thought="已签收，查政策确认" → check_return_policy → 得到政策
    Round 3: Thought="政策和订单都有了，再算退款" → calculate_refund
    Round 4: 综合回答
    → 优势：每步看到结果后灵活调整下一步
    → 劣势：4 轮 API 调用，延迟高

  【Plan & Execute 风格（本 Demo）】
    规划阶段: [查订单 → 查政策 → 算退款]  一次性出计划
    执行阶段: 三步有序执行
    汇总阶段: 综合回答
    → 优势：计划清晰、步骤可预期、可并行执行
    → 劣势：第一步查完发现不需要后续步骤时，浪费了后续调用

  选择建议：
  - 任务结构已知、步骤明确 → P&E（批量查询、报表生成）
  - 需要根据中间结果判断 → ReAct（故障诊断、多条件决策）
  - 混合场景 → LangGraph（Demo 09），条件分支 + 节点编排
""")


def main():
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║  Agent-Playground Demo 07: Plan & Execute Agent  ║")
    print("║  规划 → 执行 → 汇总                               ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    demo_plan_execute_basic()
    demo_plan_execute_dependency()
    demo_compare_react()

    print("=" * 60)
    print(" Demo 07 完成！P&E = 先看地图再走路")
    print("=" * 60)


if __name__ == "__main__":
    main()
