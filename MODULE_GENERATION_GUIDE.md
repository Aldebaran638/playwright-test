# playwright信息获取模块系统规范

这份文档用于约束后续这类任务的生成方式：

使用playwright获取信息,构建围绕playwright形成的项目

## 1. 固定目录

- 工作目录默认定位在 `projects`
- 模块文件放在 `projects/modules`
- 测试文件放在 `projects/tests`
- 虚拟环境统一使用项目根目录的 `venv`

推荐结构：

```text
playwright/
├─ projects/
│  ├─ modules/
│  │  └─ xxx_module.py
│  └─ tests/
│     └─ test_xxx_module.py
└─ venv/
```

## 2. 模块代码怎么写

- 模块要围绕"一个明确能力"来写，不要把多个不相关能力堆进同一个文件
- 优先提供清晰、直接的函数入口，方便被别的脚本调用
- 函数名和文件名要表达用途，不要使用模糊命名
- 实现时优先保证可读性、稳定性和后续复用性
- 如果有筛选逻辑、默认值、后备策略，要写清楚
- 必要时可以拆出私有辅助函数，但对外暴露的入口要尽量少

建议：

- 一个模块至少有一个明确的主函数
- 主函数返回值要稳定，便于测试断言
- 如果模块需要日志，使用 `loguru`

## 3. 测试文件怎么写

- 每个模块都要有对应测试文件
- 测试文件命名使用 `test_模块名.py`
- 测试要能支持直接运行，例如：

```powershell
& C:\Users\winkey\Desktop\网站研究\playwright\venv\Scripts\python.exe C:\Users\winkey\Desktop\网站研究\playwright\projects\tests\test_xxx_module.py
```

- 测试文件要考虑导入路径问题，保证直接执行测试脚本时也能找到 `projects/modules`
- 测试至少覆盖：
  - 主函数能正常调用
  - 返回值格式或核心行为符合预期
  - 如有"轮换、重试、去重、过滤"等逻辑，要至少验证一次

## 4. 模块注释怎么写

- 注释尽量简短，只标关键行
- 注释优先使用中文
- 不要把每一行都注释一遍
- 重点注释这些地方：
  - 为什么要这样导入
  - 被测试函数是怎么调用的
  - 关键断言在验证什么
  - 为什么这样配置日志或测试入口

合格注释示例：

- `# 导入被测试函数，下面会直接调用它获取随机 UA。`
- `# 连续调用被测试函数，确认它会返回不同的 UA。`

## 5. main文件注释怎么写

- 每一个循环和 `if` 块都要加注释，说明这个分支在处理什么情况
- 代码正文以模块调用为单位，用一句话简短说明当前在做什么
- 全局变量必须标注含义

## 6. 日志怎么写

- 模块和测试都可以打日志，但要区分清楚
- 统一使用 `loguru`
- 日志输出优先使用 `stdout`，避免和 `unittest` 默认输出流混在一起
- 日志文案要尽量能和代码步骤对应

推荐风格：

- 模块日志使用前缀：`[模块名]`
- 测试日志使用前缀：`[测试1]`、`[测试2]`
- `run_step` 日志使用前缀：`[run_step]`

推荐写法：

- `[模块] 已加载可信桌面 UA 数量: 1862`
- `[模块] 本次选中 UA -> 浏览器: Chrome, 版本: 135.0.0.0, 系统: Windows`
- `[测试1] 开始调用 get_rotating_user_agent()`
- `[测试1] 函数返回的 UA: ...`
- `[run_step] 步骤"点击加载更多" 第1次重试...`
- `[run_step] 步骤"点击加载更多" 失败，已跳过。错误: TimeoutError`
- `[run_step] 步骤"打开浏览器" 失败，流程中止。错误: ...`

## 7. run_step 步骤执行规范

### 7.1 设计目标

- 每一步的失败不影响其他步骤执行（除非该步骤被标记为关键步骤）
- 代码逻辑分层清晰：主脚本 → 大模块 → 小模块 → playwright元步骤
- 每一层都通过 `run_step` 调用下一层，统一处理重试、异常和日志

### 7.2 函数签名

```python
def run_step(fn, *args, step_name="", critical=False, retries=0, **kwargs) -> StepResult:
    ...
```

参数说明：

