# -*- coding: utf-8 -*-
"""
07_tuple_set.py — 元组与集合：不可变容器与去重运算
==================================================

【概念】
tuple: 不可变的序列——一旦创建，不能增删改。用 () 或直接逗号分隔。
set:   无序、不重复的集合——自动去重，支持交/并/差集运算。用 {} 或 set()。

选择指南：
  需要修改内容 → list
  不需要修改、用作 key → tuple
  需要去重、集合运算 → set

【在智能客服中的应用】
- tuple: 函数返回多个值（订单号, 状态, 金额）
- tuple: dict 的 key——如 {(user_id, order_id): session}
- set:   提取唯一品类列表做筛选器
- set:   两个用户群的交集/差集分析

【ASCII 架构图】

  tuple（不可变）                     set（自动去重）
  ──────────────                     ─────────────

  ("ORD001", "已签收", 299)          {"耳机", "手机壳", "充电器"}
        │  │     │                       │
        │  │     └── 价格                │  {"耳机","手机壳","充电器","耳机"}
        │  └── 状态                      │   → {"耳机","手机壳","充电器"}
        └── 订单号                       │
                                         │
  index 访问: t[0] → "ORD001"         交: A & B  并: A | B  差: A - B
"""

# ══════════════════════════════════════════════════════════════
# 1. tuple 基础 —— 不可变序列
# WHY: 函数返回多个值时 Python 自动打包成 tuple——
#      order_id, status, amount = get_order() 这个解包
#      就是 tuple 的 unpacking。
# ══════════════════════════════════════════════════════════════

def demo_tuple_basics():
    print("=" * 50)
    print(" 1. tuple 基础 —— 多值返回与解包")
    print("=" * 50)

    def get_order_summary(order_id: str):
        """
        返回订单摘要。
        WHY: return a, b, c 就是 return (a, b, c)——
             Python 自动打包成 tuple，调用方自动解包。
        """
        mock_db = {
            "ORD001": ("漫步者 W820NB", "已签收", 299.0),
            "ORD002": ("手机壳", "运输中", 49.0),
        }
        if order_id in mock_db:
            product, status, price = mock_db[order_id]  # tuple 解包
            return product, status, price                # 自动打包为 tuple
        return "未知", "不存在", 0.0

    # tuple 解包——三个变量同时赋值
    name, status, price = get_order_summary("ORD001")
    print(f" 商品: {name}, 状态: {status}, 价格: ¥{price}")

    name, status, price = get_order_summary("ORD002")
    print(f" 商品: {name}, 状态: {status}, 价格: ¥{price}")

    # tuple 不可变——这会报错:
    # t = (1, 2, 3)
    # t[0] = 99  # TypeError: 'tuple' object does not support item assignment
    print()


# ══════════════════════════════════════════════════════════════
# 2. tuple 作为 dict key —— 复合键
# WHY: dict 的 key 必须是"可哈希"的——list 可变所以不能做 key，
#      tuple 不可变所以可以。
#      复合 key 场景: 同时按用户+订单查询缓存。
# ══════════════════════════════════════════════════════════════

def demo_tuple_as_key():
    print("=" * 50)
    print(" 2. tuple 作为 dict key —— 复合键")
    print("=" * 50)

    # WHY: (user_id, order_id) 做复合 key——
    #      同一用户对不同订单有独立 session
    sessions = {
        ("U001", "ORD001"): {"round": 3, "intent": "退货", "satisfaction": 4},
        ("U001", "ORD002"): {"round": 1, "intent": "查物流", "satisfaction": 0},
        ("U002", "ORD001"): {"round": 2, "intent": "咨询", "satisfaction": 5},
    }

    key = ("U001", "ORD001")
    info = sessions[key]
    print(f" 用户{key[0]} 订单{key[1]}: "
          f"意图={info['intent']}, 轮次={info['round']}")

    # 这里不能用 list 做 key
    # sessions[["U001","ORD001"]] = {}  # TypeError!
    print()


# ══════════════════════════════════════════════════════════════
# 3. set 基础 —— 去重
# WHY: 集合最核心的能力就是自动去重——
#      从几千条订单里提取"有哪些品类"，一行 set comprehension 搞定。
# ══════════════════════════════════════════════════════════════

def demo_set_basics():
    print("=" * 50)
    print(" 3. set 基础 —— 去重")
    print("=" * 50)

    # 模拟所有订单的品类（含大量重复）
    all_categories = ["耳机", "手机壳", "耳机", "充电器",
                      "手机壳", "耳机", "数据线", "手机壳"]

    unique_categories = set(all_categories)
    # WHY: set 自动去重——3个"耳机"变1个
    print(f" 原始数量: {len(all_categories)} 条")
    print(f" 唯一品类: {unique_categories}")

    # 客服筛选器通常还要排个序
    sorted_categories = sorted(unique_categories)
    print(f" 筛选器选项: {sorted_categories}")
    print()


# ══════════════════════════════════════════════════════════════
# 4. 集合运算 —— 交集、并集、差集
# WHY: & | - 运算符在集合上有特殊含义——
#      客服数据分析：买了A又买了B的用户（交集）
#                  只咨询没下单的用户（差集）
# ══════════════════════════════════════════════════════════════

def demo_set_operations():
    print("=" * 50)
    print(" 4. 集合运算 —— 用户群分析")
    print("=" * 50)

    # 模拟客服数据
    chatted_users = {"U001", "U002", "U003", "U005"}    # 咨询过的用户
    ordered_users = {"U002", "U003", "U004", "U006"}     # 下单的用户
    complained_users = {"U002", "U005"}                   # 投诉的用户

    # 交集 &: 咨询且下单——高意向用户
    high_intent = chatted_users & ordered_users
    print(f" 咨询并下单: {high_intent}  (高意向用户)")

    # 差集 -: 咨询但没下单——需要跟进的
    not_converted = chatted_users - ordered_users
    print(f" 咨询未下单: {not_converted}  (需跟进)")

    # 并集 |: 所有触达过的用户
    all_touched = chatted_users | ordered_users
    print(f" 触达总数:   {len(all_touched)} 人")

    # 复杂分析: 下单+投诉的用户
    problem_users = ordered_users & complained_users
    print(f" 下单且投诉: {problem_users}  (需人工回访)")
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║  Python 基础 07: 元组与集合                   ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    demo_tuple_basics()
    demo_tuple_as_key()
    demo_set_basics()
    demo_set_operations()


if __name__ == "__main__":
    main()
