from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    output = Path("baidu.png")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        page.goto("https://www.baidu.com", wait_until="domcontentloaded", timeout=30000)
        page.screenshot(path=str(output), full_page=True)

        print(f"已保存截图: {output.resolve()}")
        browser.close()


if __name__ == "__main__":
    main()