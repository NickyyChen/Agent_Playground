# -*- coding: utf-8 -*-
"""
17_import_system.py — 模块导入：import、from、sys.path、__name__
==============================================================

【概念】
Python 的模块系统决定了"代码在哪里、怎么找到它"：
  import module        → 导入整个模块
  from module import X → 从模块中导入特定内容
  sys.path             → Python 搜索模块的路径列表
  __name__             → 当前模块的名字（直接运行时是 "__main__"）

【在智能客服中的应用】
- sys.path.insert(0, "..") —— 所有 demo 文件共享的导入模式
- from shared.llm_client import chat —— 复用公共模块
- if __name__ == "__main__" —— 让 .py 文件既能直接运行又能被导入

【ASCII 架构图】

  Agent-Playground/
  ├── shared/
  │   ├── llm_client.py      ← chat(), create_completion()
  │   ├── mock_data.py       ← MOCK_ORDERS, RETURN_POLICY
  │   └── config.py
  └── demos/
      └── 01_llm_basic.py    ← 需要 import shared 下的模块
            │
            │ sys.path.insert(0, "..")   让 Python 能找到 shared/
            │ from shared.llm_client import chat
            ▼
        跨目录导入成功
"""

import sys
import os


# ══════════════════════════════════════════════════════════════
# 1. import vs from ... import
# WHY: import X 导入整个模块，需用 X.func() 调用——
#      好处是明确知道函数来自哪个模块，避免命名冲突。
#      from X import func 直接导入函数，func() 直接用——
#      简洁但可能和本地变量冲突。
# ══════════════════════════════════════════════════════════════

def demo_import_styles():
    print("=" * 50)
    print(" 1. import vs from import —— 两种导入风格")
    print("=" * 50)

    # 方式A: import 模块名 —— 用 模块.函数() 调用
    import json as json_module  # WHY: as 可以重命名，避免和变量冲突
    data_a = json_module.dumps({"status": "ok"})
    print(f" import json → json.dumps(): {data_a}")

    # 方式B: from 模块 import 函数 —— 直接用函数名调用
    from json import dumps as to_json  # WHY: as 给导入的函数重命名
    data_b = to_json({"status": "ok"})
    print(f" from json import dumps → dumps(): {data_b}")
    print()


# ══════════════════════════════════════════════════════════════
# 2. sys.path —— Python 怎么找到模块
# WHY: 当 from shared.xxx import yyy 报 ModuleNotFoundError 时，
#      根因是 sys.path 里没有 shared 的父目录。
#      sys.path.insert(0, ...) 动态添加搜索路径，是最常见的解决方案。
# ══════════════════════════════════════════════════════════════

def demo_sys_path():
    print("=" * 50)
    print(" 2. sys.path —— 模块搜索路径")
    print("=" * 50)

    print(f" sys.path 包含 {len(sys.path)} 个路径:")
    for i, p in enumerate(sys.path[:5]):  # 只展示前5个
        print(f"   [{i}] {p}")

    print(f"\n 特点:")
    print(f"   - 第一个是当前脚本所在目录")
    print(f"   - 按顺序搜索，找到即停")
    print(f"   - sys.path.insert(0, path) 插到最前面优先搜索")

    # WHY: 演示动态添加路径——添加当前目录到搜索路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
        print(f"\n 已添加: {current_dir}")
    print()


# ══════════════════════════════════════════════════════════════
# 3. __name__ == "__main__" —— 直接运行 vs 被导入
# WHY: Python 文件被直接运行时 __name__ 是 "__main__"，
#      被 import 导入时 __name__ 是模块的文件名。
#      这个判断让文件"既能直接运行 demo，又能被其他文件导入复用"。
# ══════════════════════════════════════════════════════════════

def demo_name_main():
    print("=" * 50)
    print(" 3. __name__ == '__main__' —— 双重身份")
    print("=" * 50)

    print(f" 当前 __name__: {__name__}")
    print(f" 当前 __file__: {os.path.basename(__file__)}")
    print()
    print(f" 用法说明:")
    print(f"   if __name__ == '__main__':")
    print(f"       main()   ← 只在此文件被直接运行(run)时执行")
    print(f"                 ← 被 import 时这段代码不会执行")
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║  Python 基础 17: 模块导入系统                  ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    demo_import_styles()
    demo_sys_path()
    demo_name_main()


if __name__ == "__main__":
    main()
