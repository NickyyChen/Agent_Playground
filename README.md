<p align="center">
  <h1 align="center">🤖 Agent Playground</h1>
  <p align="center"><strong>从入门到生产 —— Agent 开发全栈学习实验室</strong></p>
  <p align="center">
    <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python">
    <img src="https://img.shields.io/badge/LLM-DeepSeek--v4-green.svg" alt="DeepSeek">
    <img src="https://img.shields.io/badge/Framework-LangGraph-orange.svg" alt="LangGraph">
    <img src="https://img.shields.io/badge/Demos-21-red.svg" alt="21 Demos">
    <img src="https://img.shields.io/badge/License-MIT-lightgrey.svg" alt="MIT">
  </p>
</p>

---

## 📖 项目简介

**Agent Playground** 是一个系统性的 Agent 开发学习仓库。以「好买电商智能客服」为统一业务场景，通过 **21 个独立可运行的 Python Demo** + **1 个集成演示工程**，覆盖从"如何调用 LLM"到"多 Agent 编排 + 安全护栏 + 可观测性"的完整知识链路。

> 不是碎片化的 API 调用示例，而是一条从 Day 1 到 Production 的工程路径。

---

## 🚀 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/YOUR_USERNAME/Agent_Playground.git
cd Agent_Playground

# 2. 创建虚拟环境
conda create -n aiagent python=3.10 -y
conda activate aiagent
pip install -r requirements.txt

# 3. 配置密钥
cp .env.example .env
# 编辑 .env，填入你的 DeepSeek API Key（可选：LangSmith Key）

# 4. 运行第一个 Demo
python demos/01_llm_basic.py

