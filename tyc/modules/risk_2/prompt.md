# 天眼查风险爬虫 — 完整设计文档

**本文档是喂给 AI 编码的唯一依据，所有约定均以此为准。**

---

## 一、文件结构

```
project/
├── run_step.py          ← 已有，禁止修改
├── navigate.py          ← 新建：进入公司风险详情页
├── extract.py           ← 新建：提取风险条目
└── main.py              ← 改造：生命周期 + 批量调用
```

---

## 二、全局约定（所有文件必须遵守）

| 编号 | 约定内容 |
|------|---------|
| G-1 | 所有 playwright 操作必须包在 `run_step()` 中，禁止裸调用 |
| G-2 | `navigate.py` 和 `extract.py` 内部步骤全部 `critical=True`，失败直接抛异常，由 `main.py` 外层 `run_step` 统一捕获 |
| G-3 | `reset_to_search_page` 使用 `page.goto(RISK_SEARCH_URL)`，严禁使用 `go_back()` |
| G-4 | `extract.py` 不做任何页面跳转，只读取当前页 |
| G-5 | `navigate.py` 只负责进入，不负责返回 |
| G-6 | browser / context / page 的创建和关闭只在 `main.py`，模块只接收 `page` 参数 |
| G-7 | 所有定位全部使用结构 xpath，禁止使用任何哈希 class（形如 `_fb6b9`、`_82793` 等无语义的混淆 class）定位元素 |
| G-8 | 字段名通过 `xpath=.//span[contains(text(),'：')]` 定位，字段值通过 `xpath=../span[2]` 取兄弟节点，禁止使用任何 class 定位字段行 |

---

## 三、main.py

### 3.1 常量（文件顶部）

```python
RISK_SEARCH_URL = "填入查风险搜索页的固定 URL"
# 需在运行前确认实际值
```

### 3.2 reset_to_search_page(page)

- **职责**：将 page 无条件重置回查风险搜索页
- **实现**：`goto(RISK_SEARCH_URL)`，然后等待搜索框出现（确认页面就绪）
- **注意**：此函数自身不包 `run_step`，由调用方包裹

### 3.3 批量主循环

```python
results = []
failed = []

for company in companies:

    # ── step 1: 导航 ──────────────────────────────
    nav = run_step(
        navigate_to_risk_page, page1, company,
        step_name=f"导航-{company}",
        critical=False,
        retries=1,
    )
    if not nav.ok:
        failed.append(company)
        run_step(reset_to_search_page, page1,
                 step_name="重置搜索页", critical=True)
        continue

    # ── step 2: 提取 ──────────────────────────────
    ext = run_step(
        extract_risk_data, page1, company,
        step_name=f"提取-{company}",
        critical=False,
        retries=0,
    )
    if not ext.ok:
        failed.append(company)
        run_step(reset_to_search_page, page1,
                 step_name="重置搜索页", critical=True)
        continue

    # ── step 3: 正常完成 ──────────────────────────
    results.append(ext.value)
    run_step(reset_to_search_page, page1,
             step_name="返回搜索页", critical=True)
```

> `reset_to_search_page` 在三处调用：导航失败后、提取失败后、正常完成后。三处都必须有，缺一不可。

### 3.4 生命周期（finally 块）

```python
try:
    # 1. launch browser(headless=False)
    # 2. new_context → new_page(page0)
    # 3. page0 打开天眼查首页 → 触发 popup → 得到 page1
    #    以上每步各自 run_step，critical=True
    # 4. 进入主循环
finally:
    context.close()
    browser.close()
```

---

## 四、navigate.py

### 4.1 函数签名

```python
from playwright.sync_api import Page
from run_step import run_step, StepResult

def navigate_to_risk_page(page: Page, company_name: str) -> StepResult[None]:
    """
    前置状态：page 停在「查风险」搜索页（有搜索框）
    后置状态：page 停在该公司风险详情页
    失败：异常向上抛，由外层 run_step 捕获
    """
```

### 4.2 内部步骤（全部 critical=True）

| 步骤 | retries |
|------|---------|
| 清空并填入搜索框 | 1 |
| 点击搜索按钮 | 1 |
| 等待风险详情页加载完成（等待 `#search-bar + div > div:nth-child(3)` 出现） | 2 |

> 搜索后**直接跳转**到该公司风险详情页，不存在中间结果列表，无需点击。

> **关键**：函数本身不 try/catch，所有异常透传给外层 run_step。

