# -*- coding: utf-8 -*-
"""
13_inheritance.py — 继承：父类与子类、super()、方法重写
=======================================================

【概念】
继承是"子类自动获得父类的属性和方法"的机制——子类在父类的基础上
增加或修改功能，不用重新写一遍。

核心三要素：
  继承语法: class Child(Parent) —— Child 自动拥有 Parent 的一切
  super():   调用父类的方法——"先做父类的事，再做我自己的"
  方法重写:  子类定义同名方法覆盖父类——多态的基础

【在智能客服中的应用】
- 基础 Agent → 售前Agent / 售后Agent / 物流Agent（继承 + 特化）
- ChromaDB 的 EmbeddingFunction → BGEEmbedding（demo 04 中用过）
- 自定义异常: class OrderNotFoundError(BusinessError)

真实代码案例（来自 demo 04）：
  class BGEEmbedding(EmbeddingFunction):  ← 继承 ChromaDB 的基类
      def __call__(self, input):           ← 重写 __call__ 方法
          return model.encode(input)

【ASCII 架构图】

  BaseAgent (父类/基类)
  ├── name, model
  ├── chat()            ← 通用 LLM 调用
  └── greet()           ← 通用问候
       │
       ├──▶ PreSaleAgent(BaseAgent)     ← 售前客服
       │    └── respond() 重写           ← 重写回答策略
       │
       └──▶ AfterSaleAgent(BaseAgent)   ← 售后客服
            └── respond() 重写           ← 重写回答策略
"""


# ══════════════════════════════════════════════════════════════
# 1. 继承基础 —— 子类获得父类的方法
# WHY: 继承消除重复代码——多个 Agent 共享的 chat()/log() 放父类，
#      每个子类只需要实现自己特化的 respond()。
# ══════════════════════════════════════════════════════════════

def demo_basic_inheritance():
    print("=" * 50)
    print(" 1. 继承基础 —— 子类复用父类代码")
    print("=" * 50)

    class BaseAgent:
        """所有客服 Agent 的基类——定义共用的属性和方法"""

        def __init__(self, name: str):
            self.name = name
            self.platform = "好买电商"

        def greet(self, customer: str) -> str:
            # WHY: 所有子类 Agent 都需要问候——放父类统一实现
            return f"您好{customer}，我是{self.platform}客服{self.name}"

        def log(self, message: str):
            """统一日志格式——所有子类共用"""
            print(f" [{self.name}] {message}")

    # WHY: PreSaleAgent(BaseAgent) → 继承 BaseAgent 的所有方法
    class PreSaleAgent(BaseAgent):
        """售前客服——继承 BaseAgent，只添加售前特有逻辑"""

        def recommend(self, budget: float) -> str:
            """售前特有方法——推荐商品"""
            if budget < 100:
                return "推荐 QCY T13，性价比之选 ¥99"
            elif budget < 500:
                return "推荐 漫步者 W820NB，降噪好 ¥299"
            return "推荐 索尼 WH-1000XM5，旗舰降噪 ¥2499"

    class AfterSaleAgent(BaseAgent):
        """售后客服——继承 BaseAgent，添加售后特有逻辑"""

        def check_warranty(self, days: int) -> str:
            """售后特有方法——检查保修"""
            if days <= 7:
                return "在 7 天退货期内，可全额退款"
            elif days <= 15:
                return "在 15 天换货期内，可换新"
            return "已过保修期，建议付费维修"

    # 使用：子类自动拥有父类的 greet() 和 log()
    pre = PreSaleAgent("小选")
    after = AfterSaleAgent("小修")

    print(f" {pre.greet('张先生')}")
    print(f" 售前推荐: {pre.recommend(300)}")
    pre.log("已推荐耳机给用户张先生")

    print(f"\n {after.greet('李女士')}")
    print(f" 售后检查: {after.check_warranty(10)}")
    after.log("已检查订单 ORD001 的保修状态")
    print()


# ══════════════════════════════════════════════════════════════
# 2. super() —— 调用父类方法
# WHY: super() 让子类"在父类的基础上扩展"——
#      先调 super().__init__() 完成父类的初始化，再添加自己的属性。
#      这样父类 __init__ 的逻辑只在父类里维护一份。
# ══════════════════════════════════════════════════════════════

def demo_super():
    print("=" * 50)
    print(" 2. super() —— 扩展父类方法")
    print("=" * 50)

    class BaseAgent:
        def __init__(self, name: str):
            self.name = name
            self.history = []

    class AdvancedAgent(BaseAgent):
        """
        升级版 Agent——继承 BaseAgent，增加 LLM 配置。
        WHY: super().__init__(name) 先让父类初始化 name 和 history，
             然后才设置自己的 model 和 temperature——
             不重复父类的初始化代码。
        """
        def __init__(self, name: str, model: str = "deepseek-v4",
                     temperature: float = 0.1):
            super().__init__(name)   # WHY: 先调父类 __init__，设置 name/history
            self.model = model        # 再设置子类独有的属性
            self.temperature = temperature

        def get_config(self) -> dict:
            return {
                "name": self.name,        # 来自父类 __init__
                "history_len": len(self.history),  # 来自父类 __init__
                "model": self.model,      # 子类独有
                "temperature": self.temperature,  # 子类独有
            }

    agent = AdvancedAgent("小选", temperature=0.3)
    print(f" 配置: {agent.get_config()}")
    print()


# ══════════════════════════════════════════════════════════════
# 3. 方法重写 —— 子类覆盖父类行为
# WHY: 子类可以定义和父类同名的方法，完全替代父类的实现——
#      多态的底层机制。不同子类、同名方法、不同行为。
# ══════════════════════════════════════════════════════════════

def demo_override():
    print("=" * 50)
    print(" 3. 方法重写 —— 多态")
    print("=" * 50)

    class BaseAgent:
        def respond(self, question: str) -> str:
            return "我无法处理这个问题"

    class OrderAgent(BaseAgent):
        def respond(self, question: str) -> str:
            # WHY: 同名方法完全覆盖父类实现
            return f"正在查询订单相关: {question[:20]}..."

    class PolicyAgent(BaseAgent):
        def respond(self, question: str) -> str:
            return f"根据平台政策回复: {question[:20]}..."

    # 统一调用 respond()，不同子类不同行为
    agents = [OrderAgent(), PolicyAgent(), BaseAgent()]
    question = "我能退货吗？"

    for agent in agents:
        cls_name = type(agent).__name__
        print(f" {cls_name}: {agent.respond(question)}")
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║  Python 基础 13: 继承与多态                   ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    demo_basic_inheritance()
    demo_super()
    demo_override()


if __name__ == "__main__":
    main()
