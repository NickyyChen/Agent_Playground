# Python 速查表

> 从最常用到不常用排列，覆盖内置函数、数据结构、标准库和常用第三方包。

---

## 一、内置函数（按使用频率排列）

### 1. print / len / type / range / input

```python
print("hello", 42, sep="|", end="\n")  # sep=分隔符, end=结尾符
len([1,2,3])          # 3 — 任何可迭代对象的长度
type(obj)              # <class 'xxx'>
isinstance(obj, int)   # True — 比 type() 更好，支持继承判断
range(5)              # [0,1,2,3,4]
range(2, 10, 3)       # [2,5,8] — start, stop, step
input("请输入: ")      # 永远返回 str
```

### 2. int / float / str / bool / bytes

```python
int("42")             # 42
int("ff", 16)         # 255 — 指定进制
float("3.14")         # 3.14
str(100)              # "100"
bool([])              # False — 空容器都是 False
bytes("hello", "utf-8") # b'hello'
```

### 3. enumerate —— 遍历带索引

```python
for i, v in enumerate(["a", "b", "c"], start=1):
    print(i, v)       # 1 a, 2 b, 3 c
```

### 4. zip —— 并行迭代多组数据

```python
names = ["张伟", "王芳"]
ages = [28, 32]
for name, age in zip(names, ages):
    print(f"{name}: {age}")

# 解压
pairs = [("a", 1), ("b", 2)]
letters, nums = zip(*pairs)  # ('a','b'), (1,2)

# strict=True（Python 3.10+）— 长度不同抛错
zip([1,2], [3], strict=True)  # ValueError!
```

### 5. map / filter / reduce

```python
# map — 每个元素应用函数
list(map(str.upper, ["a", "b"]))        # ["A", "B"]
list(map(lambda x: x*2, [1,2,3]))       # [2,4,6]

# filter — 筛选满足条件的元素
list(filter(None, [0, 1, False, 2]))    # [1,2] — None=过滤假值
list(filter(lambda x: x>0, [-1,0,1]))   # [1]

# reduce — 累积计算（需 from functools import reduce）
from functools import reduce
reduce(lambda a, b: a+b, [1,2,3,4])     # 10
reduce(lambda a, b: a*b, [1,2,3,4])     # 24
```

### 6. sorted / reversed

```python
sorted([3,1,2])                         # [1,2,3] — 返回新列表
sorted([3,1,2], reverse=True)           # [3,2,1]
sorted(["a", "abc"], key=len)           # ["a","abc"] — 按长度排
sorted(data, key=lambda d: d["age"])    # 按字典字段排

list(reversed([1,2,3]))                 # [3,2,1]
```

### 7. any / all

```python
any([False, True, False])   # True — 任意为真
all([True, True, False])    # False — 全部为真
all([1, "a", [1]])          # True
```

### 8. sum / min / max / abs / round / pow / divmod

```python
sum([1,2,3])                # 6
sum([1,2,3], 10)            # 16 — 带初始值
min([3,1,2])                # 1
max([3,1,2])                # 3
abs(-5)                     # 5
round(3.14159, 2)           # 3.14
pow(2, 3)                   # 8 — 等价 2**3
pow(2, 3, 5)                # 3 — 2**3 % 5（模幂）
divmod(10, 3)               # (3, 1) — 商和余数
```

### 9. open —— 文件读写

```python
# 读
with open("file.txt", "r", encoding="utf-8") as f:
    content = f.read()          # 读全部
    lines = f.readlines()       # 读全部行
    for line in f:              # 逐行读（省内存）
        print(line.strip())

# 写
with open("out.txt", "w") as f:
    f.write("hello\n")
```

### 10. ord / chr / bin / hex / oct

```python
ord("A")    # 65  — 字符→Unicode 码点
chr(65)     # "A" — Unicode→字符
bin(10)     # "0b1010"
hex(255)    # "0xff"
oct(8)      # "0o10"
```

### 11. id / hash / dir / vars

```python
id(obj)     # 对象内存地址
hash("abc") # 哈希值（可哈希对象才能做 dict key）
dir(obj)    # 列出所有属性和方法
vars(obj)   # 返回 __dict__（对象的实例属性）
```

---

## 二、数据结构操作

### list（列表）⭐⭐⭐⭐⭐

