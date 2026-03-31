# local_connect.py
from playwright.sync_api import sync_playwright

# 服务器 IP 和端口
WS_ENDPOINT = "ws://127.0.0.1:9222/devtools/browser/5e8d3086-17be-4767-87d4-7a94f167a24c"  # 替换 server_browser.py 输出的 ws_endpoint 

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(WS_ENDPOINT)
    page = browser.new_page()
    page.goto("https://baidu.com")
    print("页面标题:", page.title())
    print("等待30秒供开发者观察...")
    page.wait_for_timeout(30000)