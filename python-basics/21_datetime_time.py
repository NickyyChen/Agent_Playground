# -*- coding: utf-8 -*-
"""
21_datetime_time.py — 时间处理：datetime、时间戳、日期计算
=========================================================

【概念】
Python 的时间处理主要在 datetime 模块：
  datetime.now()         → 当前日期时间
  datetime(2024, 5, 20)  → 指定日期
  timedelta(days=7)      → 时间差，用于日期加减
  .strftime("%Y-%m-%d")  → 格式化为字符串
  .timestamp()            → 转 Unix 时间戳

【在智能客服中的应用】
- 计算"签收后第几天"来判断是否在退货期
- 订单过期判断（48小时未支付 → 自动取消）
- 会话超时检测（用户 30 分钟未回复 → 自动结束）
- 日志时间戳

【ASCII 架构图】

  时间在客服系统中的应用:

  delivery_time ──▶ now - delivery_time ──▶ 签收天数 ──▶ if <= 7: 可退货
                                                              elif <= 15: 可换货
                                                              else: 过保

  会话时间:
  last_active ──▶ now - last_active ──▶ 空闲分钟 ──▶ if > 30: 自动关闭会话
"""

from datetime import datetime, timedelta
import time


# ══════════════════════════════════════════════════════════════
# 1. 获取与格式化时间
# WHY: .strftime() 把 datetime 对象转成可读/可存储的字符串——
#      客服日志、订单时间都是用特定格式存储的。
# ══════════════════════════════════════════════════════════════

def demo_format_time():
    print("=" * 50)
    print(" 1. 获取与格式化时间")
    print("=" * 50)

    now = datetime.now()
    print(f" datetime.now():  {now}")
    print(f" 日期:            {now.strftime('%Y-%m-%d')}")
    print(f" 时间:            {now.strftime('%H:%M:%S')}")
    print(f" 完整格式:         {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f" 中文格式:         {now.strftime('%Y年%m月%d日 %H:%M')}")

    # 从字符串解析
    order_time = datetime.strptime("2024-05-20 14:30:00", "%Y-%m-%d %H:%M:%S")
    print(f"\n strptime 解析:   {order_time}")
    print()


# ══════════════════════════════════════════════════════════════
# 2. timedelta —— 日期加减
# WHY: timedelta 是日期计算的核心——"7天退货期"的本质就是:
#      if now - delivery_time <= timedelta(days=7): 可退货
#      客服系统几乎所有时间判断都是 datetime ± timedelta。
# ══════════════════════════════════════════════════════════════

def demo_timedelta():
    print("=" * 50)
    print(" 2. timedelta —— 退货期计算")
    print("=" * 50)

    # 模拟订单签收时间
    delivery = datetime(2024, 5, 20, 14, 30)
    now = datetime.now()

    days_passed = (now - delivery).days

    print(f" 签收时间: {delivery.strftime('%Y-%m-%d %H:%M')}")
    print(f" 当前时间: {now.strftime('%Y-%m-%d %H:%M')}")
    print(f" 已过天数: {days_passed} 天")

    # WHY: 客服退货判断的核心逻辑——
    #      不同天数对应不同政策
    if days_passed <= 7:
        policy = "7天退货期内 → 可全额退款"
    elif days_passed <= 15:
        policy = "15天换货期内 → 可换新，不可退款"
    else:
        policy = "已过售后期限 → 需联系人工客服"

    print(f" 售后政策: {policy}")

    # 计算截止日期
    return_deadline = delivery + timedelta(days=7)
    exchange_deadline = delivery + timedelta(days=15)
    print(f" 退货截止: {return_deadline.strftime('%Y-%m-%d')}")
    print(f" 换货截止: {exchange_deadline.strftime('%Y-%m-%d')}")
    print()


# ══════════════════════════════════════════════════════════════
# 3. 时间戳 —— Unix Timestamp
# WHY: 时间戳（秒数）是计算机间传递时间的标准格式——
#      API 返回的时间常是时间戳，需要转成 datetime 再处理。
#      time.time() 返回当前时间戳（float 秒）。
# ══════════════════════════════════════════════════════════════

def demo_timestamp():
    print("=" * 50)
    print(" 3. 时间戳 —— Unix Timestamp")
    print("=" * 50)

    # 时间戳 → datetime
    ts = 1716198600  # 2024-05-20 14:30:00 UTC+8
    dt = datetime.fromtimestamp(ts)
    print(f" 时间戳 {ts} → {dt.strftime('%Y-%m-%d %H:%M:%S')}")

    # datetime → 时间戳
    now_ts = time.time()
    now_dt = datetime.fromtimestamp(now_ts)
    print(f" 当前时间戳: {now_ts:.0f} → {now_dt}")

    # 性能计时: time.time() 适合计算耗时
    start = time.time()
    # 模拟一些操作
    _ = sum(range(1000000))
    elapsed = time.time() - start
    print(f"\n sum(range(1000000)) 耗时: {elapsed * 1000:.1f}ms")
    print()


# ══════════════════════════════════════════════════════════════
# 4. 实战：会话超时检测
# WHY: 客服系统需要检测用户是否长时间没回复——
#      超过 N 分钟自动关闭会话，释放资源。
# ══════════════════════════════════════════════════════════════

def demo_session_timeout():
    print("=" * 50)
    print(" 4. 实战 —— 会话超时检测")
    print("=" * 50)

    class Session:
        """客服会话——带超时检测"""
        def __init__(self, user_id: str, timeout_minutes: int = 30):
            self.user_id = user_id
            self.timeout = timedelta(minutes=timeout_minutes)
            self.last_active = datetime.now()

        def is_expired(self) -> bool:
            """
            检查会话是否过期。
            WHY: datetime.now() - last_active > timeout → 过期
            """
            idle = datetime.now() - self.last_active
            return idle > self.timeout

        def touch(self):
            """更新最后活动时间——用户发了新消息"""
            self.last_active = datetime.now()

    # 模拟超时会话
    session = Session("U001", timeout_minutes=30)
    # 模拟 35 分钟没活动
    session.last_active = datetime.now() - timedelta(minutes=35)

    idle = datetime.now() - session.last_active
    print(f" 会话 U001: 空闲 {idle.seconds // 60} 分钟")
    print(f" 已过期: {session.is_expired()} → {'关闭会话' if session.is_expired() else '保持活跃'}")
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║  Python 基础 21: 时间处理                     ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    demo_format_time()
    demo_timedelta()
    demo_timestamp()
    demo_session_timeout()


if __name__ == "__main__":
    main()
