from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # 必须开可视化

    context = browser.new_context(
        record_har_path="manual.har",
        record_har_content="embed"
    )

    page = context.new_page()

    # 打开一个起始页面（也可以不写）
    page.goto("https://analytics.zhihuiya.com/")

    print("👉 现在你可以随便操作浏览器，操作完按回车结束...")
    input()  # 阻塞，让你自由操作

    context.close()  # 关键：写入 HAR
    browser.close()