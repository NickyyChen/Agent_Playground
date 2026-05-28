# -*- coding: utf-8 -*-
"""
26_database.py — FastAPI 数据库集成
======================================

【概念】FastAPI 数据库集成
FastAPI 不限制数据库选择——可以用任何 ORM 或原生驱动。
常见搭配：
  - SQLAlchemy (ORM) + SQLite/PostgreSQL/MySQL
  - SQLModel (SQLAlchemy + Pydantic 的结合体)
  - Tortoise ORM (异步 ORM)
  - Peewee (轻量 ORM)
  - MongoDB (motor/beanie)
  - Redis (redis-py)

本篇使用 SQLAlchemy + SQLite 展示最经典的 FastAPI 数据库集成模式。

【在智能客服中解决什么问题】
智能客服系统需要持久化存储：
  - 订单数据（用户下单）
  - 工单数据（退款/投诉工单）
  - 用户数据（顾客和客服）
  - 对话记录（聊天历史）

【核心流程】

  请求进来
      │
      ▼
  ┌──────────────────────────────────┐
  │  Depends(get_db)                 │
  │  ┌──────────────────────────┐    │
  │  │ 创建数据库会话            │    │
  │  │ 注入到路由函数            │    │
  │  └──────────────────────────┘    │
  └──────────────────────────────────┘
      │
      ▼
  路由函数使用 db 参数查询/写入
      │
      ▼
  ┌──────────────────────────────────┐
  │  请求结束                         │
  │  ┌──────────────────────────┐    │
  │  │ 关闭数据库会话            │    │
  │  └──────────────────────────┘    │
  └──────────────────────────────────┘

数据库连接管理：
  ┌──────────────────────────────────────────────┐
  │  SessionLocal (会话工厂)                      │
  │  ┌────────┐  ┌────────┐  ┌────────┐         │
  │  │请求1会话│  │请求2会话│  │请求3会话│  ...    │
  │  └────────┘  └────────┘  └────────┘         │
  │     独立会话    独立会话    独立会话             │
  └──────────────────────────────────────────────┘
  ★ 每个请求有独立的数据库会话，互不干扰

【测试案例】
  # 启动服务器（自动创建 SQLite 数据库并插入示例数据）
  python fastapi-basics/26_database.py
  # → 首次运行自动插入 3 条订单 + 1 条工单到 haomai_customer_service.db

  # ── 查询 ──
  # 订单列表（分页 + 状态筛选）
  curl "http://localhost:8000/orders?status=已签收&skip=0&limit=10"
  # → 返回已签收订单列表

  # 订单详情
  curl http://localhost:8000/order/ORD-20240115-0001
  # → {"order_id":"ORD-20240115-0001","product_name":"漫步者 W820NB","price":299.0,...}

  # 不存在的订单 → 404
  curl http://localhost:8000/order/NOTEXIST
  # → 404

  # ── 创建 ──
  # 创建订单 → 201 Created
  curl -X POST http://localhost:8000/order \
    -H "Content-Type: application/json" \
    -d '{"product_name":"数据线","price":19.9,"customer_name":"张伟"}'
  # → {"order_id":"ORD-20260528-0004","product_name":"数据线","price":19.9,...}

  # 创建售后工单 → 201 Created
  curl -X POST http://localhost:8000/ticket \
    -H "Content-Type: application/json" \
    -d '{"order_id":"ORD-20240115-0001","customer_name":"张伟","reason":"蓝牙耳机有杂音，需要退货退款"}'
  # → {"ticket_id":"TKT-20260528-0002",...}

  # 工单关联不存在的订单 → 404
  curl -X POST http://localhost:8000/ticket \
    -H "Content-Type: application/json" \
    -d '{"order_id":"NOTEXIST","customer_name":"张伟","reason":"测试工单"}'
  # → 404（订单不存在，无法创建工单）

  # ── 更新 ──
  # 分配工单给客服
  curl -X PUT "http://localhost:8000/ticket/TKT-20240120-0001/assign?agent_name=张经理"
  # → {"ticket_id":"TKT-20240120-0001","assigned_to":"张经理","status":"处理中"}

  # ── 工单筛选 ──
  # 按状态筛选
  curl "http://localhost:8000/tickets?status=处理中"
  # → 返回处理中的工单

  # 按处理人筛选
  curl "http://localhost:8000/tickets?assigned_to=张经理"
  # → 返回张经理的工单

  # ── 统计 ──
  curl http://localhost:8000/stats
  # → {"total_orders":4,"total_tickets":2,"pending_tickets":2,...}

  # 数据库文件位置: ./haomai_customer_service.db
  # 可用 sqlite3 haomai_customer_service.db ".tables" 查看表结构

【pip install】
pip install fastapi uvicorn sqlalchemy
"""

import uvicorn
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    Enum as SAEnum,
)
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase
import enum
from datetime import datetime, timedelta

# ══════════════════════════════════════════════════════════════
# 1. 数据库配置
# ══════════════════════════════════════════════════════════════

# WHY: SQLite 文件数据库——零配置，适合学习和开发
#      PostgreSQL/MySQL 只需改连接字符串：postgresql://user:pass@host/db
DATABASE_URL = "sqlite:///./haomai_customer_service.db"

