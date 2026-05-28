# -*- coding: utf-8 -*-
"""
14_magic_methods.py — 魔术方法：__call__、__str__、__repr__
===========================================================

【概念】
魔术方法（Magic Methods / Dunder Methods）是 Python 中以双下划线
开头和结尾的特殊方法——它们不直接调用，由 Python 解释器在特定时机
自动触发。

最常用的三个：
  __call__: 让实例可以像函数一样被调用 obj()
  __str__:  定义 print(obj) 和 str(obj) 的输出（给人看的）
  __repr__: 定义 repr(obj) 和调试时的输出（给开发者看的）

【在智能客服中的应用】
- __call__: ChromaDB 的 EmbeddingFunction 接口——必须实现 __call__
- __call__: 可调用的 Agent 实例——agent(user_input) 直接返回回复
- __str__:  打印订单对象时显示为 "订单ORD001: 耳机 ¥299"

【ASCII 架构图】

  class Agent:
      def __call__(self, question):
          return self.respond(question)

  agent = Agent()

  普通调用:  agent.chat("你好")   ← 明确调用方法
  __call__:  agent("你好")        ← 实例像函数一样被调用，自动触发 __call__

  这就是为什么 EmbeddingFunction 子类必须实现 __call__——
  ChromaDB 调用的是 embedding_fn(documents)，不是 embedding_fn.encode(documents)
"""


# ══════════════════════════════════════════════════════════════
# 1. __call__ —— 让实例可调用
# WHY: __call__ 是 Agent 开发中接触最多的魔术方法——
#      ChromaDB 的 EmbeddingFunction 要求子类实现 __call__。
#      LangChain 的 Chain 也是通过 __call__ 让实例可调用。
# ══════════════════════════════════════════════════════════════

def demo_call():
    print("=" * 50)
    print(" 1. __call__ —— 让实例像函数一样调用")
    print("=" * 50)

    class SimpleAgent:
        """
        可调用的 Agent 实例。
        WHY: 实现 __call__ 后，agent("你好") 等价于 agent.__call__("你好")。
             这样 Agent 实例的使用方式和普通函数完全一致。
        """
        def __init__(self, name: str):
            self.name = name

        def __call__(self, question: str) -> str:
            """
            直接调用实例时触发。
            WHY: 这个接口让 Agent 的使用方式极简——
                 用户只需要 agent("问题") 一行代码。
            """
            if "退货" in question:
                return f"[{self.name}] 请提供订单号，我帮您处理退货"
            if "订单" in question:
                return f"[{self.name}] 正在查询，请稍候..."
            return f"[{self.name}] 您好！请问有什么可以帮您？"

    agent = SimpleAgent("小选")

    # 两种调用方式等价
    reply1 = agent("我想退货")           # __call__ 自动触发
    reply2 = agent.__call__("我想退货")   # 显式调用（不推荐）
    print(f" agent('我想退货'):  {reply1}")
    print(f" agent.__call__():    {reply2}")
    print(f" 两者相同: {reply1 == reply2}")
    print()


# ══════════════════════════════════════════════════════════════
# 2. __str__ 与 __repr__ —— 对象的字符串表示
# WHY: 默认打印对象显示 <__main__.Foo at 0x7f...> 毫无价值。
#      __str__ 定义给人看的描述，__repr__ 定义给开发者的调试信息。
# ══════════════════════════════════════════════════════════════

def demo_str_repr():
    print("=" * 50)
    print(" 2. __str__ 与 __repr__ —— 可读的输出")
    print("=" * 50)

    class Order:
        def __init__(self, order_id: str, product: str, price: float):
            self.order_id = order_id
            self.product = product
            self.price = price

        def __str__(self) -> str:
            """
            给人看的——print(order) 时自动调用。
            WHY: 客服日志中打印订单时，应该显示可读的摘要。
            """
            return f"订单{self.order_id}: {self.product} ¥{self.price}"

        def __repr__(self) -> str:
            """
            给开发者看的——调试时、列表打印时自动调用。
            WHY: repr 应该尽量返回"可执行"的表示——能复制到代码里重建对象。
            """
            return (f"Order(order_id='{self.order_id}', "
                    f"product='{self.product}', price={self.price})")

    order = Order("ORD001", "漫步者 W820NB", 299.0)

    # print() 调用 __str__
    print(f" print(order):  {order}")

    # repr() 调用 __repr__
    print(f" repr(order):   {repr(order)}")

    # 列表中的元素使用 __repr__
    orders = [order, Order("ORD002", "手机壳", 49.0)]
    print(f"\n 列表中的订单:")
    for o in orders:
        print(f"   {o}")
    print()


# ══════════════════════════════════════════════════════════════
# 3. 模拟 ChromaDB 的 EmbeddingFunction 接口
# WHY: 真实场景——demo 04 中继承了 ChromaDB 的 EmbeddingFunction，
#      必须实现 __call__ 方法供 ChromaDB 调用。
#      这里展示这个模式的核心原理。
# ══════════════════════════════════════════════════════════════

def demo_real_world():
    print("=" * 50)
    print(" 3. __call__ 实战 —— 模拟 EmbeddingFunction")
    print("=" * 50)

    class MockEmbeddingFunction:
        """
        模拟 ChromaDB 的 EmbeddingFunction 基类。
        WHY: ChromaDB 的约定——子类必须实现 __call__(input)，
             返回 List[List[float]] 格式的向量。
             ChromaDB 内部会调用 embedding_fn(documents)，而非手动调方法。
        """
        def __call__(self, documents):
            raise NotImplementedError("子类必须实现 __call__")

    # WHY: 继承并实现 __call__——这是 ChromaDB 的标准用法
    class ChineseEmbedding(MockEmbeddingFunction):
        """中文嵌入模型——实现 __call__"""

        def __call__(self, documents):
            """
            ChromaDB 把文档传进来，返回对应的向量。
            WHY: 必须叫 __call__——ChromaDB 的源码写的是 fn(docs)，
                 如果子类方法不叫 __call__，ChromaDB 调不到。
            """
            print(f" 将 {len(documents)} 条文档转为向量...")
            # 模拟向量化——实际场景用 SentenceTransformer
            return [[0.1 * (i + 1) * (j + 1) for j in range(3)]
                    for i in range(len(documents))]

    embedding_fn = ChineseEmbedding()
    docs = ["用户问退货流程", "用户查订单状态", "用户投诉质量问题"]

    # ChromaDB 的调用方式——直接调实例
    vectors = embedding_fn(docs)   # __call__ 触发

    print(f" 输入 {len(docs)} 条文档 → 输出 {len(vectors)} 个向量")
    for doc, vec in zip(docs, vectors):
        print(f"   '{doc}' → {vec}")
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║  Python 基础 14: 魔术方法                     ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    demo_call()
    demo_str_repr()
    demo_real_world()


if __name__ == "__main__":
    main()
