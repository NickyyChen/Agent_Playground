# -*- coding: utf-8 -*-
"""
19_json_operations.py — JSON 序列化：Python dict ↔ JSON 字符串
==============================================================

【概念】
JSON（JavaScript Object Notation）是前后端、API 之间交换数据的标准格式。
Agent 开发中 JSON 无处不在：
  - LLM API 的请求体和响应体都是 JSON
  - 工具参数在 LLM 和代码之间用 JSON 传递
  - 配置文件、数据存储常用 JSON

核心只有两个操作：
  json.dumps(obj)   → Python 对象 → JSON 字符串（序列化）
  json.loads(str)   → JSON 字符串 → Python 对象（反序列化）

常见陷阱：
  - 中文会被转义成 \\uXXXX → 用 ensure_ascii=False 解决
  - LLM 返回的 JSON 可能格式错误 → 必须 try/except
  - datetime 对象不能直接序列化 → 先转成字符串

【在智能客服中的应用】
- 解析 LLM 的 structured output（意图识别、实体提取）
- 构建 API 请求体
- 日志记录（dict → JSON 字符串写入日志）

【ASCII 架构图】

  Python dict                          JSON 字符串
  ────────────                         ──────────

  {"order_id": "ORD001",         ←→    '{"order_id":"ORD001","price":299}'
   "price": 299}

      json.dumps(obj)  ──────▶  JSON 字符串（发送给 API）
      json.loads(str)  ◀──────  JSON 字符串（从 API 接收）
"""

import json
from datetime import datetime


# ══════════════════════════════════════════════════════════════
# 1. dumps / loads 基础 —— dict 与 JSON 互转
# WHY: dumpS → String（序列化为字符串），loadS → String（从字符串解析）。
#      dumps/loads 是 Agent 开发中调用频率最高的 JSON 操作。
# ══════════════════════════════════════════════════════════════

def demo_dumps_loads():
    print("=" * 50)
    print(" 1. dumps / loads —— 序列化与反序列化")
    print("=" * 50)

    # Python dict → JSON 字符串
    order: dict = {
        "order_id": "ORD20240001",
        "product": "漫步者 W820NB",
        "price": 299.0,
        "in_stock": True,
        "tags": ["热销", "降噪"],
    }

    json_str: str = json.dumps(order, ensure_ascii=False)
    # WHY: ensure_ascii=False → 中文不转义（否则 "漫步者" 变成 "漫步者"）
    print(f" dumps (序列化):")
    print(f"   Python: {order}")
    print(f"   JSON:   {json_str}")

    # JSON 字符串 → Python dict
    parsed: dict = json.loads(json_str)
    print(f"\n loads (反序列化):")
    print(f"   类型: {type(parsed).__name__}")
    print(f"   价格: ¥{parsed['price']} ({type(parsed['price']).__name__})")
    print()


# ══════════════════════════════════════════════════════════════
# 2. indent —— 美化输出
# WHY: indent=2 让 JSON 输出带缩进和换行——
#      API 调试、日志记录时美化的 JSON 远比压缩的单行可读。
# ══════════════════════════════════════════════════════════════

def demo_pretty_print():
    print("=" * 50)
    print(" 2. indent 美化 —— 调试用的必备参数")
    print("=" * 50)

    # 模拟 LLM API 返回的复杂结构
    response = {
        "id": "chatcmpl-abc123",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "您的订单已签收，7天内可退货。",
                "tool_calls": None,
            },
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 45, "completion_tokens": 28,
                  "total_tokens": 73},
    }

    print(" 压缩格式 (indent=None):")
    print(f"  {json.dumps(response, ensure_ascii=False)}")

    print("\n 美化格式 (indent=2):")
    print(json.dumps(response, ensure_ascii=False, indent=2))
    print()


# ══════════════════════════════════════════════════════════════
# 3. 容错解析 —— LLM 返回的 JSON 可能格式错误
# WHY: LLM 不是 JSON 生成器——它经常在 JSON 前后加废话、
#      漏逗号、多写单引号。直接 json.loads() 会崩溃，
#      必须用 try/except 包裹并提供降级方案。
# ══════════════════════════════════════════════════════════════

def demo_safe_parsing():
    print("=" * 50)
    print(" 3. 容错解析 —— LLM 输出不可靠")
    print("=" * 50)

    def safe_json_parse(text: str) -> dict:
        """
        安全解析 LLM 返回的 JSON。
        WHY: LLM 经常返回格式不完美的 JSON——
             可能前后有废话、部分字段缺失。
             这个函数封装了清洗+解析+降级的完整逻辑。
        """
        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # WHY: LLM 常在 JSON 前后加说明文字——
        #      尝试只提取 { } 之间的内容
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(text[start:end])
        except (json.JSONDecodeError, ValueError):
            pass

        return {"error": "无法解析", "raw": text[:100]}

    # 模拟 LLM 的各种"不合格"输出
    llm_outputs = [
        '{"order_id": "ORD001", "reason": "质量问题"}',  # 正常
        '好的，查到了：{"order_id": "ORD001", "reason": "退货"} 以上是结果',  # 前后有废话
        '这不是JSON',                                 # 完全不是 JSON
    ]

    for i, output in enumerate(llm_outputs, 1):
        parsed = safe_json_parse(output)
        print(f" LLM输出{i}: {output[:60]}...")
        print(f" 解析结果: {parsed}")
        print()
    print()


# ══════════════════════════════════════════════════════════════
# 4. 自定义序列化 —— datetime 等特殊类型
# WHY: json.dumps() 默认只支持 str/int/float/bool/list/dict/None——
#      datetime/set/自定义类 会报 TypeError。
#      用 default 参数传入自定义转换函数。
# ══════════════════════════════════════════════════════════════

def demo_custom_serializer():
    print("=" * 50)
    print(" 4. 自定义序列化 —— datetime 转换")
    print("=" * 50)

    def custom_encoder(obj):
        """
        自定义序列化器。
        WHY: datetime 不能直接 JSON 序列化——
             先转成 ISO 格式字符串再序列化。
        """
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        raise TypeError(f"不能序列化类型: {type(obj)}")

    order_with_time = {
        "order_id": "ORD001",
        "product": "耳机",
        "created_at": datetime.now(),
        "delivered_at": datetime(2024, 5, 20, 14, 30),
    }

    # 方式A: default 参数
    json_a = json.dumps(order_with_time, ensure_ascii=False,
                        default=custom_encoder, indent=2)

    # 方式B: 手动转字符串（更简单，推荐日常使用）
    order_manual = {
        **order_with_time,
        "created_at": order_with_time["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
        "delivered_at": order_with_time["delivered_at"].strftime("%Y-%m-%d %H:%M:%S"),
    }
    json_b = json.dumps(order_manual, ensure_ascii=False, indent=2)

    print(f" 方式A (default=custom_encoder):")
    print(json_a)
    print(f"\n 方式B (手动转字符串):")
    print(json_b)
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║  Python 基础 19: JSON 序列化                 ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    demo_dumps_loads()
    demo_pretty_print()
    demo_safe_parsing()
    demo_custom_serializer()


if __name__ == "__main__":
    main()