| 参数 | 类型 | 说明 |
|------|------|------|
| `fn` | callable | 要执行的函数 |
| `*args` | any | 传给 fn 的位置参数 |
| `step_name` | str | 步骤名称，用于日志，建议每次都填 |
| `critical` | bool | True = 失败后中止整个流程；False = 失败后跳过继续执行 |
| `retries` | int | 失败后最多重试几次，默认0次（不重试） |
| `**kwargs` | any | 传给 fn 的关键字参数 |

### 7.3 返回值

统一返回 `StepResult`：

```python
@dataclass
class StepResult:
    ok: bool            # 是否成功
    value: Any          # 成功时的返回数据
    error: Exception    # 失败时的异常，成功时为 None
```

### 7.4 两种执行策略

**策略一：可跳过步骤（`critical=False`）**

- 适用场景：某个板块内容获取失败（如遇到VIP墙），不影响其他板块继续抓取
- 行为：重试 `retries` 次后仍失败，记录日志，返回 `StepResult(ok=False, ...)`
- 上层拿到返回值后自行决定是否 `continue` 或跳过后续依赖步骤

```python
result = run_step(获取板块内容, page, step_name="获取热榜板块", retries=2)
if not result.ok:
    continue  # 跳过这个板块，抓下一个
```

**策略二：关键步骤（`critical=True`）**

- 适用场景：打开浏览器、登录等后续所有步骤都依赖的操作
- 行为：重试 `retries` 次后仍失败，记录日志，向上抛出异常，整个流程中止

```python
result = run_step(打开浏览器, step_name="启动浏览器", critical=True, retries=3)
# 失败会直接抛出，不需要判断 result.ok
```

### 7.5 步骤内部处理验证码等阻塞情况

验证码、人工确认弹窗等情况，由步骤函数内部自行阻塞等待，不向 `run_step` 暴露。
对 `run_step` 而言，该步骤最终要么成功返回，要么超时失败，外部感知不到中间发生了什么。

### 7.6 参考实现

```python
import time
from dataclasses import dataclass
from typing import Any, Callable
from loguru import logger

@dataclass
class StepResult:
    ok: bool
    value: Any
    error: Exception = None

def run_step(
    fn: Callable,
    *args,
    step_name: str = "",
    critical: bool = False,
    retries: int = 0,
    **kwargs
) -> StepResult:
    name = step_name or fn.__name__
    last_error = None

    # 最多执行 retries+1 次
    for attempt in range(retries + 1):
        if attempt > 0:
            logger.info(f"[run_step] 步骤\"{name}\" 第{attempt}次重试...")
        try:
            value = fn(*args, **kwargs)
            return StepResult(ok=True, value=value)
        except Exception as e:
            last_error = e

    # 所有重试耗尽
    if critical:
        logger.error(f"[run_step] 步骤\"{name}\" 失败，流程中止。错误: {last_error}")
        raise last_error
    else:
        logger.warning(f"[run_step] 步骤\"{name}\" 失败，已跳过。错误: {last_error}")
        return StepResult(ok=False, value=None, error=last_error)
```

### 7.7 检查清单（涉及 run_step 的模块）

- `run_step` 模块文件放在 `projects/modules/run_step.py`
- 每个步骤调用都填写了 `step_name`
- 关键步骤明确标注了 `critical=True`
- 上层对 `result.ok == False` 的情况有明确处理（跳过/continue/记录）
- 有对应测试文件 `test_run_step.py`，覆盖：成功路径、重试成功、重试失败跳过、critical失败抛出

## 8. AI 交付前必须做的事

- 必须先在项目根目录的 `venv` 里实际运行测试
- 测试跑通后才能告诉用户"已经完成"
- 如果测试没跑通，不能直接交付，要先继续修
- 如果遇到环境问题，要先复核，不要直接下"环境损坏"的结论

推荐执行方式：

```powershell
& \venv\Scripts\python.exe C:\Users\winkey\Desktop\网站研究\playwright\projects\tests\test_xxx_module.py
```

## 9. AI 最终交付格式

每次完成后，默认要向用户说明：

- 模块文件放在哪里
- 测试文件放在哪里
- 主函数如何调用
- 用项目根目录 `venv` 做了什么测试
- 测试结果是否通过
- 如果做了额外修正，要简短说明修了什么

## 10. 最终检查清单

交付前至少自查以下内容：

- 模块文件已创建在 `projects/modules`
- 测试文件已创建在 `projects/tests`
- 使用了 `loguru`
- 测试支持直接运行
- 注释为中文且只标关键行
- 日志能和代码步骤对应
- 已使用项目根目录 `venv` 实际测试
- 测试已经通过