# 5. 启动集成系统
python demos_all/main.py --demo        # 自动演示 4 种 Agent 模式
python demos_all/main.py               # 交互式 CLI
python demos_all/main.py --server      # FastAPI 服务 (http://localhost:8080/docs)
```

---

## 🏗️ 项目架构

```
Agent_Playground/
│
├── 📂 demos/                      # 21 个独立 Demo（零依赖，逐个击破）
│   ├── 01_llm_basic.py            # LLM 调用与参数控制
│   ├── 02_prompt_template.py      # Prompt Engineering 提示词工程
│   ├── 03_tool_calling.py         # Function Calling 工具调用
│   ├── 04_memory.py               # 短期 + 长期记忆系统
│   ├── 05_rag_basic.py            # RAG 检索增强生成
│   ├── 06_agent_react.py          # ReAct Agent 自主推理
│   ├── 07_plan_execute.py         # Plan & Execute 规划执行
│   ├── 08_reflection.py           # Reflection 自我反思
│   ├── 09_mcp_client.py           # MCP 协议客户端
│   ├── 09_mcp_server.py           # MCP 协议服务端
│   ├── 10_multi_agent.py          # 多 Agent 协作
│   ├── 11_langgraph_flow.py       # LangGraph 状态图编排
│   ├── 12_langchain_basic.py      # LangChain 链式调用
│   ├── 13_safety_guard.py         # 安全护栏（三重防护）
│   ├── 14_observability.py        # 可观测性追踪
│   ├── 15_agent_testing.py        # Agent 自动化评测
│   ├── 16_human_in_the_loop.py    # Human-in-the-Loop 人工审核
│   ├── 17_context_window.py       # Context Window 窗口管理
│   ├── 18_error_handling.py       # 错误处理与重试熔断
│   ├── 19_model_router.py         # 模型路由（分级调度）
│   ├── 20_prompt_cache.py         # Prompt 缓存策略
│   └── 21_skill_system.py         # Agent Skill 制作方法
│
├── 📂 demos_all/                  # 🎯 集成演示工程
│   ├── main.py                    # 统一入口（CLI / Demo / Server）
│   ├── config.py                  # 配置中心
│   ├── agent/                     # 核心能力层（LLM / 记忆 / 工具 / RAG / Skill）
│   ├── workflows/                 # 工作流引擎（ReAct / P&E / Reflection / Orchestrator）
│   ├── safety/                    # 安全护栏（Topic → Input → Output）
│   ├── tracing/                   # 可观测性（LangSmith + 本地追踪）
│   ├── api/                       # FastAPI 接口 + 中间件
│   └── tests/                     # 集成测试 + 场景测试
│
├── 📂 fastapi-basics/             # FastAPI 速成（5 个 Demo）
├── 📂 shared/                     # 公共模块（LLM 客户端 / 模拟数据）
├── 📄 .env.example                # 环境变量模板
└── 📄 requirements.txt            # 依赖清单
```

---

## 🗺️ 学习路线

### 第一阶段：能力基石 `Demo 01 – 05`

| 序号 | 主题 | 掌握什么 | 
|:---:|------|---------|
| 01 | **LLM 调用与参数控制** | `temperature` / `top_p` / `max_tokens` 如何塑造模型行为 |
| 02 | **Prompt Engineering** | System Prompt 人设设计 · 变量模板注入 · Few-shot 格式约束 |
| 03 | **Function Calling** | 让 LLM 调用外部工具——查订单、查物流、查政策 |
| 04 | **记忆系统** | `messages[]` 短期记忆 + ChromaDB 向量长期记忆 |
| 05 | **RAG 检索增强** | 文档切块 → BGE 向量嵌入 → 语义检索 → 多文档融合生成 |

### 第二阶段：Agent 思维模式 `Demo 06 – 08`

| 序号 | 模式 | 哲学 |
|:---:|------|------|
| 06 | **ReAct** | Thought → Action → Observation → Think again · 边走边看 |
| 07 | **Plan & Execute** | 先完整规划 → 再逐条执行 → 汇总回答 · 谋定后动 |
| 08 | **Reflection** | Generate → Critique → Revise · 自我审查，迭代修正 |

### 第三阶段：架构与协议 `Demo 09 – 12`

| 序号 | 主题 | 掌握什么 |
|:---:|------|---------|
| 09 | **MCP 协议** | 手写 JSON-RPC 2.0 over stdio，Client + Server 完整实现 |
| 10 | **多 Agent 协作** | Router 路由分发 · Handoff 接力传递 · Parallel 并行汇总 |
| 11 | **LangGraph 编排** | StateGraph 状态图 + 条件路由 + Checkpoint 持久化 |
| 12 | **LangChain 链式** | LCEL 管道语法 · PromptTemplate · OutputParser 结构化输出 |

### 第四阶段：生产工程化 `Demo 13 – 21`

| 序号 | 主题 | 掌握什么 |
|:---:|------|---------|
| 13 | **安全护栏** | Topic Guard → Input Guard → Output Guard 三重拦截 |
| 14 | **可观测性** | Span → Trace 树 → 瓶颈分析 + LangSmith 云端上报 |
| 15 | **自动化评测** | 测试用例构造 · 工具正确率 / 关键词命中率 / 拒识率评分 |
| 16 | **Human-in-the-Loop** | `interrupt()` 暂停等待人工审批 + `Command(resume)` 继续 |
| 17 | **Context Window 管理** | Token 计数预警 · 滑动窗口 · LLM 对话摘要压缩 |
| 18 | **错误处理** | 指数退避重试 · 熔断器 · JSON 修复重试 · 优雅降级 |
| 19 | **模型路由** | 问题复杂度分级 → Fast / Standard / Premium 三档调度 |
| 20 | **Prompt 缓存** | 本地缓存命中逻辑 · 缓存友好的 Message 排序策略 |
| 21 | **Skill 系统** | SkillMeta 元数据 · SkillRegistry 注册中心 · `@skill` 装饰器 |

### 第五阶段：集成实战 `demos_all/`

将前 21 个 Demo 的知识融为一个**可运行的智能客服演示系统**，集中展示各知识点如何协同工作：

- 🧠 **4 种 Agent 模式**：ReAct / Plan & Execute / Reflection / Multi-Agent Orchestrator
- 🖥️ **3 种运行方式**：交互式 CLI · `--demo` 自动演示 · `--server` FastAPI 服务
- 🛡️ **集成的知识点**：安全护栏 · LangSmith 追踪 · 错误重试 · 模型路由 · 记忆管理

---

## 🛠️ 技术栈

| 分类 | 技术 | 说明 |
|:---|------|------|
| 大模型 | **DeepSeek-v4-pro** | 兼容 OpenAI SDK，通过 `base_url` 接入 |
| Agent 框架 | **LangChain** + **LangGraph** | 链式调用 + 状态图编排 |
| 向量数据库 | **ChromaDB** | 轻量级本地向量存储 |
| 嵌入模型 | **BGE-large-zh-v1.5** | 中文语义专用，本地加载 |
| API 服务 | **FastAPI** + **Uvicorn** | 高性能异步 Web 框架 |
| 可观测性 | **LangSmith** | 云端 Trace 看板（可选，离线模式默认启用） |
| MCP 协议 | **手写 JSON-RPC 2.0** | 零外部依赖，理解协议本质 |

---

## ✨ 设计原则

| 原则 | 说明 |
|:---|------|
| 🔌 **独立可运行** | 每个 Demo 零依赖其他 Demo，任意挑选一个即可运行 |
| 💬 **注释解释 WHY** | 中文注释不解释「代码做了什么」，只解释「为什么这样设计」 |
| 🏪 **统一业务场景** | 全部 Demo 共享「好买电商智能客服」背景，故事连贯 |
| 🏭 **工程化思维** | 重试、熔断、护栏、追踪——将最佳实践融入每个 Demo |
| 📐 **自包含** | 每个 `.py` 文件头包含 ASCII 架构图、pip 安装指令、可直接 `python xxx.py` |

---

## 📊 运行集成系统

```bash
# 🤖 自动演示全部 4 种 Agent 模式（LangSmith 自动追踪）
python demos_all/main.py --demo

