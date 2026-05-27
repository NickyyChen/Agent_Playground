# -*- coding: utf-8 -*-
"""
工具系统 —— Function Calling(Demo 03) + MCP兼容(Demo 09)
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from shared.mock_data import MOCK_ORDERS, MOCK_LOGISTICS, RETURN_POLICY


class ToolRegistry:
    """
    工具注册中心。
    知识点:
      Demo 03 — Function Calling 工具定义
      Demo 09 — MCP 兼容 output（tools/list + tools/call 格式）
    """

    def __init__(self):
        self._tools = {}
        self._register_defaults()

    def _register_defaults(self):
        self.register("query_order", query_order,
                      "根据订单号查询订单状态、商品、金额",
                      {"order_id": "string"})
        self.register("query_logistics", query_logistics,
                      "根据快递单号查询物流轨迹",
                      {"tracking_no": "string"})
        self.register("check_return_policy", check_return_policy,
                      "查询退换货政策，可选按品类筛选",
                      {"category": "string"})

    def register(self, name: str, fn, description: str,
                 params: dict[str, str], required: list = None):
        if required is None:
            required = list(params.keys())
        properties = {}
        for k, v in params.items():
            properties[k] = {"type": v, "description": f"{k}参数"}
        self._tools[name] = {
            "name": name, "fn": fn, "description": description,
            "input_schema": {
                "type": "object", "properties": properties,
                "required": required,
            }
        }

    def get_fn(self, name: str):
        t = self._tools.get(name)
        return t["fn"] if t else None

    def call(self, name: str, **kwargs) -> str:
        t = self._tools.get(name)
        if not t:
            return f"工具 {name} 不存在"
        try:
            return t["fn"](**kwargs)
        except Exception as e:
            return f"执行失败: {e}"

    # ─── OpenAI Function Calling 格式 ────────────
    def to_openai(self, names: list[str] = None) -> list[dict]:
        tools = [self._tools[n] for n in names] if names else self._tools.values()
        return [{"type": "function", "function": {
            "name": t["name"], "description": t["description"],
            "parameters": t["input_schema"],
        }} for t in tools]

    # ─── MCP tools/list 格式 (Demo 09) ───────────
    def to_mcp_tools(self) -> list[dict]:
        return [{"name": t["name"], "description": t["description"],
                 "inputSchema": t["input_schema"]}
                for t in self._tools.values()]

    def to_mcp_tools_call(self, name: str, arguments: dict) -> dict:
        t = self._tools.get(name)
        if not t:
            return {"error": f"Tool not found: {name}"}
        result = t["fn"](**arguments)
        return {"result": {"content": [{"type": "text", "text": result}]}}


# ─── 工具函数 ────────────────────────────────────

def query_order(order_id: str) -> str:
    order = MOCK_ORDERS.get(order_id)
    if not order:
        return f"订单 {order_id} 不存在"
    return json.dumps(order, ensure_ascii=False, indent=2)

def query_logistics(tracking_no: str) -> str:
    info = MOCK_LOGISTICS.get(tracking_no)
    if not info:
        return f"快递 {tracking_no} 暂无记录"
    return json.dumps(info, ensure_ascii=False, indent=2)

def check_return_policy(category: str = "") -> str:
    if category:
        return f"'{category}'：{RETURN_POLICY}"
    return RETURN_POLICY
