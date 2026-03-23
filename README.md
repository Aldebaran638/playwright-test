# Playwright 信息收集项目

该项目用于自动化登录并访问 Mintel 页面，辅助信息收集。

## 快速开始

### 1. 安装依赖

```powershell
pip install -r requirements.txt
python -m playwright install chromium
```

### 2. 配置账号（Keyring）

在运行 `main.py` 之前，需要先把账号和密码写入系统凭据库。

可使用 `info.py`（请先把占位符改成真实账号）：

```python
import keyring

keyring.set_password("mintel", "username", "你的邮箱")
keyring.set_password("mintel", "password", "你的密码")
```

执行：

```powershell
python info.py
```

### 3. 运行主程序

```powershell
python main.py
```

## 运行产物

- `auth.json`：登录态缓存文件（下次可复用登录态）
- `test.html`：当前页面 HTML 快照

## 常见问题

- 报错 `请先用 keyring 保存 mintel 的 username 和 password`：
  先执行 `python info.py`，确认已写入账号密码。
- 登录态失效：
  删除 `auth.json` 后重新运行 `python main.py` 进行登录。
