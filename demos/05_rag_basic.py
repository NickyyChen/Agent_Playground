# -*- coding: utf-8 -*-
"""
05_rag_basic.py — RAG 基础：检索增强生成
========================================

【概念】
RAG（Retrieval-Augmented Generation）= 检索 + 生成。
LLM 的训练数据有截止日期，且不可能记住所有商品参数、内部政策——
RAG 的思路是：用户提问时，先从外部知识库"检索"相关文档片段，
再把片段作为"参考资料"注入 prompt，让 LLM 据此生成准确回答。

类比：LLM 是一个答题高手，RAG 是考试前塞给它一本"开卷参考资料"。

【在智能客服中解决什么问题】
智能客服需要回答用户关于商品参数、使用技巧、售后政策的具体问题：
- "这款耳机支持LDAC吗？" ← LLM 的训练数据不知道新品参数
- "跑步用的耳机防水等级多少？" ← 需要查商品规格表
- "同价位 A 和 B 哪个好？" ← 需要多文档对比

这些答案不能靠 LLM 背课文，必须从知识库实时检索。

【核心流程】
1. 构建知识库：把商品文档切成小块(chunk)，逐一向量化存入 ChromaDB
2. 用户提问 → 向量化 → 在 ChromaDB 中语义检索 top-k 相似片段
3. 把检索到的片段拼入 system prompt 作为"参考资料"
4. LLM 阅读参考资料，生成有依据的回答

【pip install】
pip install openai chromadb sentence-transformers langchain-text-splitters

【ASCII 架构图】

 ┌───────────────────────────────────────────────────────────────┐
 │                        RAG 流程                                │
 │                                                                │
 │   【离线阶段：构建知识库】                                         │
 │   ┌──────────┐    ┌───────────┐    ┌──────────┐               │
 │   │ 商品文档  │───▶│ 文本切块   │───▶│ 向量嵌入  │───▶ ChromaDB  │
 │   │ 政策文档  │    │ (chunking) │    │ (BGE模型) │               │
 │   │ FAQ文档  │    └───────────┘    └──────────┘               │
 │   └──────────┘                                                 │
 │                                                                │
 │   【在线阶段：检索+生成】                                          │
 │   ┌──────────┐    ┌───────────┐    ┌──────────┐               │
 │   │ 用户提问  │───▶│ 语义检索   │───▶│ 拼接Prompt│               │
 │   │          │    │ top-k=3   │    │          │               │
 │   └──────────┘    └───────────┘    └────┬─────┘               │
 │                                         │                      │
 │                    ┌────────────────────┘                      │
 │                    ▼                                           │
 │   ┌────────────────────────────────────┐                      │
 │   │ System: 你是客服 + 【参考资料】...     │                      │
 │   │ User: 用户问题                       │──▶ LLM ──▶ 回答      │
 │   └────────────────────────────────────┘                      │
 └───────────────────────────────────────────────────────────────┘
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from shared.llm_client import chat

# ─── BGE 中文嵌入模型 ──────────────────────────────────────
BGE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "bge-large-zh-v1.5")
_bge = SentenceTransformer(BGE_PATH)


class BGEEmbedding(EmbeddingFunction):
    """ChromaDB 自定义嵌入函数，使用本地 BGE 中文模型。"""
    def __call__(self, input: Documents) -> Embeddings:
        return _bge.encode(input, normalize_embeddings=True).tolist()


# ══════════════════════════════════════════════════════════════
# 知识库文档（模拟电商平台的商品/政策/FAQ 资料）
# WHY: 这些文档涵盖三类：商品规格、使用技巧、售后政策，
#      模拟真实客服知识库的多主题、多风格内容。
# ══════════════════════════════════════════════════════════════

KNOWLEDGE_DOCS = [
    # ─── 商品规格 ────────────────────────────────────
    {
        "title": "漫步者W820NB产品规格",
        "content": """
漫步者 W820NB 头戴式降噪耳机参数：
- 蓝牙版本：5.2，支持 SBC/AAC/LDAC 三种音频编码
- 降噪深度：-43dB 混合主动降噪，支持环境声模式
- 续航：开降噪 50 小时，关降噪 60 小时，充电 10 分钟可用 5 小时
- 重量：265g，耳罩可折叠，配备收纳盒
- 防水等级：IPX4（防溅水，适合运动但不适合游泳）
- 频率响应：20Hz-40kHz，获得 Hi-Res Audio 认证
- 售价：299 元，保修期 1 年
""",
    },
    {
        "title": "Sony WH-1000XM5产品规格",
        "content": """