# WHY: create_engine 创建数据库引擎——连接池、方言翻译都由它管理
#      connect_args={"check_same_thread": False} 是 SQLite 特有的，
#      因为 SQLite 不支持多线程——FastAPI 的异步特性需要这个参数
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite only
    echo=False,  # WHY: echo=True 会打印所有 SQL 语句——开发调试时打开
)

# WHY: sessionmaker 是会话工厂——每个请求从这里获取独立会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ══════════════════════════════════════════════════════════════
# 2. 定义 ORM 模型（数据库表结构）
# ══════════════════════════════════════════════════════════════

# WHY: DeclarativeBase 是所有 ORM 模型的基类——
#      继承它，SQLAlchemy 自动把类属性映射为表字段
class Base(DeclarativeBase):
    pass


class OrderStatus(str, enum.Enum):
    """订单状态枚举。"""
    PENDING = "待付款"
    PAID = "已付款"
    SHIPPED = "已发货"
    DELIVERED = "已签收"
    REFUNDING = "退款中"


class TicketStatus(str, enum.Enum):
    """工单状态枚举。"""
    OPEN = "待分配"
    PROCESSING = "处理中"
    WAITING = "等待顾客回复"
    RESOLVED = "已完成"
    CLOSED = "已关闭"


class CustomerOrder(Base):
    """
    订单表。
    WHY: __tablename__ 显式命名表名——避免 SQLAlchemy 自动生成的奇怪命名。
    """
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(30), unique=True, nullable=False, index=True, comment="订单号")
    product_name = Column(String(100), nullable=False, comment="商品名称")
    price = Column(Float, nullable=False, comment="价格")
    customer_name = Column(String(50), nullable=False, comment="顾客姓名")
    status = Column(SAEnum(OrderStatus), default=OrderStatus.PENDING, comment="订单状态")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")


class SupportTicket(Base):
    """
    售后工单表。
    WHY: 工单关联订单——通过 order_id 字段建立逻辑外键。
    """
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(String(30), unique=True, nullable=False, index=True, comment="工单号")
    order_id = Column(String(30), nullable=False, comment="关联订单号")
    customer_name = Column(String(50), nullable=False, comment="顾客姓名")
    reason = Column(Text, nullable=False, comment="投诉/退款原因")
    status = Column(SAEnum(TicketStatus), default=TicketStatus.OPEN, comment="工单状态")
    assigned_to = Column(String(50), nullable=True, comment="处理客服")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    resolved_at = Column(DateTime, nullable=True, comment="解决时间")


# WHY: 创建所有表——实际项目用 Alembic 做数据库迁移
Base.metadata.create_all(bind=engine)


# ══════════════════════════════════════════════════════════════
# 3. 数据库会话依赖
# ══════════════════════════════════════════════════════════════

def get_db():
    """
    获取数据库会话。
    WHY: 每个请求获取独立会话——操作完后自动关闭，避免连接泄漏。
         yield 确保 finally 块一定执行。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════
# 4. Pydantic 模型（API 的请求/响应）
# ══════════════════════════════════════════════════════════════

class OrderCreate(BaseModel):
    """创建订单的请求体。"""
    product_name: str = Field(..., min_length=1)
    price: float = Field(..., gt=0)
    customer_name: str = Field(..., min_length=1)


class OrderResponse(BaseModel):
    """订单的响应模型。"""
    order_id: str
    product_name: str
    price: float
    customer_name: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True  # WHY: 让 Pydantic 可以读取 SQLAlchemy ORM 对象


class TicketCreate(BaseModel):
    """创建工单的请求体。"""
    order_id: str = Field(..., min_length=5)
    customer_name: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=5)


class TicketResponse(BaseModel):
    """工单的响应模型。"""
    ticket_id: str
    order_id: str
    customer_name: str
    reason: str
    status: str
    assigned_to: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════
# 5. 生命周期——初始化示例数据
# ══════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时插入示例数据。"""
    db = SessionLocal()
    try:
        # 只在表为空时插入
        if db.query(CustomerOrder).count() == 0:
            db.add_all([
                CustomerOrder(
                    order_id="ORD-20240115-0001",
                    product_name="漫步者 W820NB",
                    price=299.0,
                    customer_name="张伟",
                    status=OrderStatus.DELIVERED,
                ),
                CustomerOrder(
                    order_id="ORD-20240116-0002",
                    product_name="iPhone 15 手机壳",
                    price=29.9,
                    customer_name="王小明",
                    status=OrderStatus.SHIPPED,
                ),
                CustomerOrder(
                    order_id="ORD-20240118-0003",
                    product_name="小米 Buds 4 Pro",
                    price=399.0,
                    customer_name="李小红",
                    status=OrderStatus.PAID,
                ),
            ])
            db.commit()
            print("✅ 示例订单数据已插入")

        if db.query(SupportTicket).count() == 0:
            db.add_all([
                SupportTicket(
                    ticket_id="TKT-20240120-0001",
                    order_id="ORD-20240115-0001",
                    customer_name="张伟",
                    reason="蓝牙耳机有杂音，需要退货",
                    status=TicketStatus.PROCESSING,
                    assigned_to="李小美",
                ),
            ])
            db.commit()
            print("✅ 示例工单数据已插入")
    finally:
        db.close()
    yield


