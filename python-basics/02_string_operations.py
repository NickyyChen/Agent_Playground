# -*- coding: utf-8 -*-
"""
02_string_operations.py — 字符串操作：f-string、常用方法、多行文本
==================================================================

【概念】
字符串是 Agent 开发中使用频率最高的类型——所有 LLM 的输入（prompt）
和输出（回复文本）都是字符串。

核心技能就三个：
  1. f-string 插值：把变量嵌入文本，构建动态 prompt
  2. 常用方法：split/join/strip/replace——清洗和格式化文本
  3. 多行文本：三引号写长 prompt，保持可读性

【在智能客服中的应用】
- 构建 system prompt：你是客服，名叫{name}
- 清洗用户输入：去掉首尾空格、敏感词替换
- 格式化订单信息：把 dict 转成人类可读的文本"""
"""
【ASCII 架构图】

  变量                              字符串操作                    输出
  ────                              ──────────                   ────

  name="小选"  ──┐
  today="5.28" ──┤──▶ f"你好，我是{name}" ──▶ "你好，我是小选"
                  │
  用户输入 ──────┼──▶ input.strip().lower() ──▶ 标准化文本
                  │
  prompt模板 ────┘──▶ .format() / f-string   ──▶ 完整 prompt
"""

# ══════════════════════════════════════════════════════════════
# 1. f-string —— 把变量嵌入文本
# WHY: f-string（f"...{var}..."）是构建动态 prompt 最核心的技巧。
#      Agent 需要把用户问题、订单信息、政策文本嵌入 prompt 模板——
#      f-string 让这个操作一行完成，且可读性极好。
#      支持表达式：f"总价: {price * qty:.2f}" → "总价: 897.00"
# ══════════════════════════════════════════════════════════════

def demo_fstring():
    print("=" * 50)
    print(" 1. f-string —— 构建动态客服消息")
    print("=" * 50)

    customer_name = "张先生"
    product = "漫步者 W820NB"
    price = 299.0
    quantity = 2

    # WHY: {var:.2f} → 保留两位小数，{var:,} → 千分位逗号
    message = (
        f"{customer_name}您好，"
        f"您购买的「{product}」共 {quantity} 件，"
        f"总价 ¥{price * quantity:.2f}，"
        f"预计 3 天内送达。"
    )
    print(f" 客服消息: {message}")
    print()


# ══════════════════════════════════════════════════════════════
# 2. 多行字符串 —— 写 System Prompt
# WHY: 三引号 """...""" 保留换行和缩进，是写 system prompt 的标准姿势。
#      比一行写到底的 \n 拼接清晰 100 倍。
# ══════════════════════════════════════════════════════════════

def demo_multiline():
    print("=" * 50)
    print(" 2. 三引号多行文本 —— System Prompt")
    print("=" * 50)

    agent_name = "小选"
    # WHY: 三引号内可以随意换行，prompt 结构和代码缩进一致。
    #      需要避免多余空格时用 textwrap.dedent()，这里演示基础用法。
    system_prompt = f"""
    你是"{agent_name}"，某电商平台的智能客服助手。

    行为规范：
    - 回答简洁专业，不超过3句话
    - 涉及退换货/退款时，必须引用平台政策
    - 态度友好
    """

    print(f" System Prompt:")
    print(system_prompt)
    print()


# ══════════════════════════════════════════════════════════════
# 3. 常用字符串方法 —— 清洗用户输入
# WHY: 用户输入充满噪音——前后空格、大小写混乱、多余标点。
#      strip()/lower()/replace() 是清洗三步曲。
# ══════════════════════════════════════════════════════════════

def demo_string_methods():
    print("=" * 50)
    print(" 3. 字符串方法 —— 清洗用户输入")
    print("=" * 50)

    # 模拟用户输入的各种"脏"数据
    raw_inputs = [
        "  我要退货  ",                       # 前后空格
        "我要退貨！！！",                      # 繁体和多余标点
        "Order ORD12345 STATUS",             # 中英混杂
        "",                                   # 空输入——边界情况
    ]

    for raw in raw_inputs:
        cleaned = raw.strip()                      # WHY: strip() 去首尾空白
        print(f" 输入: '{raw}'")
        print(f" 清洗: '{cleaned}'")
        print(f" 长度: {len(cleaned)} 字符")        # WHY: len() 判断是否空输入
        print(f" 是否为空: {not cleaned}")           # WHY: 空串在 if 中为 False
        print()


# ══════════════════════════════════════════════════════════════
# 4. split / join —— 文本拆解与拼装
# WHY: split() 把字符串按分隔符切成列表，
#      join() 把列表用分隔符拼回字符串。
#      客服系统中：解析用户多意图、拼接订单摘要。
# ══════════════════════════════════════════════════════════════

def demo_split_join():
    print("=" * 50)
    print(" 4. split / join —— 拆解与拼装")
    print("=" * 50)

    # 用户一句话里可能有多个意图
    user_msg = "我想查订单状态，还想申请退款，顺便问一下优惠活动"

    intents = user_msg.split("，")   # WHY: split 按逗号切分
    print(f" 用户原话: {user_msg}")
    print(f" 拆成意图列表:")
    for i, intent in enumerate(intents, 1):
        print(f"   {i}. {intent}")

    # 反过来——把列表拼成摘要
    order_items = ["蓝牙耳机 x1", "手机壳 x2", "数据线 x1"]
    summary = " | ".join(order_items)  # WHY: join 用分隔符拼接列表
    print(f"\n 订单摘要: {summary}")
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║  Python 基础 02: 字符串操作                  ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    demo_fstring()
    demo_multiline()
    demo_string_methods()
    demo_split_join()


if __name__ == "__main__":
    main()
