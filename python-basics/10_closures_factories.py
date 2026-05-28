# -*- coding: utf-8 -*-
"""
10_closures_factories.py — 闭包与工厂函数
=========================================

【概念】
闭包（Closure）：函数内部定义的函数，能"记住"外部函数的变量，
              即使外部函数已经执行完毕。
              
工厂函数（Factory）：返回函数的函数——根据参数批量生成不同行为的函数。

两者关系：工厂函数是闭包最常见的应用场景。

【在智能客服中的应用】
- 工厂函数生成不同风格的回复模板（友好型/专业型/幽默型）
- 工具函数批量生成——闭包记住不同的工具配置
- LangGraph 节点工厂——make_result_fn("approved") 返回不同策略的节点函数

真实代码案例（来自 demo 11）：
  def make_result_fn(label: str):
      def result_fn(state):    ← 闭包: result_fn 记住了 label
          ...
      return result_fn          ← 工厂: 返回一个函数

  approved_fn = make_result_fn("approved")  ← 生成的函数自带 "approved" 标签

【ASCII 架构图】

  make_result_fn("approved")     →    result_fn(state) { 记住 label="approved" }
  make_result_fn("rejected")     →    result_fn(state) { 记住 label="rejected" }
  make_result_fn("escalated")    →    result_fn(state) { 记住 label="escalated" }

       工厂函数                           三个行为不同的闭包函数
"""


# ══════════════════════════════════════════════════════════════
# 1. 闭包基础 —— 内层函数"记住"外层变量
# WHY: 内层函数可以访问外层函数的变量，即使外层函数已经 return——
#      这个"记住"的能力就是闭包，是工厂函数的底层机制。
# ══════════════════════════════════════════════════════════════

def demo_closure_basics():
    print("=" * 50)
    print(" 1. 闭包 —— 内层函数记住外层变量")
    print("=" * 50)

    def make_greeter(agent_name: str):
        """
        返回一个"记住客服名字"的问候函数。
        WHY: agent_name 是 make_greeter 的局部变量——
             greet() 能访问它，即使 make_greeter() 已经执行完毕。
             这就是闭包：函数 + 它捕获的外部变量。
        """
        def greet(customer: str) -> str:
            # WHY: agent_name 来自外层函数，被 greet "捕获"了
            return f"{agent_name}: 您好{customer}，有什么可以帮您？"
        return greet

    # 生成两个不同名字的客服函数
    greet_xiaoxuan = make_greeter("小选")
    greet_xiaomei = make_greeter("小美")

    print(f" {greet_xiaoxuan('张先生')}")
    print(f" {greet_xiaomei('李女士')}")
    print()


# ══════════════════════════════════════════════════════════════
# 2. 工厂函数 —— 批量生成工具函数
# WHY: Agent 有多个功能相似的工具（查订单、查物流、查政策）——
#      不用每个手写一遍，用工厂函数基于配置批量生成。
# ══════════════════════════════════════════════════════════════

def demo_factory_tools():
    print("=" * 50)
    print(" 2. 工厂函数 —— 批量生成 Agent 工具")
    print("=" * 50)

    # 模拟数据库
    DB = {
        "ORD001": {"product": "耳机", "price": 299, "status": "已签收"},
        "ORD002": {"product": "手机壳", "price": 49, "status": "运输中"},
    }

    def make_query_tool(data_source: dict, tool_name: str):
        """
        工厂：生成查询工具函数。
        WHY: data_source 和 tool_name 被闭包捕获——
             同一个 make_query_tool 可以生成查订单、查政策、查物流等
             任意数量的查询工具，每个工具"记住"自己的数据源和名称。
        """
        def query(key: str) -> str:
            result = data_source.get(key)
            if result is None:
                return f"[{tool_name}] 未找到: {key}"
            return f"[{tool_name}] {key} → {result}"

        # WHY: 在函数上挂属性，方便注册表读取工具信息
        query.tool_name = tool_name
        return query

    # 批量生成工具——两行代码生成 N 个工具
    query_order = make_query_tool(DB, "订单查询")
    query_policy = make_query_tool(
        {"退货": "7天内未拆封可退", "换货": "15天内质量问题可换"},
        "政策查询"
    )

    # 生成的函数各司其职
    print(f" {query_order('ORD001')}")
    print(f" {query_order('ORD999')}")
    print(f" {query_policy('退货')}")
    print(f" {query_policy('保修')}")
    print()


# ══════════════════════════════════════════════════════════════
# 3. 带配置的工厂 —— LangGraph 节点工厂模式
# WHY: 这是 demo 11 中实际使用的模式——
#      每个节点函数行为不同但结构相同，工厂函数让 20 行代码变成 3 行。
# ══════════════════════════════════════════════════════════════

def demo_node_factory():
    print("=" * 50)
    print(" 3. 节点工厂 —— LangGraph 节点生成")
    print("=" * 50)

    # 模拟不同的回复策略
    REPLY_TEMPLATES = {
        "approved": "恭喜！您的退款申请 {order_id} 已批准，¥{amount} 原路退回。",
        "rejected": "抱歉，订单 {order_id} 不符合退款条件，建议联系人工客服。",
        "escalated": "订单 {order_id} 情况复杂，已升级人工处理，请稍候。",
    }

    def make_result_node(decision: str):
        """
        生成特定决策的结果节点函数。
        WHY: decision 被闭包记住——3 行代码生成 3 个不同行为的节点，
             对比手写 3 个节点函数（每个 5 行 = 15 行）。
             且新增决策类型只需加一个模板，不用改任何生成逻辑。
        """
        template = REPLY_TEMPLATES.get(decision, "处理中...")

        def result_fn(order_id: str, amount: float = 0) -> str:
            return template.format(order_id=order_id, amount=amount)

        return result_fn

    # 三行代码生成三个节点
    approved_node = make_result_node("approved")
    rejected_node = make_result_node("rejected")
    escalated_node = make_result_node("escalated")

    # 测试
    test_order = "ORD001"
    print(f" 批准节点: {approved_node(test_order, 299.0)}")
    print(f" 拒绝节点: {rejected_node(test_order)}")
    print(f" 升级节点: {escalated_node(test_order)}")
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║  Python 基础 10: 闭包与工厂函数               ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    demo_closure_basics()
    demo_factory_tools()
    demo_node_factory()


if __name__ == "__main__":
    main()
