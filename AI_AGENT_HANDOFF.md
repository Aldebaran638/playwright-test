# AI Agent Handoff

## 1. 文档目标

这份文档用于给后续 AI 提供“可快速承接的记忆”。

重点覆盖：

- 这个仓库里 Playwright 项目的演进过程
- `mintel` 和 `tyc` 两个项目的共同模式
- `tyc` 当前已经完成的模块化结构
- 用户在对话中明确表达过的偏好
- 下一步正在抽象的“流水线式 AI Agent 工程”方案

读完这份文档后，新的 AI 应该能：

- 快速理解当前项目为什么会被拆成这些模块
- 避免重复走已经踩过的坑
- 按现有风格继续扩展新的站点采集项目


## 2. 仓库背景

仓库根目录下已经出现多个 Playwright 相关项目，其中这次对话主要围绕：

- `mintel/`
- `tyc/`

用户当前的目标已经从“写单个站点脚本”，逐渐升级成：

**总结一套可复用的信息收集项目框架，并进一步抽象成一个可流水线生产此类项目的 AI Agent 工程。**


## 3. 对话演进概览

### 3.1 早期问题：登录态、页面元素、基础抓取

最开始的讨论集中在：

- 如何判断一个网站是否处于登录态
- 如何用 Playwright 从页面中定位元素
- 如何把页面中的纯文本信息保存到文件

在这个阶段，用户更关注：

- “页面上是否已登录”的判断逻辑
- “如何从具体元素块中抽出纯文本”
- “不要把 HTML 一起存下来”

### 3.2 从样例抓取走向模块化

后续在 `tyc` 项目中，需求逐渐从“能抓到信息”发展为：

- 主流程只做编排
- 页面操作和提取逻辑拆成模块
- 异常页面、登录弹窗、验证码页要能统一处理
- 能批量查询多个公司

因此 `tyc` 被逐步拆成了：

- 浏览器环境模块
- 登录态模块
- 通用步骤执行模块
- 页面总检查模块
- 非法页面识别子模块
- 搜索并进入详情页模块
- 公司元信息模块
- 公司风险模块
- 批量查询模块

### 3.3 从单站点脚本走向“流水线工程”

用户后来明确提出：

> 现在已经做了若干个 Playwright 项目了（mintel 和 tyc），想总结它们的共同点，方便以后流水线生产这种信息收集项目。

然后对框架进行了升级讨论：

- 每个“必须模块”都应该由 AI 结合用户参数来生成
- 参数缺失时要有默认行为和终端提示
- 例如浏览器上下文模块：
  - 如果用户给了真实浏览器路径和用户数据目录，就生成持久化真实环境
  - 如果路径非法或没给用户数据目录，就降级到默认浏览器环境
  - 但必须明确提示用户当前正在使用默认环境

结论是：

**以后这类项目的核心不是“从零写脚本”，而是“基于参数装配模块”。**


## 4. 已经形成的工程共识

### 4.1 `main.py` 只做编排

用户已经多次确认：

- `main.py` 不应该堆页面细节
- 细节都应下沉到 `modules/`

也就是说：

- `main.py` 负责串联流程
- `modules/` 负责具体能力

### 4.2 模块必须职责单一

对话中已经逐步建立了一个很清楚的原则：

- “进入详情页”模块只做进入页面
- “公司元信息”模块只做元信息抽取
- “风险信息”模块只做风险信息相关逻辑
- “总检查模块”只做页面状态调度

不要把多个无关能力硬塞进一个文件。

### 4.3 所有 Playwright 步骤都应尽量走统一封装

后来引入了 `run_step(...)` 这个统一封装思想。

目标是让所有元步骤都具备统一能力：

- 超时自动重试
- 成功后自动随机等待
- 失败后自动调用页面总检查模块
- 如果发现非法页，则阻塞等待用户处理，再继续重试

对话中还明确了一个重要经验：

> 如果一个 Playwright 行为是“点击并等待 popup / 点击并等待跳转”，那就要把整个组合动作作为一个元步骤交给 `run_step(...)`，而不是只包点击。

### 4.4 页面异常处理必须模块化