Sony WH-1000XM5 旗舰头戴式降噪耳机参数：
- 蓝牙版本：5.2，支持 SBC/AAC/LDAC
- 降噪：集成处理器 V1 + 8 麦克风AI降噪，自适应环境
- 续航：开降噪 30 小时，充电 3 分钟可用 3 小时（快充）
- 重量：250g，全新无折叠设计，舒适蛋白皮革耳罩
- 无防水等级认证（不建议运动中大量出汗使用）
- 频率响应：4Hz-40kHz，Hi-Res Audio 认证
- 售价：2299 元，保修期 2 年
- 特色功能：佩戴检测、智能免摘（说话时自动暂停音乐和降噪）
""",
    },
    {
        "title": "小米Buds 4 Pro产品规格",
        "content": """
小米 Buds 4 Pro 真无线降噪耳塞参数：
- 蓝牙版本：5.3，支持 SBC/AAC/LHDC 5.0（最高 192kHz）
- 降噪深度：-48dB 自适应降噪，三档可调
- 续航：耳机单次 9 小时，配合充电盒 38 小时，支持无线充电
- 单耳重量：5.0g
- 防水等级：IP54（防尘防溅，适合运动）
- 售价：899 元，保修期 1 年
- 特色功能：空间音频、双设备连接、佩戴贴合度检测
""",
    },
    {
        "title": "QCY T13入门级耳塞参数",
        "content": """
QCY T13 入门级真无线耳塞参数：
- 蓝牙版本：5.1，支持 SBC/AAC
- 无主动降噪，依赖入耳式物理隔音
- 续航：单次 8 小时，配合充电盒 40 小时
- 防水等级：IPX5（防汗防雨，适合运动和通勤）
- 售价：79 元，保修期 6 个月
- 适合人群：学生党、预算有限、对音质要求不高的日常使用
""",
    },

    # ─── 使用技巧 / FAQ ───────────────────────────────
    {
        "title": "降噪耳机使用技巧FAQ",
        "content": """
降噪耳机常见问题 FAQ：
Q: 主动降噪和被动降噪有什么区别？
A: 主动降噪（ANC）通过麦克风收集环境噪音并产生反向声波抵消，
   对低频噪音（飞机引擎、空调）效果好；
   被动降噪靠物理隔音（耳罩、耳塞），对中高频（人声）更有效。

Q: 降噪耳机戴着头晕怎么办？
A: 部分人对 ANC 的"耳压感"敏感。建议：(1)先开低档降噪适应几天；
   (2)选择有"自适应降噪"的型号；(3)每隔 1 小时摘下休息。

Q: LDAC 和 AAC 编码有什么区别？
A: LDAC 支持最高 990kbps 传输速率，接近无损音质，需要安卓手机
   （设置→蓝牙→开启LDAC）。AAC 最高 320kbps，苹果设备默认使用。
   普通用户日常听歌差异不大，发烧友建议用 LDAC。

Q: 运动时能戴降噪耳机吗？
A: 跑步/健身建议选防水等级 IPX4 以上的耳塞式降噪耳机；
   头戴式运动时容易晃动且汗液可能损坏耳罩，不建议。
   户外跑步注意安全，建议开环境声模式。
""",
    },
    {
        "title": "耳机选购指南",
        "content": """
耳机选购参考：
| 使用场景     | 推荐类型       | 关键参数               | 建议预算 |
| 通勤/办公    | 头戴式ANC      | 降噪深度、续航、舒适度    | 300-2000元 |
| 运动/跑步    | 真无线/骨传导   | 防水等级(≥IPX4)、佩戴稳固 | 100-600元 |
| 学生/预算    | 真无线入门      | 续航、性价比、售后        | 50-300元 |
| 发烧/音质    | 有线/头戴LDAC  | 频响范围、单元尺寸         | 1000-5000元 |

选购技巧：
- 降噪不是越深越好——通勤需要强降噪，办公室轻度降噪即可
- 长时间佩戴选轻量头戴式（<280g）或轻巧入耳式（<6g/耳）
- 通话多的注意麦克风数量（≥3个为佳）
- 务必试戴！每个人的耳型不同，舒适度差异很大
""",
    },
    {
        "title": "耳机的清洁与保养",
        "content": """
