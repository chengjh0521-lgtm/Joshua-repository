import asyncio
import sys
import threading
from typing import Optional
from urllib.parse import quote_plus

from playwright.async_api import BrowserContext, Page, Playwright, async_playwright

from backend.config import settings


class ZhihuBrowser:
    def __init__(self) -> None:
        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._thread_ready = threading.Event()
        self._thread_error: Optional[BaseException] = None
        self._start_lock = threading.Lock()
        self._operation_lock = threading.Lock()

    async def open_editor(self, title: str, body: str, *, wait_for_draft: bool = False) -> dict[str, str]:
        return await asyncio.to_thread(self._open_editor_blocking, title, body, wait_for_draft)

    async def open_idea_editor(
        self,
        body: str,
        *,
        wait_for_draft: bool = False,
        publish: bool = False,
    ) -> dict[str, str]:
        return await asyncio.to_thread(self._open_idea_editor_blocking, body, wait_for_draft, publish)

    async def open_question_answer(
        self,
        question_title: str,
        body: str,
        *,
        wait_for_draft: bool = False,
        publish: bool = False,
    ) -> dict[str, str]:
        return await asyncio.to_thread(
            self._open_question_answer_blocking,
            question_title,
            body,
            wait_for_draft,
            publish,
        )

    def _open_editor_blocking(self, title: str, body: str, wait_for_draft: bool) -> dict[str, str]:
        self._ensure_browser_thread()
        assert self._loop is not None

        with self._operation_lock:
            future = asyncio.run_coroutine_threadsafe(
                self._open_editor_impl(title, body, wait_for_draft),
                self._loop,
            )
            return future.result()

    def _open_idea_editor_blocking(self, body: str, wait_for_draft: bool, publish: bool) -> dict[str, str]:
        self._ensure_browser_thread()
        assert self._loop is not None

        with self._operation_lock:
            future = asyncio.run_coroutine_threadsafe(
                self._open_idea_editor_impl(body, wait_for_draft, publish),
                self._loop,
            )
            return future.result()

    def _open_question_answer_blocking(
        self,
        question_title: str,
        body: str,
        wait_for_draft: bool,
        publish: bool,
    ) -> dict[str, str]:
        self._ensure_browser_thread()
        assert self._loop is not None

        with self._operation_lock:
            future = asyncio.run_coroutine_threadsafe(
                self._open_question_answer_impl(question_title, body, wait_for_draft, publish),
                self._loop,
            )
            return future.result()

    def _ensure_browser_thread(self) -> None:
        if self._loop and self._thread and self._thread.is_alive():
            return

        with self._start_lock:
            if self._loop and self._thread and self._thread.is_alive():
                return
            self._thread_ready.clear()
            self._thread_error = None
            self._thread = threading.Thread(
                target=self._run_browser_loop,
                name="zhihu-playwright-loop",
                daemon=True,
            )
            self._thread.start()
            self._thread_ready.wait(timeout=10)

            if self._thread_error:
                raise RuntimeError("Failed to start Playwright browser thread.") from self._thread_error
            if not self._loop:
                raise RuntimeError("Timed out while starting Playwright browser thread.")

    def _run_browser_loop(self) -> None:
        try:
            if sys.platform.startswith("win"):
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            self._thread_ready.set()
            loop.run_forever()
        except BaseException as exc:
            self._thread_error = exc
            self._thread_ready.set()

    async def _open_editor_impl(self, title: str, body: str, wait_for_draft: bool) -> dict[str, str]:
        await self._ensure_context()
        assert self._context is not None

        self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        page = self._page
        await page.goto(settings.zhihu_editor_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2500)

        title_filled = await self._fill_first_available(
            page,
            [
                "textarea[placeholder*='标题']",
                "input[placeholder*='标题']",
                "[contenteditable='true'][data-placeholder*='标题']",
                "[contenteditable='true'][placeholder*='标题']",
            ],
            title,
        )
        body_filled = await self._fill_first_available(
            page,
            [
                "[contenteditable='true'][data-placeholder*='正文']",
                "[contenteditable='true'][data-placeholder*='请输入正文']",
                ".DraftEditor-editorContainer [contenteditable='true']",
                ".public-DraftEditor-content[contenteditable='true']",
                "[contenteditable='true']",
                "textarea",
            ],
            self._strip_first_heading(body, title),
        )

        if wait_for_draft and title_filled and body_filled:
            await page.wait_for_timeout(settings.zhihu_draft_wait_seconds * 1000)

        return {
            "status": "draft_waited" if wait_for_draft else "opened",
            "url": page.url,
            "title_filled": str(title_filled),
            "body_filled": str(body_filled),
            "note": (
                "已填入知乎编辑页并等待自动保存；请人工检查草稿箱或编辑页，不会点击发布。"
                if wait_for_draft
                else "已停留在知乎编辑页，请人工检查并决定是否发布。"
            ),
        }

    async def _open_idea_editor_impl(self, body: str, wait_for_draft: bool, publish: bool) -> dict[str, str]:
        await self._ensure_context()
        assert self._context is not None

        self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        page = self._page
        response = await page.goto(settings.zhihu_idea_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2500)
        if await self._is_unprocessable_page(page, response):
            await page.goto("https://www.zhihu.com", wait_until="domcontentloaded")
            await page.wait_for_timeout(2500)

        risk_control = await self._detect_risk_control(page)
        if risk_control:
            return risk_control

        editor_opened = await self._click_first_available(
            page,
            [
                "button:has-text('写想法')",
                "button:has-text('发布想法')",
                "button:has-text('分享想法')",
                "div[role='button']:has-text('写想法')",
                "div[role='button']:has-text('发布想法')",
                "div[role='button']:has-text('分享想法')",
                "[placeholder*='想法']",
                "[data-placeholder*='想法']",
            ],
        )
        await page.wait_for_timeout(1500)

        body_filled = await self._fill_first_available(
            page,
            [
                "[contenteditable='true'][data-placeholder*='想法']",
                "[contenteditable='true'][placeholder*='想法']",
                "[contenteditable='true'][data-placeholder*='分享']",
                "[contenteditable='true'][placeholder*='分享']",
                ".DraftEditor-editorContainer [contenteditable='true']",
                ".public-DraftEditor-content[contenteditable='true']",
                "[contenteditable='true']",
                "textarea[placeholder*='想法']",
                "textarea",
            ],
            body.strip(),
        )

        if wait_for_draft and body_filled:
            await page.wait_for_timeout(settings.zhihu_draft_wait_seconds * 1000)

        publish_button_visible = await self._scroll_first_available_into_view(
            page,
            self._idea_publish_button_selectors(),
        )

        published = False
        if publish and body_filled and publish_button_visible:
            published = await self._click_first_available(page, self._idea_publish_button_selectors())
            if published:
                await page.wait_for_timeout(3000)

        return {
            "status": self._idea_status(wait_for_draft, publish, published),
            "url": page.url,
            "editor_opened": str(editor_opened),
            "body_filled": str(body_filled),
            "publish_button_visible": str(publish_button_visible),
            "published": str(published),
            "note": (
                "已打开知乎想法编辑器、填入内容并点击发布按钮。"
                if published
                else (
                    "已打开知乎想法编辑器并填入内容，等待页面保留草稿；不会点击发布。"
                    if wait_for_draft
                    else "已打开知乎想法编辑器并尝试填入内容；不会点击发布。"
                )
            ),
        }

    async def _open_question_answer_impl(
        self,
        question_title: str,
        body: str,
        wait_for_draft: bool,
        publish: bool,
    ) -> dict[str, str]:
        await self._ensure_context()
        assert self._context is not None

        self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        page = self._page
        search_url = f"https://www.zhihu.com/search?type=content&q={quote_plus(question_title)}"
        await page.goto(search_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2500)
        risk_control = await self._detect_risk_control(page)
        if risk_control:
            return risk_control

        question_opened = await self._open_first_matching_question(page, question_title)
        if not question_opened:
            return {
                "status": "question_not_found",
                "url": page.url,
                "question_opened": "False",
                "answer_box_opened": "False",
                "body_filled": "False",
                "note": "没有在知乎搜索结果中找到匹配的问题，请人工确认问题标题或登录状态。",
            }

        await page.wait_for_timeout(2500)
        risk_control = await self._detect_risk_control(page)
        if risk_control:
            return risk_control

        answer_box_opened = await self._click_first_available(
            page,
            [
                "button:has-text('写回答')",
                "button:has-text('回答')",
                "a:has-text('写回答')",
                "div[role='button']:has-text('写回答')",
                "div[role='button']:has-text('回答')",
            ],
        )
        await page.wait_for_timeout(1500)

        body_filled = await self._fill_first_available(
            page,
            [
                ".DraftEditor-editorContainer [contenteditable='true']",
                ".public-DraftEditor-content[contenteditable='true']",
                "[contenteditable='true'][data-placeholder*='回答']",
                "[contenteditable='true'][data-placeholder*='写回答']",
                "[contenteditable='true']",
                "textarea",
            ],
            body.strip(),
        )

        if wait_for_draft and body_filled:
            await page.wait_for_timeout(settings.zhihu_draft_wait_seconds * 1000)

        publish_button_visible = await self._scroll_first_available_into_view(
            page,
            self._publish_button_selectors(),
        )

        published = False
        if publish and body_filled and publish_button_visible:
            published = await self._click_first_available(page, self._publish_button_selectors())
            if published:
                await page.wait_for_timeout(3000)

        return {
            "status": self._answer_status(wait_for_draft, publish, published),
            "url": page.url,
            "question_opened": str(question_opened),
            "answer_box_opened": str(answer_box_opened),
            "body_filled": str(body_filled),
            "publish_button_visible": str(publish_button_visible),
            "published": str(published),
            "note": (
                "已进入知乎问题页、填入回答并点击发布按钮。"
                if published
                else (
                    "已进入知乎问题页并填入回答，等待自动保存。"
                    if wait_for_draft
                    else "已进入知乎问题页并尝试展开回答框。"
                )
            ),
        }

    async def _ensure_context(self) -> None:
        if self._context:
            return
        self._playwright = await async_playwright().start()
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(settings.zhihu_user_data_dir),
            headless=settings.zhihu_headless,
            viewport={"width": 1366, "height": 900},
        )

    async def _fill_first_available(self, page: Page, selectors: list[str], value: str) -> bool:
        for selector in selectors:
            locator = page.locator(selector).first
            try:
                await locator.wait_for(state="visible", timeout=2500)
                await locator.click()
                try:
                    await locator.fill(value)
                except Exception:
                    await page.keyboard.press("Control+A")
                    await page.keyboard.insert_text(value)
                return True
            except Exception:
                continue
        return False

    async def _click_first_available(self, page: Page, selectors: list[str]) -> bool:
        for selector in selectors:
            locator = page.locator(selector).first
            try:
                await locator.wait_for(state="visible", timeout=2500)
                await locator.click()
                return True
            except Exception:
                continue
        return False

    async def _scroll_first_available_into_view(self, page: Page, selectors: list[str]) -> bool:
        for selector in selectors:
            locator = page.locator(selector).first
            try:
                await locator.wait_for(state="visible", timeout=2500)
                await locator.scroll_into_view_if_needed()
                return True
            except Exception:
                continue
        return False

    async def _open_first_matching_question(self, page: Page, question_title: str) -> bool:
        exact_link = page.locator("a[href*='/question/']").filter(has_text=question_title).first
        try:
            await exact_link.wait_for(state="visible", timeout=5000)
            await exact_link.click()
            return True
        except Exception:
            pass

        any_question_link = page.locator("a[href*='/question/']").first
        try:
            await any_question_link.wait_for(state="visible", timeout=5000)
            await any_question_link.click()
            return True
        except Exception:
            return False

    @staticmethod
    def _publish_button_selectors() -> list[str]:
        return [
            "button:has-text('发布回答')",
            "button:has-text('提交回答')",
            "button:has-text('发布')",
            "button:has-text('提交')",
        ]

    @staticmethod
    def _idea_publish_button_selectors() -> list[str]:
        return [
            "button:has-text('发布想法')",
            "button:has-text('发布')",
        ]

    async def _detect_risk_control(self, page: Page) -> Optional[dict[str, str]]:
        try:
            content = await page.locator("body").inner_text(timeout=2500)
        except Exception:
            return None

        if "40362" not in content and "当前请求存在异常" not in content and "暂时限制本次访问" not in content:
            return None

        return {
            "status": "zhihu_risk_control",
            "url": page.url,
            "question_opened": "False",
            "answer_box_opened": "False",
            "body_filled": "False",
            "publish_button_visible": "False",
            "published": "False",
            "note": "知乎返回 40362 异常访问限制。程序已停止自动操作，请等待一段时间后用普通浏览器人工登录和访问。",
        }

    async def _is_unprocessable_page(self, page: Page, response: object) -> bool:
        try:
            status = getattr(response, "status", None)
            if status == 422:
                return True
        except Exception:
            pass

        try:
            content = await page.locator("body").inner_text(timeout=1500)
        except Exception:
            return False

        return "Unprocessable Entity" in content

    @staticmethod
    def _answer_status(wait_for_draft: bool, publish: bool, published: bool) -> str:
        if published:
            return "answer_published"
        if publish:
            return "publish_button_not_clicked"
        if wait_for_draft:
            return "answer_draft_waited"
        return "answer_editor_opened"

    @staticmethod
    def _idea_status(wait_for_draft: bool, publish: bool, published: bool) -> str:
        if published:
            return "idea_published"
        if publish:
            return "idea_publish_button_not_clicked"
        if wait_for_draft:
            return "idea_draft_waited"
        return "idea_editor_opened"

    @staticmethod
    def _strip_first_heading(body: str, title: str) -> str:
        lines = body.strip().splitlines()
        if lines and lines[0].lstrip("# ").strip() == title.strip():
            return "\n".join(lines[1:]).strip()
        return body.strip()


zhihu_browser = ZhihuBrowser()
