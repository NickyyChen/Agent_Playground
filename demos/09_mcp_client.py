# -*- coding: utf-8 -*-
"""
09_mcp_client.py — MCP Client：连接 Server，让 LLM 通过 MCP 调工具
=================================================================

【概念】
MCP Client 是 MCP 协议的消费方。它启动 MCP Server 子进程，
通过 stdin/stdout 管道与 Server 进行 JSON-RPC 2.0 通信，
把 Server 提供的工具转成 OpenAI Function Calling 格式，
让 LLM 能通过标准协议调用远程工具。

【在智能客服中解决什么问题】
Agent 不再直接 import 工具函数，而是通过 MCP Client 动态发现和调用。
好处：换一个 Server（比如从"测试环境"切换到"生产环境"），
Agent 代码一行不改，只改 Server 路径。

【核心流程】
1. MCPClient 启动 Server 子进程
2. initialize() → 握手，确认 Server 身份
3. list_tools() → 动态发现 Server 提供哪些工具
4. mcp_tools_to_openai() → 转成 OpenAI Function Calling 格式
5. LLM 决定调工具 → Client.call_tool() → JSON-RPC → Server 执行 → 返回结果
6. Client 把结果喂给 LLM → 生成最终回答

【pip install】
pip install openai

【ASCII 架构图】

  ┌───────────────────────────────────────────────────────┐
  │                   MCP Client (本文件)                   │
  │                                                        │
  │  ┌──────────┐    ┌──────────────┐    ┌─────────────┐  │
  │  │  用户问题  │───▶│  LLM 大脑     │───▶│ 最终回答     │  │
  │  └──────────┘    │              │    └─────────────┘  │
  │                  │ 需要工具?    │                      │
  │                  │ 调哪个?      │                      │
  │                  └──────┬───────┘                      │
  │                         │ tool_call 请求               │
  │                         ▼                              │
  │                  ┌──────────────┐                      │
  │                  │  MCPClient   │                      │
  │                  │  call_tool() │                      │
  │                  └──────┬───────┘                      │
  └─────────────────────────┼──────────────────────────────┘
                            │
                  JSON-RPC 2.0 over stdio
                            │
  ┌─────────────────────────┼──────────────────────────────┐
  │                   MCP Server (独立进程)                  │
  │                         ▼                              │
  │                  ┌──────────────┐                      │
  │                  │  工具执行器    │                      │
  │                  │  query_order │                      │
  │                  │  query_logis │                      │
  │                  │  check_policy│                      │
  │                  └──────────────┘                      │
  └───────────────────────────────────────────────────────┘
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json, subprocess
from shared.llm_client import chat, create_completion


# ══════════════════════════════════════════════════════════════
# MCPClient —— 与 MCP Server 的 stdio 通信封装
# ══════════════════════════════════════════════════════════════

class MCPClient:
    """
    MCP 客户端：启动 Server 子进程，通过 stdin/stdout 进行 JSON-RPC 通信。
    WHY: 封装子进程管理 + JSON-RPC 协议细节，
         对外只暴露三个方法：initialize / list_tools / call_tool
    """

    def __init__(self, server_script: str = None):
        """
        server_script: MCP Server 脚本路径，默认用同目录的 09_mcp_server.py
        """
        if server_script is None:
            server_script = os.path.join(os.path.dirname(__file__),
                                         "09_mcp_server.py")

        # WHY: stdin=PIPE 发送请求，stdout=PIPE 读取响应，
        #      stderr 继承终端（Server 日志直接输出，不经过管道）
        self.process = subprocess.Popen(
            [sys.executable, server_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            text=True,
        )
        self._request_id = 0

    def _send_request(self, method: str, params: dict = None) -> dict:
        """
        发送一行 JSON-RPC 请求，读取一行 JSON-RPC 响应。
        WHY: "一行一请求"是最简单的 stdio 协议——
             不需要分隔符、不需要长度前缀、人眼可读可调试。
        """
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {},
        }
        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        return json.loads(line)

    def initialize(self) -> dict:
        """
        MCP 握手：告知 Server 自己的身份，获取 Server 信息。
        WHY: 协议要求首次通信必须是 initialize，
             用于版本协商和能力交换。
        """
        return self._send_request("initialize", {
            "protocolVersion": "2025-03-26",
            "clientInfo": {"name": "Agent-Playground Client", "version": "1.0.0"}
        })

    def list_tools(self) -> list[dict]:
        """
        获取 Server 提供的工具列表。
        WHY: 运行时动态发现，Agent 不需要硬编码工具有哪些——
             新增工具只需在 Server 端注册，Client 自动发现。
        """
        result = self._send_request("tools/list")
        return result.get("result", {}).get("tools", [])

    def call_tool(self, tool_name: str, arguments: dict) -> str:
        """
        调用 Server 上的指定工具，返回执行结果文本。
        WHY: 这是 MCP 最核心的方法——Client 不直接执行任何业务逻辑，
             而是把工具名+参数打包成 JSON-RPC 请求发给 Server，
             Server 执行完后返回结果。
        """
        result = self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })
        if "error" in result:
            return f"MCP Error [{result['error']['code']}]: " \
                   f"{result['error']['message']}"
        content = result.get("result", {}).get("content", [])
        if content:
            return content[0].get("text", "")
        return ""

    def close(self):
        """关闭 Server 子进程"""
        self.process.terminate()
        self.process.wait()


# ══════════════════════════════════════════════════════════════
# 格式转换：MCP tools → OpenAI Function Calling
# WHY: MCP 的 inputSchema 字段对应 OpenAI 的 parameters 字段，
#      做一次简单的字段映射即可让 LLM 使用 MCP 工具
# ══════════════════════════════════════════════════════════════

def mcp_tools_to_openai(mcp_tools: list[dict]) -> list[dict]:
    """将 MCP tools/list 返回的格式转为 OpenAI Function Calling 格式"""
    openai_tools = []
    for tool in mcp_tools:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["inputSchema"],
            }
        })
    return openai_tools


# ══════════════════════════════════════════════════════════════
# 演示函数
# ══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """你是"小选"，好买电商的智能客服。
你通过 MCP 协议连接后端工具获取数据，所有结论基于工具返回的真实数据。
回答简洁专业。"""


def demo_discovery(client: MCPClient):
    """
    演示1：工具发现 —— Client 运行时动态获取 Server 的工具列表。
    WHY: 对比 Demo 03 中 import 时就知道有哪些函数，
         MCP 的工具发现是"运行时"的——Server 启动后 Client 才
         知道有哪些工具可用。这意味着可以不重启 Agent 就换工具集。
    """
    print("=" * 60)
    print(" 演示1：MCP 工具发现 —— 动态获取工具列表")
    print("=" * 60)

    # ① 握手
    print("  ① initialize → 连接 Server")
    init_result = client.initialize()
    info = init_result.get("result", {}).get("serverInfo", {})
    print(f"     Server: {info.get('name')} v{info.get('version')}")

    # ② 获取工具
    print("  ② tools/list → 获取可用工具")
    tools = client.list_tools()
    for t in tools:
        print(f"     - {t['name']}: {t['description'][:55]}...")

    # ③ 格式转换
    print(f"  ③ → 转为 OpenAI format, 共 {len(tools)} 个 functions")
    print()


def demo_tool_call(client: MCPClient, openai_tools: list[dict]):
    """
    演示2：通过 MCP 协议让 LLM 调用工具。
    WHY: 完整展示 MCP 链路：
         LLM 想调工具 → Client 发 tools/call → Server 执行 →
         Client 收结果 → LLM 综合回答。
         关键：Client.call_tool() 不是直接调 Python 函数，
         而是通过 JSON-RPC 向另一个进程发请求。
    """
    print("=" * 60)
    print(" 演示2：MCP 协议 + LLM Function Calling")
    print("=" * 60)

    question = "查下订单 ORD20240001，顺便看看耳机退货政策"
    print(f" 用户: {question}\n")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    # Step 1: LLM 决定需要哪些工具
    print("  [Step 1] LLM 分析 → 决定调用哪些工具")
    response = create_completion(messages, tools=openai_tools, temperature=0.1)
    msg = response.choices[0].message

    if not msg.tool_calls:
        print(f"  LLM 直接回答: {msg.content}")
        return

    # Step 2: 通过 MCP 调用
    messages.append(msg)
    for tc in msg.tool_calls:
        func_name = tc.function.name
        args = json.loads(tc.function.arguments)
        print(f"  [Step 2] Client.call_tool({func_name}, {args})")

        # WHY: 这里就是 MCP 区别于 Demo 03 的地方——
        #      不是 import 后直接调 query_order(**args)，
        #      而是通过 JSON-RPC 向 Server 进程发请求
        result = client.call_tool(func_name, args)
        short = result[:100].replace("\n", " ")
        print(f"          Server 返回: {short}...")

        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": result,
        })

    # Step 3: LLM 综合回答
    print("  [Step 3] LLM 阅读工具结果 → 生成回答")
    final = chat(messages, temperature=0.1)
    print(f"          客服: {final}")
    print()


def demo_architecture():
    """
    演示3：MCP vs 直接调用的架构对比。
    """
    print("=" * 60)
    print(" 演示3：MCP vs 直接函数调用 —— 架构对比")
    print("=" * 60)

    print("""
  【Demo 03 — 直接函数调用】
    Agent ──import──▶ query_order() ──▶ MOCK_ORDERS
    → 同进程、同语言、紧耦合

  【Demo 09 — MCP 协议】
    Agent(Client) ──JSON-RPC/stdio──▶ MCP Server ──▶ MOCK_ORDERS
    → 跨进程、跨语言、松耦合

  ┌─────────────────┬──────────────────┬──────────────────┐
  │     维度         │  直接函数调用     │    MCP 协议       │
  ├─────────────────┼──────────────────┼──────────────────┤
  │ 语言无关         │ Python only      │ Server 可用任何语言│
  │ 部署独立         │ 同一进程          │ 独立进程/容器     │
  │ 工具发现         │ import 时已知     │ 运行时动态发现     │
  │ 新增/替换工具     │ 改 Agent 代码     │ 换 Server 即可     │
  │ 权限隔离         │ 无隔离            │ 进程级隔离        │
  │ 版本管理         │ 随 Agent 发布     │ Server 独立版本    │
  └─────────────────┴──────────────────┴──────────────────┘
""")


def main():
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║  Agent-Playground Demo 09: MCP Client             ║")
    print("║  连接 MCP Server，让 LLM 通过标准协议调用工具       ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    print(" 正在启动 MCP Server 子进程...")
    client = MCPClient()
    print()

    try:
        demo_discovery(client)
        tools = client.list_tools()
        openai_tools = mcp_tools_to_openai(tools)
        demo_tool_call(client, openai_tools)
        demo_architecture()
    finally:
        client.close()

    print("=" * 60)
    print(" Demo 09 Client 完成！MCP = AI 工具的 USB-C 接口")
    print("=" * 60)


if __name__ == "__main__":
    main()