耳机保养注意事项：
- 耳罩/耳塞套每月用微湿软布擦拭，不要用酒精（会加速皮革/硅胶老化）
- 折叠式耳机避免频繁反复折叠，排线故障是头戴式耳机最常见的维修原因
- 充电口保持干燥，汗渍会导致触点氧化，建议运动后用干布擦拭
- 长期不使用时保持 50-80% 电量存放（锂电池最健康的存储状态）
- 夏季高温不要把耳机留在车内，电池可能鼓包
""",
    },

    # ─── 售后政策 ────────────────────────────────────
    {
        "title": "好买电商耳机品类退换货政策",
        "content": """
好买电商耳机品类退换货政策（2024版）：
1. 退货条件：签收后7天内，未拆封、配件齐全可无理由退货。拆封后不支持无理由退货（属个人卫生用品）。
2. 换货条件：签收后15天内，出现非人为质量问题（偏音、杂音、无法开机、蓝牙断连等），
   经售后检测确认后可免费换新。人为损坏（进水、摔落、外观损毁）不在免费换货范围。
3. 退款时效：退货签收后 3 个工作日内原路退回。
4. 保修期：耳机类商品保修期根据品牌不同为 6 个月至 2 年，具体以商品页标注为准。
   保修期内非人为故障免费维修。
5. 退换流程：App内"我的订单→申请售后"→填写原因/上传照片→等待审核→寄回/上门取件。
""",
    },
]


# ══════════════════════════════════════════════════════════════
# 知识库构建
# ══════════════════════════════════════════════════════════════

def build_knowledge_base():
    """
    将文档切块 → 嵌入向量 → 存入 ChromaDB。
    WHY: 切块（chunking）是 RAG 的关键预处理步骤——
         块太大 → 检索噪音多、LLM 抓不住重点
         块太小 → 语义不完整、检索容易断章取义
         RecursiveCharacterTextSplitter 按自然段落边界切，优先保证完整性
    """
    client = chromadb.PersistentClient(
        path=os.path.join(os.path.dirname(__file__), "..", ".chroma_rag")
    )
    try:
        client.delete_collection("knowledge_base")
    except Exception:
        pass
    collection = client.create_collection(
        "knowledge_base",
        embedding_function=BGEEmbedding(),
    )

    # WHY: chunk_size=300 每块约 300 字符，chunk_overlap=50 相邻块重叠
    #      50 字符——避免关键信息刚好落在分割边界上被切碎。
    #      中文约 2 字符/token，300 字符 ≈ 150 token
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=300, chunk_overlap=50,
        separators=["\n\n", "\n", "。", "；", "，", " ", ""],
    )

    doc_id = 0
    for doc in KNOWLEDGE_DOCS:
        chunks = splitter.split_text(doc["content"])
        for i, chunk in enumerate(chunks):
            # WHY: 每条 chunk 存入时附带 metadata（来源文档标题），
            #      检索时可以看到每条结果来自哪个文档，增强可解释性
            collection.add(
                documents=[chunk],
                metadatas=[{"source": doc["title"], "chunk_index": i}],
                ids=[f"doc_{doc_id}"],
            )
            doc_id += 1

    return collection


# ══════════════════════════════════════════════════════════════
# 演示函数
# ══════════════════════════════════════════════════════════════

SYSTEM_WITHOUT_RAG = """你是"小选"，好买电商的智能客服，回答简洁专业。"""


def demo_no_rag_vs_rag(collection):
    """
    演示1：无 RAG vs 有 RAG —— 同一个问题，回答质量天差地别。
    WHY: 没有 RAG 时，LLM 对具体商品的参数回答靠"猜"（训练数据中的模糊记忆）
         → 可能过时、可能编造、可能遗漏；
         有 RAG 时，检索到的文档片段作为"参考资料"塞入 prompt
         → LLM 基于真实数据回答，准确度和可信度大幅提升。
    """
    print("=" * 60)
    print(" 演示1：无 RAG vs 有 RAG")
    print("=" * 60)

    question = "漫步者W820NB支持LDAC吗？续航多久？能戴着跑步吗？"

    # ─── 无 RAG ─────────────────────────────────────
    print(f" 用户: {question}")
    print()
    print("【无 RAG——LLM 凭训练记忆回答】")
    reply_no_rag = chat([
        {"role": "system", "content": SYSTEM_WITHOUT_RAG},
        {"role": "user", "content": question},
    ])
    print(f"  客服: {reply_no_rag}")

    # ─── 有 RAG ─────────────────────────────────────
    # WHY: n_results=3 —— 检索 top-3 最相关文档片段。
    #      太少可能漏掉关键信息（这个问了三方面），
    #      太多会稀释重点，3~5 是实践中常用的范围
    results = collection.query(query_texts=[question], n_results=3)

    # WHY: 把检索到的片段拼接成"参考资料"，格式化后注入 system prompt
    context_parts = []
    if results["documents"] and results["documents"][0]:
        for i, (doc, meta) in enumerate(zip(
            results["documents"][0], results["metadatas"][0]
        )):
            context_parts.append(f"[参考{i+1} | 来源: {meta['source']}]\n{doc}")
    retrieved_context = "\n\n---\n\n".join(context_parts)

    rag_system = SYSTEM_WITHOUT_RAG + f"""

