Python 内置的 `json` 模块是处理 JSON (JavaScript Object Notation) 数据的标准工具。它的核心作用是在 Python 数据结构（主要是字典和列表）与 JSON 格式（字符串或文件）之间进行互相转换。

为了方便记忆，你可以把它的核心方法分为两组：

* **处理字符串 (带 `s`，代表 string)：** `dumps()` 和 `loads()`
* **处理文件 (不带 `s`)：** `dump()` 和 `load()`

以下是这 4 个核心方法的直接代码示例与进阶用法：

---

### 1. 字符串与 Python 对象的互转 (最常用场景)

#### `json.dumps()`: Python 字典 -> JSON 字符串

常用于准备发送给前端或 API 接口的数据。

```python
import json

data = {
    "name": "张三",
    "age": 25,
    "is_student": False,
    "skills": ["Python", "JavaScript", "Go"],
    "score": None # Python 的 None 会转换成 JSON 的 null
}

# 基础转换
json_str = json.dumps(data)
print("基础转换结果:", json_str)
# 输出 (中文可能会变成 \u 编码): {"name": "\u5f20\u4e09", "age": 25, "is_student": false, "skills": ["Python", "JavaScript", "Go"], "score": null}

# 💡 进阶用法 (强烈推荐)：美化输出 & 保持中文显示
pretty_json = json.dumps(
    data, 
    ensure_ascii=False, # 关键：False 表示不将非 ASCII 字符(如中文)转义，直接输出中文
    indent=4,           # 关键：缩进 4 个空格，让数据变成多行，极具可读性
    sort_keys=True      # 可选：按键名字母顺序排序
)
print("\n美化后的结果:\n", pretty_json)

```

#### `json.loads()`: JSON 字符串 -> Python 字典

常用于解析从网络请求 (如 `requests.get().text`) 获取回来的数据。

```python
import json

# 注意：JSON 格式中的字符串必须使用双引号 ""，布尔值必须小写
api_response = '{"user_id": 101, "status": "success", "data": ["item1", "item2"]}'

# 将字符串解析为 Python 字典
parsed_data = json.loads(api_response)

print(type(parsed_data))      # 输出: <class 'dict'>
print(parsed_data["status"])  # 输出: success
print(parsed_data["data"][0]) # 输出: item1

```

---

### 2. 本地文件的读写

如果你需要直接将数据存入硬盘，或者从硬盘读取配置文件，使用不带 `s` 的方法效率更高。

#### `json.dump()`: Python 字典 -> 写入 JSON 文件

```python
import json

config = {
    "host": "127.0.0.1",
    "port": 8080,
    "debug": True
}

# 打开文件并写入 (注意加上 encoding='utf-8')
with open('config.json', 'w', encoding='utf-8') as f:
    # 直接将数据写入文件句柄 f 中
    json.dump(config, f, ensure_ascii=False, indent=4)
    
print("文件写入成功！")

```

#### `json.load()`: 读取 JSON 文件 -> Python 字典

```python
import json

# 打开刚才生成的文件读取
with open('config.json', 'r', encoding='utf-8') as f:
    # 直接从文件句柄 f 中加载数据
    loaded_config = json.load(f)

print("读取出的端口号:", loaded_config["port"]) # 输出: 8080

```

---

### 3. 常见避坑指南

1. **类型不支持错误 (`TypeError`)：** `json` 模块只能转换基本数据类型（字典、列表、字符串、数字、布尔值、None）。如果你尝试转换 Python 特有的对象（比如 `datetime` 时间对象、自定义的 `Class` 实例、`set` 集合），它会报错 `TypeError: Object of type X is not JSON serializable`。
* **解决办法：** 在转换前，先手动将这些特殊类型转成普通字符串或字典。


2. **JSON 格式错误 (`json.decoder.JSONDecodeError`)：**
当你用 `json.loads()` 解析一段不合规的字符串时（比如属性名用了单引号 `{'name': 'Bob'}`，或者结尾多了一个逗号），会引发此错误。建议在解析不可控的网络数据时，加上 `try...except` 捕获异常。

---

你平时处理的 JSON 数据主要是来自网络 API 接口，还是本地的配置文件呢？