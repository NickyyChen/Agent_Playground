# -*- coding: utf-8 -*-
"""
18_package_structure.py — 包结构：__init__.py 与相对导入
========================================================

【概念】
包（package）是包含 __init__.py 的目录——把相关模块组织在一起。
__init__.py 有两个作用：
  1. 标记目录为 Python 包（没有它就不能 import）
  2. 控制 from package import * 时暴露什么

相对导入 vs 绝对导入：
  绝对导入: from shared.llm_client import chat（从项目根开始）
  相对导入: from .llm_client import chat（从当前包开始，. 表示同级目录）

【在智能客服中的应用】
- shared/ 是一个包——__init__.py + llm_client.py + config.py
- agent/、workflows/ 都是包——把相关模块组织在一起
- 相对导入在包内部使用——如 from .tools import query_order

【ASCII 架构图】

  shared/                           import 方式
  ├── __init__.py          ← 标记这是包  from shared import ...
  ├── llm_client.py        ← 核心模块    from shared.llm_client import chat
  ├── mock_data.py         ← 模拟数据    from shared.mock_data import ORDERS
  └── config.py            ← 配置        from shared.config import LLM_CONFIG

  包内使用相对导入:
  在 shared/agent.py 中:
    from .llm_client import chat       ← . 表示同级目录
    from .config import LLM_CONFIG     ← . 表示 shared/ 目录
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ══════════════════════════════════════════════════════════════
# 1. __init__.py 的作用
# WHY: __init__.py 让目录变成"可导入的包"——
#      没有这个文件，Python 不能 import 这个目录。
#      可以在 __init__.py 中做"扁平导出"——
#      让用户 from shared import chat 而不是 from shared.llm_client import chat。
# ══════════════════════════════════════════════════════════════

def demo_init_py():
    print("=" * 50)
    print(" 1. __init__.py —— 包的入口")
    print("=" * 50)

    # 看一下真实项目的 shared/__init__.py
    init_path = os.path.join(os.path.dirname(__file__), "..",
                             "shared", "__init__.py")
    if os.path.exists(init_path):
        print(" shared/__init__.py 内容:")
        with open(init_path) as f:
            content = f.read()
            if content.strip():
                print(f"  {content}")
            else:
                print("  (空文件——仅标记这是包)")
    print()


# ══════════════════════════════════════════════════════════════
# 2. 绝对导入 —— 从项目根开始
# WHY: 绝对导入从 sys.path 中的某个目录开始，路径清晰不迷糊——
#      读代码的人能直接知道模块在哪里。
# ══════════════════════════════════════════════════════════════

def demo_absolute_import():
    print("=" * 50)
    print(" 2. 绝对导入 —— from project.module import X")
    print("=" * 50)

    # WHY: 绝对导入——路径从 shared 包开始，清晰明确
    from shared.llm_client import chat
    from shared.config import LLM_CONFIG
    from shared.mock_data import MOCK_ORDERS

    print(f" 已导入:")
    print(f"   chat()         来自 shared/llm_client.py")
    print(f"   LLM_CONFIG     来自 shared/config.py")
    print(f"   MOCK_ORDERS    来自 shared/mock_data.py")
    print(f"   模型: {LLM_CONFIG['model']}")
    print(f"   订单数: {len(MOCK_ORDERS)}")
    print()


# ══════════════════════════════════════════════════════════════
# 3. 相对导入 —— 从当前包开始
# WHY: 相对导入用 . 表示当前包，.. 表示上级包——
#      包内部模块互相引用时用相对导入，
#      好处是包重命名时不用改所有 import 语句。
#      . 当前目录, .. 上级目录, ... 上上级
# ══════════════════════════════════════════════════════════════

def demo_relative_import():
    print("=" * 50)
    print(" 3. 相对导入（示例说明）")
    print("=" * 50)

    print("""
  假设 shared/ 内部有一个 agent.py:

  绝对导入写法:
    from shared.llm_client import chat     ← 包名写死了
    from shared.config import LLM_CONFIG

  相对导入写法:
    from .llm_client import chat           ← . = shared/
    from .config import LLM_CONFIG
    from ..demos import some_func          ← .. = Agent-Playground/

  什么时候用哪个？
    跨包引用（demos 引用 shared）  → 绝对导入: from shared.xxx import yyy
    包内引用（shared 内部互相引用） → 相对导入: from .xxx import yyy
  """)
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║  Python 基础 18: 包结构与导入                 ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    demo_init_py()
    demo_absolute_import()
    demo_relative_import()


if __name__ == "__main__":
    main()