---

## 五、extract.py

### 5.1 函数签名

```python
from playwright.sync_api import Page
from run_step import run_step, StepResult

def extract_risk_data(page: Page, company_name: str) -> StepResult[list[dict]]:
    """
    前置状态：page 停在该公司风险详情页
    后置状态：page 仍停在该公司风险详情页（不做任何跳转）
    返回：StepResult，value 为 list[dict]，每个 dict 代表一条风险记录
    失败：异常向上抛，由外层 run_step 捕获，整个公司跳过
    """
```

### 5.2 页面结构（定位依据）

```
#search-bar                      ← 稳定 id 锚点
  + 紧邻兄弟 div
      ./div[1]                   ← 筛选区（风险类型/省份/年份），跳过
      ./div[2]                   ← 收起按钮，跳过
      ./div[3]                   ← 所有记录的容器 ✅
            ./div[1]             ← 第1条记录
            ./div[2]             ← 第2条记录
            ...
                ./div[1]         ← 头部区
                      ./div[1]   ← 标题文本（案号或自然语言标题）
                      ./div[2]   ← 风险类型标签（开庭公告、裁判文书 等）
                ./div[2]         ← 详情区
                      .//span[contains(text(),'：')]  ← 每个字段标签
                            ../span[2]               ← 对应字段值
```

### 5.3 定位规则（严格遵守）

| 目标 | 定位方式 |
|------|---------|
| 记录列表容器 | `page.locator("#search-bar + div > div:nth-child(3)")` |
| 单条记录 | `records_container.locator("xpath=./div").all()` |
| 标题文本 | `record.locator("xpath=./div[1]/div[1]").inner_text()` |
| 风险类型 | `record.locator("xpath=./div[1]/div[2]").inner_text()` |
| 字段标签列表 | `record.locator("xpath=./div[2]//span[contains(text(),'：')]").all()` |
| 对应字段值 | `label_el.locator("xpath=../span[2]").inner_text()` |

> 字段值说明：如果值 span 内含多个子 span（如多个当事人），`inner_text()` 会自动合并全部文本。

### 5.4 每条记录输出格式

```python
{
    "title":     "（2024）闽01民初931号",  # 头部 ./div[1]/div[1] 原文
    "risk_type": "开庭公告",               # 头部 ./div[1]/div[2] 原文
    "fields": {
        "原告": "陈某",
        "被告": "福建实达集团股份有限公司",
        "案由": "损害股东利益责任纠纷",
        # 有什么字段就放什么，缺的不填，不补 None
    }
}
```

> **禁止**：不要预定义字段列表然后填 `None`。有什么字段就往 dict 里放什么。

### 5.5 提取流程

```python
# step 1: 等待记录列表容器出现（critical=True, retries=2）
records_container = page.locator("#search-bar + div > div:nth-child(3)")
run_step(records_container.locator("xpath=./div[1]").wait_for,
         step_name="等待记录列表", critical=True, retries=2)

# step 2: 获取所有记录（critical=True, retries=1）
records = run_step(
    lambda: records_container.locator("xpath=./div").all(),
    step_name="获取记录列表", critical=True, retries=1
)

# step 3: 逐条提取（每条记录内部不用 run_step，整体由外层兜底）
result = []
for record in records.value:
    title     = record.locator("xpath=./div[1]/div[1]").inner_text()
    risk_type = record.locator("xpath=./div[1]/div[2]").inner_text()
    fields = {}
    for label_el in record.locator("xpath=./div[2]//span[contains(text(),'：')]").all():
        key = label_el.inner_text().rstrip("：:")
        val = label_el.locator("xpath=../span[2]").inner_text()
        if key and val.strip():
            fields[key] = val.strip()
    result.append({"title": title, "risk_type": risk_type, "fields": fields})

return result
```

---

## 六、数据流总览

```
main.py
│
├── 初始化：launch → context → page0
├── page0 触发 popup → page1（全程复用）
│
└── for company in companies:
      run_step(navigate_to_risk_page, page1, company)
          └── 填搜索框 → 点击搜索 → 等待 #search-bar + div > div:nth-child(3) 出现
      run_step(extract_risk_data, page1, company)
          └── #search-bar + div > div:nth-child(3) > ./div[N]
                  → ./div[1]/div[1] 标题
                  → ./div[1]/div[2] 风险类型
                  → ./div[2]//span[contains(text(),'：')] 字段
      run_step(reset_to_search_page, page1)
          └── page.goto(RISK_SEARCH_URL)
```

