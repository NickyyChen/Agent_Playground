# -*- coding: utf-8 -*-
"""
11_lambda.py — lambda 表达式与高阶函数
======================================

【概念】
lambda 是单行匿名函数——不需要 def + 名字，直接写逻辑。
语法：lambda 参数: 返回值表达式

它和普通函数的区别：
  - lambda 只能写单个表达式（不能多行、不能有语句）
  - lambda 不需要名字——适合"临时用一下"的场景
  - lambda 常作为参数传给高阶函数（sorted/map/filter）

【在智能客服中的应用】
- sorted(results, key=lambda x: x["score"]) —— 搜索结果按匹配度排序
- filter(lambda x: x["status"] == "已签收", orders) —— 过滤可退货订单
- 工具定义的参数 map 转换

【ASCII 架构图】

  普通函数                              lambda 等价写法
  ────────                              ──────────────

  def add(x):                  ←→       lambda x: x + 1
      return x + 1

  def by_score(item):          ←→       lambda item: item["score"]
      return item["score"]

  使用场景：sorted() 的 key 参数、map/filter 的第一个参数
"""


# ══════════════════════════════════════════════════════════════
# 1. lambda 基础 —— 对比 def
# WHY: lambda 是"用完即扔"的函数——
#      当函数体只有一个简单表达式时，lambda 比 def 更紧凑。
# ══════════════════════════════════════════════════════════════

def demo_lambda_basics():
    print("=" * 50)
    print(" 1. lambda vs def —— 同一个逻辑的两种写法")
    print("=" * 50)

    # def 写法——3行
    def add_one_def(x):
        return x + 1

    # lambda 写法——1行
    add_one_lambda = lambda x: x + 1

    print(f" def 版本:  {add_one_def(5)}")
    print(f" lambda 版本: {add_one_lambda(5)}")

    # lambda 多参数
    calc_total = lambda price, qty, discount=1.0: price * qty * discount
    print(f" 计算总价: ¥{calc_total(299, 2, 0.9):.2f}")
    print()


# ══════════════════════════════════════════════════════════════
# 2. lambda 作为 sorted 的 key —— 最常用场景
# WHY: sorted() 的 key 参数需要一个函数——
#      def 定义太啰嗦，lambda 一行正好。
#      这是 Agent 开发中 lambda 出现频率最高的场景。
# ══════════════════════════════════════════════════════════════

def demo_lambda_sort():
    print("=" * 50)
    print(" 2. sorted + lambda —— 搜索结果排序")
    print("=" * 50)

    results = [
        {"name": "索尼 WH-1000XM5", "score": 0.88, "price": 2499},
        {"name": "漫步者 W820NB", "score": 0.95, "price": 299},
        {"name": "AirPods Pro", "score": 0.72, "price": 1899},
        {"name": "QCY T13", "score": 0.91, "price": 99},
    ]

    # 按匹配度降序:
    by_score = sorted(results, key=lambda r: r["score"], reverse=True)
    print(" 按匹配度排序:")
    for r in by_score:
        print(f"   {r['name']:20s} 匹配度:{r['score']:.0%}")

    # 按性价比（score/price 比值）
    by_value = sorted(results, key=lambda r: r["score"] / r["price"],
                      reverse=True)
    print("\n 按性价比（匹配度÷价格）排序:")
    for r in by_value:
        print(f"   {r['name']:20s} 性价比:{r['score']/r['price']:.4f}")
    print()


# ══════════════════════════════════════════════════════════════
# 3. map / filter —— 批量转换与过滤
# WHY: map(函数, 列表) → 对每个元素执行函数，返回迭代器
#      filter(函数, 列表) → 保留函数返回 True 的元素
#      lambda 让 map/filter 的参数声明变得极其简洁。
# ══════════════════════════════════════════════════════════════

def demo_map_filter():
    print("=" * 50)
    print(" 3. map / filter + lambda")
    print("=" * 50)

    orders = [
        {"id": "ORD001", "price": 299, "status": "已签收"},
        {"id": "ORD002", "price": 49, "status": "运输中"},
        {"id": "ORD003", "price": 29, "status": "已签收"},
        {"id": "ORD004", "price": 79, "status": "已取消"},
    ]

    # filter: 保留已签收的订单
    delivered = list(filter(lambda o: o["status"] == "已签收", orders))
    print(f" 可售后订单: {[o['id'] for o in delivered]}")

    # map: 提取所有订单号+金额
    summaries = list(map(
        lambda o: f"{o['id']}: ¥{o['price']}", orders
    ))
    print(f" 订单摘要: {summaries}")

    # map: 价格转美元（模拟多币种）
    usd_prices = list(map(lambda o: round(o["price"] / 7.2, 2), orders))
    print(f" 美元价格: {usd_prices}")
    print()


# ══════════════════════════════════════════════════════════════
# 4. lambda vs 推导式 —— 什么时候用哪个
# WHY: 大多数场景下推导式比 map/filter + lambda 更可读——
#      [o for o in orders if o["status"]=="已签收"] vs
#      list(filter(lambda o: o["status"]=="已签收", orders))
#      但 sorted 的 key 参数必须传函数，lambda 是最佳选择。
# ══════════════════════════════════════════════════════════════

def demo_lambda_vs_comprehension():
    print("=" * 50)
    print(" 4. lambda vs 推导式 —— 选哪个？")
    print("=" * 50)

    orders = [
        {"id": "ORD001", "price": 299, "status": "已签收"},
        {"id": "ORD002", "price": 49, "status": "运输中"},
        {"id": "ORD003", "price": 29, "status": "已签收"},
    ]

    # 场景A: 过滤 —— 推导式更清晰
    method_a = [o for o in orders if o["price"] > 50]
    method_b = list(filter(lambda o: o["price"] > 50, orders))
    print(f" 过滤高价值订单:")
    print(f"   推导式: {[o['id'] for o in method_a]} ← 推荐")
    print(f"   lambda: {[o['id'] for o in method_b]}")

    # 场景B: 排序 key —— lambda 是唯一优雅的选择
    by_price = sorted(orders, key=lambda o: o["price"])
    print(f"\n 按价格排序: {[o['id'] for o in by_price]} ← lambda 最佳")
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║  Python 基础 11: lambda 表达式               ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    demo_lambda_basics()
    demo_lambda_sort()
    demo_map_filter()
    demo_lambda_vs_comprehension()


if __name__ == "__main__":
    main()