不是某个地方报错就直接退出，而是：

- 先调用总检查模块
- 再由总检查模块调用若干非法页识别子模块

这套设计已经在 `tyc` 中形成：

- `page_guard.py`
- `guards/verification_page.py`
- `guards/login_modal.py`

### 4.5 数据获取方式不应只限于“页面提取”

后期用户提出一个关键更新：

> 信息提取模块或许不是必须的，因为有的网站提供开放下载按钮。

因此框架认识发生升级：

- “信息提取”只是数据获取的一种实现
- 更大的抽象应该是“数据获取层”

未来数据获取方式可能包括：

- 页面 DOM 提取
- 下载文件
- 调接口
- 读取内嵌脚本变量


## 5. `mintel` 项目给出的模板价值

`mintel` 主要提供了一个重要模板：

### 浏览器上下文模板

例如：

- 指定真实浏览器 executable path
- 指定用户数据目录
- 指定 profile
- 使用 `launch_persistent_context(...)`
- 注入 stealth 脚本

这部分被用户认可为后续多个项目都可参考的“环境初始化模板”。

在 `tyc` 中，浏览器上下文模块就是按这个思路扩展出来的。


## 6. `tyc` 项目已经形成的模块结构

### 6.1 浏览器环境

- [browser_context.py](/c:/Users/winkey/Desktop/网站研究/playwright/tyc/modules/browser_context.py)

职责：

- 校验浏览器环境路径
- 启动持久化上下文
- 注入 stealth

### 6.2 登录态与等待登录

- [login_state.py](/c:/Users/winkey/Desktop/网站研究/playwright/tyc/modules/login_state.py)

职责：

- 判断当前是否登录
- 如果未登录，则阻塞等待用户登录
- 每隔 3 秒复查一次
- 无超时

用户明确强调过：

> 未登录时不要直接报错退出，要阻塞等待用户处理。

### 6.3 通用步骤执行器

- [run_step.py](/c:/Users/winkey/Desktop/网站研究/playwright/tyc/modules/run_step.py)

职责：

- 封装 Playwright 元步骤
- 超时自动重试
- 成功后自动随机等待
- 失败后调用 `page_guard.check_page(...)`
- 如果检测到非法页面，则调用恢复等待模块

### 6.4 页面总检查模块

- [page_guard.py](/c:/Users/winkey/Desktop/网站研究/playwright/tyc/modules/page_guard.py)

职责：

- 统一调度非法页识别子模块
- 返回当前页面状态

当前已经接入的子模块：

- [verification_page.py](/c:/Users/winkey/Desktop/网站研究/playwright/tyc/modules/guards/verification_page.py)
- [login_modal.py](/c:/Users/winkey/Desktop/网站研究/playwright/tyc/modules/guards/login_modal.py)

### 6.5 非法页等待恢复

- [wait_for_recovery.py](/c:/Users/winkey/Desktop/网站研究/playwright/tyc/modules/wait_for_recovery.py)

职责：

- 如果当前页是非法页
- 阻塞等待用户处理
- 每隔几秒复查一次
- 恢复后返回

### 6.6 搜索并进入详情页

- [enter_company_detail_page.py](/c:/Users/winkey/Desktop/网站研究/playwright/tyc/modules/enter_company_detail_page.py)

职责：

- 从天眼查主页搜索指定公司
- 打开公司详情页 popup

这个模块经历过一次重要修正：

- 早期依赖 `get_by_role(..., name=...)`
- 后来用户发现搜索框 `name` 是动态的，而且按钮有重复
- 因此改成更稳的“主搜索区内部定位”策略：
  - 先锁定 `main section`
  - 再取区内 `input[type='text']`
  - 再取区内按钮

这个修改反映了一个重要共识：

> 尽量依赖稳定结构和相对定位，不要过度依赖动态 name。

### 6.7 公司元信息模块

现在已经被放进独立目录：

- [company_metadata/__init__.py](/c:/Users/winkey/Desktop/网站研究/playwright/tyc/modules/company_metadata/__init__.py)
- [company_metadata/extractor.py](/c:/Users/winkey/Desktop/网站研究/playwright/tyc/modules/company_metadata/extractor.py)

