# -*- coding: utf-8 -*-
"""
09_mcp_server.py — MCP Server：标准化工具服务
=============================================

【概念】
MCP Server 是工具提供方，通过 JSON-RPC 2.0 over stdio 协议暴露工具。
它不关心谁在调用它、也不关心 LLM 怎么用——只负责"收请求 → 执行 → 返回结果"。

可以在终端直接运行：
  python demos/09_mcp_server.py
然后手动输入 JSON-RPC 请求进行调试。

【在智能客服中解决什么问题】
把订单查询、物流追踪、退换货政策这些工具从 Agent 代码中"拆出来"，
以独立进程形式运行。Agent（Client）通过标准协议调用，实现业务逻辑
与工具实现的解耦。

【核心流程】
1. 启动 → 在 stdin 上循环读取 JSON-RPC 请求（每行一个 JSON）
2. 根据 method 字段分发：initialize / tools/list / tools/call
3. 执行对应的 Python 函数，结果封装为 JSON-RPC 响应
4. 响应写入 stdout（日志写入 stderr，不污染协议通道）

【pip install】
无需额外依赖

【ASCII 架构图】

  外部调用方（MCP Client / curl / 任何语言）
       │
       │  JSON-RPC 2.0 over stdio
       ▼
  ┌─────────────────────────────────────┐
  │           MCP Server                 │
  │                                      │
  │  ┌────────────────────────────────┐  │
  │  │  JSON-RPC 分发器                │  │
  │  │                                │  │
  │  │  initialize  → 握手信息         │  │
  │  │  tools/list  → 工具清单         │  │
  │  │  tools/call  → 执行具体工具 ──▶  │  │
  │  └────────────────────────────────┘  │
  │                                      │
  │  ┌────────────────────────────────┐  │
  │  │  工具执行器                      │  │
  │  │  query_order()                 │  │
  │  │  query_logistics()             │  │
  │  │  check_return_policy()         │  │
  │  └────────────────────────────────┘  │
  └─────────────────────────────────────┘
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from typing import Callable
from shared.mock_data import MOCK_ORDERS, MOCK_LOGISTICS, RETURN_POLICY


# ══════════════════════════════════════════════════════════════
# 工具实现 —— 和之前 Demo 共享同一套业务逻辑
# WHY: 业务逻辑不变，变得只是"调用方式"——
#      以前是 Agent 直接 import 调函数，现在是通过 MCP 协议远程调
# ══════════════════════════════════════════════════════════════

def query_order(order_id: str) -> str:
    """根据订单号查询订单状态、商品、金额、下单时间"""
    order = MOCK_ORDERS.get(order_id)
    if not order:
        return f"订单 {order_id} 不存在，请核实订单号"
    return json.dumps(order, ensure_ascii=False, indent=2)


def query_logistics(tracking_no: str) -> str:
    """根据快递单号查询物流轨迹、当前位置和预计送达时间"""
    info = MOCK_LOGISTICS.get(tracking_no)
    if not info:
        return f"快递 {tracking_no} 暂无物流记录"
    return json.dumps(info, ensure_ascii=False, indent=2)


def check_return_policy(category: str = "") -> str:
    """查询退换货政策，可选按品类筛选"""
    if category:
        return f"'{category}'品类政策：\n{RETURN_POLICY}"
    return RETURN_POLICY


# ══════════════════════════════════════════════════════════════
# MCP 工具注册表
# WHY: TOOLS_SCHEMA 是 MCP 协议中 tools/list 的返回格式——
#      每个工具用 JSON Schema 描述参数类型和含义，
#      Client 拿到后可以自动转为 OpenAI / 其他 LLM 的 function 格式
# ══════════════════════════════════════════════════════════════

TOOLS_SCHEMA = [
    {
        "name": "query_order",
        "description": "根据订单号查询订单状态、商品、金额、下单时间等完整信息",
        "inputSchema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "订单号，如 ORD20240001"}
            },
            "required": ["order_id"]
        }
    },
    {
        "name": "query_logistics",
        "description": "根据快递单号查询物流轨迹、当前位置和预计送达时间",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tracking_no": {"type": "string", "description": "快递单号，如 SF1234567890"}
            },
            "required": ["tracking_no"]
        }
    },
    {
        "name": "check_return_policy",
        "description": "查询退换货政策，可选传入品类名称做筛选",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "品类名，如'耳机'、'手机壳'"}
            },
            "required": []
        }
    },
]

# WHY: 工具名 → 函数的映射，tools/call 时分发到正确的执行函数
TOOL_EXECUTORS: dict[str, Callable] = {
    "query_order": query_order,
    "query_logistics": query_logistics,
    "check_return_policy": check_return_policy,
}


# ══════════════════════════════════════════════════════════════
# MCP Server 主循环
# ══════════════════════════════════════════════════════════════

def run():
    """
    MCP Server 主循环：stdin 读 JSON-RPC → 处理 → stdout 写响应。
    WHY: 协议使用"一行一个 JSON"的简单格式（适合 stdio 管道），
         stderr 留给 Server 自身日志，不污染 stdout 的协议数据。
    """
    print("[MCP Server] 启动完成，等待 JSON-RPC 请求...", file=sys.stderr)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            print("[MCP Server] ⚠ 收到非法 JSON，跳过", file=sys.stderr)
            continue

        req_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})

        # ── initialize：握手，声明 Server 身份和能力 ─────
        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2025-03-26",
                    "serverInfo": {
                        "name": "好买电商客服 MCP Server",
                        "version": "1.0.0"
                    },
                    "capabilities": {"tools": {}}
                }
            }
            print(json.dumps(response), flush=True)
            print("[MCP Server] initialize 完成", file=sys.stderr)

        # ── tools/list：返回工具清单 ────────────────────
        elif method == "tools/list":
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": TOOLS_SCHEMA}
            }
            print(json.dumps(response), flush=True)
            print(f"[MCP Server] tools/list → 返回 {len(TOOLS_SCHEMA)} 个工具",
                  file=sys.stderr)

        # ── tools/call：执行指定工具 ────────────────────
        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            executor = TOOL_EXECUTORS.get(tool_name)

            if executor:
                try:
                    result_text = executor(**arguments)
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": result_text}]
                        }
                    }
                except Exception as e:
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32000, "message": str(e)}
                    }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Tool not found: {tool_name}"
                    }
                }

            print(json.dumps(response), flush=True)
            print(f"[MCP Server] tools/call {tool_name}({arguments}) → done",
                  file=sys.stderr)

        # ── 未知 method ────────────────────────────────
        else:
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Unknown method: {method}"
                }
            }
            print(json.dumps(response), flush=True)
            print(f"[MCP Server] 未知请求 method={method}", file=sys.stderr)


if __name__ == "__main__":
    print("[MCP Server] 好买电商客服 MCP Server v1.0.0", file=sys.stderr)
    print("[MCP Server] 协议: JSON-RPC 2.0 over stdio", file=sys.stderr)
    print("[MCP Server] 提供 3 个工具: query_order, "
          "query_logistics, check_return_policy", file=sys.stderr)
    run()
