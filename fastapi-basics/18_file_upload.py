# -*- coding: utf-8 -*-
"""
18_file_upload.py — FastAPI 文件上传
======================================

【概念】FastAPI 文件上传
FastAPI 提供三种方式处理上传的文件：

  类型           适用场景              原理
  ──────────────────────────────────────────────
  bytes          小文件 (<100KB)       全部读入内存
  UploadFile     大文件 (任意大小)      写入临时文件，可流式读取
  List[bytes]    多个小文件            一次上传多个
  List[UploadFile] 多个大文件          批量上传

UploadFile 的属性：
  .filename       → 原始文件名
  .content_type   → MIME 类型（如 image/png）
  .file           → 类文件对象，可 read()
  .size           → 文件大小（需先 read 或在临时文件中）

【在智能客服中解决什么问题】
  - 顾客上传商品瑕疵照片作为退款凭证
  - 客服上传处理结果截图
  - 批量导入 CSV 格式的工单数据

【核心流程】

  客户端                              FastAPI
  ──────────────────────────────────────────

  POST /ticket/create
  Content-Type: multipart/form-data   ← 关键：multipart 编码
                                          │
  ------WebKitFormBoundary                ▼
  customer_name: "张伟"          ┌────────────────────┐
  complaint: "商品有划痕"         │ Form()  ← 文本字段  │
  photo: [binary data...]        │ File()  ← 文件字段  │
  ------WebKitFormBoundary--      └────────────────────┘
                                       │
                                       ▼
                                   文件存入 uploads/ 目录

【测试案例】
  # 启动服务器
  python fastapi-basics/18_file_upload.py

  # 单文件上传（创建测试文件）
  echo "test image content" > /tmp/test_photo.png
  curl -X POST http://localhost:8000/upload/single \
    -F "file=@/tmp/test_photo.png"
  # → {"filename":"test_photo.png","content_type":"image/png","size_bytes":19,...}

  # 多文件批量上传
  echo "file1" > /tmp/f1.txt && echo "file2" > /tmp/f2.txt
  curl -X POST http://localhost:8000/upload/multiple \
    -F "files=@/tmp/f1.txt" \
    -F "files=@/tmp/f2.txt"
  # → {"total_files":2,"files":[{...},{...}]}

  # 创建工单——表单+文件混合（模拟真实售后场景）
  curl -X POST http://localhost:8000/ticket/create \
    -F "customer_name=张伟" \
    -F "order_id=ORD001" \
    -F "complaint=蓝牙耳机有杂音，需退货" \
    -F "photo=@/tmp/test_photo.png"
  # → {"ticket_id":"TKT-ORD001","customer":"张伟","attachments":[{...}]}

  # bytes 方式上传小文件
  curl -X POST http://localhost:8000/upload/bytes \
    --data-binary @/tmp/f1.txt
  # → {"size_bytes":6}

  # 图片类型校验——传非图片 → 400
  echo "not an image" > /tmp/test.txt
  curl -X POST http://localhost:8000/upload/image \
    -F "image=@/tmp/test.txt"
  # → 400（不支持的文件类型）

【pip install】
pip install fastapi uvicorn python-multipart aiofiles
"""

import os
import shutil
import uvicorn
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI(title="好买电商客服 API - 文件上传")

# WHY: 确保上传目录存在
UPLOAD_DIR = "/tmp/fastapi_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ══════════════════════════════════════════════════════════════
# 1. 单文件上传——UploadFile
# ══════════════════════════════════════════════════════════════

@app.post("/upload/single")
async def upload_single_file(
    # WHY: UploadFile 是推荐方式——支持大文件，不会撑爆内存
    #      文件写入临时位置，需要时再 read()
    file: UploadFile = File(..., description="上传的文件"),
):
    """
    上传单个文件。
    WHY: UploadFile 使用 Python 的 tempfile 存储大文件，内存友好。
    """
    # WHY: 限制文件大小——防止上传超大文件耗尽磁盘
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(status_code=413, detail="文件大小不能超过 10MB")

    # 保存到本地
    save_path = os.path.join(UPLOAD_DIR, f"{datetime.now().timestamp()}_{file.filename}")
    with open(save_path, "wb") as f:
        f.write(content)

    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": len(content),
        "saved_to": save_path,
    }


