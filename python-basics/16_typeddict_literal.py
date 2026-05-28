# -*- coding: utf-8 -*-
"""
16_typeddict_literal.py — TypedDict 与 Literal：精确类型约束
============================================================

【概念】
Python 的类型系统有两套工具用于精确约束：
  TypedDict: 定义 dict 的"形状"——有哪些字段、每个字段什么类型
  Literal:   约束值只能是某几个字符串——类似于"枚举"

普通 dict 注解: list[dict] — 只知道是 dict 列表，不知道 dict 里有什么
TypedDict:      list[OrderDict] — 知道每个 dict 必有 order_id: str, price: float

【在智能客服中的应用】
- TypedDict: LangGraph State 定义——每个节点精准知道 state 有哪些字段
- Literal:   LangGraph 条件路由——返回值只能是 "approved"|"rejected"|"escalated"
- Literal:   工具参数 action: Literal["query", "create", "delete"]

真实代码案例（来自 demo 11）：
  class RefundState(TypedDict):
      user_input: str
      order_id: str
      decision: str

  def decision_router(state) -> Literal["approved", "rejected", "escalated"]:
      ...

【ASCII 架构图】

  dict vs TypedDict:

  dict 注解:                                       TypedDict 注解:
  {"name": "...", "price": 299}                    class Product(TypedDict):
       │                                              name: str
       │  IDE 不知道里面有什么字段                       price: float
       │  无法自动补全                                  │
       │                                             IDE 知道字段，自动补全
       ▼                                              ▼
  def f(item: dict): ...                          def f(item: Product): ...
"""

from typing import TypedDict, Literal


# ══════════════════════════════════════════════════════════════
# 1. TypedDict —— 定义 dict 的"形状"
# WHY: 普通 dict 注解太粗糙——不知道里面有什么字段。
#      TypedDict 精确描述 dict 结构，IDE 会做字段补全和类型检查。
#      LangGraph 的 State 就是用 TypedDict 定义的。
# ══════════════════════════════════════════════════════════════

def demo_typeddict():
    print("=" * 50)
    print(" 1. TypedDict —— 定义 dict 的形状")
    print("=" * 50)

    # WHY: 继承 TypedDict，声明每个字段的类型——
    #      IDE 会知道 order_id 是 str、price 是 float
    class OrderInfo(TypedDict):
        order_id: str
        product: str
        price: float
        status: str

    class AgentState(TypedDict):
        """Agent 的共享状态——类似 LangGraph State"""
        user_input: str
        intent: str
        order_info: dict
        decision: str
        response: str

    # 创建符合 TypedDict 的 dict
    order: OrderInfo = {
        "order_id": "ORD001",
        "product": "漫步者 W820NB",
        "price": 299.0,
        "status": "已签收",
    }

    state: AgentState = {
        "user_input": "我要退货",
        "intent": "",
        "order_info": order,
        "decision": "",
        "response": "",
    }

    print(f" OrderInfo 字段: {list(OrderInfo.__annotations__.keys())}")
    print(f" AgentState 字段: {list(AgentState.__annotations__.keys())}")
    print(f" Order 数据: {order['product']} ¥{order['price']}")
    print()


# ══════════════════════════════════════════════════════════════
# 2. Literal —— 值只能是某几个字符串
# WHY: Literal["a", "b", "c"] 限制参数/返回值只能是这几个字面量——
#      LangGraph 条件路由中，返回值必须是节点名字符串，
#      Literal 让 IDE 能自动补全和检查拼写错误。
# ══════════════════════════════════════════════════════════════

def demo_literal():
    print("=" * 50)
    print(" 2. Literal —— 限定值的范围")
    print("=" * 50)

    # WHY: Literal 限定 decision 只能是这三个值之一——
    #      IDE 会补全这三个选项，传错值 IDE 直接标红。
    #      这就是 LangGraph add_conditional_edges 的模式。
    def make_decision(order_status: str) -> Literal["approved",
                                                     "rejected",
                                                     "escalated"]:
        """根据订单状态做退款决策"""
        if order_status == "已签收":
            return "approved"
        elif order_status == "已取消":
            return "rejected"
        else:
            return "escalated"

    Status = Literal["待支付", "已支付", "运输中", "已签收", "已取消"]

    def handle_order(status: Status) -> str:
        """处理订单——status 只能是那5个状态之一"""
        actions = {
            "待支付": "催付",
            "已支付": "备货",
            "运输中": "查物流",
            "已签收": "可售后",
            "已取消": "已结束",
        }
        return actions.get(status, "未知")

    # 测试
    print(f" 决策 '已签收' → {make_decision('已签收')}")
    print(f" 决策 '已取消' → {make_decision('已取消')}")
    print(f" 处理 '运输中' → {handle_order('运输中')}")
    print()


# ══════════════════════════════════════════════════════════════
# 3. 实战：LangGraph 风格的条件路由
# WHY: 这是 demo 11 的精简版——展示 TypedDict + Literal
#      如何精确描述 LangGraph 工作流。
# ══════════════════════════════════════════════════════════════

def demo_langgraph_style():
    print("=" * 50)
    print(" 3. 实战 —— LangGraph 风格的类型定义")
    print("=" * 50)

    class RefundState(TypedDict):
        """退款审批的共享状态——每个节点读写这个 dict"""
        user_input: str
        order_id: str
        order_status: str
        decision: str

    Decision = Literal["approved", "rejected", "escalated"]

    def policy_node(state: RefundState) -> dict:
        """
        政策匹配节点。
        WHY: 返回 dict 而非完整 state——
             LangGraph 会自动把返回的 dict 合并到 state 中。
        """
        status = state.get("order_status", "")
        if status == "已签收":
            return {"decision": "approved"}
        elif status == "已取消":
            return {"decision": "rejected"}
        return {"decision": "escalated"}

    def decision_router(state: RefundState) -> Decision:
        """
        条件路由——返回值决定走哪个分支。
        WHY: Literal["approved","rejected","escalated"] 确保
             IDE 能检查返回值是否合法。
        """
        return state["decision"]

    # 模拟流程
    state: RefundState = {
        "user_input": "我要退货",
        "order_id": "ORD001",
        "order_status": "已签收",
        "decision": "",
    }

    # 执行政策节点
    update = policy_node(state)
    state.update(update)
    route = decision_router(state)

    print(f" State: {state}")
    print(f" 路由结果: → {route}")
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║  Python 基础 16: TypedDict 与 Literal        ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    demo_typeddict()
    demo_literal()
    demo_langgraph_style()


if __name__ == "__main__":
    main()
