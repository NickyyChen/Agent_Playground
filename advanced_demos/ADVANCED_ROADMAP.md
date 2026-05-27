# Agent 进阶学习路线

## 一、RAG 深度进化

| 主题 | 核心问题 | 复杂度 |
|------|---------|--------|
| **Chunk 策略深度** | 固定大小 vs 语义切分 vs 句子窗口 vs 层级切分——不同文档类型怎么切？ | ⭐⭐ |
| **Hybrid Search + Rerank** | 向量检索 + BM25 关键词检索融合，再加 Reranker 精排 | ⭐⭐ |
| **Self-RAG / Corrective RAG** | Agent 检索后自检"搜到的文档有用吗？"，不够就重搜 | ⭐⭐⭐ |
| **Agentic RAG** | 不是"搜一次→回答"，而是 Agent 自主决定搜几次、搜哪里、怎么搜 | ⭐⭐⭐ |
| **GraphRAG** | 不用向量——用知识图谱表达实体关系，适合"A 和 B 什么关系"类问题 | ⭐⭐⭐⭐ |
| **RAPTOR / 层级索引** | 长文档先聚类建摘要树，检索时不搜碎片而是搜层级 | ⭐⭐⭐⭐ |
| **Multi-Modal RAG** | 用户发图（破损包裹照片）→ 图片+文本融合检索 | ⭐⭐⭐⭐ |

## 二、LangGraph 编排进阶

| 主题 | 核心问题 | 复杂度 |
|------|---------|--------|
| **Map-Reduce** | N 个文档并行分析→汇总，适合批量客服工单分析 | ⭐⭐ |
| **Fan-out / Fan-in** | 一个请求并行分发给多个 Agent → 合并结果 | ⭐⭐ |
| **Supervisor-Worker** | 一个"主管 Agent"分配任务→多个"执行 Agent"干活→主管汇总 | ⭐⭐⭐ |
| **Sub-graph 嵌套** | 大图里嵌套子图，退款子流程 → 质检子流程 → 通知子流程 | ⭐⭐⭐ |
| **Dynamic Breakpoints** | 运行时动态决定在哪暂停（而不是写死 interrupt 位置） | ⭐⭐⭐ |
| **Time-Travel** | 回退到之前某个状态重新执行——客服场景的"撤销操作" | ⭐⭐⭐ |
| **Streaming + Events** | 图执行过程中实时推送事件（"正在查订单..."→"正在匹配政策..."） | ⭐⭐ |

## 三、Agent 架构模式

| 主题 | 核心问题 | 复杂度 |
|------|---------|--------|
| **LLM-as-Judge** | 用一个独立 LLM 给 Agent 的回答打分，不满分会自动重试 | ⭐⭐ |
| **Multi-Agent Debate** | 多个 Agent 并行回答同一问题，辩论后投票选最佳答案 | ⭐⭐⭐ |
| **Hierarchical Agent Teams** | 三层结构：Coordinator → Team Leads → Workers | ⭐⭐⭐⭐ |
| **Dynamic Tool Generation** | Agent 发现自己缺工具时，自动写新工具而非死板返回"做不到" | ⭐⭐⭐⭐ |
| **Continual Learning Agent** | 从历史对话中学习——用户偏好、常见问题模式自动沉淀为知识 | ⭐⭐⭐⭐ |

## 四、Memory 体系深化

| 主题 | 核心问题 | 复杂度 |
|------|---------|--------|
| **Buffer / Summary / Token-Window** | 三种短期记忆策略的实际取舍和混合使用 | ⭐⭐ |
| **Entity Memory** | 不只记对话，而是提取"实体"（用户小明→偏好头戴式→预算300）建图谱 | ⭐⭐⭐ |
| **Multi-Session Profile** | 用户跨设备、跨时间的统一画像，客服的"360度用户视图" | ⭐⭐⭐ |

## 五、MCP 生产级应用

| 主题 | 核心问题 | 复杂度 |
|------|---------|--------|
| **Multi-Server MCP** | 订单 Server + 物流 Server + 知识库 Server → Client 统一聚合 | ⭐⭐⭐ |
| **SSE/HTTP Transport** | stdio 只适合本地，远程部署需要 HTTP/SSE 传输 | ⭐⭐ |
| **MCP Resource + Prompt** | 除了 tools，MCP 还定义了 resources（数据）和 prompts（模板） | ⭐⭐ |
| **OAuth + 权限** | 不同 MCP Server 需要不同权限控制 | ⭐⭐⭐ |

## 六、评估体系

| 主题 | 核心问题 | 复杂度 |
|------|---------|--------|
| **RAGAS 评估框架** | Faithfulness / Answer Relevancy / Context Precision / Context Recall | ⭐⭐ |
| **DeepEval / MLflow Eval** | 自动化评估管线——每次改 prompt 自动跑全量评测 | ⭐⭐⭐ |
| **Synthetic Data Generation** | 用 LLM 自动生成测试用例——覆盖客服的 100 种退货场景 | ⭐⭐⭐ |

## 七、生产运维

| 主题 | 核心问题 | 复杂度 |
|------|---------|--------|
| **Sessions + Concurrency** | 多用户同时对话的会话隔离和并发控制 | ⭐⭐ |
| **Prompt 版本管理** | System prompt 改了怎么回滚？怎么 A/B 测试新旧 Prompt？ | ⭐⭐ |
| **异步 + 非阻塞** | asyncio + 流式输出 + 批量处理 | ⭐⭐ |
| **LangFuse 深度接入** | 不止追踪，还要 Dashboard / 告警 / 成本分析 | ⭐⭐ |

---

## 建议学习顺序（按依赖关系）

```
第一层：RAG 深化
  ├─ Chunk 策略 → Hybrid Search + Rerank
  ├─ Self-RAG / Corrective RAG → Agentic RAG
  └─ GraphRAG（独立路线）

第二层：编排进阶
  ├─ Map-Reduce → Fan-out/Fan-in → Supervisor-Worker
  ├─ Sub-graphs → Dynamic Breakpoints → Time-Travel
  └─ Streaming + Events

第三层：Agent 架构
  ├─ LLM-as-Judge → Hierarchical Teams
  └─ Multi-Agent Debate

第四层：评估 + 运维
  ├─ RAGAS → 自动化评测管线
  └─ LangFuse → Prompt 版本管理
```
