这是一个playWright项目，辅助收集信息

- 在启动项目main.py之前，需要执行keyring的python程序来将账户密码存进系统
1. 安装环境
```powershell
pip install -r requirements.txt
```
2. 创建并执行info.py
```python
import keyring

keyring.set_password("mintel", "username", "你的邮箱")
keyring.set_password("mintel", "password", "你的密码")
```

3. 执行main.py
```python
python main.py
```
