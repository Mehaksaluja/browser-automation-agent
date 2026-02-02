import sys
import uuid
import base64
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional, Any

# On Windows, async Playwright can raise NotImplementedError (subprocess in event loop).
# Use sync Playwright in a thread to avoid that.
_USE_SYNC_PLAYWRIGHT = sys.platform.startswith("win")

if _USE_SYNC_PLAYWRIGHT:
    from playwright.sync_api import sync_playwright
    _executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="playwright")
else:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    _executor = None


class BrowserManager:
    def __init__(self):
        self._playwright: Any = None
        self._browser: Any = None
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._sync_pw = None  # sync playwright instance (Windows)

    def _start_playwright_sync(self, headless: bool) -> None:
        """Run in thread: start sync Playwright and launch browser."""
        try:
            pw = sync_playwright().start()
            self._sync_pw = pw
            self._browser = pw.chromium.launch(headless=headless)
        except Exception as e:
            err_msg = str(e).lower()
            if "executable" in err_msg or "browser" in err_msg or "chromium" in err_msg:
                raise RuntimeError(
                    "Playwright Chromium not found. Run: playwright install chromium"
                ) from e
            raise

    async def _ensure_browser(self, headless: bool = False) -> None:
        if _USE_SYNC_PLAYWRIGHT:
            if self._browser is not None:
                return
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                _executor,
                self._start_playwright_sync,
                headless,
            )
            return
        # Non-Windows: use async API
        if self._playwright is None:
            if sys.platform.startswith("win"):
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            self._playwright = await async_playwright().start()
        if self._browser is None:
            self._browser = await self._playwright.chromium.launch(headless=headless)

    async def create_session(self, headless: bool = False) -> str:
        await self._ensure_browser(headless=headless)
        if _USE_SYNC_PLAYWRIGHT:
            loop = asyncio.get_event_loop()
            def new_session():
                context = self._browser.new_context()
                page = context.new_page()
                return context, page
            context, page = await loop.run_in_executor(_executor, new_session)
        else:
            context = await self._browser.new_context()
            page = await context.new_page()
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = {"context": context, "page": page}
        return session_id

    def _get_page(self, session_id: str):
        if session_id not in self._sessions:
            raise ValueError("Invalid session_id")
        return self._sessions[session_id]["page"]

    async def get_page(self, session_id: str):
        return self._get_page(session_id)

    async def navigate(self, session_id: str, url: str):
        page = self._get_page(session_id)
        if _USE_SYNC_PLAYWRIGHT:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(_executor, lambda: page.goto(url, wait_until="domcontentloaded"))
        else:
            await page.goto(url, wait_until="domcontentloaded")

    async def screenshot_base64(self, session_id: str) -> str:
        page = self._get_page(session_id)
        if _USE_SYNC_PLAYWRIGHT:
            loop = asyncio.get_event_loop()
            image_bytes = await loop.run_in_executor(_executor, lambda: page.screenshot(full_page=True))
        else:
            image_bytes = await page.screenshot(full_page=True)
        return base64.b64encode(image_bytes).decode("utf-8")

    async def click(self, session_id: str, selector: str, timeout_ms: int = 8000):
        page = self._get_page(session_id)
        if _USE_SYNC_PLAYWRIGHT:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(_executor, lambda: page.locator(selector).first.click(timeout=timeout_ms))
        else:
            await page.locator(selector).first.click(timeout=timeout_ms)

    async def type_text(
        self,
        session_id: str,
        selector: str,
        text: str,
        clear_first: bool = True,
        timeout_ms: int = 8000
    ):
        page = self._get_page(session_id)
        if _USE_SYNC_PLAYWRIGHT:
            loop = asyncio.get_event_loop()
            def do_type():
                loc = page.locator(selector).first
                loc.wait_for(state="visible", timeout=timeout_ms)
                if clear_first:
                    loc.fill("")
                loc.type(text, delay=10)
            await loop.run_in_executor(_executor, do_type)
        else:
            loc = page.locator(selector).first
            await loc.wait_for(state="visible", timeout=timeout_ms)
            if clear_first:
                await loc.fill("")
            await loc.type(text, delay=10)

    async def observe_basic(self, session_id: str):
        page = self._get_page(session_id)
        if _USE_SYNC_PLAYWRIGHT:
            loop = asyncio.get_event_loop()
            def get_info():
                return {"url": page.url, "title": page.title()}
            return await loop.run_in_executor(_executor, get_info)
        return {"url": page.url, "title": await page.title()}

    async def observe_enhanced(self, session_id: str) -> Dict:
        page = self._get_page(session_id)
        if _USE_SYNC_PLAYWRIGHT:
            loop = asyncio.get_event_loop()
            def get_enhanced():
                vb = page.locator("button:visible").count()
                vi = page.locator("input:visible, textarea:visible").count()
                vl = page.locator("a:visible").count()
                try:
                    body_text = page.locator("body").inner_text()
                    preview = (body_text or "")[:500]
                except Exception:
                    preview = ""
                return {
                    "url": page.url,
                    "title": page.title(),
                    "visible_buttons": vb,
                    "visible_inputs": vi,
                    "visible_links": vl,
                    "text_preview": preview,
                }
            return await loop.run_in_executor(_executor, get_enhanced)
        visible_buttons = await page.locator("button:visible").count()
        visible_inputs = await page.locator("input:visible, textarea:visible").count()
        visible_links = await page.locator("a:visible").count()
        try:
            body_text = await page.locator("body").inner_text()
            page_text_preview = body_text[:500] if body_text else ""
        except Exception:
            page_text_preview = ""
        return {
            "url": page.url,
            "title": await page.title(),
            "visible_buttons": visible_buttons,
            "visible_inputs": visible_inputs,
            "visible_links": visible_links,
            "text_preview": page_text_preview,
        }

    async def wait_for_element(
        self,
        session_id: str,
        selector: str,
        timeout_ms: int = 10000
    ):
        page = self._get_page(session_id)
        if _USE_SYNC_PLAYWRIGHT:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                _executor,
                lambda: page.locator(selector).first.wait_for(state="visible", timeout=timeout_ms),
            )
        else:
            await page.locator(selector).first.wait_for(state="visible", timeout=timeout_ms)

    async def scroll(self, session_id: str, direction: str = "down"):
        page = self._get_page(session_id)
        if direction == "down":
            js = "window.scrollBy(0, window.innerHeight)"
        elif direction == "up":
            js = "window.scrollBy(0, -window.innerHeight)"
        elif direction == "top":
            js = "window.scrollTo(0, 0)"
        else:
            js = "window.scrollTo(0, document.body.scrollHeight)"
        if _USE_SYNC_PLAYWRIGHT:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(_executor, lambda: page.evaluate(js))
        else:
            await page.evaluate(js)

    async def select_option(
        self,
        session_id: str,
        selector: str,
        value: str,
        timeout_ms: int = 8000
    ):
        page = self._get_page(session_id)
        if _USE_SYNC_PLAYWRIGHT:
            loop = asyncio.get_event_loop()
            def do_select():
                loc = page.locator(selector).first
                loc.wait_for(state="visible", timeout=timeout_ms)
                loc.select_option(value)
            await loop.run_in_executor(_executor, do_select)
        else:
            loc = page.locator(selector).first
            await loc.wait_for(state="visible", timeout=timeout_ms)
            await loc.select_option(value)

    async def close_session(self, session_id: str):
        if session_id in self._sessions:
            context = self._sessions[session_id]["context"]
            if _USE_SYNC_PLAYWRIGHT:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(_executor, context.close)
            else:
                await context.close()
            del self._sessions[session_id]
