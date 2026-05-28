# -*- coding: utf-8 -*-
"""
23_async_await.py — 异步编程：async/await 基础
==============================================

【概念】
Python 默认是同步的——代码一行一行执行，前一步不完后一步不等。
异步（async）让代码在等待的时候可以去做别的事情。

核心三要素：
  async def:   定义异步函数（协程 coroutine）
  await:       等待异步操作完成（期间不阻塞其他任务）
  asyncio.run(): 运行异步程序的入口

什么场景需要异步？
  - 等待 I/O：网络请求、文件读写、数据库查询
  - 并发调用：同时查 5 个订单、同时调 3 个 API
  - Web 服务：FastAPI 本身就是异步框架

什么场景不需要？
  - 纯计算任务（CPU 密集）
  - 简单的脚本和 demo

【在智能客服中的应用】
- FastAPI 路由函数都是 async def——同时处理多个用户请求
- 同时查询订单 + 物流 + 政策（并发而非串行）
- SSE 流式输出——逐 token 返回 LLM 结果

【ASCII 架构图】

  同步（串行）:                         异步（并发）:
  ─────                                  ─────

  查订单(0.5s)                           查订单(0.5s) ─┐
     ↓                                               │
  查物流(0.5s)                           查物流(0.5s) ─┼─ 同时等待
     ↓                                               │
  查政策(0.5s)                           查政策(0.5s) ─┘
     ↓
  总耗时: 1.5s                           总耗时: ~0.5s
"""

import asyncio
import time


# ══════════════════════════════════════════════════════════════
# 1. async/await 基础
# WHY: async def 定义的函数是协程——用 await 等待异步操作，
#      await 期间不阻塞，CPU 可以处理其他协程。
#      类比: 同步是"排队等"，异步是"取号等"——等的时候可以做别的。
# ══════════════════════════════════════════════════════════════

def demo_basics():
    print("=" * 50)
    print(" 1. async/await 基础")
    print("=" * 50)

    async def query_order(order_id: str) -> dict:
        """
        模拟异步查订单。
        WHY: await asyncio.sleep(0.5) 模拟 API 调用的等待时间——
             关键：await 期间不阻塞其他协程。
        """
        print(f"   开始查 {order_id}...")
        await asyncio.sleep(0.5)  # WHY: 模拟网络等待——实际场景是 await httpx.get()
        print(f"   完成查 {order_id}")
        return {"order_id": order_id, "status": "已签收"}

    async def main_async():
        print(" 单个查询（和同步一样）:")
        result = await query_order("ORD001")
        print(f"   结果: {result}\n")
        print(" 多个并发查询:")

    asyncio.run(main_async())
    print()


# ══════════════════════════════════════════════════════════════
# 2. asyncio.gather —— 并发执行
# WHY: asyncio.gather() 是异步并发的核心——
#      传入多个协程，同时执行（而非一个个等），
#      全部完成后返回结果列表。客服系统同时查订单+物流+政策就用这个。
# ══════════════════════════════════════════════════════════════

def demo_gather():
    print("=" * 50)
    print(" 2. asyncio.gather —— 并发执行")
    print("=" * 50)

    async def fetch_info(name: str, delay: float) -> str:
        """模拟获取信息（订单/物流/政策各有不同延迟）"""
        await asyncio.sleep(delay)
        return f"[{name}] 查询完成 (耗时 {delay}s)"

    async def concurrent_demo():
        """
        并发查询订单 + 物流 + 政策。
        WHY: gather 同时启动三个协程，总耗时 = 最慢的那个（0.5s），
             而非三个之和（0.9s）。
        """
        start = time.time()

        # 三个查询"同时"启动
        results = await asyncio.gather(
            fetch_info("查订单", 0.3),   # 每个延迟不同
            fetch_info("查物流", 0.5),   # 但并发执行
            fetch_info("查政策", 0.2),   # 不用互相等
        )

        elapsed = time.time() - start
        for r in results:
            print(f"   {r}")
        print(f"   总耗时: {elapsed:.2f}s (不是 0.3+0.5+0.2={1.0}s!)")

    asyncio.run(concurrent_demo())
    print()


# ══════════════════════════════════════════════════════════════
# 3. 同步 vs 异步 对比
# WHY: 用同一组任务对比同步和异步的耗时差异——
#      3 个各 0.3s 的任务：同步 0.9s，异步 ~0.3s
# ══════════════════════════════════════════════════════════════

def demo_sync_vs_async():
    print("=" * 50)
    print(" 3. 同步 vs 异步 —— 耗时对比")
    print("=" * 50)

    def fetch_sync(name: str) -> str:
        """同步版本——sleep 阻塞整个线程"""
        time.sleep(0.3)
        return f"[{name}] 完成"

    async def fetch_async(name: str) -> str:
        """异步版本——await 不阻塞其他协程"""
        await asyncio.sleep(0.3)
        return f"[{name}] 完成"

    # 同步运行
    start = time.time()
    results_sync = [fetch_sync(f"任务{i}") for i in range(3)]
    sync_time = time.time() - start

    # 异步运行
    async def run_async():
        start = time.time()
        results = await asyncio.gather(
            fetch_async("任务1"),
            fetch_async("任务2"),
            fetch_async("任务3"),
        )
        return results, time.time() - start

    async_results, async_time = asyncio.run(run_async())

    print(f" 同步 (串行): {sync_time:.2f}s  ← 3个任务排队等")
    print(f" 异步 (并发): {async_time:.2f}s  ← 3个任务同时跑")
    print(f" 提速:       {sync_time/async_time:.0f}x")
    print()


# ══════════════════════════════════════════════════════════════
# 4. async 在 FastAPI 中的角色
# WHY: FastAPI 路由写 async def——框架自动处理并发请求。
#      每个请求是一个协程，FastAPI 的事件循环调度它们的执行。
# ══════════════════════════════════════════════════════════════

def demo_fastapi_context():
    print("=" * 50)
    print(" 4. async 在 FastAPI 中的应用")
    print("=" * 50)

    print("""
  FastAPI 路由函数:

    @app.get("/order/{order_id}")
    async def get_order(order_id: str):     ← async def
        result = await query_db(order_id)   ← await 不阻塞其他请求
        return result

  为什么 FastAPI 用 async？
    1. 单个请求等待数据库时，服务器可以处理其他请求
    2. 高并发场景下吞吐量远高于同步框架（Flask）
    3. SSE（Server-Sent Events）流式输出需要 async

  什么时候路由用 def 而不是 async def？
    - 函数内部没有需要 await 的操作 → 用 def
    - 有 await 操作 → 用 async def
  """)
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║  Python 基础 23: async/await 异步编程        ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    demo_basics()
    demo_gather()
    demo_sync_vs_async()
    demo_fastapi_context()


if __name__ == "__main__":
    main()
