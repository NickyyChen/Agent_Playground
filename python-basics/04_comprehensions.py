# -*- coding: utf-8 -*-
"""
04_comprehensions.py — 推导式：列表、字典、集合推导式
=====================================================

【概念】
推导式（Comprehension）是 Python 特有的"一行循环"语法：
  列表推导式：[表达式 for x in 可迭代对象 if 条件]
  字典推导式：{键: 值 for x in 可迭代对象 if 条件}
  集合推导式：{表达式 for x in 可迭代对象 if 条件}

它的本质是把 for 循环 + if 过滤 + 结果收集 压缩到一行。

【在智能客服中的应用】
- 从订单列表中提取所有订单号 → 列表推导式
- 构建 {订单号: 状态} 查找表 → 字典推导式
- 提取唯一品类做筛选项 → 集合推导式

【ASCII 架构图】

  原始数据                      推导式                           结果
  ────────                     ────────                        ────

  [{订单1}, {订单2}, {订单3}]
       │
       ├──▶ [o["id"] for o in orders]                    → ["ORD1","ORD2","ORD3"]
       ├──▶ {o["id"]: o["status"] for o in orders}       → {"ORD1":"已签收",...}
       └──▶ {o["category"] for o in orders}              → {"耳机","手机壳"}
"""

# ══════════════════════════════════════════════════════════════
# 1. 列表推导式 —— 提取/过滤/转换
# WHY: for 循环 3 行做的事，列表推导式 1 行搞定。
#      更关键的是——它"声明式"地描述"我要什么"，一眼能看懂意图。
#      带 if 条件就是过滤，不带就是映射。
# ══════════════════════════════════════════════════════════════

def demo_list_comprehension():
    print("=" * 50)
    print(" 1. 列表推导式 —— 提取与过滤")
    print("=" * 50)

    orders = [
        {"id": "ORD001", "product": "耳机", "price": 299, "status": "已签收"},
        {"id": "ORD002", "product": "手机壳", "price": 49, "status": "运输中"},
        {"id": "ORD003", "product": "数据线", "price": 29, "status": "已签收"},
        {"id": "ORD004", "product": "充电头", "price": 79, "status": "已取消"},
    ]

    # 提取所有订单号: [表达式 for x in 列表]
    order_ids = [o["id"] for o in orders]
    print(f" 所有订单号: {order_ids}")

    # 过滤已签收的: [表达式 for x in 列表 if 条件]
    delivered = [o for o in orders if o["status"] == "已签收"]
    print(f" 已签收订单: {[o['id'] for o in delivered]}")

    # 提取+过滤+计算: 已签收订单的总金额
    total = sum(o["price"] for o in orders if o["status"] == "已签收")
    # WHY: sum() 接收一个生成器表达——去掉方括号就是生成器，省内存
    print(f" 已签收总金额: ¥{total}")

    # 构建客服消息列表
    alerts = [f"订单{o['id']}：{o['status']}" for o in orders
              if o["status"] != "已签收"]
    print(f" 待跟进提醒: {alerts}")
    print()


# ══════════════════════════════════════════════════════════════
# 2. 字典推导式 —— 构建查找表
# WHY: {k: v for ...} 是把列表快速变成"查询字典"的最高效方式。
#      客服系统中：订单号→订单详情、商品ID→商品名。
#      对比: 不用推导式需要 4 行 for 循环。
# ══════════════════════════════════════════════════════════════

def demo_dict_comprehension():
    print("=" * 50)
    print(" 2. 字典推导式 —— 构建查找表")
    print("=" * 50)

    orders = [
        {"id": "ORD001", "product": "耳机", "price": 299},
        {"id": "ORD002", "product": "手机壳", "price": 49},
        {"id": "ORD003", "product": "数据线", "price": 29},
        {"id": "ORD004", "product": "充电头", "price": 79},
    ]

    # WHY: {o["id"]: o["product"] for o in orders}
    #      左边是 key 表达式，右边是 value 表达式
    id_to_product = {o["id"]: o["product"] for o in orders}
    print(f" ID→商品: {id_to_product}")

    # 带过滤的字典推导
    cheap_items = {o["id"]: o["price"] for o in orders if o["price"] < 100}
    print(f" 百元以下: {cheap_items}")

    # 客服场景: 构建订单状态速查表
    status_lookup = {o["id"]: o["status"] if "status" in o else "未知"
                     for o in orders if o["price"] > 50}
    print(f" 高价订单状态: {status_lookup}")
    print()


# ══════════════════════════════════════════════════════════════
# 3. 集合推导式 —— 去重与唯一值提取
# WHY: {x for ...} 自动去重——提取所有不重复的品类、状态。
#      客服筛选器中"品类下拉选项"就是这样生成的。
# ══════════════════════════════════════════════════════════════

def demo_set_comprehension():
    print("=" * 50)
    print(" 3. 集合推导式 —— 去重提取")
    print("=" * 50)

    orders = [
        {"id": "ORD001", "category": "耳机", "status": "已签收"},
        {"id": "ORD002", "category": "手机配件", "status": "运输中"},
        {"id": "ORD003", "category": "耳机", "status": "已签收"},
        {"id": "ORD004", "category": "充电器", "status": "已取消"},
        {"id": "ORD005", "category": "手机配件", "status": "待支付"},
    ]

    # WHY: 集合自动去重——3个"耳机"只保留1个
    categories = {o["category"] for o in orders}
    print(f" 所有品类(去重): {categories}")

    statuses = {o["status"] for o in orders}
    print(f" 所有状态(去重): {statuses}")
    print()


# ══════════════════════════════════════════════════════════════
# 4. 对比：推导式 vs for 循环
# WHY: 推导式不是必须的——任何推导式都可以用 for 循环写。
#      但推导式更简洁、更快（C 层面优化），可读性也更好（声明式）。
# ══════════════════════════════════════════════════════════════

def demo_vs_for_loop():
    print("=" * 50)
    print(" 4. 推导式 vs for 循环 —— 同样的事，不同写法")
    print("=" * 50)

    prices = [299, 49, 29, 79]

    # 方式A: for 循环（5行）
    discounted_a = []
    for p in prices:
        if p > 50:
            discounted_a.append(p * 0.9)
    print(f" for 循环: {discounted_a}")

    # 方式B: 列表推导式（1行）
    discounted_b = [p * 0.9 for p in prices if p > 50]
    print(f" 推导式:   {discounted_b}")

    print(f" 结果相同: {discounted_a == discounted_b}")
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║  Python 基础 04: 推导式                       ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    demo_list_comprehension()
    demo_dict_comprehension()
    demo_set_comprehension()
    demo_vs_for_loop()


if __name__ == "__main__":
    main()