```python
# 创建
lst = [1, 2, 3]
lst = list(range(5))
lst = [x*2 for x in range(5)]          # 列表推导式 [0,2,4,6,8]
lst = [x for x in range(10) if x%2==0] # 带过滤 [0,2,4,6,8]

# 增删改
lst.append(4)           # 末尾追加
lst.extend([5,6])       # 批量追加
lst.insert(0, 99)       # 指定位置插入
lst.pop()               # 弹出末尾
lst.pop(0)              # 弹出指定位置
lst.remove(3)           # 删除第一个匹配值
lst.clear()             # 清空
del lst[0]              # 删除元素

# 查找
lst.index(3)            # 返回索引，找不到抛 ValueError
lst.count(3)            # 出现次数
3 in lst                # True/False

# 排序
lst.sort()              # 原地排序
lst.sort(reverse=True)
lst.sort(key=len)
new = sorted(lst)       # 返回新列表

# 反转
lst.reverse()           # 原地反转
new = lst[::-1]         # 切片反转（不改变原列表）

# 切片
lst[0:3]                # 索引 0,1,2
lst[:3]                 # 前3个
lst[-3:]                # 后3个
lst[::2]                # 步长2（隔一个取一个）
lst[1:5:2]              # 索引1,3
```

### dict（字典）⭐⭐⭐⭐⭐

```python
# 创建
d = {"a": 1, "b": 2}
d = dict(a=1, b=2)
d = dict(zip(["a","b"], [1,2]))
d = {k: v*2 for k, v in [("a",1), ("b",2)]}  # 字典推导式

# 访问
d["a"]                  # KeyError 如果不存在
d.get("c", "默认值")     # 安全访问，返回默认值
d.setdefault("c", 3)    # 如果key不存在则设值并返回

# 增删改
d["c"] = 3              # 添加/更新
d.update({"d":4,"e":5}) # 批量更新
del d["a"]
v = d.pop("c", None)    # 删除并返回值
item = d.popitem()      # 弹出最后一个键值对（3.7+ 保序）
d |= {"f": 6}           # Python 3.9+ 合并运算符

# 合并字典
merged = {**d1, **d2}   # Python 3.5+
merged = d1 | d2        # Python 3.9+

# 遍历
for k in d:             # 遍历key（默认）
for k in d.keys():      # 同上
for v in d.values():    # 遍历value
for k, v in d.items():  # 遍历键值对

# 视图对象（动态反映字典变化）
d.keys()    # dict_keys
d.values()  # dict_values
d.items()   # dict_items
```

### str（字符串）⭐⭐⭐⭐⭐

```python
# 格式化
f"姓名: {name}, 年龄: {age}"           # f-string（推荐）
"{} {}".format("a", "b")               # format
"姓名: %s, 年龄: %d" % ("张伟", 28)    # % 格式化

# 大小写
s.upper()               # 全大写
s.lower()               # 全小写
s.capitalize()          # 首字母大写
s.title()               # 每个单词首字母大写
s.swapcase()            # 大小写互换

# 去除空白
s.strip()               # 去头尾空白
s.lstrip()              # 去左边
s.rstrip()              # 去右边

# 查找和替换
s.find("abc")           # 返回索引，找不到 -1
s.index("abc")          # 返回索引，找不到 ValueError
s.count("a")            # 子串出现次数
s.replace("old","new")  # 全部替换
s.replace("old","new", 1) # 只替换第1次
s.startswith("prefix")
s.endswith(".py")

# 拆分和拼接
s.split()               # 按空白分隔
s.split(",")            # 按逗号分隔
s.split(",", maxsplit=1) # 最多分1次
s.rsplit(",", 1)        # 从右边分
s.splitlines()          # 按换行分隔
",".join(["a","b"])     # "a,b" — 用逗号拼接列表
"".join(iterable)       # 拼接为字符串

# 判断
s.isdigit()             # 纯数字
s.isalpha()             # 纯字母
s.isalnum()             # 字母+数字
s.isspace()             # 纯空白
s.islower() / s.isupper()
```

### tuple（元组）⭐⭐⭐

```python
t = (1, 2, 3)           # 不可变
t = 1, 2, 3             # 括号可省略
t = (1,)                # 单元素必须加逗号
a, b, c = t             # 解包
a, *rest = (1,2,3,4)    # rest = [2,3,4] 带星号解包
t.count(1)              # 计数
t.index(2)              # 索引

# namedtuple — 有名字的元组
from collections import namedtuple
Point = namedtuple("Point", ["x", "y"])
p = Point(10, 20)
p.x, p.y                # 10, 20
p._replace(x=99)        # 替换字段（返回新的）
```

