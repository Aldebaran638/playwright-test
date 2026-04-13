# Playwright 信息获取模块生成规范

这份文档用于约束后续这类任务的生成方式：

使用 Playwright 获取信息，构建围绕 Playwright 形成的项目。

---

## 1. 固定目录

* 工作目录默认定位在 `playwright_project`
* 模块文件**必须**放在 `playwright_project/modules/<feature_group>/`
* 不同功能的模块集群**必须**放在各自独立的子目录中，**严禁**把模块文件直接平铺在 `playwright_project/modules`
* 流程脚本**必须**放在 `playwright_project/tasks`
* 测试文件**必须**放在 `playwright_project/tests/` 下，并尽量与 `playwright_project/modules/` 的功能分组结构对齐
* 虚拟环境统一使用 `playwright_project` 项目根目录下的 `.venv`
* 输入、输出、缓存、临时文件**必须**放在 `data` 目录下
* 目录结构不只是为了整齐，**必须直接表达代码职责**
* AI 在创建、拆分、移动、重组文件时，**必须严格遵守以下目录职责定义**
* **严禁**仅凭文件当前名字决定目录归属，**必须**根据文件实际承担的职责判断它应该放在哪里

### 1.1 各目录职责说明

#### `playwright_project/tasks/`

* 该目录下的文件**必须**是流程文件
* 流程文件**必须**用于完成某一个具体需求
* 流程文件**必须**负责：

  * 组装参数
  * 调用多个模块
  * 控制执行顺序
  * 决定这次流程的输入与输出
* 流程文件中可以有默认参数，也可以有命令行参数
* **严禁**把高复用模块能力直接堆在 `tasks/` 中反复复制
* **严禁**把应当沉淀为模块的通用能力长期留在 `tasks/` 中

#### `playwright_project/modules/`

* 该目录下的文件**必须**是模块文件
* 模块文件**必须**提供一个明确、具体、可复用的能力
* 模块文件**必须**能在多个不同流程中被重复调用
* 模块文件**必须**有固定输入和明确输出
* **严禁**把流程文件放入 `modules/`
* **严禁**在 `modules/` 下放“只是调用其他模块、本身没有新增能力”的伪模块

#### `playwright_project/modules/browser/`

* 该目录下的文件**必须**只负责浏览器、context、page 等相关能力
* 例如：

  * 构建 browser/context
  * 构建 page
  * 注入基础浏览器配置
* **严禁**在该目录中放业务获取逻辑
* **严禁**在该目录中放完整流程代码

#### `playwright_project/modules/init/`

* 该目录下的文件**必须**只负责初始化能力
* 例如：

  * 站点初始化
  * 工作空间初始化
  * 页面初始进入
  * 环境初始化
* **严禁**在该目录中混入 fetch、compare、report、persist 等职责

#### `playwright_project/modules/fetch/`

* 该目录下的文件**必须**只负责获取数据
* fetch 模块**必须**返回原始数据或基础结构化数据
* **严禁**在 fetch 模块中直接生成报告
* **严禁**在 fetch 模块中承担完整流程编排
* 如果“获取数据”和“保存数据”经常分开使用，那么它们**必须**拆成 `fetch/` 和 `persist/` 下的两个模块
* 如果多个步骤共同构成一个稳定能力，且几乎总是一起出现，才**可以**写在同一个模块中

#### `playwright_project/modules/transform/`

* 该目录下的文件**必须**只负责数据整理、清洗、转换、映射、补充、合并等能力
* **严禁**在该目录中承担数据获取职责
* **严禁**在该目录中承担报告输出职责
* **严禁**把 transform 模块写成完整流程中间站

#### `playwright_project/modules/compare/`

* 该目录下的文件**必须**只负责比较、差异识别、变化提取等能力
* **严禁**在该目录中承担 fetch、persist、task 编排职责
* compare 模块**必须**围绕“比较结果”这一能力编写