---

## 七、易错点速查

| 错误模式 | 正确做法 |
|---------|---------|
| 用 `go_back()` 返回搜索页 | `goto(RISK_SEARCH_URL)`，不依赖浏览器历史 |
| 用任何哈希 class 定位元素 | 全部改用结构 xpath，从 `#search-bar` 稳定锚点出发 |
| 直接用 class 定位字段值 | `xpath=.//span[contains(text(),'：')]` 找标签，`../span[2]` 取值 |
| 字段缺失时填 `None` | 字段不存在就不放进 dict，不预定义结构 |
| 导航/提取失败后不重置页面 | 失败 `continue` 前必须先调 `reset_to_search_page` |
| 模块内自己 try/catch 吞异常 | 异常透传，让 `main.py` 的 `run_step` 统一处理 |
| 在 `extract` 内做页面跳转 | `extract` 只读，任何 `click/goto` 都不允许出现 |
| 搜索后等待结果列表再点击 | 搜索直接跳转详情页，无中间结果列表，无需点击 |

---

## 八、定位稳定性风险评估

| 定位点 | 定位方式 | 稳定性 | 说明 |
|--------|---------|:------:|------|
| 查风险搜索页（`goto`） | 固定 URL | ✅ 高 | 不依赖任何 DOM |
| 搜索框 | `role=textbox` + `name` 属性 | ✅ 高 | 语义化属性 |
| 搜索按钮 | `role=button` + `name` 属性 | ✅ 高 | 语义化属性 |
| 记录列表容器 | `#search-bar + div > div:nth-child(3)` | ✅ 高 | 以稳定 id 为锚点，纯结构关系，无 class 依赖 |
| 详情页加载判断 | 等待记录列表容器内 `./div[1]` 出现 | ✅ 高 | 同上，无 class 依赖 |
| 单条记录 | 记录列表容器的 `xpath=./div` | ✅ 高 | 纯结构，无 class 依赖 |
| 标题文本 | `xpath=./div[1]/div[1]` | ✅ 高 | 纯结构，头部区永远是第1个div，标题永远是第1段文本 |
| 风险类型 | `xpath=./div[1]/div[2]` | ✅ 高 | 同上，风险类型永远是第2段文本 |
| 字段标签 | `xpath=.//span[contains(text(),'：')]` | ✅ 高 | 以「：」字符为语义锚点，与 class 完全无关 |
| 字段值 | `xpath=../span[2]` | 🟢 中高 | 依赖字段标签与值的兄弟关系，结构稳定但若天眼查在两者间插入新 span 会断 |
| `reset_to_search_page` | `goto` 固定 URL | ✅ 高 | 不依赖任何 DOM |

**总结：**

经过本轮讨论，项目中所有哈希 class 依赖已全部消除。现在只剩一个残留风险：**字段值定位用的是 `../span[2]`**，这依赖字段标签 span 和值 span 之间没有其他 span 插入。从当前 HTML 结构看这个假设成立，但如果天眼查未来在两者之间加入新的 span 节点（如角标、图标），这一步会静默取错数据而非报错，是需要留意的点。其余所有定位点均为结构稳定或语义稳定，前端重建不会影响。

---

## 九、补充点

### 补充点 1：字段值提取方式修正

**影响位置**：`extract.py` 5.3 定位规则中「对应字段值」一行，以及 5.5 提取流程中字段值的取值代码。

**修改原因**：原方案 `xpath=../span[2]` 依赖字段名与字段值之间不存在其他 span，若天眼查插入图标等额外节点会静默取错。

**新方案**：含 `：` 的 span 是字段名，其之后的**所有兄弟 span** 合并文本作为字段值。

定位规则替换为：

| 目标 | 定位方式 |
|------|---------|
| 对应字段值 | `label_el.locator("xpath=following-sibling::span").all()`，对结果列表做 `"".join(el.inner_text() for el in val_els).strip()` |

提取流程中字段值部分替换为：

```python
for label_el in record.locator("xpath=./div[2]//span[contains(text(),'：')]").all():
    key = label_el.inner_text().rstrip("：:")
    val_els = label_el.locator("xpath=following-sibling::span").all()
    val = "".join(el.inner_text() for el in val_els).strip()
    if key and val:
        fields[key] = val
```

日期筛选
阻塞发邮箱Z1941704428@outlook.com
翻页？？？