### set（集合）⭐⭐⭐

```python
s = {1, 2, 3}           # 去重、无序
s = set([1,2,2,3])      # {1,2,3}
s = {x for x in range(10) if x%2==0}  # 集合推导式

# 操作
s.add(4)                # 添加
s.remove(3)             # 删除（不存在抛 KeyError）
s.discard(3)            # 安全删除（不存在不报错）
s.pop()                 # 随机弹出
3 in s                  # 成员检查（O(1)）

# 集合运算
a | b                   # 并集
a & b                   # 交集
a - b                   # 差集（a有b没有）
a ^ b                   # 对称差（仅在一边的元素）
a <= b                  # a是否是b的子集
a >= b                  # a是否是b的超集
a.isdisjoint(b)         # 无交集则True

# frozenset — 不可变集合（可哈希，可做 dict key）
fs = frozenset([1,2,3])
```

### bytes / bytearray（字节）⭐⭐

```python
b = b"hello"            # bytes — 不可变
b = "你好".encode("utf-8")
s = b.decode("utf-8")
b.hex()                 # 转十六进制字符串

ba = bytearray(b"hello") # 可变字节
ba[0] = 72              # 修改
```

---

## 三、常用语法和技巧

### 推导式

```python
# 列表推导
[x*2 for x in range(5)]                        # [0,2,4,6,8]
[x for x in range(10) if x%2==0]               # 带 if 过滤
[x if x>0 else 0 for x in [-1,0,1]]            # 带 if-else
[(x,y) for x in "ab" for y in "12"]            # 嵌套循环

# 字典推导
{k:v for k,v in [("a",1),("b",2)]}
{k: v*2 for k, v in d.items() if v > 0}

# 集合推导
{x for x in [1,2,2,3]}

# 生成器表达式（省内存）
sum(x*x for x in range(1000))                  # 不创建中间列表
```

### 解包

```python
a, b = (1, 2)
a, *b = [1, 2, 3, 4]      # a=1, b=[2,3,4]
*a, b = [1, 2, 3, 4]      # a=[1,2,3], b=4
a, *b, c = [1,2,3,4,5]    # a=1, b=[2,3,4], c=5

# 函数参数解包
def f(x, y, z): pass
f(*[1,2,3])                # 解包 list/tuple
f(**{"x":1,"y":2,"z":3})   # 解包 dict
```

### 条件表达式和运算符

```python
# 三元表达式
x = a if condition else b

# 链式比较
1 <= x <= 10                # 等价 x >= 1 and x <= 10

# is vs ==
a is None                   # 身份比较（同一对象）
a == b                      # 值比较

# None 的常见写法
x = a or b                  # a 为假值时取 b
x = a if a is not None else b
```

### 异常处理

```python
try:
    result = risky_operation()
except ValueError as e:
    print(f"值错误: {e}")
except (KeyError, IndexError):
    pass
except Exception as e:
    logger.error(str(e))
    raise                    # 重新抛出
else:
    print("无异常时执行")
finally:
    cleanup()                # 无论如何都执行
```

### 上下文管理器

```python
with open("file.txt") as f:
    content = f.read()

# 多个上下文
with open("a.txt") as f1, open("b.txt") as f2:
    pass

# 自定义上下文管理器
from contextlib import contextmanager
@contextmanager
def timer():
    import time
    start = time.time()
    yield
    print(f"耗时: {time.time()-start:.2f}s")
```

### walrus operator（海象运算符）Python 3.8+

```python
# 表达式中赋值
if (n := len(data)) > 100:
    print(f"数据量: {n}")

while (line := f.readline()):
    process(line)

# 列表推导中复用计算结果
[result for x in data if (result := expensive(x)) > threshold]
```

### match-case（模式匹配）Python 3.10+

```python
match status:
    case 200:
        print("成功")
    case 404:
        print("未找到")
    case 500:
        print("服务器错误")
    case _:
        print(f"未知状态: {status}")

# 结构匹配
match point:
    case (0, 0):
        print("原点")
    case (x, 0):
        print(f"x轴: {x}")
    case (x, y):
        print(f"坐标: {x}, {y}")
```

