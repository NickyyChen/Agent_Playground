# -*- coding: utf-8 -*-
"""
15_type_hints.py — 类型注解：函数签名、变量标注、Optional
=========================================================

【概念】
Python 是动态类型语言，但从 3.5+ 开始支持类型注解（Type Hints）——
在代码中声明变量/参数/返回值的预期类型。

注意：类型注解不强制类型检查（Python 不会因为类型不匹配报错），
      它的作用是：
      1. IDE 智能提示——写代码时自动补全、显示参数类型
      2. 静态检查——mypy/pyright 在运行前发现类型错误
      3. 文档——看函数签名就知道参数该传什么

【在智能客服中的应用】
- LangChain/LangGraph 中函数签名都有类型注解
- llm_client.py: def chat(messages: list[dict], **kwargs) -> str
- 工具函数参数类型标注，让调用方知道该传什么

【ASCII 架构图】

  类型注解在 Agent 代码中的位置:

  def chat(
      messages: list[dict],        ← 参数: list[dict]
      temperature: float = 0.1,   ← 参数: float
      max_tokens: int = 200,      ← 参数: int
  ) -> str:                        ← 返回值: str
      ...
"""

from typing import Optional


# ══════════════════════════════════════════════════════════════
# 1. 基本类型注解 —— 参数与返回值
# WHY: 类型注解让代码自文档化——
#      看 def query(order_id: str) -> dict 就知道:
#      入参是字符串，返回是字典，不用读函数体。
# ══════════════════════════════════════════════════════════════

def demo_basic_hints():
    print("=" * 50)
    print(" 1. 基本类型注解 —— 函数签名")
    print("=" * 50)

    def query_order(order_id: str) -> dict:
        """查订单: str 入参 → dict 返回值"""
        return {"order_id": order_id, "status": "已签收"}

    def calculate_total(price: float, quantity: int,
                        discount: float = 1.0) -> float:
        """计算总价: float/int → float 返回值"""
        return price * quantity * discount

    def is_deliverable(order_id: str) -> bool:
        """是否可配送 → bool 返回值"""
        return order_id in ["ORD001", "ORD002"]

    # 使用: IDE 会根据类型注解给出智能提示
    order: dict = query_order("ORD001")
    total: float = calculate_total(299.0, 2, 0.9)

    print(f" order 类型: {type(order).__name__} = {order}")
    print(f" total 类型: {type(total).__name__} = {total:.2f}")
    print()


# ══════════════════════════════════════════════════════════════
# 2. 复杂类型注解 —— list[dict]、Optional
# WHY: Python 3.9+ 支持 list[dict]、dict[str, int] 等泛型注解——
#      不仅标注"是列表"，还标注"列表里是什么"。
#      Optional[X] = X | None —— 表示"可能是 X，也可能是 None"。
# ══════════════════════════════════════════════════════════════

def demo_complex_hints():
    print("=" * 50)
    print(" 2. 复杂类型注解 —— list[dict]、Optional")
    print("=" * 50)

    # WHY: list[dict] 告诉调用方: 这是 dict 的列表——
    #      你不需要猜 messages 里装的是什么。
    def chat(messages: list[dict],
             temperature: float = 0.1,
             max_tokens: Optional[int] = None  # WHY: Optional[int] = int | None
             ) -> str:
        """模拟 LLM 调用——展示了完整的类型注解风格"""
        msg_count = len(messages)
        tok_info = max_tokens if max_tokens else "不限制"
        return f"[模拟回复] 处理了{msg_count}条消息, max_tokens={tok_info}"

    messages: list[dict] = [
        {"role": "system", "content": "你是客服"},
        {"role": "user", "content": "查订单"},
    ]

    reply = chat(messages, temperature=0.1, max_tokens=200)
    print(f" {reply}")

    # Optional: 不传 max_tokens（默认 None）
    reply2 = chat(messages)
    print(f" {reply2}")
    print()


# ══════════════════════════════════════════════════════════════
# 3. 类型注解不影响运行 —— 但还是应该写
# WHY: Python 不强制类型——传错类型不会报错但会导致运行时 bug。
#      类型注解的价值在"阅读"和"静态检查"，不在"运行时强制"。
# ══════════════════════════════════════════════════════════════

def demo_not_enforced():
    print("=" * 50)
    print(" 3. 类型注解不强制 —— 但能提前发现问题")
    print("=" * 50)

    def add_price(a: float, b: float) -> float:
        return a + b

    # 正常调用——符合类型注解
    result1 = add_price(299.0, 49.0)
    print(f" float+float: {result1} (类型: {type(result1).__name__})")

    # "错误"调用——传字符串，Python 不报错但行为改变！
    result2 = add_price("299", "49")  # 字符串 + 字符串 = 拼接！
    print(f" str+str:     {result2} (类型: {type(result2).__name__})")
    print(f" 注意: 没有报错，但结果完全不同——这就是静态检查的价值")
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║  Python 基础 15: 类型注解                     ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    demo_basic_hints()
    demo_complex_hints()
    demo_not_enforced()


if __name__ == "__main__":
    main()