app = FastAPI(title="好买电商客服 API - 数据库集成", lifespan=lifespan)


# ══════════════════════════════════════════════════════════════
# 6. 路由——CRUD 操作
# ══════════════════════════════════════════════════════════════

@app.get("/orders", response_model=List[OrderResponse])
def list_orders(
    status: Optional[OrderStatus] = Query(None, description="按状态筛选"),
    skip: int = Query(0, ge=0, description="跳过条数"),
    limit: int = Query(20, ge=1, le=100, description="返回条数"),
    db: Session = Depends(get_db),
):
    """
    查询订单列表（分页 + 状态筛选）。
    WHY: db.query(Model) 开始查询 → filter() 加条件 → offset/limit 分页。
    """
    query = db.query(CustomerOrder)
    if status:
        # WHY: 按枚举筛选——ORM 自动转换 Python 枚举到数据库值
        query = query.filter(CustomerOrder.status == status)
    orders = query.offset(skip).limit(limit).all()
    return orders


@app.get("/order/{order_id}", response_model=OrderResponse)
def get_order(order_id: str, db: Session = Depends(get_db)):
    """
    根据订单号查询订单详情。
    WHY: filter_by(**kwargs) 是 filter() 的简化版——按关键字过滤。
    """
    order = db.query(CustomerOrder).filter_by(order_id=order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"订单 {order_id} 不存在")
    return order


@app.post("/order", response_model=OrderResponse, status_code=201)
def create_order(order_data: OrderCreate, db: Session = Depends(get_db)):
    """
    创建订单——写入数据库。
    WHY: db.add() → db.commit() → db.refresh() 三步走——
         add 标记新增、commit 写入、refresh 获取数据库生成的 id/时间。
    """
    # 生成订单号
    today = datetime.now().strftime("%Y%m%d")
    count = db.query(CustomerOrder).count()
    order_id = f"ORD-{today}-{count + 1:04d}"

    db_order = CustomerOrder(
        order_id=order_id,
        product_name=order_data.product_name,
        price=order_data.price,
        customer_name=order_data.customer_name,
        status=OrderStatus.PENDING,
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)  # WHY: 从数据库重新读取——获取 id、created_at
    return db_order


@app.post("/ticket", response_model=TicketResponse, status_code=201)
def create_ticket(ticket_data: TicketCreate, db: Session = Depends(get_db)):
    """
    创建售后工单。
    WHY: 先检查关联订单是否存在——保证数据一致性。
    """
    # 检查订单是否存在
    order = db.query(CustomerOrder).filter_by(order_id=ticket_data.order_id).first()
    if not order:
        raise HTTPException(
            status_code=404,
            detail=f"订单 {ticket_data.order_id} 不存在，无法创建工单",
        )

    # 生成工单号
    today = datetime.now().strftime("%Y%m%d")
    count = db.query(SupportTicket).count()
    ticket_id = f"TKT-{today}-{count + 1:04d}"

    db_ticket = SupportTicket(
        ticket_id=ticket_id,
        order_id=ticket_data.order_id,
        customer_name=ticket_data.customer_name,
        reason=ticket_data.reason,
        status=TicketStatus.OPEN,
    )
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    return db_ticket


@app.get("/tickets", response_model=List[TicketResponse])
def list_tickets(
    status: Optional[TicketStatus] = Query(None),
    assigned_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    查询工单列表——支持按状态和处理人筛选。
    """
    query = db.query(SupportTicket)
    if status:
        query = query.filter(SupportTicket.status == status)
    if assigned_to:
        query = query.filter(SupportTicket.assigned_to == assigned_to)
    return query.all()


@app.put("/ticket/{ticket_id}/assign")
def assign_ticket(
    ticket_id: str,
    agent_name: str = Query(..., description="分配的客服姓名"),
    db: Session = Depends(get_db),
):
    """
    分配工单给客服。
    WHY: 更新操作——先查询再修改，commit 持久化。
    """
    ticket = db.query(SupportTicket).filter_by(ticket_id=ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail=f"工单 {ticket_id} 不存在")

    ticket.assigned_to = agent_name
    ticket.status = TicketStatus.PROCESSING
    db.commit()
    db.refresh(ticket)

    return {
        "ticket_id": ticket_id,
        "assigned_to": agent_name,
        "status": TicketStatus.PROCESSING.value,
    }


@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """
    统计数据——展示聚合查询。
    WHY: db.query(func.count(...)) → SQL 的 COUNT 聚合。
    """
    total_orders = db.query(CustomerOrder).count()
    total_tickets = db.query(SupportTicket).count()
    pending_tickets = (
        db.query(SupportTicket)
        .filter(SupportTicket.status.in_([TicketStatus.OPEN, TicketStatus.PROCESSING]))
        .count()
    )

    return {
        "total_orders": total_orders,
        "total_tickets": total_tickets,
        "pending_tickets": pending_tickets,
        "created_at": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
