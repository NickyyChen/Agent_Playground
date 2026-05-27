# Agent-Playground

围绕**智能客服**这一统一业务场景，通过多个独立可运行的 Python demo文件，系统性学习 Agent 开发知识。

## 业务场景

所有 demo 共享同一个背景——某电商平台的智能客服系统：

- 用户咨询商品信息、退换货政策、优惠活动
- 用户查询订单状态、物流轨迹
- 用户投诉或申请退款，需升级人工处理
- 客服需具备知识检索、工具调用、多轮记忆、安全风控等能力

## 技术栈

- Python 3.10+
- LLM：DeepSeek-v4-pro
- 核心库：`langchain`、`langgraph`、`chromadb`、`mcp`、`openai`、`Qdrant`等
- 每个 demo 顶部注释标注所需的 `pip install` 命令

## 目录结构

```
Agent-Playground/
├── demos/           # 所有 demo 脚本，按序号排列
├── shared/           # 公共模块（LLM 客户端、模拟数据、配置）
├── requirements.txt
└── CLAUDE.md
```

## Demo 文件规范

每个 `.py` 文件必须包含：

1. **文件头中文说明**：这个概念是什么、在智能客服中解决什么问题、核心流程
2. **ASCII 架构/流程图**：简单的可视化数据流和组件交互
3. **关键代码中文注释**：解释**为什么这样做（WHY）**，**说明关键参数/函数代表什么**
4. **可直接运行**：`python demos/01_llm_basic.py`，依赖最少，输出清晰

## Claude 行为约束

- 每个 demo 独立可运行，不依赖其他 demo
- 中文注释只解释 WHY，并且写清楚关键参数和函数
- ASCII 图必须画清楚数据流向和组件角色
- 始终在智能客服场景下举例，保持故事连贯
- 不引入不必要的抽象，代码教学友好，能跑优先

## 运行环境

全程要安装的包和运行环境都在虚拟环境 aiagent 中
可以使用 **conda activate aiagent** 命令进行启动 