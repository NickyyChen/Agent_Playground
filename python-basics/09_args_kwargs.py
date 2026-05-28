# -*- coding: utf-8 -*-
"""
09_args_kwargs.py — *args 与 **kwargs：参数解包与透传
=====================================================

【概念】
*args   —— 接收任意数量的位置参数（打包成 tuple）
**kwargs —— 接收任意数量的关键字参数（打包成 dict）

反过来，在调用时：
*list   —— 把 list 解包成位置参数
**dict  —— 把 dict 解包成关键字参数

这是 Agent 开发中最重要的 Python 特性之一——**kwargs 参数透传
让你不需要在中间层函数里逐个声明参数。

【在智能客服中的应用】
- llm_client.chat() 用 **kwargs 透传 temperature/top_p/max_tokens 给 API
- 工具注册系统用 *args 接收不同工具的不同参数
- APIt rate **base_params 合并默认参数

【ASCII 架构图】

  调用方                         中间层                    底层 API
  ──────                        ──────                   ───────

  chat(messages,              def chat(                 client.create(
      temperature=0.1,           messages,                model="...",
      max_tokens=200)            **kwargs                  messages=...,
          │                        │                       temperature=0.1,
          │  temperature=0.1       │  **kwargs             max_tokens=200)
          │  max_tokens=200 ──────▶│  解包并传递 ────────▶
                                   │
                            kwargs = {"temperature":0.1,
                                      "max_tokens":200}
"""


# ══════════════════════════════════════════════════════════════
# 1. *args —— 接收任意数量的位置参数
# WHY: *args 让函数可以接受"不确定个数"的参数——
#      比如 log() 函数接受任意多条日志消息，内部把它们拼起来。
#      在函数体内 args 是一个 tuple。
# ══════════════════════════════════════════════════════════════

def demo_star_args():
    print("=" * 50)
    print(" 1. *args —— 任意数量位置参数")
    print("=" * 50)

    def log_event(event_type: str, *details):
        """
        记录客服事件。
        WHY: *details 可以接收任意多个参数——
             调用者可以传 0 个、1 个、10 个，函数都能处理。
             details 在函数体内是 tuple。
        """
        print(f" [{event_type}]", end=" ")
        for d in details:
            print(f"| {d}", end=" ")
        print(f"  (共 {len(details)} 条详情)")

    # 传不同数量的参数——*args 全部接收
    log_event("用户提问", "用户ID=U001", "问题=退货")
    log_event("系统警告", "响应超时", "模型=deepseek", "耗时=5.2s",
              "重试次数=2")
    log_event("会话结束")   # 0 个额外参数也行
    print()


# ══════════════════════════════════════════════════════════════
# 2. **kwargs —— 接收任意关键字参数（透传核心）
# WHY: **kwargs 是 LLM 调用封装中最关键的技巧——
#      chat() 不需要知道有哪些参数（temperature/top_p/max_tokens...），
#      全部收进 kwargs dict，原封不动传给底层 API——
#      调用方加新参数不用改 chat() 的签名。
# ══════════════════════════════════════════════════════════════

def demo_star_kwargs():
    print("=" * 50)
    print(" 2. **kwargs —— 参数透传")
    print("=" * 50)

    # 模拟底层 API 调用
    def call_llm_api(model: str, messages: list, **options):
        """
        底层 API 调用。
        WHY: options 收集所有额外参数（temperature, max_tokens...）
             然后透传给真正的 API。
        """
        print(f" 调用 {model}")
        print(f" 消息数: {len(messages)}")
        print(f" 额外参数: {options}")
        return "模拟回复"

    # 中间层封装——关键！用 **kwargs 透传
    def chat(messages: list, **kwargs):
        """
        统一的聊天接口。
        WHY: **kwargs 把 temperature/top_p/max_tokens 等
             所有参数原封不动透传给底层 API——
             中间层不需要声明这些参数，底层 API 加了新参数也不用改这里。
        """
        model = "deepseek-v4-pro"
        return call_llm_api(model, messages, **kwargs)  # WHY: **解包透传

    # 调用方自由加参数——chat() 不需要任何修改
    reply = chat(
        [{"role": "user", "content": "查订单"}],
        temperature=0.1,
        max_tokens=200,
    )
    print(f" 结果: {reply}")

    # 更复杂的参数组合——chat() 一样处理
    reply2 = chat(
        [{"role": "user", "content": "推荐商品"}],
        temperature=1.5,
        top_p=0.9,
        max_tokens=500,
        stop=["\n\n"],
    )
    print(f" 结果: {reply2}")
    print()


