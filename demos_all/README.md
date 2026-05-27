# 好买电商智能客服系统 —— Agent 全知识点集成工程

本项目将 21 个 Demo 中学到的所有 Agent 开发知识点，集成到一个可运行的生产级客服系统中。

## 运行方式

```bash
# CLI 交互模式
python demos_all/main.py

# 自动演示所有知识点
python demos_all/main.py --demo

# 启动 FastAPI 服务 (http://localhost:8080/docs)
python demos_all/main.py --server
```

## 目录结构

```
demos_all/
├── main.py                    # 系统入口 (CLI / Server / Demo 三种模式)
├── config.py                  # 统一配置中心
├── README.md                  # 本文档
│
├── agent/                     # ── 核心能力层 ──
│   ├── llm.py                 # LLM 客户端 (路由+重试+缓存+参数控制)
│   ├── memory.py              # 记忆系统 (短期+长期+窗口管理)
│   ├── tools.py               # 工具注册中心 (Function Calling + MCP兼容)
│   ├── rag.py                 # RAG 知识库 (切块+嵌入+检索+多文档融合)
│   └── skills.py              # Skill 系统 (注册中心+装饰器)
│
├── workflows/                 # ── Agent 工作流层 ──
│   ├── react.py               # ReAct Agent (Thought→Action→Observation)
│   ├── planner.py             # Plan & Execute (规划→执行→汇总)
│   ├── reflector.py           # Reflection (生成→审查→修正)
│   └── orchestrator.py        # 多Agent编排 (Router→售前/售后 + HITL)
│
├── safety/                    # ── 安全层 ──
│   └── guard.py               # 三道护栏 (Topic/Input/Output Guard)
│
├── tracing/                   # ── 可观测层 ──
│   └── tracer.py              # Span/Trace 追踪 + 瓶颈分析
│
├── api/                       # ── 接口层 ──
│   └── routes.py              # FastAPI 路由 + 中间件 + 请求/响应模型
│
└── tests/                     # ── 测试层 ──
    └── test_agent.py          # 8 条测试用例, 覆盖功能/边界/安全
```

## 知识点覆盖矩阵

| # | 知识点 | 对应模块 | 核心实现 |
|---|--------|---------|---------|
| 01 | LLM 参数控制 | `agent/llm.py` | temperature/max_tokens 透传 |
| 02 | Prompt 模板 | `config.py` | SYSTEM_PROMPT 人设定义 |
| 03 | Function Calling | `agent/tools.py` | ToolRegistry + OpenAI/MCP 双格式 |
| 04 | 短期+长期记忆 | `agent/memory.py` | messages[] + ChromaDB + 召回注入 |
| 05 | RAG 检索增强 | `agent/rag.py` | 文档切块 + BGE嵌入 + 语义检索 + 多文档融合 |
| 06 | ReAct Agent | `workflows/react.py` | Thought→Action→Observation 循环 |
| 07 | Plan & Execute | `workflows/planner.py` | 规划阶段→执行阶段→汇总阶段 |
| 08 | Reflection | `workflows/reflector.py` | Generate→Reflect→Revise 迭代 |
| 09 | MCP 协议 | `agent/tools.py` | to_mcp_tools() + tools/call 格式 |
| 10 | 多 Agent 协作 | `workflows/orchestrator.py` | Router → 售前/售后 Agent |
| 11 | LangGraph 编排 | `workflows/orchestrator.py` | StateGraph + 条件路由 + checkpointer |
| 12 | LangChain 链式 | `agent/llm.py` | 链式调用封装 |
| 13 | 安全护栏 | `safety/guard.py` | Topic/Input/Output 三道 Guard |
| 14 | 可观测性 | `tracing/tracer.py` | Span→Trace→瓶颈分析报告 |
| 15 | Agent 评测 | `tests/test_agent.py` | 8条用例, 工具调用+关键词+拒识 |
| 16 | Human-in-the-Loop | `workflows/orchestrator.py` | interrupt() + Command(resume) |
| 17 | Context Window | `agent/memory.py` | 滑动窗口 + 摘要压缩 |
| 18 | 错误处理 | `agent/llm.py` | 指数退避重试 + 熔断器 |
| 19 | 模型路由 | `agent/llm.py` | fast/standard/premium 三档分级 |
| 20 | Prompt 缓存 | `agent/llm.py` | 本地缓存 + cache_stats |
| 21 | Skill 系统 | `agent/skills.py` | SkillRegistry + @skill 装饰器 |

## 系统架构图

```
  ┌──────────────────────────────────────────────────────────┐
  │                    用户请求 (CLI / API)                    │
  └──────────────────────────┬───────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  Safety Guard    │  ← Demo 13
                    │  Topic→Input     │
                    └────────┬────────┘
                             │ pass
                    ┌────────▼────────┐
                    │  Model Router    │  ← Demo 19
                    │  fast/std/prem   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Memory + RAG    │  ← Demo 04/05/17
                    │  上下文增强       │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
       ┌──────▼─────┐ ┌──────▼─────┐ ┌──────▼──────┐
       │ ReAct (06) │ │ P&E (07)   │ │ Reflect (08)│
       └────────────┘ └────────────┘ └─────────────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                    ┌────────▼────────┐
                    │  Output Guard    │  ← Demo 13
                    │  + 追踪 (14)     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  最终回答         │
                    └─────────────────┘
```