---

## 四、函数和类

### 函数

```python
# 参数类型
def f(a, b, c=0, *args, **kwargs):
    """a,b=必填位置参数 c=默认参数 *args=多余位置 **kwargs=多余关键字"""
    pass

# 仅限关键字参数（* 后面的参数必须用关键字传）
def f(a, *, b, c):
    pass
f(1, b=2, c=3)  # 正确
f(1, 2, 3)      # TypeError

# 仅限位置参数（/ 前面的参数只能用位置传）Python 3.8+
def f(a, b, /, c, d):
    pass
f(1, 2, c=3, d=4)  # 正确
f(a=1, b=2, c=3, d=4) # TypeError

# lambda
square = lambda x: x**2
sorted(data, key=lambda x: x["age"])

# 装饰器
@decorator
def f(): pass
# 等价于: f = decorator(f)
```

### 类

```python
class Person:
    cls_attr = "类属性"    # 所有实例共享

    def __init__(self, name, age):
        self.name = name   # 实例属性
        self._age = age    # 约定：受保护（实际仍可访问）
        self.__secret = 0  # 名称改写 _Person__secret

    def method(self):
        return f"{self.name}"

    @classmethod
    def from_dict(cls, d):
        return cls(d["name"], d["age"])

    @staticmethod
    def helper(x):
        return x * 2

    @property
    def age(self):
        return self._age

    @age.setter
    def age(self, value):
        if value < 0:
            raise ValueError
        self._age = value

# 继承
class Employee(Person):
    def __init__(self, name, age, salary):
        super().__init__(name, age)
        self.salary = salary

# 数据类（Python 3.7+）
from dataclasses import dataclass, field

@dataclass
class Order:
    product: str
    price: float
    quantity: int = 1
    tags: list = field(default_factory=list)  # 可变默认值必须用 default_factory

    @property
    def total(self):
        return self.price * self.quantity
```

---

## 五、collections 模块 ⭐⭐⭐⭐

```python
from collections import (
    defaultdict, Counter, OrderedDict, deque,
    namedtuple, ChainMap
)
```

### defaultdict — 带默认值的字典

```python
d = defaultdict(int)        # 默认 0
d = defaultdict(list)       # 默认 []
d = defaultdict(set)        # 默认 set()
d = defaultdict(lambda: "default")

d["a"] += 1                 # 无需判断 key 是否存在
```

### Counter — 计数器

```python
c = Counter("abracadabra")  # Counter({'a':5, 'b':2, 'r':2, ...})
c = Counter(["a","b","a"])
c["a"]                      # 计数
c.most_common(2)            # [("a",5), ("b",2)]
c.update("abc")             # 增加计数
c1 + c2                     # 合并
c1 - c2                     # 差（结果 >=0）
c.total()                   # Python 3.10+ 总计数
```

### deque — 双端队列（两端 O(1) 操作）

```python
dq = deque([1, 2, 3])
dq.append(4)                # 右端加
dq.appendleft(0)            # 左端加
dq.pop()                    # 右端弹出
dq.popleft()                # 左端弹出
dq.rotate(2)                # 右旋2步
dq.rotate(-1)               # 左旋1步
dq.extend([5,6])            # 右端批量加
dq.extendleft([-2,-1])      # 左端批量加
```

### OrderedDict — 有序字典

```python
# Python 3.7+ 普通 dict 已保序，但仍有用：
od = OrderedDict()
od.move_to_end("key")       # 移到末尾
od.move_to_end("key", last=False)  # 移到开头
od.popitem(last=False)      # FIFO 弹出（普通 dict 只能 LIFO）
```

### ChainMap — 多层字典合并

```python
defaults = {"color": "red", "size": "M"}
user = {"color": "blue"}
combined = ChainMap(user, defaults)
combined["color"]           # "blue" — 优先取前面的
combined["size"]            # "M" — 前面的没有则往后找
```

### namedtuple — 上面已介绍

---

## 六、itertools 模块 ⭐⭐⭐

```python
import itertools as it
```

### 无限迭代器

```python
it.count(10, 2)             # 10, 12, 14, ... 无限
it.cycle("ABC")             # A, B, C, A, B, C, ... 无限循环
it.repeat("X", 3)           # X, X, X
```

### 组合迭代器

