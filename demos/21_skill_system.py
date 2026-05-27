# -*- coding: utf-8 -*-
"""
21_skill_system.py — Agent Skill 制作方法：注册、发现、编排
==========================================================

【概念】
前面 20 个 Demo 中，"工具（Tool）"是零散的 Python 函数加上 JSON Schema。
当工具数量从 3 个增长到 30 个时，需要一套更系统的管理方式——这就是"Skill"。

Skill vs Tool：
  Tool = 一个函数 + 参数描述（LLM 能调哪个函数）
  Skill = 一个自包含的能力单元（分类、版本、文档、依赖、输入输出 Schema）
  类比：Tool 是"螺丝刀"，Skill 是"维修技能"（可能用到多把螺丝刀 + 操作流程）

一个规范的 Skill 包含：
  1. 元数据：name, description, category, version, tags
  2. 接口定义：input_schema（输入什么）、output_schema（输出什么）
  3. 执行逻辑：execute() 方法
  4. 依赖声明：需要哪些其他 Skill/外部资源

【在智能客服中解决什么问题】
客服系统有 30+ 个能力（查订单、退换货、物流追踪、投诉处理、优惠券...
无 Skill 管理 = 散落一地的函数。
有 Skill 系统 = 注册表统一管理，LLM 按需发现+调用，新增 Skill 不改框架代码。

【核心流程】
1. 定义 Skill 基类——统一元数据+接口
2. SkillRegistry——注册/发现/查找
3. @skill 装饰器——一行代码将函数变为 Skill
4. Skill Pipeline——编排多个 Skill 联动

【pip install】
无需额外依赖

【ASCII 架构图】

  ┌──────────────────────────────────────────────────────┐
  │                  Agent Skill 系统                      │
  │                                                       │
  │  ┌─────────────────────────────────────────┐         │
  │  │         SkillRegistry (注册中心)          │         │
  │  │                                          │         │
  │  │  ┌────────┐ ┌────────┐ ┌────────────┐   │         │
  │  │  │订单查询  │ │物流追踪  │ │退换货处理   │   │         │
  │  │  │Skill   │ │Skill   │ │Skill       │   │         │
  │  │  └────────┘ └────────┘ └────────────┘   │         │
  │  │  ┌────────┐ ┌────────┐                  │         │
  │  │  │优惠券   │ │投诉升级  │    ...         │         │
  │  │  │Skill   │ │Skill   │                  │         │
  │  │  └────────┘ └────────┘                  │         │
  │  └─────────────────────────────────────────┘         │
  │                                                       │
  │  Skill 定义:             Skill 编排:                   │
  │  @skill(                pipeline = Pipeline([        │
  │    name="order_query",    order_query,               │
  │    category="订单"        policy_check,              │
  │  )                        refund_calc                │
  │  class OrderSkill:      ])                           │
  │    ...                   result = pipeline.run(inp)   │
  └──────────────────────────────────────────────────────┘
"""

import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Any, Optional
from functools import wraps
from shared.llm_client import chat
from shared.mock_data import MOCK_ORDERS, MOCK_LOGISTICS, RETURN_POLICY


# ══════════════════════════════════════════════════════════════
# 1. Skill 基类 —— 一切 Skill 的模板
# WHY: 所有 Skill 共享同一套接口（metadata + execute），
#      Registry 才能统一管理。不定义基类，每个 Skill 都长得不一样。
# ══════════════════════════════════════════════════════════════

@dataclass
class SkillMeta:
    """Skill 元数据——描述这个 Skill 是什么、怎么用"""
    name: str
    description: str
    category: str = "general"
    version: str = "1.0.0"
    tags: list[str] = field(default_factory=list)
    requires_human: bool = False   # 是否需要人工确认


