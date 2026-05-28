# -*- coding: utf-8 -*-
"""
03_control_flow.py — 控制流：条件判断与循环
===========================================

【概念】
控制流决定代码的执行路径：
  if/elif/else —— 条件分支（根据状态走不同逻辑）
  for ... in ...—— 遍历循环（逐条处理数据）
  while ........—— 条件循环（不确定次数，直到满足条件）
  break/continue— 循环控制（提前退出 / 跳过本轮）

【在智能客服中的应用】
- 根据订单状态走不同处理流程（if/elif）
- 批量查询多个订单（for）
- Agent 思考循环直到找到答案（while 是 ReAct Agent 的核心）

【ASCII 架构图】

  订单状态
     │
     ▼
  ┌─────────────────────┐
  │ if status=="运输中"  │──▶ "预计明天送达"
  │ elif status=="已签收"│──▶ "可申请售后"
  │ elif status=="已取消"│──▶ "该订单已取消"
  │ else:               │──▶ "状态未知"
  └─────────────────────┘
"""

# ══════════════════════════════════════════════════════════════
# 1. if/elif/else —— 条件分支
# WHY: 客服系统中最常见的是"根据订单状态走不同处理流程"——
#      每种状态对应不同的业务逻辑，if/elif 是最直接的表达。
# ══════════════════════════════════════════════════════════════

def demo_if_elif():
    print("=" * 50)
    print(" 1. if/elif/else —— 订单状态路由")
    print("=" * 50)

    def handle_order(order: dict):
        """
        根据订单状态返回不同的处理指令。
        WHY: 每种状态对应不同的客服话术和操作——
             if/elif 链让每个分支独立清晰。
        """
        status = order["status"]

        if status == "待支付":
            action = "请尽快完成支付，超时订单将自动取消"
        elif status == "已支付":
            action = "订单已确认，仓库正在备货中"
        elif status == "运输中":
            action = f"快递单号 {order.get('tracking', '暂无')}，预计 3 天送达"
        elif status == "已签收":
            action = "订单已签收，7天内可申请退换货"
        elif status == "已取消":
            action = "订单已取消，如有疑问请联系人工客服"
        else:
            action = "订单状态异常，已转人工处理"

        return action

    # WHY: 遍历多种状态，验证每个分支都能命中
    orders = [
        {"id": "ORD001", "status": "待支付"},
        {"id": "ORD002", "status": "已支付"},
        {"id": "ORD003", "status": "运输中", "tracking": "SF123456"},
        {"id": "ORD004", "status": "已签收"},
        {"id": "ORD005", "status": "已取消"},
    ]

    for order in orders:
        result = handle_order(order)
        print(f" {order['id']} ({order['status']}): {result}")
    print()


# ══════════════════════════════════════════════════════════════
# 2. for 循环 —— 批量处理
# WHY: 客服系统需要批量操作——检查多个订单、遍历工具返回结果、
#      解析 LLM 输出的 token。for 是最高频的循环。
# ══════════════════════════════════════════════════════════════

def demo_for_loop():
    print("=" * 50)
    print(" 2. for 循环 —— 批量订单处理")
    print("=" * 50)

    # 模拟 RAG 搜索结果——多个商品匹配
    search_results = [
        {"name": "漫步者 W820NB", "price": 299, "score": 0.95},
        {"name": "索尼 WH-1000XM5", "price": 2499, "score": 0.88},
        {"name": "AirPods Pro", "price": 1899, "score": 0.72},
    ]

    # enumerate 同时拿到索引和值，i 从 0 开始
    for i, item in enumerate(search_results):
        rank = i + 1
        if item["score"] > 0.9:
            tag = "[强推荐]"
        elif item["score"] > 0.7:
            tag = "[推荐]"
        else:
            tag = ""
        print(f" {rank}. {item['name']} ¥{item['price']} "
              f"(匹配度: {item['score']:.0%}) {tag}")
    print()


# ══════════════════════════════════════════════════════════════
# 3. while 循环 + break —— Agent 思考循环
# WHY: while 用于"不知道要循环多少次"的场景——
#      Agent 的 ReAct 循环就是 while: 只要没找到答案就继续。
#      break 在"够了"时提前退出，continue 跳过本轮继续下一轮。
# ══════════════════════════════════════════════════════════════

def demo_while_loop():
    print("=" * 50)
    print(" 3. while + break —— 模拟 Agent 思考循环")
    print("=" * 50)

    max_rounds = 5                     # WHY: 安全阀——防止死循环
    found = False
    round_num = 0
    target = "订单已签收，3天前"

    while round_num < max_rounds and not found:
        round_num += 1
        # 模拟每轮"思考"获取的信息
        info_at_round = {
            1: "查到订单号 ORD001",
            2: "订单状态：已签收",
            3: "签收时间：3天前",
            4: "退换货政策：7天内可退",
            5: "可以退款 ¥299",
        }
        info = info_at_round[round_num]
        print(f" 第{round_num}轮: {info}")

        if target in info:
            print(f"   → 找到目标信息，停止循环！")
            found = True
            # WHY: break 立即退出 while，不执行后续轮次
            #      类比 Agent: 确认可以回答用户时就 break

    if not found:
        print(f"  → 达到最大轮次 {max_rounds}，强制停止")
    print()


# ══════════════════════════════════════════════════════════════
# 4. range() —— 生成数字序列
# WHY: range(n) 生成 0 到 n-1 的数字序列，常用于
#      "重复 N 次"的循环。range(start, stop, step) 可以指定起止和步长。
# ══════════════════════════════════════════════════════════════

def demo_range():
    print("=" * 50)
    print(" 4. range() 的三种用法")
    print("=" * 50)

    # 用法1: range(n) → 0, 1, ..., n-1
    print(" range(5):    ", list(range(5)))

    # 用法2: range(start, stop) → start, start+1, ..., stop-1
    print(" range(2, 7):  ", list(range(2, 7)))

    # 用法3: range(start, stop, step) → 带步长
    print(" range(1, 10, 2):", list(range(1, 10, 2)))

    # 客服场景：生成分页页码
    total_pages = 5
    print(f"\n 订单分页（共{total_pages}页）:")
    for page in range(1, total_pages + 1):
        print(f"   第 {page} 页", end="")
        if page != total_pages:
            print(" →", end="")
    print()
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║  Python 基础 03: 控制流                      ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    demo_if_elif()
    demo_for_loop()
    demo_while_loop()
    demo_range()


if __name__ == "__main__":
    main()
