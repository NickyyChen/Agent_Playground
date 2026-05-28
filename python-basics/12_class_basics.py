# -*- coding: utf-8 -*-
"""
12_class_basics.py — 类基础：class、__init__、self、实例方法
============================================================

【概念】
class 是把"数据 + 操作数据的方法"打包在一起的代码组织方式。
对比：
  纯函数：数据放 dict、函数独立存在、到处传数据
  类：数据（属性）+ 方法 绑定在一起，self 引用自身

三个核心要素：
  __init__:  初始化方法——创建实例时自动调用，设置初始状态
  self:      代表"这个实例本身"——通过 self 访问自己的属性和方法
  实例方法:  定义在 class 内的 def，第一个参数必须是 self

【在智能客服中的应用】
- Agent 类：封装 LLM 调用 + 工具管理 + 记忆管理
- OrderService 类：封装订单业务逻辑（demo 03 中用过）
- CustomerSession 类：管理单个客户的对话状态

【ASCII 架构图】

  class CustomerSession:
      __init__(self, user_id)    ← 创建会话时自动调用
          self.user_id = user_id
          self.history = []      ← 每个实例独立的对话历史

      add_message(self, msg)     ← 实例方法，self 指向调用者
          self.history.append(msg)

  实例A: session_a = CustomerSession("U001")
          session_a.add_message("你好")     → session_a.history = ["你好"]

  实例B: session_b = CustomerSession("U002")
          session_b.add_message("退货")     → session_b.history = ["退货"]

  每个实例的数据独立，互不影响
"""


# ══════════════════════════════════════════════════════════════
# 1. __init__ 与 self —— 创建实例
# WHY: __init__ 是"构造函数"——创建实例时自动执行，
#      self 指向当前这个实例，通过 self.xxx 设置属性。
#      self 不是关键字但约定俗成必须叫 self。
# ══════════════════════════════════════════════════════════════

def demo_init_self():
    print("=" * 50)
    print(" 1. __init__ 与 self —— 客服会话类")
    print("=" * 50)

    class CustomerSession:
        """
        单个客户的对话会话。
        WHY: 把 user_id、history、状态 封装在一起——
             每个 session 实例是独立的空间，互不干扰。
        """
        def __init__(self, user_id: str, user_name: str = "未知"):
            # WHY: self.user_id 是实例属性——每个实例有自己的值
            self.user_id = user_id
            self.user_name = user_name
            self.history = []         # 对话历史，每个实例独立
            self.started_at = "2024-05-28"

        def add_message(self, role: str, content: str):
            """
            追加一条消息到对话历史。
            WHY: self.history 访问的是"这个实例的" history，
                 不同实例调用时 self 指向不同对象。
            """
            self.history.append({"role": role, "content": content})

        def get_summary(self) -> str:
            """返回会话摘要"""
            return (f"用户{self.user_name}({self.user_id}) "
                    f"共 {len(self.history)} 条消息")

    # 创建两个独立会话
    session_a = CustomerSession("U001", "张先生")
    session_b = CustomerSession("U002", "李女士")

    # 各自添加消息——数据独立
    session_a.add_message("user", "查订单 ORD001")
    session_a.add_message("assistant", "订单已签收，¥299")

    session_b.add_message("user", "我要退货")
    session_b.add_message("assistant", "请提供订单号")

    print(f" 会话A: {session_a.get_summary()}")
    print(f" 会话B: {session_b.get_summary()}")
    print(f" A的history ≠ B的history: {session_a.history != session_b.history}")
    print()


# ══════════════════════════════════════════════════════════════
# 2. 实例方法 —— 操作实例数据
# WHY: 方法就是定义在 class 内部的函数，第一个参数 self。
#      方法可以读写 self 上的属性——数据和行为绑定。
# ══════════════════════════════════════════════════════════════

def demo_methods():
    print("=" * 50)
    print(" 2. 实例方法 —— Agent 类")
    print("=" * 50)

    class SimpleAgent:
        """最简单的 Agent——封装 LLM 调用逻辑"""

        def __init__(self, name: str):
            self.name = name
            self.system_prompt = f"你是{name}，电商客服"

        def greet(self, customer: str) -> str:
            """生成问候语——使用实例的 name 属性"""
            return f"您好{customer}，我是{self.name}，有什么可以帮您？"

        def respond(self, question: str) -> str:
            """模拟回答——实际应用中这里调 LLM"""
            if "退货" in question:
                return "请提供订单号，我帮您查询退货资格。"
            elif "订单" in question:
                return "正在为您查询订单，请稍候..."
            return "请详细描述您的问题，我会尽力帮您解决。"

    agent = SimpleAgent("小选")
    print(f" {agent.greet('张先生')}")
    print(f" 用户: 我想退货")
    print(f" {agent.name}: {agent.respond('我想退货')}")
    print()


# ══════════════════════════════════════════════════════════════
# 3. 类属性 vs 实例属性
# WHY: 类属性是所有实例共享的（定义在 class 下、方法外），
#      实例属性是每个实例独立的（定义在 __init__ 的 self 上）。
#      共享 vs 独立的区别很重要——搞混是常见的 bug 来源。
# ══════════════════════════════════════════════════════════════

def demo_class_vs_instance():
    print("=" * 50)
    print(" 3. 类属性 vs 实例属性")
    print("=" * 50)

    class CSAgent:
        # WHY: 类属性——所有 Agent 实例共享（平台名不变）
        platform = "好买电商"

        def __init__(self, name: str):
            # WHY: 实例属性——每个 Agent 实例独立（名字不同）
            self.name = name
            self.total_chats = 0

        def handle_chat(self):
            self.total_chats += 1

    agent1 = CSAgent("小选")
    agent2 = CSAgent("小美")

    # 修改实例属性——只影响自己
    agent1.handle_chat()
    agent1.handle_chat()
    agent2.handle_chat()

    print(f" 类属性 platform:")
    print(f"   agent1.platform = {agent1.platform}")
    print(f"   agent2.platform = {agent2.platform}")
    print(f"   两者相同: {agent1.platform == agent2.platform}")

    print(f"\n 实例属性 total_chats:")
    print(f"   agent1({agent1.name}) = {agent1.total_chats} 次")
    print(f"   agent2({agent2.name}) = {agent2.total_chats} 次")
    print(f"   两者独立: {agent1.total_chats != agent2.total_chats}")
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║  Python 基础 12: 类基础                       ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    demo_init_self()
    demo_methods()
    demo_class_vs_instance()


if __name__ == "__main__":
    main()
