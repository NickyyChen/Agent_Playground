# -*- coding: utf-8 -*-
"""
08_reflection.py — Reflection Agent：自我反思，迭代修正
========================================================

【概念】
Reflection（反思）是 Agent 的"自我审查"模式，流程为：

  生成(Generate) → 反思(Reflect) → 修正(Revise)
       │                │               │
  产出初版回答     审视初版的问题     基于反思重写回答

类比：写作文 → 自己读一遍找出毛病 → 修改后交卷。

与之前模式的对比：
  - ReAct（06）：多步推理→找答案，但找到后就停了，不检查
  - P&E（07）：按计划执行→汇总回答，但回答质量依赖一次生成
  - Reflection（08）：产出答案后多一个"自我打分再修改"的环节

【在智能客服中解决什么问题】
客服回答的质量直接影响用户满意度和公司形象：
  - 初版回答可能遗漏政策细节（如"耳机拆封不支持退货"这句没说）
  - 语气可能过于生硬或过于随意
  - 可能没注意到用户隐含的情绪（愤怒、焦虑）
  Reflection 让 Agent 自己找出这些问题并修正，无需人工审查。

【核心流程】
1. Generator: 根据用户问题 + 工具结果生成初版回答
2. Reflector: 用独立的审查 prompt 检查初版，输出具体问题清单
3. Reviser: 根据问题清单修正回答，生成最终版本

【pip install】
pip install openai

【ASCII 架构图】

     用户问题 + 工具结果
           │
           ▼
    ┌─────────────┐
    │ ① Generator │ ──→  初版回答 v1
    │   (生成)     │      "您可以退货，7天内就行"
    └─────────────┘       （可能遗漏：拆封不支持）
           │
           ▼
    ┌─────────────┐
    │ ② Reflector │ ──→  问题清单
    │   (反思)     │      ❌ 未提及拆封限制
    │             │      ❌ 未区分无理由/质量退货
    │             │      ❌ 未说明退款时效
    └─────────────┘
           │
           ▼
    ┌─────────────┐
    │ ③ Reviser   │ ──→  修正回答 v2
    │   (修正)     │      "签收7天内、未拆封可无理由退货；
    │             │       质量问题15天内免费换新；
    │             │       退款3个工作日内原路返回"
    └─────────────┘

   对比：没有 Reflection 的 Agent（06/07）停在 v1；
         有了 Reflection，交付的是质量更高的 v2。
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.llm_client import chat
from shared.mock_data import RETURN_POLICY

# ══════════════════════════════════════════════════════════════
# 三个角色的 System Prompt
# ══════════════════════════════════════════════════════════════

# WHY: Generator 直接面向用户，要求快速、友好、专业
GENERATOR_PROMPT = """你是"小选"，好买电商的智能客服助手。
请根据用户问题和提供的参考资料，生成一份客服回答。
要求：友好专业，简洁清晰。"""

# WHY: Reflector 是"质检员"角色，不看用户感受只看问题——
#      追问政策是否完整、逻辑是否有漏洞、语气是否恰当。
#      把审查维度写清楚，确保每次反思覆盖全面。
REFLECTOR_PROMPT = """你是客服回答的质检审查员。请严格审查以下客服回答，
找出所有问题。从以下 5 个维度逐一检查：

1. 准确性：回答是否引用了正确的政策条款？是否有事实错误？
2. 完整性：是否遗漏了关键信息？（如退货时效、退款方式、特殊限制）
3. 清晰度：逻辑是否通顺？用户能否一眼看懂？
4. 语气：是否专业友好？对愤怒/焦虑的用户是否有安抚？
5. 合规性：是否做出了不该做的承诺？（如承诺具体赔偿金额）

输出格式：
[问题1] (维度名) 具体问题描述
[问题2] (维度名) 具体问题描述
...
[总评] 一句话总结最需要改进的地方

如果没有发现问题，输出：NO_ISSUES"""

# WHY: Reviser 需要同时看到"原回答"和"问题清单"，
#      在改正问题的同时保留原回答中好的部分，不推倒重来
REVISER_PROMPT = """你是"小选"，好买电商的智能客服助手。
以下是你之前给用户的回答和质检发现的问题。请基于问题清单修正回答，
输出一个改进后的最终版本。