class Skill(ABC):
    """
    Skill 基类。
    WHY: 统一的 metadata 属性让 Registry 能按分类/标签检索 Skill；
         统一的 input_schema 让 LLM 能自动发现可调参数；
         统一的 execute() 让编排器能任意串接多个 Skill。
    """
    meta: SkillMeta

    @property
    def input_schema(self) -> dict:
        """返回 JSON Schema 格式的输入定义（子类覆盖）"""
        return {"type": "object", "properties": {}, "required": []}

    @abstractmethod
    def execute(self, **kwargs) -> dict:
        """
        执行 Skill，返回 {"success": bool, "data": ..., "error": ...}。
        WHY: 统一返回格式是 Skill 可编排的前提——
             编排器不关心每个 Skill 内部逻辑，只关心统一的结果格式。
        """
        ...

    def to_openai_function(self) -> dict:
        """转为 OpenAI Function Calling 格式"""
        return {
            "type": "function",
            "function": {
                "name": self.meta.name,
                "description": self.meta.description,
                "parameters": self.input_schema,
            }
        }

    def to_mcp_tool(self) -> dict:
        """转为 MCP tools/list 格式"""
        return {
            "name": self.meta.name,
            "description": self.meta.description,
            "inputSchema": self.input_schema,
        }

    def to_dict(self) -> dict:
        """Skill 的完整描述——供 LLM 技能发现使用"""
        return {
            "name": self.meta.name,
            "description": self.meta.description,
            "category": self.meta.category,
            "tags": self.meta.tags,
            "version": self.meta.version,
            "input_schema": self.input_schema,
        }


# ══════════════════════════════════════════════════════════════
# 2. 具体 Skill 实现 —— 以客服业务为例
# WHY: 每个 Skill 是自包含的——它有自己的数据、逻辑和校验，
#      不需要依赖全局变量或外部数据库。
# ══════════════════════════════════════════════════════════════

class OrderQuerySkill(Skill):
    """
    订单查询 Skill。
    WHY: 继承 Skill 基类，只需实现 meta + input_schema + execute，
         框架自动处理 OpenAI/MCP 格式转换。
    """
    meta = SkillMeta(
        name="order_query",
        description="根据订单号查询订单状态、商品、金额、物流信息",
        category="售后",
        tags=["订单", "查询", "售后"],
    )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "订单号，如 ORD20240001"
                }
            },
            "required": ["order_id"]
        }

    def execute(self, **kwargs) -> dict:
        order_id = kwargs.get("order_id", "")
        order = MOCK_ORDERS.get(order_id)
        if not order:
            return {"success": False, "data": None,
                    "error": f"订单 {order_id} 不存在"}
        return {"success": True, "data": order, "error": None}


class LogisticsQuerySkill(Skill):
    """物流查询 Skill"""
    meta = SkillMeta(
        name="logistics_query",
        description="根据快递单号查询物流轨迹、当前位置、预计送达",
        category="售后",
        tags=["物流", "查询", "售后"],
    )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "tracking_no": {"type": "string", "description": "快递单号"}
            },
            "required": ["tracking_no"]
        }

    def execute(self, **kwargs) -> dict:
        tn = kwargs.get("tracking_no", "")
        info = MOCK_LOGISTICS.get(tn)
        if not info:
            return {"success": False, "data": None,
                    "error": f"快递 {tn} 暂无记录"}
        return {"success": True, "data": info, "error": None}


class PolicyCheckSkill(Skill):
    """
    政策查询 Skill。
    WHY: 这个 Skill 内部用了 LLM——Skill 不限于纯函数，
         可以封装任何复杂逻辑（LLM 调用、数据库查询、API 请求等）。
    """
    meta = SkillMeta(
        name="policy_check",
        description="查询退换货政策，判断具体场景是否符合退货/换货/退款条件",
        category="售后",
        tags=["政策", "退货", "换货", "审核"],
    )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "scenario": {"type": "string", "description": "退货场景描述"},
                "category": {"type": "string", "description": "商品品类"}
            },
            "required": ["scenario"]
        }

    def execute(self, **kwargs) -> dict:
        scenario = kwargs.get("scenario", "")
        category = kwargs.get("category", "商品")
        reply = chat([
            {"role": "system",
             "content": f"根据政策判断：\n{RETURN_POLICY}\n\n"
                        f"输出 JSON: "
                        f'{{"eligible": bool, "policy_ref": "引用的政策条款", '
                        f'"suggestion": "建议"}}'},
            {"role": "user", "content": f"品类: {category}, 场景: {scenario}"},
        ], temperature=0.1)
        try:
            return {"success": True, "data": json.loads(reply), "error": None}
        except json.JSONDecodeError:
            return {"success": False, "data": None, "error": "LLM 返回格式异常"}