```python
it.product("AB", [1,2])     # 笛卡尔积: (A,1),(A,2),(B,1),(B,2)
it.permutations("ABC", 2)   # 排列: AB, AC, BA, BC, CA, CB
it.combinations("ABC", 2)   # 组合: AB, AC, BC
it.combinations_with_replacement("ABC", 2) # 可重复组合
```

### 合并/拆分

```python
it.chain([1,2], [3,4])      # 1,2,3,4 — 串联多个可迭代对象
it.chain.from_iterable([[1,2],[3,4]])  # 串联嵌套列表

# zip_longest — 以最长为准，短的填默认值
it.zip_longest("AB", [1,2,3], fillvalue=None)
```

### 过滤/分组/切片

```python
# 条件筛选
it.takewhile(lambda x: x<5, [1,3,5,2,7])    # 1,3 — 满足则取，遇不满足停止
it.dropwhile(lambda x: x<5, [1,3,5,2,7])    # 5,2,7 — 跳过满足的，取之后的
it.filterfalse(lambda x: x%2, range(10))     # 0,2,4,6,8 — 过滤掉满足条件的

# 分组
it.groupby("AAABBBCC")       # 按连续相同值分组
# [(k, list(g)) for k, g in it.groupby("AAABBBCC")]
# → [('A',['A','A','A']), ('B',['B','B','B']), ('C',['C','C'])]

# 切片
it.islice(range(10), 3, 8, 2)  # 类似 [3:8:2]

# 成对迭代（Python 3.10+）
it.pairwise([1,2,3,4])         # (1,2), (2,3), (3,4)

# 累积
it.accumulate([1,2,3,4])       # 1,3,6,10 — 累加
it.accumulate([1,2,3,4], lambda a,b: a*b)  # 1,2,6,24 — 累积
```

---

## 七、functools 模块 ⭐⭐⭐

```python
from functools import lru_cache, partial, reduce, wraps, total_ordering
```

### lru_cache — 函数结果缓存

```python
@lru_cache(maxsize=128)
def expensive(n):
    return n ** n
# Python 3.9+ 可用 @cache（=@lru_cache(maxsize=None)）
```

### partial — 固定部分参数

```python
def power(base, exp):
    return base ** exp

square = partial(power, exp=2)
square(5)                   # 25
```

### wraps — 保留装饰函数元信息

```python
from functools import wraps

def log(func):
    @wraps(func)            # 保留 func 的 __name__、__doc__
    def wrapper(*args, **kwargs):
        print(f"调用 {func.__name__}")
        return func(*args, **kwargs)
    return wrapper
```

### cached_property（Python 3.8+）

```python
from functools import cached_property

class DataSet:
    @cached_property
    def variance(self):
        return expensive_calc()  # 只计算一次
```

---

## 八、datetime / time 模块 ⭐⭐⭐

```python
from datetime import datetime, date, time, timedelta, timezone
import time
```

### datetime

```python
now = datetime.now()                        # 当前本地时间
now_utc = datetime.now(timezone.utc)         # 当前 UTC 时间
dt = datetime(2024, 1, 15, 10, 30, 0)       # 指定时间

# 解析和格式化
dt = datetime.strptime("2024-01-15", "%Y-%m-%d")
s = dt.strftime("%Y-%m-%d %H:%M:%S")
s = dt.isoformat()                          # "2024-01-15T10:30:00"
dt = datetime.fromisoformat("2024-01-15T10:30:00")

# 时间戳
ts = dt.timestamp()                         # datetime → unix时间戳
dt = datetime.fromtimestamp(1705315800.0)   # 时间戳 → datetime

# 时区
from datetime import timezone, timedelta
tz_utc8 = timezone(timedelta(hours=8))
dt_bj = datetime(2024, 1, 15, tzinfo=tz_utc8)
```

### timedelta — 时间差

```python
delta = timedelta(days=1, hours=2, minutes=30)
next_week = now + timedelta(weeks=1)
diff = dt2 - dt1                # timedelta
diff.days                       # 天数
diff.total_seconds()            # 总秒数
```

### time

```python
time.time()                     # Unix 时间戳（秒）
time.sleep(2)                   # 暂停2秒
time.perf_counter()             # 高精度计时（性能测试用）
```

---

## 九、os / sys / pathlib 模块 ⭐⭐⭐

### pathlib（Python 3.4+ 推荐）⭐⭐⭐