#### `playwright_project/modules/persist/`

* 该目录下的文件**必须**只负责读写、缓存、保存、加载等能力
* 例如：

  * 保存 json
  * 读取 json
  * 保存 excel
  * 读取缓存
* **严禁**在该目录中混入业务判断
* **严禁**把“获取 + 分析 + 保存”整个流程全塞进 persist 模块

#### `playwright_project/modules/report/`

* 该目录下的文件**必须**只负责报告数据构造、报告内容生成等能力
* report 模块可以生成：

  * markdown
  * html
  * 文本报告
  * 报告输入数据结构
* **严禁**在该目录中承担原始数据获取职责
* **严禁**在该目录中承担完整流程职责

#### `playwright_project/modules/common/`

* 该目录下的文件**必须**是真正跨多个功能组复用的通用能力
* 例如：

  * 通用异常
  * 通用类型
  * 通用执行器
  * 通用重试逻辑
* **严禁**把“不知道该放哪里”的文件丢进 `common/`
* **严禁**把单一业务能力伪装成通用模块放入 `common/`

#### `playwright_project/tests/`

* 测试文件**必须**与 `modules/` 的功能分组尽量对齐
* `tests/modules/<feature_group>/` **必须**主要测试对应模块能力
* `tests/tasks/` **必须**主要测试流程文件
* **严禁**让测试目录结构完全脱离模块结构

#### `playwright_project/data/`

* 该目录下**必须**只放输入、输出、缓存、临时文件
* 例如：

  * `data/input/`
  * `data/output/`
  * `data/cache/`
  * `data/tmp/`
* **严禁**把代码文件放进 `data/`
* **严禁**把配置逻辑、流程逻辑、模块逻辑塞进 `data/`

### 1.2 目录结构示例

以下结构中的所有文件名都只是示例，不代表实际项目中必须存在同名文件。

```text
playwright_project/
  tasks/                           # 流程代码：完成某一个具体需求
    run_xxx_task.py
    run_yyy_task.py

  modules/                         # 模块代码：高复用、固定输入输出、只表达能力
    browser/                       # 浏览器 / context / page 相关能力
      build_context.py
      build_page.py

    init/                          # 初始化能力
      init_site.py
      init_workspace.py

    fetch/                         # 获取数据能力
      fetch_folder_items.py
      fetch_remote_records.py

    transform/                     # 数据整理 / 清洗 / 映射 / 合并能力
      normalize_records.py
      enrich_records.py
      merge_records.py

    compare/                       # 比较 / 差异识别能力
      compare_snapshots.py
      detect_changes.py

    persist/                       # 读写 / 缓存 / 保存 / 加载能力
      save_json.py
      load_json.py
      save_excel.py

    report/                        # 报告数据构造 / 报告内容生成能力
      build_report_data.py
      build_report_markdown.py

    common/                        # 真正跨域复用的通用能力
      run_step.py
      exceptions.py
      types.py

  tests/
    modules/
      browser/
      init/
      fetch/
      transform/
      compare/
      persist/
      report/

    tasks/

  data/
    input/
    output/
    cache/
    tmp/
```

### 1.3 示例目录详细说明

以下示例用于帮助 AI 正确理解“为什么文件要放在这里”，而不是只记住目录名字。

#### 示例 1：获取数据模块

文件：

```text
playwright_project/modules/fetch/fetch_folder_items.py
```

说明：

* 该文件**必须**只负责获取某个 folder 的数据
* 它的输入可以是 folder_id、请求参数、page、headers 等
* 它的输出**必须**是原始数据或基础结构化数据
* **严禁**在这个模块中直接保存文件
* **严禁**在这个模块中直接决定后续流程
* 它属于 `fetch/`，因为它表达的是“获取数据能力”

#### 示例 2：保存数据模块

文件：

```text
playwright_project/modules/persist/save_json.py
```

说明：