职责：

- 等待公司详情主容器出现
- 从 `#J_CompanyHeaderContent` 中提取结构化元信息

这一模块的设计过程有几个关键结论：

- 依赖稳定容器比依赖散乱 class 更稳
- 不要直接抓整页一大块文本
- 应该把页面内容拆成字段
- 允许字段缺失，不要因为单字段缺失就整体失败

### 6.8 公司风险模块

已经被整理进独立目录：

- [company_risk/__init__.py](/c:/Users/winkey/Desktop/网站研究/playwright/tyc/modules/company_risk/__init__.py)
- [company_risk/models.py](/c:/Users/winkey/Desktop/网站研究/playwright/tyc/modules/company_risk/models.py)
- [company_risk/navigator.py](/c:/Users/winkey/Desktop/网站研究/playwright/tyc/modules/company_risk/navigator.py)
- [company_risk/page_extractor.py](/c:/Users/winkey/Desktop/网站研究/playwright/tyc/modules/company_risk/page_extractor.py)
- [company_risk/collector.py](/c:/Users/winkey/Desktop/网站研究/playwright/tyc/modules/company_risk/collector.py)

职责拆分如下：

- `navigator.py`
  - 在详情页中按顺序扫描：
    - 自身风险
    - 周边风险
    - 历史风险
    - 预警提醒
  - 找到第一个数量大于 0 的风险入口并点击
  - 如果四项全为 0，则不进入风险页

- `page_extractor.py`
  - 进入风险页后，优先解析页面中内嵌的 `var mm = {...}` 数据
  - 而不是硬抓大量展示层 DOM

- `models.py`
  - 定义风险摘要和截断规则

- `collector.py`
  - 串联导航和提取

这里还有一个很重要的规则：

> 对于 `mm` 里的四项风险，每项最多抓取前 10 个“和 `count` 同单位的内容”。

也就是说：

- 不是简单截 10 行
- 而是按 `riskCount` 计数累计到 10 左右为止

### 6.9 批量查询模块

- [batch_company_query.py](/c:/Users/winkey/Desktop/网站研究/playwright/tyc/modules/batch_company_query.py)

职责：

- 接收公司名称数组
- 顺序逐个查询
- 每家公司返回统一结果结构

这一模块后面还被 `main.py` 再包了一层：

- 先做元信息批量查询
- 再逐家补充风险信息


## 7. `tyc/main.py` 的当前思路

当前 `main.py` 的职责是高层编排。

主流程大致是：

1. 初始化浏览器环境
2. 打开天眼查首页
3. 检查登录状态
4. 调用批量公司查询模块
5. 在批量结果基础上逐个补充风险信息
6. 保存结果并退出

这体现了用户明确提出过的原则：

- `main.py` 只做流程组织
- 具体页面动作应下沉进模块


## 8. 已经踩过的重要坑

### 8.1 不要说“虚拟环境坏了”

用户明确强调过：

> 虚拟环境绝对不会出错。

因此后续 AI 需要注意：

- 不要轻易把问题归因到 `venv` 本身
- 如果当前终端调用出错，只能描述为：
  - “当前这次终端里的解释器入口调用异常”
  - 或“当前调用路径没有按预期解析”

不要直接下结论说虚拟环境损坏。

### 8.2 页面定位不要过度依赖动态文案或动态类名

对话中已经多次暴露这个问题：

- 搜索框 `name` 可能变化
- class 名很多是构建产物
- 同名按钮可能在页面上出现多个

因此后续模块设计时，应优先采用：

- 稳定容器
- 相对定位
- 区域内定位
- 文本锚点
- 结构锚点

### 8.3 Popup 等待要作为完整元步骤

用户遇到过：

- 点击已成功
- 但 `expect_popup()` 超时

因此后来确认：

> `click + wait popup` 必须作为一个整体交给 `run_step(...)`

### 8.4 异常页面不要只处理验证码页

后续已经补上：

- 身份验证页
- 登录弹窗

说明非法页体系必须可扩展。


## 9. 用户偏好总结