修正原则：
- 逐条解决质检列出的问题
- 保留原回答中正确、友好的部分
- 修正后的回答仍然保持简洁专业，不用过度冗长"""


# ══════════════════════════════════════════════════════════════
# Reflection 循环引擎
# ══════════════════════════════════════════════════════════════

def reflection_cycle(user_question: str, context: str = "",
                     verbose: bool = True, max_rounds: int = 2):
    """
    Generate → Reflect → Revise 的一次完整循环。
    WHY: max_rounds=2 是实践中的平衡点——
         1 轮反思通常能抓到 80% 的问题，
         2 轮可以进一步打磨，但超过 2 轮收益递减。
    """
    # ─── Step 1: Generate 初版回答 ────────────────
    if verbose:
        print("╔══════════════════════════════════════════════╗")
        print("║  ① Generate —— 生成初版回答                     ║")
        print("╚══════════════════════════════════════════════╝")

    gen_context = f"\n\n【参考资料】\n{context}" if context else ""
    draft = chat([
        {"role": "system", "content": GENERATOR_PROMPT + gen_context},
        {"role": "user", "content": user_question},
    ])
    if verbose:
        print(f"  初版回答:\n  「{draft}」\n")

    # ─── Step 2-3: Reflection 循环 ────────────────
    current = draft
    for rnd in range(1, max_rounds + 1):
        # ─── Reflect ───────────────────────────
        if verbose:
            print(f"╔══════════════════════════════════════════════╗")
            print(f"║  ② Reflect (第{rnd}轮) —— 自我审查               ║")
            print(f"╚══════════════════════════════════════════════╝")

        reflection = chat([
            {"role": "system", "content": REFLECTOR_PROMPT},
            {"role": "user",
             "content": f"用户问题: {user_question}\n\n客服回答:\n{current}\n\n"
                        f"{'参考资料: ' + context if context else ''}"},
        ])

        if verbose:
            print(f"  审查结果:\n{reflection}\n")

        # WHY: 如果质检认为没问题，立即终止，不过度修正
        if "NO_ISSUES" in reflection.upper():
            if verbose:
                print(f"  质检通过，无需修正 → 输出当前版本\n")
            return current

        # ─── Revise ───────────────────────────
        if verbose:
            print(f"╔══════════════════════════════════════════════╗")
            print(f"║  ③ Revise (第{rnd}轮) —— 基于审查修正           ║")
            print(f"╚══════════════════════════════════════════════╝")

        current = chat([
            {"role": "system", "content": REVISER_PROMPT + gen_context},
            {"role": "user",
             "content": f"用户问题: {user_question}\n\n"
                        f"原回答:\n{current}\n\n"
                        f"质检问题:\n{reflection}\n\n"
                        f"请输出修正后的回答："},
        ])

        if verbose:
            print(f"  修正后回答:\n  「{current}」\n")

    return current


# ══════════════════════════════════════════════════════════════
# 演示函数
# ══════════════════════════════════════════════════════════════

def demo_reflection_full_cycle():
    """
    演示1：Reflection 完整流程 —— 从初版到修正的全过程。
    WHY: 构造一个需要精确政策引用的场景（耳机退货），
         初版回答大概率会遗漏细节（拆封限制、质保换货等），
         Reflection 能抓到这些遗漏并修正。
    """
    print("=" * 60)
    print(" 演示1：Reflection 完整流程 —— 耳机退货咨询")
    print("=" * 60)

    question = "我的蓝牙耳机用了5天，左耳突然没声音了，能退货退款吗？"
    print(f" 用户: {question}\n")

    final = reflection_cycle(question, context=RETURN_POLICY)

    print("=" * 60)
    print(f" 最终回答: {final}")
    print()


def demo_reflection_comparison():
    """
    演示2：对比 —— 有/无 Reflection 的回答质量。
    WHY: 同一个场景跑两次：一次直出回答（模拟06/07的行为），
         一次经过 Reflection 修正，并列对比差异。
         让用户直观感受 Reflection 带来的质量提升。
    """
    print("=" * 60)
    print(" 演示2：有/无 Reflection 质量对比")
    print("=" * 60)

    question = ("我买的耳机到了，但包装盒被压扁了，耳机看起来没问题，"
                "但我心里不舒服，你们怎么处理？")

    # ─── 无 Reflection ──────────────────────────
    print("【无 Reflection —— 直接生成（模拟 Demo 06/07 的输出）】")
    no_reflect = chat([
        {"role": "system", "content": GENERATOR_PROMPT +
         f"\n\n【参考资料】\n{RETURN_POLICY}"},
        {"role": "user", "content": question},
    ])
    print(f"  回答: {no_reflect}\n")

    # ─── 有 Reflection ──────────────────────────
    print("【有 Reflection —— 生成→审查→修正】")
    with_reflect = reflection_cycle(
        question, context=RETURN_POLICY, verbose=False
    )
    print(f"  回答: {with_reflect}\n")

    # ─── 差异分析 ────────────────────────────────
    print("【差异分析】")
    print(f"  无Reflection字数: {len(no_reflect)}")
    print(f"  有Reflection字数: {len(with_reflect)}")
    print(f"  关键差异: Reflection 版本通常会补充更多政策细节和情绪安抚")


def demo_reflection_no_issues():
    """
    演示3：边界情况 —— 当回答已经够好时，Reflection 不会乱改。
    WHY: Reflection 不是"无论如何都要改点什么"——
         质检员输出 NO_ISSUES 时，循环立即终止，
         避免把正确回答改坏（过度修正）。
    """
    print("=" * 60)
    print(" 演示3：Reflection 的克制 —— 没问题就不改")
    print("=" * 60)

    question = "你们平台的客服电话是多少？"
    print(f" 用户: {question}\n")

    # WHY: 简单事实类问题，参考信息充足，初版就应该是正确的
    context = "好买电商客服热线：400-800-8888，工作时间：每天 9:00-21:00。"
    final = reflection_cycle(question, context=context)

    print("=" * 60)
    print(f" 最终回答: {final}")
    print(" （如果初版就合格，Reflection 不会强行修改）")
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║  Agent-Playground Demo 08: Reflection Agent       ║")
    print("║  Generate → Reflect → Revise → 更高质量的回答       ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    demo_reflection_full_cycle()
    demo_reflection_comparison()
    demo_reflection_no_issues()

    print("=" * 60)
    print(" Demo 08 完成！Reflection = 写完答案再检查一遍")
    print("=" * 60)


if __name__ == "__main__":
    main()