【参考资料 —— 请严格根据以下资料回答，不要编造】
{retrieved_context}
"""
    print()
    print("【有 RAG——检索到的参考资料】")
    for i, (doc, meta) in enumerate(zip(
        results["documents"][0], results["metadatas"][0]
    )):
        print(f"  参考{i+1} [来源: {meta['source']}]: {doc[:80]}...")
    print()

    reply_with_rag = chat([
        {"role": "system", "content": rag_system},
        {"role": "user", "content": question},
    ])
    print(f"  客服: {reply_with_rag}")
    print()


def demo_semantic_search(collection):
    """
    演示2：语义检索 —— 同一句话不同说法，检索结果应该一致。
    WHY: 向量检索理解的是"语义"，不是"关键词"——
         用户说"跑步用的耳机"能匹配到"运动耳机"相关的文档片段，
         即使用词完全不同。这是向量检索相比关键词检索的核心优势。
    """
    print("=" * 60)
    print(" 演示2：语义检索 —— 换说法也能找到")
    print("=" * 60)

    # WHY: 三句话表达的是同一类需求，关键词不同，但语义相近
    queries = [
        "推荐一款适合健身用的耳机",
        "有没有运动的时候戴的那种耳机？",
        "我跑步比较多，配个什么耳机好？",
    ]

    for q in queries:
        results = collection.query(query_texts=[q], n_results=1)
        if results["documents"] and results["documents"][0]:
            source = results["metadatas"][0][0]["source"]
            snippet = results["documents"][0][0][:60]
            print(f" 查询: {q}")
            print(f"  最佳匹配 ← {source}: \"{snippet}...\"")
            print()


def demo_multi_doc_fusion(collection):
    """
    演示3：多文档融合 —— 一个问题需要综合多篇文档才能完整回答。
    WHY: 真实客服场景中，用户经常问"A和B哪个好？"这类对比问题，
         单篇文档只能提供其中一个商品的信息，必须检索多个文档片段，
         LLM 综合所有素材后才能给出有依据的对比回答。
    """
    print("=" * 60)
    print(" 演示3：多文档融合 —— 跨文档对比回答")
    print("=" * 60)

    question = "小米Buds 4 Pro和QCY T13，我是学生党预算有限，该选哪个？"

    results = collection.query(query_texts=[question], n_results=4)
    context_parts = []
    if results["documents"] and results["documents"][0]:
        for i, (doc, meta) in enumerate(zip(
            results["documents"][0], results["metadatas"][0]
        )):
            context_parts.append(f"[参考{i+1} | {meta['source']}]\n{doc}")

    rag_system = SYSTEM_WITHOUT_RAG + "\n\n【参考资料】\n" + \
        "\n\n---\n\n".join(context_parts) + \
        "\n\n请综合以上参考资料，对比两款产品，给出明确推荐并说明理由。"

    print(f" 用户: {question}")
    print(f" 检索到 {len(results['documents'][0])} 篇相关文档")
    reply = chat([
        {"role": "system", "content": rag_system},
        {"role": "user", "content": question},
    ])
    print(f" 客服: {reply}")
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║  Agent-Playground Demo 05: RAG 检索增强生成       ║")
    print("║  文档切块→向量嵌入→语义检索→上下文注入→生成        ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    print(" 正在构建知识库（切块 + 嵌入）...")
    collection = build_knowledge_base()
    print(f" 知识库就绪，共 {collection.count()} 个文档块\n")

    demo_no_rag_vs_rag(collection)
    demo_semantic_search(collection)
    demo_multi_doc_fusion(collection)

    print("=" * 60)
    print(" Demo 05 完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
