# -*- coding: utf-8 -*-
"""
01_variables_types.py — 变量、基本类型与类型转换
================================================

【概念】
Python 是动态类型语言——变量不需要声明类型，解释器根据赋值自动推断。
但"动态"不等于"没类型"：每个值在运行时都有明确类型，类型决定了
能做什么运算、能传什么参数。

四种最常用的基本类型：
  str  — 文本（用户消息、API 响应）
  int  — 整数（数量、页码）
  float— 小数（价格、概率值）
  bool — 真假（开关、校验结果）

【在智能客服中的应用】
- 用户消息是 str
- 订单价格是 float，数量是 int
- 退款校验结果是 bool（是否满足条件）

【ASCII 架构图】

  用户输入                     Python 处理                   输出
  ────────                    ───────────                  ────

  "299.5"  ──▶ float("299.5") ──▶ 299.5 ──▶ 价格比较
  "3"      ──▶ int("3")      ──▶ 3    ──▶ 数量计算
  折扣规则  ──▶ bool(0.8)      ──▶ True ──▶ 是否使用优惠券
"""

# ══════════════════════════════════════════════════════════════
# 1. 基本类型与 type() 检查
# WHY: type() 告诉你变量"到底是什么"——
#      从 API 拿回来的 JSON 数据，price 可能是 str 而非 float，
#      不检查类型直接做数学运算会报错。
# ══════════════════════════════════════════════════════════════

def demo_basic_types():
    print("=" * 50)
    print(" 1. 四种基本类型")
    print("=" * 50)

    product: str = "漫步者 W820NB"      # str: 商品名——永远用引号
    quantity: int = 3                    # int: 购买数量——无小数点
    price: float = 299.0                 # float: 单价——有小数点
    in_stock: bool = True                # bool: 是否有货——True/False 首字母大写

    print(f" 商品名:   {product}   → 类型: {type(product).__name__}")
    print(f" 数量:     {quantity}     → 类型: {type(quantity).__name__}")
    print(f" 单价:     {price}     → 类型: {type(price).__name__}")
    print(f" 有货:     {in_stock}   → 类型: {type(in_stock).__name__}")
    print()


# ══════════════════════════════════════════════════════════════
# 2. 类型转换 —— 客服系统中最常见的坑
# WHY: API 返回的 JSON 中 price 是字符串 "299" 而非数字 299——
#      必须显式转换，否则 total = price * quantity 直接报 TypeError。
#      float("299") → 299.0, int("3") → 3, str(299) → "299"
# ══════════════════════════════════════════════════════════════

def demo_type_casting():
    print("=" * 50)
    print(" 2. 类型转换 —— 模拟从 JSON 拿到的字符串数据")
    print("=" * 50)

    # WHY: 模拟 API 返回——所有值都是字符串
    raw_price = "299.0"       # JSON 中的 price 字段
    raw_quantity = "3"        # JSON 中的 quantity 字段
    raw_discount = "0.85"     # JSON 中的折扣率

    # 字符串不能直接相乘——必须转换
    price = float(raw_price)           # "299.0" → 299.0
    quantity = int(raw_quantity)        # "3" → 3
    discount = float(raw_discount)       # "0.85" → 0.85

    total = price * quantity * discount
    print(f" raw数据: price='{raw_price}', qty='{raw_quantity}', "
          f"discount='{raw_discount}'")
    print(f" 转换后:   price={price}(float), qty={quantity}(int), "
          f"discount={discount}(float)")
    print(f" 折后总价: ¥{total:.2f}")
    print()


# ══════════════════════════════════════════════════════════════
# 3. bool 的实际应用 —— 校验逻辑
# WHY: bool 不只是 True/False——空字符串、0、None、空列表在
#      if 判断中都是 False。理解这点可以写出更简洁的校验代码。
# ══════════════════════════════════════════════════════════════

def demo_bool_in_practice():
    print("=" * 50)
    print(" 3. bool 在客服校验中的应用")
    print("=" * 50)

    def can_refund(order_status: str, days_since_delivery: int) -> bool:
        """
        判断订单是否可以退款。
        WHY: 两个条件都必须满足——用 and 连接。
             每个条件本身也是 bool 表达式。
        """
        return order_status == "已签收" and days_since_delivery <= 7

    # 测试三个场景
    cases = [
        ("已签收", 3, "签收3天 → 可退"),
        ("已签收", 10, "签收10天 → 不可退（超7天）"),
        ("运输中", 2, "运输中 → 不可退（未签收）"),
    ]

    for status, days, desc in cases:
        result = can_refund(status, days)
        print(f" {desc}: {result}")
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║  Python 基础 01: 变量、类型与类型转换        ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    demo_basic_types()
    demo_type_casting()
    demo_bool_in_practice()


if __name__ == "__main__":
    main()