# ══════════════════════════════════════════════════════════════
# 2. 多文件上传
# ══════════════════════════════════════════════════════════════

@app.post("/upload/multiple")
async def upload_multiple_files(
    # WHY: List[UploadFile] 支持同时上传多个文件
    files: List[UploadFile] = File(..., description="多个文件（可批量上传）"),
):
    """
    批量上传文件——如顾客上传多张瑕疵照片。
    WHY: 前端用同一个字段名多次 append 文件，后端自动收集为 List。
    """
    result = []
    for file in files:
        content = await file.read()
        save_path = os.path.join(UPLOAD_DIR, file.filename or "unknown")
        with open(save_path, "wb") as f:
            f.write(content)
        result.append({
            "filename": file.filename,
            "content_type": file.content_type,
            "size_bytes": len(content),
        })

    return {
        "total_files": len(result),
        "files": result,
    }


# ══════════════════════════════════════════════════════════════
# 3. 表单 + 文件——创建工单（带截图）
# ══════════════════════════════════════════════════════════════

@app.post("/ticket/create")
async def create_ticket_with_attachment(
    customer_name: str = Form(..., description="顾客姓名"),
    order_id: str = Form(..., description="关联订单号"),
    complaint: str = Form(..., description="问题描述"),
    # WHY: Form 和 File 可以混用——同一个请求中既有文本字段又有文件
    photo: Optional[UploadFile] = File(None, description="问题截图（可选）"),
    video: Optional[UploadFile] = File(None, description="问题视频（可选）"),
):
    """
    创建售后工单——支持上传截图和视频。
    WHY: 多媒体证据是售后处理的关键——照片证明瑕疵，视频证明功能故障。
    """
    attachments = []
    for f in [photo, video]:
        if f and f.filename:
            content = await f.read()
            save_path = os.path.join(UPLOAD_DIR, f"TKT-{order_id}_{f.filename}")
            with open(save_path, "wb") as fp:
                fp.write(content)
            attachments.append({
                "filename": f.filename,
                "content_type": f.content_type,
                "size_bytes": len(content),
            })

    return {
        "ticket_id": f"TKT-{order_id}",
        "customer": customer_name,
        "complaint": complaint,
        "attachments": attachments,
    }


# ══════════════════════════════════════════════════════════════
# 4. bytes 方式上传（小文件）
# ══════════════════════════════════════════════════════════════

@app.post("/upload/bytes")
async def upload_as_bytes(
    file: bytes = File(..., description="小文件（<1MB），直接读入内存"),
):
    """
    以 bytes 方式上传文件。
    WHY: bytes 适合小文件（<1MB）——简单直接，不需要 await。
         大文件用 bytes 会导致内存飙升，应用 UploadFile。
    """
    if len(file) > 1024 * 1024:  # 1MB
        raise HTTPException(status_code=413, detail="bytes 模式仅支持 <1MB 的文件")
    return {"size_bytes": len(file)}


# ══════════════════════════════════════════════════════════════
# 5. 文件类型校验
# ══════════════════════════════════════════════════════════════

ALLOWED_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
}


@app.post("/upload/image")
async def upload_image(
    image: UploadFile = File(..., description="仅支持 JPG/PNG/GIF/WEBP"),
):
    """
    上传图片——带类型校验。
    WHY: 限制文件类型防止恶意文件上传（如 .exe, .js 等）。
    """
    if image.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {image.content_type}，仅支持 {ALLOWED_TYPES}",
        )

    content = await image.read()
    if len(content) > 5 * 1024 * 1024:  # 5MB
        raise HTTPException(status_code=413, detail="图片大小不能超过 5MB")

    save_path = os.path.join(UPLOAD_DIR, f"img_{datetime.now().timestamp()}_{image.filename}")
    with open(save_path, "wb") as f:
        f.write(content)

    return {
        "filename": image.filename,
        "content_type": image.content_type,
        "size_kb": round(len(content) / 1024, 2),
        "message": "图片上传成功",
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