# 💬 交互式 CLI（支持模式切换：r/p/f/o）
python demos_all/main.py

# 🌐 启动 FastAPI 服务
python demos_all/main.py --server
# 浏览器打开 http://localhost:8080/docs 查看 Swagger 文档

# 🧪 运行集成测试
python demos_all/test_integration.py    # 18 项自动化测试
python demos_all/test_scenarios.py       # 5 个真实业务场景
```

---

## ⚙️ 配置

复制 `.env.example` 为 `.env`，填入密钥：

```bash
# 必填 —— DeepSeek API
DEEPSEEK_API_KEY=sk-your-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

# 可选 —— LangSmith 云端追踪（不填则使用本地追踪）
LANGCHAIN_API_KEY=lsv2_pt_your-key-here
LANGCHAIN_PROJECT=agent-playground
```

| 服务 | 注册地址 |
|:---|------|
| DeepSeek API | [platform.deepseek.com](https://platform.deepseek.com) |
| LangSmith | [smith.langchain.com](https://smith.langchain.com) |

---

## 📈 演示效果

运行 `python demos_all/main.py --demo` 后的典型输出：

```
                    🤖 好买电商智能客服系统

  LangSmith: 已连接 ✓
  {"platform": "LangSmith Cloud", "project": "agent-playground"}

  [ReAct] 订单 ORD20240001 的耳机左耳有杂音，能换货吗？
    工具调用: query_order → 漫步者 W820NB, 已签收
    工具调用: check_return_policy → 15天内质量问题免费换新
    客服: 您好，您的耳机符合换货条件...

  [Plan&Exec] 查订单 ORD20240001，再看物流 SF1234567890
    规划: [query_order, query_logistics] 2 步
    执行: ✓ 订单已查  ✓ 物流已查
    客服: 订单已签收，快递运输中，预计明天送达...

  [Reflection] 耳机用5天左耳没声，能退款吗？
    初版 → 审查(NO_ISSUES) → 终版
    客服: 拆封不支持无理由退货，但质量问题可免费换新...

  [MultiAgent] 推荐一款300以内的降噪耳机
    Router → 售前Agent
    客服: 推荐漫步者 W820NB，299元，-43dB降噪，50h续航...
```

---

## 🤝 贡献

这是一个简单直观的学习型仓库，欢迎：

- 📖 以此仓库为模板构建你自己的 Agent 学习项目

---

## 📄 开源协议

MIT License

---

<p align="center">
  <sub>Built with ❤️ using DeepSeek · LangChain · LangGraph · ChromaDB · FastAPI · LangSmith</sub>
</p>