下面这些偏好是用户在对话中明确表达过的，后续 AI 应当继承：

### 9.1 沟通与执行

- 不要总停在讨论层，能落代码就尽量落代码
- 但当用户明确说“本次对话不用改代码”时，要尊重
- 需要时可以直接改，不必每次都先长篇提方案

### 9.2 结构偏好

- 喜欢 `main.py` 只编排
- 喜欢 `modules/` 存放模块
- 喜欢将同一业务域的模块集中到独立子目录
  - 如 `company_metadata/`
  - 如 `company_risk/`

### 9.3 工程偏好

- 每个模块最好有对应测试
- 使用 `loguru`
- 注释使用中文
- 注释应当简洁，只标关键逻辑

### 9.4 运行时偏好

- 未登录时阻塞等待，不直接退出
- 非法页出现时阻塞等待用户处理
- 不要默认“环境坏了”


## 10. 当前正在抽象的“流水线工程”方案

用户现在的目标，不再只是 `mintel` 或 `tyc`。

用户想做的是：

**一个面向信息收集类 Playwright 项目的流水线工程 / AI Agent 工程。**

### 10.1 核心理念

这个工程不是：

- AI 从零随意生成一个脚本

而是：

- 针对每个必须模块
- 结合用户意见或输入参数
- 逐个生成模块内容
- 缺失参数时按规则降级并提示

### 10.2 用户给出的典型例子

浏览器上下文模块：

- 如果用户提供真实浏览器环境，就使用真实浏览器环境
- 如果用户提供了非法路径，或者没有提供用户数据目录
- 就退回默认浏览器环境
- 但要在终端明确提示用户当前正在使用默认环境

### 10.3 当前抽象出的流水线框架

建议的总体流程：

1. 用户需求输入
2. 模块识别
3. 模块参数收集
4. 参数校验
5. 默认值补全
6. 依赖顺序生成模块
7. 生成测试
8. 组装 `main.py`
9. 输出项目

### 10.4 当前建议的模块层级

#### 环境层

- `config`
- `browser_context`

#### 执行控制层

- `run_step`
- `page_guard`
- `wait_for_recovery`

#### 页面状态层

- `login_state`
- `guards/*`

#### 页面进入层

- `enter_target_page`

#### 数据获取层

这一层是更新后的关键抽象。

不应再默认叫“提取模块”，而应叫：

- `data_acquisition`
- 或 `collector`

因为实际获取方式可能是：

- 页面提取
- 下载文件
- 调接口

#### 编排层

- `batch_query`
- `main.py`


## 11. 对未来 AI 的建议

如果后续 AI 接手这个仓库，建议按下面顺序理解和继续：

1. 先读 `MODULE_GENERATION_GUIDE.md`
2. 再读本文档
3. 再看 `tyc/modules/` 的当前结构
4. 优先复用已有模块设计，而不是重新发明命名
5. 对新站点也采用：
   - 环境层
   - 执行控制层
   - 页面状态层
   - 页面进入层
   - 数据获取层
   - 编排层

### 特别提醒

- 不要把所有站点都当成必须用“页面提取”
- 不要轻易说“虚拟环境坏了”
- 不要在全页范围内直接用模糊选择器定位动态元素
- 先想“稳定锚点是什么”


## 12. 下一步最自然的工作

从当前状态继续，最自然的后续工作包括：

### 方向一：继续完善 `tyc`

- 让风险模块更稳地挂进批量流程
- 完善更多页面异常识别子模块
- 优化搜索区定位

### 方向二：把经验抽成通用模板

- 生成一个可复用的 Playwright 信息采集项目模板
- 形成参数驱动式模块生成规则

### 方向三：正式搭建流水线 AI Agent

- 定义“必须模块”清单
- 为每个模块定义参数协议
- 定义默认值与降级策略
- 让 AI 能按顺序生成整个项目


## 13. 一句话总结

这个仓库里的 `mintel` 和 `tyc`，已经不只是两个站点脚本，而是在共同沉淀一套：

**模块化、可扩展、可批量复制、可被 AI 参数化生成的 Playwright 信息收集工程框架。**
