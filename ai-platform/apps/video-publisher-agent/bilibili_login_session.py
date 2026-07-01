# -*- coding: utf-8 -*-

import json
import os
import time
import traceback
from pathlib import Path

from config import CONFIG
from playwright.sync_api import sync_playwright


DONE_FILE = Path(os.getenv("BILIBILI_LOGIN_DONE_FILE", "runtime/bilibili_login_done.signal"))
STATUS_FILE = Path(os.getenv("BILIBILI_LOGIN_STATUS_FILE", "runtime/bilibili_login_status.json"))
TIMEOUT_SECONDS = int(os.getenv("BILIBILI_LOGIN_TIMEOUT_SECONDS", "900"))


def write_status(status: str, message: str = "") -> None:
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(
        json.dumps(
            {
                "status": status,
                "message": message,
                "updated_at": time.time(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> int:
    state_file = Path(CONFIG["bilibili_state_file"])
    state_file.parent.mkdir(parents=True, exist_ok=True)
    DONE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if DONE_FILE.exists():
        DONE_FILE.unlink()

    write_status("starting", "正在打开 B 站登录页面。")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()
            page.goto("https://member.bilibili.com/platform/home", wait_until="domcontentloaded")

            write_status("waiting", "请在打开的浏览器中完成 B 站登录，然后回到网页点击“我已登录”。")
            deadline = time.time() + TIMEOUT_SECONDS
            while time.time() < deadline:
                if DONE_FILE.exists():
                    write_status("saving", "正在保存 B 站登录态。")
                    context.storage_state(path=str(state_file))
                    browser.close()
                    write_status("saved", f"B 站登录态已保存：{state_file}")
                    return 0
                time.sleep(1)

            browser.close()
            write_status("timeout", "等待登录超时，请重新开始。")
            return 124
    except Exception as exc:
        write_status("error", f"{exc}\n{traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
