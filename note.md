```powershell
playwright codegen https://portal.mintel.com/portal/login?next=https%3A%2F%2Foauth.mintel.com%2F
```
执行以后自己操作浏览器,自动生成代码

# unittest 基础 API + with 用法总结

## 一、unittest 基础结构

```python
import unittest

class TestDemo(unittest.TestCase):

    def setUp(self):
        # 每个测试前执行
        pass

    def tearDown(self):
        # 每个测试后执行
        pass

    def test_xxx(self):
        # 测试函数（必须以 test_ 开头）
        self.assertEqual(1, 1)

if __name__ == "__main__":
    unittest.main()
````

---

## 二、常用断言 API

```python
self.assertEqual(a, b)        # a == b
self.assertNotEqual(a, b)     # a != b
self.assertTrue(x)            # x 为 True
self.assertFalse(x)           # x 为 False
self.assertIs(a, b)           # a 和 b 是同一对象
self.assertIsNone(x)          # x is None
self.assertIn(a, b)           # a in b
self.assertIsInstance(a, t)   # a 是 t 类型
self.assertRaises(E)          # 断言抛出异常
```

---

## 三、assertRaises 用法

```python
with self.assertRaises(TypeError):
    func()
```

含义：
→ 代码必须抛出指定异常，否则测试失败

等价逻辑：

```python
try:
    func()
    raise AssertionError("没有抛异常")
except TypeError:
    pass
```

---

## 四、with 原理

### 1. 基本结构

```python
with obj:
    do_something()
```

等价：

```python
obj.__enter__()
try:
    do_something()
finally:
    obj.__exit__()
```

---

### 2. 上下文管理器

必须实现：

```python
class Demo:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass
```

---

### 3. 执行流程

1. 调用 `__enter__()`
2. 执行 with 代码块
3. 调用 `__exit__()`

---

### 4. 异常处理机制

```python
def __exit__(self, exc_type, exc, tb):
    return True
```

含义：
→ 吞掉异常（不再向外抛）

---

## 五、with 的本质

```text
with = try/finally + 自动资源管理 + 可选异常处理
```

---

## 六、pass / raise 补充

```python
pass     # 什么都不做，占位
raise    # 主动抛出异常
```

```python
raise AssertionError("错误")
```

→ 强制让程序报错（测试失败）

```