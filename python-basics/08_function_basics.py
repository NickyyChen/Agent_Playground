# -*- coding: utf-8 -*-
"""
08_function_basics.py — 函数基础：定义、参数、返回值、作用域
===========================================================

【概念】
函数是代码复用的基本单位——把一段逻辑封装起来，给一个名字，需要时调用。
Agent 开发中函数承担两个角色：
  1. 工具函数：query_order()、check_policy()——被 Agent 调用的"手脚"
  2. 组织代码：把大段逻辑拆成小函数，每个做一件事

核心要素：
  参数：传入的数据（必备 vs 可选）
  返回值：传出的结果（无 return 则返回 None）
  作用域：变量在哪里可见（函数内 vs 函数外）

【在智能客服中的应用】
- 每个工具都是独立函数：query_order(order_id) → 订单信息
- 参数校验函数：validate_phone(phone) → bool
- 封装 LLM 调用：chat(messages) → str

【ASCII 架构图】

  输入 → 函数 → 输出

  "ORD001" ──▶ query_order() ──▶ {"product":"耳机", "price":299}
  "138xxx" ──▶ validate_phone() ──▶ True
  messages[] ──▶ chat() ──▶ "您的订单已签收..."
"""

# ══════════════════════════════════════════════════════════════
# 1. 函数定义与调用
# WHY: def 定义一个函数——给一段逻辑起名字。
#      参数是输入，return 是输出。
#      每个客服工具都是一个函数。
# ══════════════════════════════════════════════════════════════

def demo_basic_function():
    print("=" * 50)
    print(" 1. 函数定义 —— 客服工具函数")
    print("=" * 50)

    # WHY: 默认参数 order_id=None 让参数可选——
    #      不传的时候返回全部订单列表
    def query_order(order_id: str = None):
        """
        查询订单。
        有 order_id → 返回单个订单
        无 order_id → 返回全部订单列表
        """
        orders = {
            "ORD001": {"product": "漫步者 W820NB", "price": 299},
            "ORD002": {"product": "手机壳", "price": 49},
        }
        if order_id:
            return orders.get(order_id, f"订单 {order_id} 不存在")
        return orders

    # 调用: 传入参数
    result1 = query_order("ORD001")
    print(f" 查单个: {result1}")

    # 调用: 不传参数，使用默认值
    result2 = query_order()
    print(f" 查全部: {list(result2.keys())}")

    # 调用: 传未知订单号
    result3 = query_order("ORD999")
    print(f" 不存在: {result3}")
    print()


# ══════════════════════════════════════════════════════════════
# 2. 作用域 —— 变量在哪里可见
# WHY: 函数内定义的变量是局部的（local），外面看不到。
#      函数外定义的变量是全局的（global），函数内可以读但不要改。
#      理解作用域是避免 bug 的基础。
# ══════════════════════════════════════════════════════════════

def demo_scope():
    print("=" * 50)
    print(" 2. 作用域 —— 局部 vs 全局")
    print("=" * 50)

    PLATFORM_NAME = "好买电商"  # WHY: 全大写 → 约定俗成表示"全局常量"

    def build_greeting(customer_name: str) -> str:
        """
        构建问候语。
        WHY: PLATFORM_NAME 是外部变量，函数内可以读。
             greeting 是局部变量，函数外无法访问。
        """
        greeting = f"欢迎光临{PLATFORM_NAME}，{customer_name}您好！"
        return greeting

    msg = build_greeting("张先生")
    print(f" 问候: {msg}")
    # print(greeting)  ← 报错! greeting 在函数内定义，外面看不见
    print()


# ══════════════════════════════════════════════════════════════
# 3. 返回值 —— 单值 vs 多值
# WHY: return 不写或写 return None 都是返回 None。
#      return a, b 实际返回 tuple (a, b)。
#      工具函数应始终返回有意义的值——方便 Agent 解析。
# ══════════════════════════════════════════════════════════════

def demo_return_values():
    print("=" * 50)
    print(" 3. 返回值 —— 工具函数的标准输出")
    print("=" * 50)

    def check_refund_eligibility(order_id: str):
        """
        检查订单是否能退款。
        WHY: 返回 (bool, str) 两个值——
             第一个是判断结果（方便 if 判断），
             第二个是原因（方便展示给用户）。
             这是 Agent 工具函数返回值的最佳实践。
        """
        policies = {
            "ORD001": (True, "签收3天，在7天退货期内"),
            "ORD002": (False, "已签收15天，超过7天退货期"),
            "ORD003": (False, "订单不存在"),
        }
        return policies.get(order_id, (False, "订单不存在"))

    for oid in ["ORD001", "ORD002", "ORD003"]:
        eligible, reason = check_refund_eligibility(oid)  # tuple 解包
        symbol = "✓" if eligible else "✗"
        print(f" {oid}: {symbol} {reason}")
    print()


# ══════════════════════════════════════════════════════════════
# 4. 参数类型 —— 位置参数、关键字参数、默认参数
# WHY: Python 函数参数三种形态各有用处——
#      位置参数→必传；默认参数→可选；关键字参数→传参时显式指定名称。
# ══════════════════════════════════════════════════════════════

def demo_parameter_types():
    print("=" * 50)
    print(" 4. 参数类型 —— 三种参数形式")
    print("=" * 50)

    def send_reply(user_message: str,
                   tone: str = "友好",          # WHY: 默认参数——不传就用默认值
                   max_length: int = 200):      # WHY: 默认值让参数可选
        """模拟客服回复生成"""
        templates = {
            "友好": f"亲爱的用户您好！关于'{user_message[:20]}...'的问题，",
            "专业": f"针对您咨询的'{user_message[:20]}...'事项，",
            "幽默": f"哈哈，您问的'{user_message[:20]}...'这个问题有意思~",
        }
        return templates.get(tone, templates["友好"])

    # 三种调用方式
    print(f" 默认语气: {send_reply('我想查订单')}")
    print(f" 指定语气: {send_reply('我要退货', tone='专业')}")
    print(f" 全参数:   {send_reply('推荐耳机', tone='幽默', max_length=100)}")
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║  Python 基础 08: 函数基础                     ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    demo_basic_function()
    demo_scope()
    demo_return_values()
    demo_parameter_types()


if __name__ == "__main__":
    main()