# ══════════════════════════════════════════════════════════════
# 3. SkillRegistry —— 统一的注册中心
# WHY: 所有 Skill 注册到 Registry，Agent 通过 Registry 发现和调用。
#      新增 Skill 只需 register()，不需要改任何 Agent 代码。
#      支持按分类/标签搜索，支持批量导出为 OpenAI/MCP 格式。
# ══════════════════════════════════════════════════════════════

class SkillRegistry:
    """
    Skill 注册中心。
    WHY: 单例模式 + dict 存储——简单但够用。
         生产环境可扩展为数据库存储、支持热加载。
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._skills: dict[str, Skill] = {}
        return cls._instance

    def register(self, skill: Skill) -> Skill:
        """注册一个 Skill"""
        self._skills[skill.meta.name] = skill
        return skill

    def get(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)

    def list_all(self) -> list[Skill]:
        return list(self._skills.values())

    def list_by_category(self, category: str) -> list[Skill]:
        return [s for s in self._skills.values()
                if s.meta.category == category]

    def list_by_tag(self, tag: str) -> list[Skill]:
        return [s for s in self._skills.values() if tag in s.meta.tags]

    def search(self, query: str) -> list[Skill]:
        """简单搜索：匹配名称和描述"""
        q = query.lower()
        return [s for s in self._skills.values()
                if q in s.meta.name.lower()
                or q in s.meta.description.lower()]

    def to_openai_functions(self, skill_names: list[str] = None) -> list[dict]:
        """将指定（或全部）Skill 转为 OpenAI Function Calling 格式"""
        skills = ([self.get(n) for n in skill_names if self.get(n)]
                  if skill_names else self.list_all())
        return [s.to_openai_function() for s in skills]

    def to_mcp_tools(self) -> list[dict]:
        return [s.to_mcp_tool() for s in self.list_all()]

    def to_llm_catalog(self) -> str:
        """
        生成供 LLM 查看的 Skill 目录。
        WHY: LLM 看到这个目录后可以在对话中主动推荐相关 Skill。
        """
        lines = ["可用 Skill 列表:", ""]
        for s in self.list_all():
            lines.append(f"- **{s.meta.name}** ({s.meta.category})")
            lines.append(f"  {s.meta.description}")
            lines.append(f"  参数: {list(s.input_schema.get('properties', {}).keys())}")
        return "\n".join(lines)


# ─── 全局注册中心 ──────────────────────────────
registry = SkillRegistry()


# ══════════════════════════════════════════════════════════════
# 4. @skill 装饰器 —— 一行代码注册 Skill
# WHY: 装饰器把"创建 Skill 类 → 注册"两步合并为一行，
#      降低 Skill 制作门槛，鼓励多创建 Skill。
# ══════════════════════════════════════════════════════════════

def skill(cls_or_name=None, **meta_kwargs):
    """
    Skill 装饰器。
    用法:
      @skill(name="my_skill", category="测试")
      class MySkill(Skill):
          ...

      @skill  # 使用类属性中的 meta
      class MySkill(Skill):
          meta = SkillMeta(name="my_skill", ...)
    """
    def _decorator(cls):
        if meta_kwargs:
            cls.meta = SkillMeta(**meta_kwargs)
        registry.register(cls())
        return cls

    if cls_or_name is not None and isinstance(cls_or_name, type):
        # @skill 不带括号
        return _decorator(cls_or_name)
    elif cls_or_name is not None:
        # @skill(name="xxx") 带参数
        meta_kwargs["name"] = cls_or_name
        return _decorator
    else:
        return _decorator


# ══════════════════════════════════════════════════════════════
# 5. Skill Pipeline —— 编排多个 Skill
# WHY: 单个 Skill 是原子操作，Pipeline 可以编排多个 Skill 按顺序
#      或条件执行——例如"先查订单→再根据状态决定是否需要查政策"。
# ══════════════════════════════════════════════════════════════

class SkillPipeline:
    """
    Skill 编排管道。
    WHY: Pipeline 本身也是 Skill 的执行模式——
         顺序执行多个 Skill，前一个的输出可以传给下一个的输入。
         如果某个 Skill 失败，可选择停止或继续。
    """
    def __init__(self, skills: list[Skill],
                 stop_on_error: bool = False):
        self.skills = skills
        self.stop_on_error = stop_on_error

    def run(self, initial_input: dict) -> dict:
        """顺序执行所有 Skill，结果累积返回"""
        results = []
        context = dict(initial_input)  # 上下文在 Skill 间传递

        for skill in self.skills:
            result = skill.execute(**context)
            results.append({
                "skill": skill.meta.name,
                "success": result["success"],
                "data": result["data"],
                "error": result["error"],
            })

            if not result["success"] and self.stop_on_error:
                return {"success": False, "steps": results,
                        "error": f"Skill [{skill.meta.name}] 执行失败"}

            # WHY: 前一个 Skill 的结果数据合并到 context，供后续 Skill 使用
            if result["success"] and isinstance(result["data"], dict):
                context.update(result["data"])

        return {"success": True, "steps": results, "final_context": context}


# ══════════════════════════════════════════════════════════════
# 注册客服 Skills
# ══════════════════════════════════════════════════════════════

registry.register(OrderQuerySkill())
registry.register(LogisticsQuerySkill())
registry.register(PolicyCheckSkill())


# ══════════════════════════════════════════════════════════════
# 演示
# ══════════════════════════════════════════════════════════════

def demo_skill_basics():
    """
    演示1：Skill 的定义与注册。
    """
    print("=" * 60)
    print(" 演示1：Skill 的定义与注册")
    print("=" * 60)

    # ─── 展示已注册的 Skill ──────────────────────
    print(f"\n  已注册 {len(registry.list_all())} 个 Skill:\n")
    for s in registry.list_all():
        print(f"  📦 {s.meta.name} (v{s.meta.version})")
        print(f"     分类: {s.meta.category} | 标签: {', '.join(s.meta.tags)}")
        print(f"     描述: {s.meta.description}")
        params = list(s.input_schema.get("properties", {}).keys())
        print(f"     参数: {params}")
        print()

    # ─── 按分类搜索 ──────────────────────────────
    print("  按分类 [售后] 搜索:")
    for s in registry.list_by_category("售后"):
        print(f"    - {s.meta.name}")

    # ─── 转 OpenAI / MCP 格式 ────────────────────
    openai_funcs = registry.to_openai_functions()
    print(f"\n  转为 OpenAI Functions: {len(openai_funcs)} 个")
    print(f"  转为 MCP Tools: {len(registry.to_mcp_tools())} 个")
    print()


def demo_skill_execute():
    """
    演示2：Skill 的执行 —— 统一接口，不同实现。
    """
    print("=" * 60)
    print(" 演示2：Skill 执行（统一接口）")
    print("=" * 60)

    # ─── 执行订单查询 Skill ──────────────────────
    print("\n  执行 order_query:")
    order_skill = registry.get("order_query")
    result = order_skill.execute(order_id="ORD20240001")
    print(f"    success={result['success']}")
    if result['success']:
        d = result['data']
        print(f"    商品: {d['product']}, 金额: {d['price']}, 状态: {d['status']}")

    # ─── 执行不存在的订单 ─────────────────────────
    print("\n  执行 order_query (不存在的订单):")
    result = order_skill.execute(order_id="NONEXIST")
    print(f"    success={result['success']}, error={result['error']}")

    # ─── 执行政策检查 Skill（含 LLM 调用）─────────
    print("\n  执行 policy_check (含 LLM):")
    policy_skill = registry.get("policy_check")
    result = policy_skill.execute(
        scenario="耳机使用5天左耳无声，要求退货退款",
        category="耳机"
    )
    print(f"    success={result['success']}")
    if result['success']:
        print(f"    判断: {json.dumps(result['data'], ensure_ascii=False)}")


def demo_skill_pipeline():
    """
    演示3：Skill 编排 —— 退换货流程的一条龙处理。
    """
    print("\n" + "=" * 60)
    print(" 演示3：Skill Pipeline —— 订单→政策一条龙")
    print("=" * 60)

    # WHY: Pipeline 把 3 个独立的 Skill 串成一条处理链——
    #      每个 Skill 独立可测试，组合在一起解决复杂问题
    pipeline = SkillPipeline([
        registry.get("order_query"),
        registry.get("policy_check"),
    ])

    print("\n  Pipeline: order_query → policy_check")
    result = pipeline.run({
        "order_id": "ORD20240001",
        "scenario": "耳机使用5天左耳无声，要求退款",
        "category": "耳机",
    })

    print(f"  Pipeline 结果: success={result['success']}")
    for step in result["steps"]:
        status = "✓" if step["success"] else "✗"
        print(f"    [{status}] {step['skill']}: "
              f"{json.dumps(step.get('data', ''), ensure_ascii=False)[:80]}")


def demo_skill_creation_guide():
    """
    演示4：创建新 Skill 的完整指南。
    """
    print("\n" + "=" * 60)
    print(" 演示4：如何创建一个新 Skill")
    print("=" * 60)

    print("""
  创建 Skill 的 4 个步骤：

  Step 1 — 定义元数据:
    meta = SkillMeta(
        name="my_new_skill",       # 唯一名称，LLM 通过名称调用
        description="清楚说明技能做什么",  # LLM 通过描述判断何时使用
        category="售后",            # 分类便于管理和搜索
        tags=["标签1", "标签2"],     # 标签支持多维度检索
    )

  Step 2 — 定义输入 Schema:
    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "参数说明"}
            },
            "required": ["param1"]
        }

  Step 3 — 实现执行逻辑:
    def execute(self, **kwargs) -> dict:
        # 核心逻辑
        return {"success": True, "data": {...}, "error": None}

  Step 4 — 注册:
    registry.register(MyNewSkill())

  或者用装饰器一行搞定:
    @skill(name="my_skill", category="售后", tags=["测试"])
    class MySkill(Skill):
        ...
""")

    # ─── 现场创建一个 Skill 演示 ──────────────────
    @skill(name="echo_skill", category="演示",
           description="回显输入——演示最简 Skill 创建")
    class EchoSkill(Skill):
        @property
        def input_schema(self):
            return {"type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"]}

        def execute(self, **kwargs):
            return {"success": True,
                    "data": {"echo": kwargs.get("text", "")}, "error": None}

    print("  现场创建 EchoSkill 并执行:")
    echo = registry.get("echo_skill")
    r = echo.execute(text="Hello, Skill!")
    print(f"    输入: Hello, Skill!")
    print(f"    输出: {r['data']}")
    print(f"  注册表当前共: {len(registry.list_all())} 个 Skill")


def main():
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║  Agent-Playground Demo 21: Agent Skill 制作方法    ║")
    print("║  Meta → Schema → Execute → Registry → Pipeline   ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    demo_skill_basics()
    demo_skill_execute()
    demo_skill_pipeline()
    demo_skill_creation_guide()

    print("=" * 60)
    print(" Demo 21 完成！Skill = 结构化的 Agent 能力单元")
    print("=" * 60)


if __name__ == "__main__":
    main()
