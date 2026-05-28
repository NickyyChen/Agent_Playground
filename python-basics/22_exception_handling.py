# -*- coding: utf-8 -*-
"""
22_exception_handling.py — 异常处理：try/except、自定义异常
===========================================================

【概念】
异常（Exception）是 Python 处理"预期外情况"的机制——程序遇到
无法继续执行的错误时抛出异常，try/except 可以捕获并处理。

核心要素：
  try:      可能出错的代码
  except:   捕获并处理特定异常
  finally:  无论是否异常都会执行（清理资源）
  raise:    主动抛出异常
  finally:  无论是否异常都会执行的清理代码

【在智能客服中的应用】
- API 调用失败重试（网络超时、限流）
- LLM 返回格式错误时的降级处理
- 工具调用失败时返回友好提示而非崩溃
- 自定义业务异常区分不同错误类型

【ASCII 架构图】

  正常流程:
  请求 → try → 成功 → 返回结果

  异常流程:
  请求 → try → 失败 → except → 降级处理 → 返回友好提示
                 ↓
              finally → 清理资源（关闭连接等）
"""

import json


# ══════════════════════════════════════════════════════════════
# 1. try/except 基础 —— 捕获并处理异常
# WHY: LLM API 调用可能因网络、限流、格式等原因失败——
#      直接崩溃意味着整个客服系统不可用。
#      try/except 让程序"优雅降级"而非"直接崩溃"。
# ══════════════════════════════════════════════════════════════

def demo_try_except():
    print("=" * 50)
    print(" 1. try/except —— 捕获特定异常")
    print("=" * 50)

    def safe_divide(a, b):
        """安全除法——不会崩溃"""
        try:
            return a / b
        except ZeroDivisionError:
            # WHY: 只捕获 ZeroDivisionError，其他异常仍会抛出
            return float('inf')  # 除以 0 返回无穷大而非崩溃
        except TypeError:
            return None  # 类型不对返回 None

    print(f" 10/2 = {safe_divide(10, 2)}")
    print(f" 10/0 = {safe_divide(10, 0)}  ← 不崩溃")
    print(f" 'a'/2 = {safe_divide('a', 2)}  ← 不崩溃")
    print()


# ══════════════════════════════════════════════════════════════
# 2. finally —— 清理资源
# WHY: finally 块无论是否异常都执行——适合关闭文件、释放连接。
#      数据库连接、文件句柄等资源必须在 finally 中释放。
# ══════════════════════════════════════════════════════════════

def demo_finally():
    print("=" * 50)
    print(" 2. finally —— 清理资源")
    print("=" * 50)

    def simulate_api_call(should_fail: bool = False):
        """模拟 API 调用——演示 finally 的清理逻辑"""
        connection_id = "CONN-001"
        print(f" 打开连接: {connection_id}")

        try:
            if should_fail:
                raise ConnectionError("网络超时")
            return "API 调用成功"
        except ConnectionError as e:
            print(f" 捕获异常: {e}")
            return "降级回复: 服务暂时不可用"
        finally:
            # WHY: finally 中的代码无论成功、失败、return 都会执行——
            #      这是释放资源的"唯一可靠位置"
            print(f" 关闭连接: {connection_id} (finally)")

    print(" 场景A: 调用成功")
    result = simulate_api_call(should_fail=False)
    print(f" 结果: {result}\n")

    print(" 场景B: 调用失败")
    result = simulate_api_call(should_fail=True)
    print(f" 结果: {result}\n")
    print()


# ══════════════════════════════════════════════════════════════
# 3. 自定义异常 —— 业务错误分类
# WHY: 不同业务错误应有不同的处理方式——
#      订单不存在 → 404，余额不足 → 400，系统错误 → 500。
#      自定义异常让调用方可以按异常类型做不同处理。
# ══════════════════════════════════════════════════════════════

def demo_custom_exception():
    print("=" * 50)
    print(" 3. 自定义异常 —— 业务错误分类")
    print("=" * 50)

    # WHY: 继承 Exception，可以添加业务字段（error_code, detail）
    class OrderNotFoundError(Exception):
        """订单不存在"""
        def __init__(self, order_id: str):
            self.order_id = order_id
            self.error_code = "ORDER_NOT_FOUND"
            super().__init__(f"订单 {order_id} 不存在")

    class RefundNotAllowedError(Exception):
        """不可退款"""
        def __init__(self, order_id: str, reason: str):
            self.order_id = order_id
            self.reason = reason
            self.error_code = "REFUND_NOT_ALLOWED"
            super().__init__(f"订单 {order_id} 不可退款: {reason}")

    def process_refund(order_id: str) -> dict:
        """处理退款——演示抛出自定义异常"""
        orders = {"ORD001": "已签收", "ORD002": "已取消"}

        if order_id not in orders:
            raise OrderNotFoundError(order_id)

        if orders[order_id] == "已取消":
            raise RefundNotAllowedError(order_id, "订单已取消")

        return {"status": "refunded", "order_id": order_id}

    # 测试不同异常
    test_cases = ["ORD001", "ORD002", "ORD999"]
    for oid in test_cases:
        try:
            result = process_refund(oid)
            print(f" {oid}: 退款成功")
        except OrderNotFoundError as e:
            print(f" {oid}: [{e.error_code}] {e}")
        except RefundNotAllowedError as e:
            print(f" {oid}: [{e.error_code}] {e}")
    print()


# ══════════════════════════════════════════════════════════════
# 4. raise —— 主动抛出异常
# WHY: raise 让函数在"无法继续"时主动通知调用方——
#      不 raise 的话，错误数据会继续往下传播，导致更隐蔽的 bug。
# ══════════════════════════════════════════════════════════════

def demo_raise():
    print("=" * 50)
    print(" 4. raise —— 主动上报错误")
    print("=" * 50)

    def validate_phone(phone: str) -> str:
        """
        校验手机号——不合法就 raise。
        WHY: 对于"不可恢复"的输入错误，直接 raise——
             让调用方决定如何处理（返回错误提示、记录日志等）。
        """
        import re
        if not phone:
            raise ValueError("手机号不能为空")
        if not re.match(r"^1[3-9]\d{9}$", phone):
            raise ValueError(f"手机号格式不正确: {phone}")
        return phone

    phones = ["13812345678", "", "12345", "19988887777"]
    for phone in phones:
        try:
            valid = validate_phone(phone)
            print(f" '{phone}' → 有效 ✓")
        except ValueError as e:
            print(f" '{phone}' → {e}")
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║  Python 基础 22: 异常处理                     ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    demo_try_except()
    demo_finally()
    demo_custom_exception()
    demo_raise()


if __name__ == "__main__":
    main()
