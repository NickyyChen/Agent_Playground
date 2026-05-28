# -*- coding: utf-8 -*-
"""
05_list_operations.py — 列表操作：增删改查、切片、排序
======================================================

【概念】
list 是 Python 最常用的容器——有序、可变、可重复。
Agent 开发中 list 无处不在：
  - messages[] 是 list[dict]——对话历史的物理载体
  - tools[] 是 list[dict]——工具定义的集合
  - 搜索结果、订单列表、商品推荐——全是 list

核心操作：
  增：append() / extend() / insert()
  删：pop() / remove()
  查：索引 [i] / 切片 [start:stop] / in 判断
  改：list[i] = 新值
  排序：sort() / sorted()

【在智能客服中的应用】
- messages 列表管理：system prompt → 用户消息 → AI 回复 → 持续追加
- 工具调用结果批量处理
- 搜索结果按匹配度排序

【ASCII 架构图】

  messages[] 的典型生命周期:
  ┌─────────────┐
  │ system 消息   │  ← append({"role":"system", ...})
  ├─────────────┤
  │ user 消息     │  ← append({"role":"user", ...})
  ├─────────────┤
  │ assistant 消息│  ← append({"role":"assistant", ...})  模型回复
  ├─────────────┤
  │ user 追问     │  ← append({"role":"user", ...})       多轮对话
  ├─────────────┤
  │ ...          │  ← 持续追加，直到超出上下文窗口
  └─────────────┘
"""

# ══════════════════════════════════════════════════════════════
# 1. 增删改查 —— 对话历史的"增删改查"
# WHY: messages 列表管理是每个 Agent 的基础操作——
#      用户每轮消息 append，旧消息可能需要 pop(0) 防止超窗口，
#      通过索引 [-1] 检查最后一条消息的角色。
# ══════════════════════════════════════════════════════════════

def demo_crud():
    print("=" * 50)
    print(" 1. 列表增删改查 —— 模拟对话历史管理")
    print("=" * 50)

    # 初始化：system prompt 永远是第一条
    messages = [
        {"role": "system", "content": "你是客服小选"}
    ]
    print(f" 初始化: {len(messages)} 条消息")

    # 增: append() 加到末尾 —— 用户发消息
    messages.append({"role": "user", "content": "查订单 ORD001"})
    messages.append({"role": "assistant", "content": "好的，正在查询..."})
    print(f" 两轮后: {len(messages)} 条消息")

    # 查: 索引访问 —— 检查最后一条是谁说的
    # WHY: [-1] 是最后一条，负索引从末尾倒数
    last_msg = messages[-1]
    print(f" 最后一条: {last_msg['role']}: {last_msg['content']}")

    # 改: 直接赋值 —— 修正 assistant 的消息
    # 这里是直接赋值，原来如此
    messages[-1]["content"] = "订单 ORD001：耳机，¥299，已签收"
    print(f" 修正后: {messages[-1]['content']}")

    # 删: pop() 删除并返回
    # WHY: pop(0) 删第一条——上下文太长时间可以移除旧消息
    if len(messages) > 5:
        removed = messages.pop(0)
        print(f" 上下文超限，移除最早消息: {removed['role']}")

    print(f" 最终消息数: {len(messages)}")
    print()


# ══════════════════════════════════════════════════════════════
# 2. 切片 —— 只看最近的 N 条
# WHY: list[1:3] 取出索引 1,2（不含 3）。
#      上下文窗口管理时，截取最近 N 条消息保留用户最近意图。
#      [start:stop:step] 三个参数都可省略。
# ══════════════════════════════════════════════════════════════

def demo_slicing():
    print("=" * 50)
    print(" 2. 切片 —— 截取对话窗口")
    print("=" * 50)

    history = ["SYS", "U1", "A1", "U2", "A2", "U3", "A3",
               "U4", "A4", "U5"]
    # SYS=system, U=user, A=assistant, 数字=轮次

    # 切片基础: list[start:stop] —— 左闭右开 [start, stop)
    print(f" 完整历史 ({len(history)} 条): {history}")
    print(f" 前3条 history[:3]:      {history[:3]}")    # 省略 start → 从0开始
    print(f" 后3条 history[-3:]:     {history[-3:]}")   # 省略 stop → 到末尾
    print(f" 第3-5条 history[2:5]:   {history[2:5]}")   # 索引从0开始
    print(f" 每2条取1 history[::2]:  {history[::2]}")   # step=2
    print()

    # 客服场景: 保留 system + 最近 4 条
    system_msg = history[0]
    recent = history[-4:]
    window = [system_msg] + recent
    print(f" 上下文窗口: {window}  "
          f"(保留 system + 最近4条，节省 token)")
    print()


# ══════════════════════════════════════════════════════════════
# 3. 排序 —— sorted() 按 key 排序
# WHY: sorted(list, key=函数) 是 Python 排序的核心——
#      key 告诉 sorted "按什么排序"，返回新列表，不修改原列表。
#      客服场景：搜索结果按匹配度排序、订单按时间排序。
# ══════════════════════════════════════════════════════════════

def demo_sorting():
    print("=" * 50)
    print(" 3. 排序 —— 搜索结果按匹配度排序")
    print("=" * 50)

    results = [
        {"name": "索尼 WH-1000XM5", "score": 0.88, "price": 2499},
        {"name": "漫步者 W820NB", "score": 0.95, "price": 299},
        {"name": "AirPods Pro", "score": 0.72, "price": 1899},
        {"name": "QCY T13", "score": 0.91, "price": 99},
    ]

    # sorted() 返回新列表，key=lambda 指定按什么排序
    # WHY: key=lambda x: x["score"] → 对每个元素取 score 字段来比较
    by_score = sorted(results, key=lambda x: x["score"], reverse=True)  # 这里最重要的是revers降序
    print(" 按匹配度降序:")
    for r in by_score:
        print(f"   {r['name']:20s} 匹配度:{r['score']:.0%}  ¥{r['price']}")

    # 按价格升序
    by_price = sorted(results, key=lambda x: x["price"])
    print("\n 按价格升序:")
    for r in by_price:
        print(f"   ¥{r['price']:5d}  {r['name']}")

    print()


def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║  Python 基础 05: 列表操作                     ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    demo_crud()
    demo_slicing()
    demo_sorting()


if __name__ == "__main__":
    main()
