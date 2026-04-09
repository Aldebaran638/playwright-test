from playwright.sync_api import sync_playwright
import json

def mock_api(route):
    data = {
        "code": 0,
        "data": [
            {"name": "公司A", "id": 1},
            {"name": "公司B", "id": 2}
        ]
    }

    route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(data)
    )

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    # 👇 拦截接口（关键）
    page.route("**/**", mock_api)

    # 👇 页面随便写（不会真的请求接口）
    page.goto("https://example.com")

    input("看效果，回车退出")
    browser.close()