* 该文件**必须**只负责把数据保存成 JSON
* 它的输入可以是数据对象和保存路径
* 它的输出可以是保存结果、保存后的路径、或明确的状态信息
* **严禁**在这个模块中发请求获取数据
* **严禁**在这个模块中承担数据比较、报告生成等职责
* 它属于 `persist/`，因为它表达的是“保存数据能力”

#### 示例 3：流程文件

文件：

```text
playwright_project/tasks/run_folder_snapshot_task.py
```

说明：

* 该文件**必须**是流程文件
* 它**必须**负责完成一个具体需求，例如：

  1. 组装 folder_id 和输出路径
  2. 调用 `fetch_folder_items`
  3. 调用 `save_json`
  4. 决定这次任务最终产物放在哪里
* 该文件之所以放在 `tasks/`，是因为它负责“完成一个完整需求”
* 即使它内部调用的都是模块，它本身仍然**不是模块**

### 1.4 错误示例（必须避免）

错误文件：

```text
playwright_project/modules/fetch/fetch_and_save_folder_items.py
```

为什么错误：

* 该文件同时承担了“获取数据”和“保存数据”两个能力
* 如果未来某个流程只想获取数据而不想保存，就无法复用该模块
* 这说明这个文件的能力边界不清晰
* 如果“获取”和“保存”在实际使用中经常分开，那么它们**必须**拆成两个模块：

  * `modules/fetch/fetch_folder_items.py`
  * `modules/persist/save_json.py`

---

## 2. 模块代码怎么写

---

### 1. 模块必须提供一个明确、可复用的能力

* 模块代码**必须围绕一个明确、具体、可复用的功能来写**
* 模块提供的能力**必须能够在多个不同流程中被重复调用**
* 模块调用后**必须返回稳定、可靠、可预期的结果**
* **严禁**把多个不相关的能力放进同一个模块文件
* **严禁**写“流程片段”冒充模块

---

### 2. 能力边界必须清晰（必须严格判断是否拆分）

* 如果两个能力**经常分开使用**，那么**必须拆成两个模块**
* 如果多个步骤**共同构成一个稳定能力**，且大多数情况下总是一起使用，**可以**放在同一个模块
* 模块拆分标准**必须基于能力是否独立**
* **严禁**以“写起来方便”为理由合并多个能力

---

### 3. 模块必须像函数一样工作

* 模块对外**必须提供清晰的函数入口**
* 函数**必须有明确输入（参数）**
* 函数**必须有明确输出（返回值）**
* 相同输入**必须返回相同结构的输出**
* 调用行为**必须可预期**

---

### 4. 模块接口必须简洁、稳定

* 模块对外暴露的函数**必须尽量少**
* 只允许暴露必要的核心能力入口
* 可以使用私有辅助函数（如 `_xxx`）
* 私有函数**必须只服务当前模块能力**
* **严禁**在模块内部构建隐藏流程链条

---

### 5. 命名必须表达能力，严禁表达流程

* 文件名和函数名**必须准确表达能力用途**

✔ 合法示例：

* `fetch_folder_items`
* `build_browser_context`
* `compare_snapshots`
* `save_json`

✘ 严禁命名：

* `step1_xxx`
* `workflow_xxx`
* `run_process`
* `do_a_then_b`

---

### 6. 必须保证可读性与可复用性

* 代码实现**必须优先保证可读性**
* 逻辑必须清晰，结构必须直观
* 模块设计时**必须假设会被多个流程复用**
* **严禁**写只服务单一流程的专用模块

---

### 7. 所有关键逻辑必须显式表达

* 如果存在：

  * 筛选逻辑
  * 默认值
  * 兜底策略
  * 失败处理逻辑
    👉 **必须明确写出**
* **严禁**隐藏关键逻辑或写成隐式行为

---

### 8. 严禁硬编码业务参数（必须执行）

* 模块文件**严禁包含任何业务相关硬编码**