# ══════════════════════════════════════════════════════════════
# 3. * 和 ** 在调用时的解包作用
# WHY: 定义时 *args/**kwargs 是"打包"，调用时 *list/**dict 是"解包"——
#      这是 Python 参数系统最强大的特性。
#      **config_dict 让你从配置文件读取参数，一行代码注入 API 调用。
# ══════════════════════════════════════════════════════════════

def demo_unpacking_call():
    print("=" * 50)
    print(" 3. 调用时解包 —— 从配置 dict 注入参数")
    print("=" * 50)

    def create_order(product: str, quantity: int,
                     price: float, note: str = ""):
        """模拟创建订单"""
        return (f"订单创建成功: {product} ×{quantity}, "
                f"¥{price * quantity}, 备注:{note or '无'}")

    # 方式A: 逐个传参（传统方式）
    result_a = create_order("耳机", 2, 299.0, note="加急")
    print(f" 逐个传参: {result_a}")

    # 方式B: 从配置 dict 解包（Agent 常用方式）
    # WHY: 从 JSON 配置或前端请求体解析出的 dict，
    #      用 **dict 解包直接传给函数——不用逐个取字段。
    config = {
        "product": "漫步者 W820NB",
        "quantity": 1,
        "price": 299.0,
        "note": "生日礼物，请包装精美",
    }
    result_b = create_order(**config)   # WHY: **config 把 dict 解包为关键字参数
    print(f" dict解包: {result_b}")

    # 方式C: 覆盖部分参数
    defaults = {"quantity": 1, "note": ""}
    result_c = create_order(product="手机壳", price=49.0, **defaults)
    print(f" 覆盖传参: {result_c}")
    print()


# ══════════════════════════════════════════════════════════════
# 4. *args + **kwargs 组合 —— 万能函数签名
# WHY: def func(*args, **kwargs) 是"万能签名"——
#      装饰器、中间件、代理函数都用这个模式：
#      不管原始函数是什么参数，全部接收，全部透传。
# ══════════════════════════════════════════════════════════════

def demo_combined():
    print("=" * 50)
    print(" 4. *args + **kwargs 万能签名")
    print("=" * 50)

    def tool_dispatcher(tool_name: str, *args, **kwargs):
        """
        工具分发器——客服 Agent 的工具路由。
        WHY: *args + **kwargs 让分发器"不知道具体工具的参数"——
             每个工具参数不同，但分发器用万能签名统一接收和转发。
        """
        print(f" 分发工具: {tool_name}")
        print(f"   位置参数: {args}")
        print(f"   关键字参数: {kwargs}")

        # 实际应用中这里会查注册表然后调用真正的工具函数
        return f"[{tool_name}] 执行完成"

    # 不同工具不同参数——同一个分发器处理
    tool_dispatcher("query_order", "ORD001")
    tool_dispatcher("search", keyword="耳机", min_price=100, max_price=500)
    tool_dispatcher("refund", "ORD001", amount=299.0, reason="质量问题")
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║  Python 基础 09: *args 与 **kwargs           ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    demo_star_args()
    demo_star_kwargs()
    demo_unpacking_call()
    demo_combined()


if __name__ == "__main__":
    main()