```python
from pathlib import Path

p = Path("/home/user/data/file.txt")

# 属性
p.name          # "file.txt"
p.stem          # "file" — 无后缀
p.suffix        # ".txt"
p.parent        # Path("/home/user/data")
p.parts         # ("/", "home", "user", "data", "file.txt")

# 操作
p.exists()      # 是否存在
p.is_file()     # 是否是文件
p.is_dir()      # 是否是目录
p.stat().st_size  # 文件大小（字节）

# 读写
content = p.read_text(encoding="utf-8")
p.write_text("hello", encoding="utf-8")
data = p.read_bytes()

# 遍历
p.iterdir()                     # 遍历目录
list(p.glob("*.py"))            # 当前目录的 py 文件
list(p.rglob("**/*.py"))        # 递归搜索所有 py 文件

# 路径运算
new = p.parent / "new_file.txt"
new = p.with_suffix(".csv")     # 换后缀
new = p.with_name("other.txt")  # 换文件名

# 创建和删除
p.mkdir(parents=True, exist_ok=True)
p.unlink()                      # 删除文件
p.rmdir()                       # 删除空目录
```

### os

```python
import os
os.getcwd()                     # 当前工作目录
os.chdir("/tmp")                # 切换目录
os.path.exists(path)
os.path.join("a", "b", "c")    # "a/b/c" — 跨平台路径拼接
os.path.dirname(path)
os.path.basename(path)
os.path.splitext("a.txt")      # ("a", ".txt")
os.makedirs("a/b/c", exist_ok=True)
os.listdir(".")
os.environ["HOME"]              # 环境变量
os.environ.get("VAR", "默认值")
```

### sys

```python
import sys
sys.argv                        # 命令行参数列表
sys.exit(0)                     # 退出程序
sys.path                        # 模块搜索路径
sys.version                     # Python 版本
sys.platform                    # 平台: linux/darwin/win32
sys.stdout.write("no newline")
sys.stdin.readline()
```

---

## 十、random 模块 ⭐⭐

```python
import random

random.random()                 # [0, 1) 随机浮点数
random.uniform(1, 10)           # [1, 10] 随机浮点数
random.randint(1, 10)           # [1, 10] 随机整数（含两端）
random.randrange(0, 100, 5)    # 0,5,10,...,95 中随机选
random.choice(["a","b","c"])    # 随机选一个
random.choices(["a","b"], k=5, weights=[0.7,0.3])  # 有放回抽样
random.sample(range(100), k=5)  # 无放回抽样
random.shuffle(lst)             # 原地打乱

random.seed(42)                 # 固定随机种子（可复现）
```

---

## 十一、json / re / logging 模块 ⭐⭐

### json

```python
import json

# 序列化
json.dumps({"a": 1})                    # → 字符串
json.dumps({"a": 1}, indent=2)          # 格式化
json.dumps({"a": 1}, ensure_ascii=False) # 中文不转义
json.dumps(datetime, default=str)       # 自定义不可序列化类型的处理

# 反序列化
json.loads('{"a": 1}')

# 文件读写
with open("data.json", "w") as f:
    json.dump(obj, f, indent=2)
with open("data.json", "r") as f:
    data = json.load(f)
```

### re（正则表达式）

```python
import re

# 匹配
re.match(r"\d+", "123abc")      # 从开头匹配 → match对象
re.search(r"\d+", "abc123")     # 搜索第一个 → match对象
re.findall(r"\d+", "a1b2c3")    # ["1","2","3"]
re.finditer(r"\d+", "a1b2")     # 迭代器（省内存）

# 替换和分割
re.sub(r"\s+", " ", "a  b  c")  # "a b c"
re.sub(r"(\w+)", r"[\1]", "hi") # "[hi]" — 引用捕获组
re.split(r"\s*,\s*", "a, b, c") # ["a","b","c"]

# 编译（复用提高性能）
pattern = re.compile(r"\d+")
pattern.findall("a1b2")

# 常用模式
r"\d"       # 数字
r"\w"       # 字母数字下划线
r"\s"       # 空白
r"."        # 任意字符（除换行）
r"^"        # 开头
r"$"        # 结尾
r"*"        # 0次以上
r"+"        # 1次以上
r"?"        # 0或1次
r"{n,m}"    # n到m次
r"[abc]"    # a或b或c
r"[^abc]"   # 非a非b非c
r"(abc|def)" # abc或def
r"(.*?)"    # 非贪婪捕获
r"(?P<name>...)" # 命名捕获组
```

