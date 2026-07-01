# -*- coding: utf-8 -*-

from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
STATE_FILE = BASE_DIR / "bilibili_state.json"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = browser.new_context(
            viewport={"width": 1440, "height": 900}
        )

        page = context.new_page()
        page.goto("https://member.bilibili.com/platform/home", wait_until="domcontentloaded")

        print("请在打开的浏览器里扫码登录 B站。")
        input("登录成功后，回到这里按回车：")

        context.storage_state(path=str(STATE_FILE))

        print(f"B站登录态已导出：{STATE_FILE}")

        browser.close()


if __name__ == "__main__":
    main()