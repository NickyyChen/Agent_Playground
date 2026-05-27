# -*- coding: utf-8 -*-
"""
04_memory.py — 对话记忆：短期记忆 vs 长期记忆
=============================================

【概念】
LLM 本身是无状态的——每次 API 调用都是"失忆"的，它不记得上一轮说过什么。
要让客服能多轮对话，必须在外部管理"记忆"。

记忆分为两层：
- **短期记忆**：当前会话内的对话历史（messages[] 列表），会话结束即消失
- **长期记忆**：跨会话保留的用户信息（偏好、历史问题），需要外部存储
  来"记住"——会话 A 了解到的用户偏好，会话 B 依然可用

【在智能客服中解决什么问题】
- 短期记忆：用户追问"那第二个呢？"时，客服需要知道前面聊了哪几个选项
- 长期记忆：用户上次投诉过耳机质量问题，这次再咨询时客服应该主动问
  "您上次的耳机换新后用得怎么样？"，而不是像第一次见面

【核心流程】
- 短期记忆：每轮把 user/assistant 消息追加到 messages[]，下次请求全量发送
- 长期记忆：用 ChromaDB 做向量存储，把历史交互摘要存进去，新会话开始
  时通过语义检索召回相关内容，注入到 system prompt 中

【pip install】
pip install openai chromadb

【ASCII 架构图】

 ┌──────────────────────────────────────────────────────────────┐
 │                      Agent 记忆系统                          │
 │                                                              │
 │   ┌──────────────────────┐    ┌───────────────────────────┐  │
 │   │    短期记忆 (会话内)   │    │    长期记忆 (跨会话)        │  │
 │   │                      │    │                           │  │
 │   │  messages[] 列表      │    │  ChromaDB 向量数据库       │  │
 │   │  ┌────────────────┐  │    │  ┌─────────────────────┐  │  │
 │   │  │ system: 人设     │  │    │  │ 历史交互摘要1        │  │  │
 │   │  │ user: 查订单     │  │    │  │ "用户偏好入耳式..."   │  │  │
 │   │  │ assistant: 哪个? │  │    │  ├─────────────────────┤  │  │
 │   │  │ user: ORD001    │  │    │  │ 历史交互摘要2        │  │  │
 │   │  │ assistant: 查到..│  │    │  │ "投诉过音质问题..."   │  │  │
 │   │  │ user: 催一下     │◀─┼────│  ├─────────────────────┤  │  │
 │   │  └────────────────┘  │    │  │ 历史交互摘要3        │  │  │
 │   │                      │    │  │ "咨询过退换货..."     │  │  │
 │   │  会话结束 → 清空      │    │  └─────────────────────┘  │  │
 │   └──────────────────────┘    │                           │  │
 │                               │  嵌入 → 语义检索 → 召回     │  │
 │                               │  会话结束 → 继续保留        │  │
 │                               └───────────────────────────┘  │
 └──────────────────────────────────────────────────────────────┘
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import json, chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
from sentence_transformers import SentenceTransformer
from shared.llm_client import chat

# ─── 中文嵌入模型加载 ───────────────────────────────────────
# WHY: ChromaDB 默认的 all-MiniLM-L6-v2 是英文模型，对中文客服场景
#      语义检索效果差。这里用本地已有的 BGE 中文模型替代。
#      模型路径指向上级目录的 bge-large-zh-v1.5。
BGE_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "bge-large-zh-v1.5")
_embedding_model = SentenceTransformer(BGE_MODEL_PATH)


class BGEEmbedding(EmbeddingFunction):
    """
    ChromaDB 自定义嵌入函数，用 BGE 中文模型做向量化。
    WHY: 必须继承 EmbeddingFunction 并实现 __call__，ChromaDB 才能调用它。
    """
    def __call__(self, input: Documents) -> Embeddings:
        return _embedding_model.encode(input, normalize_embeddings=True).tolist()

SYSTEM_PROMPT = """你是"小选"，好买电商平台的智能客服。
- 回答简洁专业，不超过3句话
- 涉及退换货/退款时必须引用平台政策
- 态度友好"""


# ══════════════════════════════════════════════════════════════
# 演示1：短期记忆 —— 多轮对话中的上下文保持
# ══════════════════════════════════════════════════════════════

def demo_short_term_memory():
    """
    演示：有记忆 vs 无记忆的多轮对话。
    WHY: 无记忆时，每轮请求的 messages 只包含当前问题——
         LLM 看到的永远是"一个新用户的第一句话"，追问全部失败。
         有记忆时，每轮都把历史 messages 原样传回去——
         LLM 能看到完整对话链，能理解指代、省略和上下文。
         代价：messages 越来越长 → token 消耗递增，需要后续做窗口管理。
    """
    print("=" * 60)
    print(" 演示1：短期记忆 —— 多轮追问")
    print("=" * 60)

    # ─── 子演示 A: 无记忆 ─────────────────────────────
    print("【A. 无记忆——每轮独立请求，不传历史】")
    questions = [
        "我想买一款降噪耳机",
        "那第二个呢？",       # 没有上下文，LLM 不知道"第二个"指什么
    ]
    for q in questions:
        # WHY: 每次都只传 system + 当前一句话 → LLM 完全不知道历史
        reply = chat([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": q},
        ])
        print(f"  用户: {q}")
        print(f"  客服: {reply}")
        print()

    # ─── 子演示 B: 有记忆 ─────────────────────────────
    print("【B. 有记忆——messages 列表逐轮累积】")
    # WHY: 第一轮：LLM 推荐了几个选项，这些选项存在于 assistant 的回复中
    first_question = "我想买一款降噪耳机，推荐3个选项"
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": first_question},
    ]
    reply1 = chat(messages)
    print(f"  用户: {first_question}")
    print(f"  客服: {reply1}")

    # WHY: 把 assistant 回复也追加到 messages，
    #      这样下一轮 LLM 能看到"我刚才推荐了什么"，从而理解"第二个"
    messages.append({"role": "assistant", "content": reply1})

    # WHY: 追问时，完整 messages 传回去 → LLM 知道自己之前推荐了3个选项
    follow_up = "你推荐的第二个是什么？说详细一点"
    messages.append({"role": "user", "content": follow_up})
    reply2 = chat(messages)
    print(f"  用户: {follow_up}")
    print(f"  客服: {reply2}")
    print()

    # ─── 追问继续 ──────────────────────────────────────
    print("【继续追问——验证上下文链条】")
    messages.append({"role": "assistant", "content": reply2})
    third_q = "它的价格和续航怎么样？"  # "它"指第二个推荐，LLM 必须从前文推断
    messages.append({"role": "user", "content": third_q})
    reply3 = chat(messages)
    print(f"  用户: {third_q}")
    print(f"  客服: {reply3}")
    print(f"  （当前 messages 共 {len(messages)} 条，token 消耗随轮次线性增长）")
    print()


# ══════════════════════════════════════════════════════════════
# 演示2：长期记忆 —— ChromaDB 跨会话信息召回
# ══════════════════════════════════════════════════════════════

# WHY: 用 ChromaDB 做长期记忆存储，核心思路是：
#      1. 每次客服对话结束后，将关键信息摘要存入 ChromaDB
#      2. 新会话开始时，用用户当前问题做语义检索，召回相关历史
#      3. 将召回的历史信息注入 system prompt → LLM 有了"前世记忆"

def init_long_term_memory():
    """
    初始化 ChromaDB，预填"历史客服记录"。
    WHY: 每条记录是一个文本块（历史交互摘要），
         检索时用语义相似度匹配，不是关键词匹配。
         嵌入模型：用本地 BGE-large-zh-v1.5（中文语义专用），
         比 ChromaDB 默认的 all-MiniLM-L6-v2（英文模型）准确得多。
    """
    client = chromadb.PersistentClient(
        path=os.path.join(os.path.dirname(__file__), "..", ".chroma_memory")
    )

    try:
        client.delete_collection("customer_memory")
    except Exception:
        pass
    # WHY: embedding_function 指定用中文 BGE 模型代替默认英文模型
    collection = client.create_collection(
        "customer_memory",
        embedding_function=BGEEmbedding(),
    )

    # WHY: 这些是模拟的"历史客服记录"——
    #      代表用户小明在过去会话中的交互摘要
    documents = [
        "用户小明在2024年5月10日投诉：购买的漫步者耳机左耳有杂音，"
        "已走换货流程，换新后用户表示满意。用户偏好：对音质敏感，"
        "预算在300元左右，偏好头戴式而非入耳式。",

        "用户小明在2024年4月咨询：想买一款适合运动的耳机，"
        "要求防水、佩戴稳固。客服推荐了骨传导运动耳机，"
        "用户最终未购买，表示价格偏高（推荐款599元）。",

        "用户小明在2024年3月首次咨询：如何领取新人优惠券，"
        "用户注册渠道为App，会员等级为普通会员，"
        "已成功领取首单9折券。",
    ]
    ids = ["session_001", "session_002", "session_003"]

    collection.add(documents=documents, ids=ids)
    return collection


def demo_long_term_memory():
    """
    演示：长期记忆的写入和召回。
    WHY: 短期记忆会话结束就消失，但客服需要"记住老客户"——
         用户小明上次投诉过耳机质量问题，这次再来咨询耳机时，
         系统自动召回那段历史并提醒客服，实现个性化服务。
    """
    print("=" * 60)
    print(" 演示2：长期记忆 —— 跨会话信息召回")
    print("=" * 60)

    collection = init_long_term_memory()

    # ─── 模拟新会话：用户又来咨询了 ──────────────────
    print("【场景：用户小明时隔一个月再次来访】")
    current_question = "我想再买一款耳机，有什么推荐吗？"

    # WHY: 用用户当前问题作为查询，在 ChromaDB 中语义检索相关历史
    #      n_results=2 控制召回条数——
    #      太少可能漏掉关键信息，太多会塞满 prompt 增加 token 消耗
    results = collection.query(query_texts=[current_question], n_results=2)

    recall_context = ""
    if results["documents"] and results["documents"][0]:
        recall_context = "【该用户的历史记录】\n" + \
            "\n".join(f"- {doc}" for doc in results["documents"][0])
        print(f"  [ChromaDB 召回了 {len(results['documents'][0])} 条相关历史]")
        for i, (doc, dist) in enumerate(zip(
            results["documents"][0], results["distances"][0]
        )):
            print(f"    #{i+1} (距离={dist:.3f}): {doc[:60]}...")
    else:
        print("  [无相关历史记录]")

    # ─── 对比：有无长期记忆的回答差异 ───────────────
    print()
    print("【无长期记忆——纯短期记忆回答】")
    reply_without = chat([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": current_question},
    ])
    print(f"  客服: {reply_without}")

    print()
    print("【有长期记忆——注入召回历史到 System Prompt】")
    # WHY: 把召回的历史信息拼入 system prompt，
    #      LLM 就能根据用户过去的偏好（预算300、偏好头戴式、曾投诉音质）
    #      给出个性化推荐，而不是泛泛推荐
    memory_system = SYSTEM_PROMPT + "\n\n" + recall_context + \
        "\n请根据该用户的历史偏好进行个性化推荐。"
    reply_with = chat([
        {"role": "system", "content": memory_system},
        {"role": "user", "content": current_question},
    ])
    print(f"  客服: {reply_with}")

    # ─── 演示：新信息写入长期记忆 ──────────────────
    print()
    print("【会话结束，将本次关键信息写入 ChromaDB】")
    new_memory = (
        f"用户小明在{(__import__('datetime').datetime.now().strftime('%Y年%m月%d日'))}"
        f"咨询耳机推荐，客服推荐了XX耳机，用户表示感兴趣。"
    )
    collection.add(documents=[new_memory], ids=[f"session_004"])
    print(f"  新记忆已写入 (当前共 {collection.count()} 条)")
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║  Agent-Playground Demo 04: 短期记忆 + 长期记忆     ║")
    print("║  短期: messages[] 列表  |  长期: ChromaDB 向量库   ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    demo_short_term_memory()
    demo_long_term_memory()

    print("=" * 60)
    print(" Demo 04 完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