### logging

```python
import logging

# 基础配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("app.log")],
)

logger = logging.getLogger(__name__)
logger.debug("调试信息")
logger.info("一般信息")
logger.warning("警告")
logger.error("错误")
logger.exception("异常（自动附加堆栈）")  # 放在 except 块中
```

---

## 十二、typing 模块 ⭐⭐

```python
from typing import (
    Optional, Union, List, Dict, Tuple, Set,
    Callable, Iterator, Iterable, Sequence, Generator,
    Any, TypeVar, Literal, TypedDict, Protocol, overload,
)

# 基础类型标注
def greet(name: str, age: int = 0) -> str:
    return f"{name} is {age}"

# 复合类型
names: List[str] = []
scores: Dict[str, int] = {}
pair: Tuple[int, str] = (1, "a")
maybe: Optional[str] = None          # = Union[str, None]
id_type: Union[int, str] = "ID001"

# 函数类型
handler: Callable[[int, str], bool]  # (int, str) -> bool

# 泛型
T = TypeVar("T")
def first(items: List[T]) -> Optional[T]:
    return items[0] if items else None

# Literal（Python 3.8+）
Status = Literal["open", "closed", "pending"]

# TypedDict（Python 3.8+）
class Person(TypedDict):
    name: str
    age: int

# 类型检查时忽略
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from my_module import MyClass  # 仅类型检查时导入，避免循环引用
```

---

## 十三、并发和异步 ⭐⭐

### threading

```python
import threading

def worker(name):
    print(f"{name} 工作中")

t = threading.Thread(target=worker, args=("线程1",), daemon=True)
t.start()
t.join(timeout=5)

# 线程安全
lock = threading.Lock()
with lock:
    shared_data += 1
```

### asyncio（异步）

```python
import asyncio

# 异步函数
async def fetch(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.text()

# 运行
asyncio.run(main())

# 并发执行
results = await asyncio.gather(
    fetch(url1),
    fetch(url2),
    return_exceptions=True,  # 异常不中断其他任务
)

# 超时
try:
    result = await asyncio.wait_for(slow_task(), timeout=5.0)
except asyncio.TimeoutError:
    pass

# 创建任务（并发执行）
task = asyncio.create_task(fetch(url))
# 中途取消
task.cancel()

# 异步上下文管理器
async with aiofiles.open("file.txt") as f:
    content = await f.read()

# 异步 for
async for item in async_generator():
    pass
```

### ThreadPoolExecutor / ProcessPoolExecutor

```python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

# 线程池（I/O 密集型）
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(download, url) for url in urls]
    for future in as_completed(futures):
        result = future.result()

# 最简单的方式
results = executor.map(download, urls)

# 进程池（CPU 密集型），用法同上
with ProcessPoolExecutor() as executor:
    results = executor.map(heavy_calc, data)
```

---

## 十四、常用包速查

### pytest ⭐⭐⭐

```bash
pip install pytest pytest-cov pytest-mock
```

```python
# 文件: test_module.py
def test_add():
    assert add(1, 2) == 3

def test_raises():
    with pytest.raises(ValueError, match="invalid"):
        might_fail()

@pytest.mark.parametrize("a,b,expected", [(1,2,3), (0,0,0), (-1,1,0)])
def test_add_param(a, b, expected):
    assert add(a, b) == expected

@pytest.fixture
def db():
    conn = create_connection()
    yield conn              # 测试用这个
    conn.close()            # 测试后清理

def test_query(db):
    assert db.query("SELECT 1") == 1

@pytest.fixture
def mock_fetch(mocker):
    return mocker.patch("module.fetch_data", return_value={"ok": True})

# 常用命令
# pytest -v                   详细输出
# pytest -s                   显示 print
# pytest -k "test_add"        按名称筛选
# pytest --cov=src            覆盖率报告
# pytest -x                   首次失败即停止
```

### requests ⭐⭐⭐

```python
import requests

# GET
r = requests.get("https://api.example.com/data", params={"page": 1})
r.status_code       # 200
r.json()            # 解析 JSON
r.text              # 原始文本
r.headers           # 响应头
r.elapsed           # 响应时间

# POST
r = requests.post(url, json={"key": "value"})           # JSON body
r = requests.post(url, data={"key": "value"})           # form body
r = requests.post(url, files={"file": open("f.png","rb")})

# 高级
s = requests.Session()          # 复用连接池和 Cookie
s.headers.update({"Authorization": "Bearer token123"})
r = s.get(url, timeout=10)      # 超时设置
r.raise_for_status()            # 非 2xx 抛异常
```

