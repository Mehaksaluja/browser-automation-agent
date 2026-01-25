import uuid
import base64
from typing import Dict, Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

class BrowserManager:
    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._sessions: Dict[str, Dict[str, object]] = {}

    async def _ensure_browser(self, headless: bool = False):
        if self._playwright is None:
            self._playwright = await async_playwright().start()

        if self._browser is None:
            self._browser = await self._playwright.chromium.launch(headless=headless)

    async def create_session(self, headless: bool = False) -> str:
        await self._ensure_browser(headless=headless)

        context: BrowserContext = await self._browser.new_context()
        page: Page = await context.new_page()

        session_id = str(uuid.uuid4())
        self._sessions[session_id] = {"context": context, "page": page}
        return session_id

    async def get_page(self, session_id: str) -> Page:
        if session_id not in self._sessions:
            raise ValueError("Invalid session_id")
        return self._sessions[session_id]["page"]  # type: ignore

    async def navigate(self, session_id: str, url: str):
        page = await self.get_page(session_id)
        await page.goto(url, wait_until="domcontentloaded")

    async def screenshot_base64(self, session_id: str) -> str:
        page = await self.get_page(session_id)
        image_bytes = await page.screenshot(full_page=True)
        return base64.b64encode(image_bytes).decode("utf-8")

    async def click(self, session_id: str, selector: str, timeout_ms: int = 8000):
        page = await self.get_page(session_id)
        await page.locator(selector).first.click(timeout=timeout_ms)

    async def type_text(
        self,
        session_id: str,
        selector: str,
        text: str,
        clear_first: bool = True,
        timeout_ms: int = 8000
    ):
        page = await self.get_page(session_id)
        loc = page.locator(selector).first
        await loc.wait_for(state="visible", timeout=timeout_ms)

        if clear_first:
            await loc.fill("")
        await loc.type(text, delay=10)

    async def observe_basic(self, session_id: str):
        page = await self.get_page(session_id)
        return {
            "url": page.url,
            "title": await page.title()
        }
    
    async def observe_enhanced(self, session_id: str) -> Dict:
        """Enhanced page observation with more details."""
        page = await self.get_page(session_id)
        
        # Get visible elements
        visible_buttons = await page.locator("button:visible").count()
        visible_inputs = await page.locator("input:visible, textarea:visible").count()
        visible_links = await page.locator("a:visible").count()
        
        # Get page text content (first 500 chars)
        try:
            body_text = await page.locator("body").inner_text()
            page_text_preview = body_text[:500] if body_text else ""
        except:
            page_text_preview = ""
        
        return {
            "url": page.url,
            "title": await page.title(),
            "visible_buttons": visible_buttons,
            "visible_inputs": visible_inputs,
            "visible_links": visible_links,
            "text_preview": page_text_preview
        }
    
    async def wait_for_element(
        self,
        session_id: str,
        selector: str,
        timeout_ms: int = 10000
    ):
        """Wait for an element to appear on the page."""
        page = await self.get_page(session_id)
        await page.locator(selector).first.wait_for(state="visible", timeout=timeout_ms)
    
    async def scroll(self, session_id: str, direction: str = "down"):
        """Scroll the page."""
        page = await self.get_page(session_id)
        if direction == "down":
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
        elif direction == "up":
            await page.evaluate("window.scrollBy(0, -window.innerHeight)")
        elif direction == "top":
            await page.evaluate("window.scrollTo(0, 0)")
        elif direction == "bottom":
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    
    async def select_option(
        self,
        session_id: str,
        selector: str,
        value: str,
        timeout_ms: int = 8000
    ):
        """Select an option from a dropdown/select element."""
        page = await self.get_page(session_id)
        loc = page.locator(selector).first
        await loc.wait_for(state="visible", timeout=timeout_ms)
        await loc.select_option(value)

    async def close_session(self, session_id: str):
        if session_id in self._sessions:
            context: BrowserContext = self._sessions[session_id]["context"]  # type: ignore
            await context.close()
            del self._sessions[session_id]
