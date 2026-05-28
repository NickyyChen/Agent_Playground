# -*- coding: utf-8 -*-
"""
06_dict_operations.py — 字典操作：读写、嵌套、默认值
====================================================

【概念】
dict 是 Python 的键值对容器——{key: value}，通过 key 快速查找 value。
Agent 开发中 dict 的使用频率仅次于 list：
  - LLM 消息: {"role": "user", "content": "..."}
  - 工具参数: {"order_id": "ORD001", "amount": 299}
  - 配置字典: {"model": "deepseek-v4", "temperature": 0.1}
  - JSON 的本质就是嵌套 dict

核心操作：
  取值: d["key"] 或 d.get("key", default)
  赋值: d["key"] = value
  遍历: for k, v in d.items()
  合并: d.update(other) 或 {**d1, **d2}

【在智能客服中的应用】
- 构建 API 请求参数（dict → JSON）
- 订单数据管理（订单号 → 详细信息）
- 配置透传（**kwargs 就是 dict 解包）

【ASCII 架构图】

  dict 在 LLM 调用中的角色:

  {"role": "user", "content": "查订单"}  ← 一条消息
       │
       ▼
  messages = [msg1, msg2, msg3, ...]     ← 消息列表 = list[dict]
       │
       ▼
  params = {"model": "...",              ← API 参数 = dict
            "messages": messages,
            "temperature": 0.1}
       │
       ▼
  **params → client.chat.completions.create(**params)  ← dict 解包传入
"""

# ══════════════════════════════════════════════════════════════
# 1. 基本操作 —— 取值、赋值、遍历
# WHY: d["key"] 和 d.get("key") 的区别是初学者的第一坑——
#      d["不存在的key"] → KeyError 崩溃
#      d.get("不存在的key") → 返回 None（或你指定的默认值）
#      客服系统中不确定字段是否存在时，永远用 get。
# ══════════════════════════════════════════════════════════════

def demo_basic_ops():
    print("=" * 50)
    print(" 1. dict 基本操作 —— 取值、赋值、遍历")
    print("=" * 50)

    # WHY: 模拟从 API 拿到的订单数据
    order = {
        "order_id": "ORD20240001",
        "product": "漫步者 W820NB",
        "price": 299.0,
        "status": "已签收",
        "delivery_time": "2024-05-20",
    }

    # 取值: d["key"] —— 确定字段存在时用
    print(f" 订单号: {order['order_id']}")

    # 取值: d.get("key", 默认值) —— 不确定字段是否存在时用
    # WHY: 不同订单类型可能没有 tracking_no 字段，get 防崩溃
    tracking = order.get("tracking_no", "暂无物流信息") # get 不到就防崩溃，返回默认值
    print(f" 物流: {tracking}")

    # 赋值/更新
    order["tracking_no"] = "SF1234567890"   # 新增字段
    order["status"] = "运输中"              # 更新已有字段
    print(f" 更新后状态: {order['status']}, 快递: {order.get('tracking_no')}")

    # 遍历: .items() 同时拿 key 和 value
    print(f"\n 完整订单信息:")
    for key, value in order.items():
        print(f"   {key}: {value}")
    print()


# ══════════════════════════════════════════════════════════════
# 2. 嵌套 dict —— 真实 API 数据结构
# WHY: JSON 就是嵌套 dict——dict 的 value 可以是另一个 dict、
#      list、或基本类型。Agent 需要从多层嵌套中提取字段。
# ══════════════════════════════════════════════════════════════

def demo_nested():
    print("=" * 50)
    print(" 2. 嵌套 dict —— 真实 API 响应结构")
    print("=" * 50)

    # 模拟 LLM API 返回的原始响应
    response = {
        "id": "chatcmpl-abc123",
        "model": "deepseek-v4-pro",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "您的订单已签收，可申请售后。",
                    "tool_calls": None,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 45,
            "completion_tokens": 28,
            "total_tokens": 73,
        },
    }

    # WHY: 逐层 .get() 访问嵌套字段——
    #      链式访问时任何一层为 None 都不会报错
    content = (response.get("choices", [{}])[0]
               .get("message", {})
               .get("content", ""))
    print(f" 回复文本: {content}")

    # 安全提取 token 用量
    usage = response.get("usage", {})
    print(f" Token 消耗: {usage.get('total_tokens', '?')} "
          f"(提示:{usage.get('prompt_tokens', '?')} "
          f"+ 生成:{usage.get('completion_tokens', '?')})")
    print()


# ══════════════════════════════════════════════════════════════
# 3. dict 合并 —— **解包
# WHY: {**d1, **d2} 快速合并两个 dict——
#      后面的覆盖前面的同名 key。
#      这是构建 API 参数的核心技巧。
# ══════════════════════════════════════════════════════════════

def demo_merge():
    print("=" * 50)
    print(" 3. dict 合并 —— 构建 API 参数")
    print("=" * 50)

    # 基础参数——所有 API 调用都需要的
    base_params = {
        "model": "deepseek-v4-pro",
        "max_tokens": 200,
        "temperature": 0.1,
    }

    # 客服场景1: 普通对话，用基础参数
    chat_params = {**base_params, "messages": [{"role": "user", "content": "你好"}]}
    print(f" 普通对话参数: {list(chat_params.keys())}")

    # 客服场景2: 创意场景，提高温度
    creative_params = {**base_params, "temperature": 1.5,  # 覆盖基础温度
                       "messages": [{"role": "user", "content": "推荐耳机"}]}
    print(f" 创意场景参数: temperature={creative_params['temperature']}")

    # 客服场景3: 带工具调用
    tool_params = {**base_params, "tools": [{"type": "function", "function": {...}}],
                   "messages": [{"role": "user", "content": "查订单"}]}
    print(f" 工具调用参数: 包含 tools 字段")
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║  Python 基础 06: 字典操作                     ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    demo_basic_ops()
    demo_nested()
    demo_merge()


if __name__ == "__main__":
    main()
