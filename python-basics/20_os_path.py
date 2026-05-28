# -*- coding: utf-8 -*-
"""
20_os_path.py — 文件路径操作：路径拼接、文件读写
================================================

【概念】
os.path 模块处理文件路径——拼接、判断存在、获取文件名。
open() 函数读写文件内容。

核心函数：
  os.path.join(a, b)       → 跨平台的路径拼接（自动处理 / 和 \\）
  os.path.dirname(p)       → 获取父目录
  os.path.abspath(p)       → 相对路径转绝对路径
  os.path.exists(p)        → 判断路径是否存在
  open(p, "r") / open(p, "w") → 读/写文件

【在智能客服中的应用】
- 加载配置文件: config_path = os.path.join(base, "config.json")
- 加载本地知识库文件
- 日志写入文件

【ASCII 架构图】

  os.path 的常用操作:

  "/home/user/project/data/file.txt"
       │                │    └──── os.path.basename() → "file.txt"
       │                └───────── os.path.dirname()  → "/home/user/project/data"
       │                          os.path.exists()    → True/False
       └────────────────────────── os.path.abspath(".") → 当前目录的绝对路径

  os.path.join("a", "b") → "a/b" (Linux) 或 "a\\b" (Windows)
"""

import os
import json


# ══════════════════════════════════════════════════════════════
# 1. os.path 常用操作
# WHY: 硬编码路径（"/home/user/xxx"）在不同机器上会失效——
#      os.path 函数让代码跨平台可移植。
# ══════════════════════════════════════════════════════════════

def demo_os_path():
    print("=" * 50)
    print(" 1. os.path 常用操作")
    print("=" * 50)

    # 当前文件路径
    current_file = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file)
    parent_dir = os.path.dirname(current_dir)

    print(f" __file__:           {__file__}")
    print(f" abspath(__file__):  {current_file}")
    print(f" dirname:            {current_dir}")
    print(f" 上级目录:            {parent_dir}")

    # 路径拼接
    config_path = os.path.join(parent_dir, "shared", "config.py")
    print(f"\n 拼接路径: {config_path}")
    print(f" 文件存在: {os.path.exists(config_path)}")

    # 获取文件名和扩展名
    print(f" basename: {os.path.basename(current_file)}")
    print(f" splitext: {os.path.splitext(current_file)}")
    print()


# ══════════════════════════════════════════════════════════════
# 2. 文件读写 —— 配置和数据的持久化
# WHY: Agent 需要加载配置、读取知识库、写日志——
#      open() + with 语句是最基本的文件操作模式。
#      with 保证文件用完后自动关闭。
# ══════════════════════════════════════════════════════════════

def demo_file_io():
    print("=" * 50)
    print(" 2. 文件读写 —— 配置加载")
    print("=" * 50)

    # 写入模拟配置文件
    temp_path = os.path.join(os.path.dirname(__file__), "_temp_config.json")

    config = {
        "agent_name": "小选",
        "model": "deepseek-v4-pro",
        "temperature": 0.1,
        "max_tokens": 200,
    }

    # WHY: "w" = 写入模式, encoding="utf-8" = 支持中文
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f" 写入文件: {os.path.basename(temp_path)}")

    # WHY: "r" = 读取模式
    with open(temp_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)

    print(f" 读回配置: agent={loaded['agent_name']}, "
          f"model={loaded['model']}")

    # 清理
    os.remove(temp_path)
    print(f" 清理完成: {not os.path.exists(temp_path)}")
    print()


# ══════════════════════════════════════════════════════════════
# 3. 实战：项目中的路径管理
# WHY: sys.path.insert(0, ...) 是每个 demo 的第一行代码——
#      目的是让 Python 能找到 shared/ 包。理解路径是调试导入错误的基础。
# ══════════════════════════════════════════════════════════════

def demo_real_project():
    print("=" * 50)
    print(" 3. 实战 —— 项目路径管理")
    print("=" * 50)

    # WHY: 这段代码出现在每个 demo 的开头:
    #      sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    #      拆解:
    #        __file__                           = 当前脚本的路径
    #        os.path.dirname(__file__)          = 当前脚本所在目录
    #        os.path.join(..., "..")            = 父目录（项目根目录）
    #        sys.path.insert(0, ...)            = 把根目录加到搜索路径最前面

    demo_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(demo_dir)

    print(f" 当前脚本目录:  {demo_dir}")
    print(f" 项目根目录:    {project_root}")
    print(f" shared 存在:  {os.path.exists(os.path.join(project_root, 'shared'))}")
    print()
    print(f" 所以每个 demo 第一行写:")
    print(f"   sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))")
    print(f"   就是把 {project_root} 加到 Python 搜索路径中")
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║  Python 基础 20: 文件与路径操作               ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    demo_os_path()
    demo_file_io()
    demo_real_project()


if __name__ == "__main__":
    main()