### python-dotenv ⭐⭐

```python
# .env 文件
# DATABASE_URL=sqlite:///db.sqlite3
# SECRET_KEY=my-secret-key

from dotenv import load_dotenv
load_dotenv()                           # 加载 .env 到 os.environ
import os
db_url = os.getenv("DATABASE_URL")
```

### click / argparse ⭐⭐

```python
# click（推荐，更简洁）
import click

@click.command()
@click.option("--name", prompt="姓名", help="用户姓名")
@click.option("--count", default=1, help="次数")
@click.argument("output")
def cli(name, count, output):
    """命令描述"""
    for _ in range(count):
        click.echo(f"Hello {name} -> {output}")

if __name__ == "__main__":
    cli()

# 内置 argparse
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("input", help="输入文件")
parser.add_argument("-o", "--output", default="out.txt")
parser.add_argument("-v", "--verbose", action="store_true")
args = parser.parse_args()
```

### pydantic ⭐⭐

```python
from pydantic import BaseModel, Field, validator

class User(BaseModel):
    name: str = Field(..., min_length=1)
    age: int = Field(ge=0, le=150)
    email: str

    @validator("email")
    def email_must_contain_at(cls, v):
        if "@" not in v:
            raise ValueError("邮箱格式不正确")
        return v

user = User(name="张伟", age=28, email="zhang@example.com")
user.model_dump()           # → dict (v2)
user.model_dump_json()       # → JSON 字符串
```

### numpy ⭐⭐

```python
import numpy as np

a = np.array([1,2,3])
a = np.zeros((3,4))
a = np.ones((2,3))
a = np.arange(10)
a = np.linspace(0, 1, 100)  # 0到1的100个等间隔数

a.shape         # (3,)
a.dtype         # int64
a.reshape(3, 1)
a.sum() / a.mean() / a.std()
a[a > 5]        # 布尔索引

# 广播
a + np.array([[1],[2],[3]])  # (3,1) + (4,) → (3,4)
```

### pandas ⭐⭐

```python
import pandas as pd

df = pd.read_csv("data.csv")
df = pd.read_json("data.json")
df = pd.DataFrame({"name": ["张伟","王芳"], "age": [28, 32]})

df.head()
df.describe()
df["age"].mean()
df[df["age"] > 30]
df.sort_values("age", ascending=False)
df.groupby("city")["sales"].sum()
df.to_csv("out.csv", index=False)
```

---

## 十五、实用代码片段

### 一行代码合集

```python
# 列表去重（保序）
list(dict.fromkeys(lst))

# 展平列表
[x for sub in lst for x in sub]
sum(lst, [])                # 不推荐（性能差）

# 分组
from itertools import groupby
{k: list(g) for k, g in groupby(sorted(lst, key=f), key=f)}

# 统计频率
from collections import Counter
Counter(lst)

# 分批
[batch[i:i+n] for i in range(0, len(batch), n)]

# 字典翻转
{v: k for k, v in d.items()}

# 列表转字典
dict(zip(keys, values))

# 安全的字典嵌套
from collections import defaultdict
d = defaultdict(lambda: defaultdict(int))

# 带索引的遍历
for i, item in enumerate(lst, 1):  # 索引从1开始

# 同时遍历多个列表
for a, b in zip(list1, list2):

# 函数超时装饰器
import signal, functools
def timeout(seconds):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            signal.alarm(seconds)
            try:
                return func(*args, **kwargs)
            finally:
                signal.alarm(0)
        return wrapper
    return decorator

# 重试装饰器
import time, functools
def retry(max_tries=3, delay=1):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_tries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_tries - 1:
                        raise
                    time.sleep(delay)
        return wrapper
    return decorator
```

---

## 附录：频率标记说明

| 标记 | 含义 |
|------|------|
| ⭐⭐⭐⭐⭐ | 每天使用 |
| ⭐⭐⭐⭐ | 每周使用 |
| ⭐⭐⭐ | 每月使用 |
| ⭐⭐ | 需要时查询 |
| ⭐ | 知道有这个东西即可 |
