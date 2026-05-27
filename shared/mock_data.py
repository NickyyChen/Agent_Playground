"""
模拟电商数据：订单、物流、退换货政策。
WHY: 真实客服系统连接数据库/API，demo 中模拟这些数据源，
     让 Function Calling 的"查数据→返回结果"流程完整可跑。
"""
from datetime import datetime, timedelta

# ─── 订单模拟数据 ─────────────────────────────────
# WHY: 用字典而非类/ORM，保持 demo 依赖最少，一眼看清数据结构
MOCK_ORDERS = {
    "ORD20240001": {
        "order_id": "ORD20240001",
        "user_name": "小明",
        "product": "漫步者 W820NB 降噪耳机",
        "price": 299.00,
        "status": "已签收",
        "order_time": (datetime.now() - timedelta(days=8)).isoformat(),
        "delivery_time": (datetime.now() - timedelta(days=1)).isoformat(),
    },
    "ORD20240002": {
        "order_id": "ORD20240002",
        "user_name": "李总",
        "product": "Sony WH-1000XM5 旗舰降噪耳机",
        "price": 2299.00,
        "status": "已发货",
        "order_time": (datetime.now() - timedelta(days=2)).isoformat(),
        "delivery_time": None,
    },
    "ORD20240003": {
        "order_id": "ORD20240003",
        "user_name": "小红",
        "product": "iPhone 15 Pro 手机壳 - 黑色",
        "price": 49.00,
        "status": "待发货",
        "order_time": (datetime.now() - timedelta(hours=3)).isoformat(),
        "delivery_time": None,
    },
}

# ─── 物流模拟数据 ─────────────────────────────────
MOCK_LOGISTICS = {
    "SF1234567890": {
        "tracking_no": "SF1234567890",
        "carrier": "顺丰速运",
        "status": "运输中",
        "current_location": "广州分拣中心",
        "estimated_delivery": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
        "history": [
            {"time": "08:30", "desc": "快件到达广州分拣中心"},
            {"time": "06:15", "desc": "快件离开深圳集散中心"},
            {"time": "02:00", "desc": "商家已揽件"},
        ],
    },
    "YT9876543210": {
        "tracking_no": "YT9876543210",
        "carrier": "圆通速递",
        "status": "派送中",
        "current_location": "北京朝阳区网点",
        "estimated_delivery": datetime.now().strftime("%Y-%m-%d"),
        "history": [
            {"time": "09:00", "desc": "快递员【张师傅 138****5678】正在派送"},
            {"time": "07:30", "desc": "快件到达北京朝阳区网点"},
            {"time": "04:00", "desc": "快件到达北京分拨中心"},
        ],
    },
}

# ─── 退换货政策 ─────────────────────────────────
# WHY: 政策文本作为工具的"知识库"，Function Calling 查到后返回给 LLM 组织语言
RETURN_POLICY = """
好买电商退换货政策 v2024：
1. 退货：签收后7天内，商品完好、配件齐全可申请退货，运费平台承担
2. 换货：签收后15天内，质量问题进行免费换新，人为损坏不在换货范围
3. 退款：退货商品仓库签收后3个工作日内，原路退回付款账户
4. 特殊商品：耳机、内衣、食品等拆封后不支持无理由退货
5. 投诉通道：致电 400-800-8888 或 App 内"我的→客服→投诉"提交工单
"""