* 包括但不限于：

  * ID
  * 路径
  * URL
  * 查询条件
  * 业务规则

* 模块所需参数**必须全部由流程文件传入**

* 模块**只能消费参数，不能定义业务参数**

---

### 9. 严禁依赖隐式状态

* 模块所需的所有数据和依赖**必须通过参数传入**
* **严禁**依赖以下内容：

  * 全局变量
  * 外部已修改对象
  * 默认存在的文件
  * 已提前打开的页面
  * 未显式传入的上下文

---

### 10. 严格禁止伪模块（必须执行）

* 如果一个模块文件：

  * 只是简单调用其他模块
  * 本身没有提供新的独立能力
  * 只是做拼接或转发

👉 该文件**必须删除，或移动到 tasks**

* **严禁**在 `modules` 中保留任何“伪模块”

---

### 总纲（必须遵守）

> 模块代码**必须只表达能力，绝对不能表达流程**。
> 模块**必须可复用、输入输出明确、无隐式依赖、无业务硬编码**。

---

## 3. 测试文件怎么写

- 每个模块都要有对应测试文件
- 测试文件命名使用 `test_模块名.py`
- 测试文件要放进对应功能分组目录，而不是全部平铺在 `projects/tests`
- 测试目录命名应尽量和 `projects/modules/<feature_group>/` 保持一致
- 测试要能支持直接运行，例如：

```powershell
& C:\Users\winkey\Desktop\网站研究\playwright\venv\Scripts\python.exe C:\Users\winkey\Desktop\网站研究\playwright\projects\tests\xxx_feature_group\test_xxx_module.py
```

- 测试文件要考虑导入路径问题，保证直接执行测试脚本时也能找到 `projects/modules`
- 测试至少覆盖：
  - 主函数能正常调用
  - 返回值格式或核心行为符合预期
  - 如果有转换、重试、去重、过滤等逻辑，要至少验证一次

## 4. 模块注释怎么写

- 注释尽量简短，只标关键点
- 注释必须使用中文
- 不要把每一行都注释一遍
- 重点注释这些地方：
  - 为什么要这样导入
  - 被测试函数是怎么调用的
  - 关键断言在验证什么
  - 为什么这样配置日志或测试入口
- 对于每个模块的主导出函数，需要在其上方给出注释：
  - 简介：一句话说明这个函数是做什么的
  - 参数：列出所有参数及其含义
  - 返回值：列出返回值及其含义
  - 逻辑：简要介绍函数逻辑

合格注释示例：

- `# 导入被测试函数，下面会直接调用它获取随机 UA`
- `# 连续调用被测试函数，确认它会返回不同的 UA`

## 5. 流程文件注释怎么写

- 每一个循环和 `if` 块都要加注释，说明这个分支在处理什么情况
- 代码正文以模块调用为单位，用一句话简短说明当前在做什么
- 全局变量必须标注意义

## 6. 日志怎么写

- 模块和测试都可以打日志，但要区分清楚
- 统一使用 `loguru`
- 日志输出优先使用 `stdout`，避免和 `unittest` 默认输出混在一起
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
- `[run_step] 步骤"点击加载更多" 第2次重试...`
- `[run_step] 步骤"点击加载更多" 失败，已跳过。错误: TimeoutError`
- `[run_step] 步骤"打开浏览器" 失败，流程中止。错误: ...`

## 7. run_step 步骤执行规范

### 7.1 设计目标

- 每一步的失败不影响其他步骤执行，除非该步骤被标记为关键步骤
- 代码逻辑分层清晰：流程文件 -> 小模块 -> Playwright 原子步骤
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
| `*args` | any | 传给 `fn` 的位置参数 |
| `step_name` | str | 步骤名称，用于日志，建议每次都填 |
| `critical` | bool | `True` 表示失败后中止整个流程；`False` 表示失败后跳过继续执行 |
| `retries` | int | 失败后最多重试几次，默认 0 次 |
| `**kwargs` | any | 传给 `fn` 的关键字参数 |

### 7.3 返回值

统一返回 `StepResult`：

```python
@dataclass
class StepResult:
    ok: bool
    value: Any
    error: Exception = None
```

### 7.4 两种执行策略

**策略一：可跳过步骤（`critical=False`）**

- 适用场景：某个板块内容获取失败，但不影响其他板块继续抓取
- 行为：重试 `retries` 次后仍失败，记录日志，返回 `StepResult(ok=False, ...)`
- 上层拿到返回值后自行决定是否 `continue`

```python
result = run_step(fetch_block, page, step_name="获取热点板块", retries=2)
if not result.ok:
    continue
```

**策略二：关键步骤（`critical=True`）**

- 适用场景：打开浏览器、登录等后续所有步骤都依赖的操作
- 行为：重试 `retries` 次后仍失败，记录日志并向上抛异常，整体流程中止

```python
result = run_step(open_browser, step_name="启动浏览器", critical=True, retries=3)
```

### 7.5 步骤内部处理验证码等阻塞情况

验证码、人工确认弹窗等情况，由步骤函数内部自行阻塞等待，不向 `run_step` 暴露。对 `run_step` 而言，该步骤最终要么成功返回，要么超时失败，外部不感知中间细节。

### 7.6 参考实现

```python
from dataclasses import dataclass
from typing import Any, Callable
from loguru import logger

@dataclass
class StepResult:
    ok: bool
    value: Any
    error: Exception = None

def run_step(fn: Callable, *args, step_name: str = "", critical: bool = False, retries: int = 0, **kwargs) -> StepResult:
    name = step_name or fn.__name__
    last_error = None

    for attempt in range(retries + 1):
        if attempt > 0:
            logger.info(f"[run_step] 步骤\"{name}\" 第{attempt}次重试...")
        try:
            value = fn(*args, **kwargs)
            return StepResult(ok=True, value=value)
        except Exception as exc:
            last_error = exc

    if critical:
        logger.error(f"[run_step] 步骤\"{name}\" 失败，流程中止。错误: {last_error}")
        raise last_error

    logger.warning(f"[run_step] 步骤\"{name}\" 失败，已跳过。错误: {last_error}")
    return StepResult(ok=False, value=None, error=last_error)
```

### 7.7 检查清单

- `run_step` 模块文件放在 `projects/modules/common/run_step.py`
- 每个步骤调用都填写了 `step_name`
- 关键步骤明确标注了 `critical=True`
- 上层对 `result.ok == False` 的情况有明确处理
- 有对应测试文件 `projects/tests/common/test_run_step.py`

## 8. AI 交付前必须做的事

- 必须先在项目根目录的 `.venv` 或 `venv` 里实际运行测试
- 测试跑通后才能告诉用户“已经完成”
- 如果测试没跑通，不能直接交付，要先继续修
- 如果遇到环境问题，要先复核，不要直接下“环境损坏”的结论

推荐执行方式：

```powershell
& C:\Users\winkey\Desktop\网站研究\playwright\venv\Scripts\python.exe C:\Users\winkey\Desktop\网站研究\playwright\projects\tests\xxx_feature_group\test_xxx_module.py
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

- 模块文件已创建在 `projects/modules/<feature_group>/`
- 流程脚本已创建在 `projects/tasks`
- 测试文件已创建在 `projects/tests/<feature_group>/`
- 模块文件没有硬编码业务参数
- 模块参数全部由流程文件传入
- 流程文件中的参数来源是命令行参数或流程文件默认值
- 使用了 `loguru`
- 测试支持直接运行
- 注释为中文且只标关键点
- 主导出函数有清晰的注释说明
- 日志能和代码步骤对应
- 已使用项目根目录 `venv` 实际测试
- 测试已经通过

