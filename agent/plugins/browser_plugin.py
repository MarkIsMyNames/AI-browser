"""Browser plugin for Semantic Kernel using Playwright."""
from typing import Annotated
from playwright.async_api import async_playwright, Page, Browser
from semantic_kernel.functions import kernel_function


class BrowserPlugin:
    """Plugin that provides browser automation capabilities using Playwright."""

    def __init__(self, headless: bool = False):
        """Initialize the browser plugin.

        Args:
            headless: Whether to run browser in headless mode.
        """
        self.headless = headless
        self.playwright = None
        self.browser: Browser = None
        self.page: Page = None
        self._initialized = False

    async def initialize(self):
        """Initialize Playwright and browser."""
        if not self._initialized:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=self.headless)
            self.page = await self.browser.new_page()
            self._initialized = True

    async def cleanup(self):
        """Clean up browser and Playwright resources."""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self._initialized = False

    @kernel_function(
        name="navigate_to_url",
        description="Navigate the browser to a specific URL"
    )
    async def navigate_to_url(
        self,
        url: Annotated[str, "The URL to navigate to"]
    ) -> Annotated[str, "The result of the navigation"]:
        """Navigate to a URL."""
        await self.initialize()
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            current_url = self.page.url
            title = await self.page.title()
            return f"Successfully navigated to {current_url}. Page title: {title}"
        except Exception as e:
            return f"Error navigating to {url}: {str(e)}"

    @kernel_function(
        name="click_element",
        description="Click on an element on the page using a CSS selector or visible text"
    )
    async def click_element(
        self,
        selector: Annotated[str, "CSS selector or text content of the element to click"]
    ) -> Annotated[str, "The result of the click action"]:
        """Click an element on the page."""
        await self.initialize()
        try:
            # Try as CSS selector first
            if await self.page.locator(selector).count() > 0:
                await self.page.locator(selector).first.click(timeout=10000)
                return f"Successfully clicked element: {selector}"

            # Try as text content
            text_locator = self.page.get_by_text(selector)
            if await text_locator.count() > 0:
                await text_locator.first.click(timeout=10000)
                return f"Successfully clicked element with text: {selector}"

            return f"Could not find element: {selector}"
        except Exception as e:
            return f"Error clicking element {selector}: {str(e)}"

    @kernel_function(
        name="fill_input",
        description="Fill an input field with text using a CSS selector"
    )
    async def fill_input(
        self,
        selector: Annotated[str, "CSS selector of the input field"],
        text: Annotated[str, "Text to fill in the input field"]
    ) -> Annotated[str, "The result of the fill action"]:
        """Fill an input field with text."""
        await self.initialize()
        try:
            await self.page.locator(selector).first.fill(text, timeout=10000)
            return f"Successfully filled '{selector}' with text: {text}"
        except Exception as e:
            return f"Error filling input {selector}: {str(e)}"

    @kernel_function(
        name="get_page_content",
        description="Get the text content of the current page or a specific element"
    )
    async def get_page_content(
        self,
        selector: Annotated[str, "Optional CSS selector to get content from a specific element. Leave empty to get all page text"] = ""
    ) -> Annotated[str, "The text content"]:
        """Get page content."""
        await self.initialize()
        try:
            if selector:
                content = await self.page.locator(selector).first.text_content(timeout=10000)
                return f"Content of {selector}: {content}"
            else:
                # Get main visible text from body
                content = await self.page.locator("body").text_content()
                # Limit content to avoid token issues
                if len(content) > 2000:
                    content = content[:2000] + "... (truncated)"
                return f"Page content: {content}"
        except Exception as e:
            return f"Error getting page content: {str(e)}"

    @kernel_function(
        name="get_page_state",
        description="Get the current state of the page including URL, title, and visible interactive elements"
    )
    async def get_page_state(self) -> Annotated[str, "The current page state"]:
        """Get current page state."""
        await self.initialize()
        try:
            url = self.page.url
            title = await self.page.title()

            # Get some key interactive elements
            buttons = await self.page.locator("button").all_text_contents()
            links = await self.page.locator("a").all_text_contents()
            inputs = await self.page.locator("input").count()

            # Limit the lists
            buttons = buttons[:10] if len(buttons) > 10 else buttons
            links = links[:10] if len(links) > 10 else links

            state = f"""Current Page State:
URL: {url}
Title: {title}
Buttons visible: {len(buttons)} - {buttons}
Links visible: {len(links)} - {links}
Input fields: {inputs}
"""
            return state
        except Exception as e:
            return f"Error getting page state: {str(e)}"

    @kernel_function(
        name="wait_for_navigation",
        description="Wait for the page to navigate or load after an action"
    )
    async def wait_for_navigation(
        self,
        timeout_ms: Annotated[int, "Timeout in milliseconds (default 5000)"] = 5000
    ) -> Annotated[str, "The result of waiting"]:
        """Wait for navigation."""
        await self.initialize()
        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
            return f"Page loaded successfully. Current URL: {self.page.url}"
        except Exception as e:
            return f"Navigation wait timeout or error: {str(e)}"

    @kernel_function(
        name="type_text",
        description="Type text character by character (simulates human typing)"
    )
    async def type_text(
        self,
        selector: Annotated[str, "CSS selector of the input field"],
        text: Annotated[str, "Text to type"]
    ) -> Annotated[str, "The result of the typing action"]:
        """Type text character by character."""
        await self.initialize()
        try:
            await self.page.locator(selector).first.type(text, delay=100, timeout=10000)
            return f"Successfully typed text into '{selector}'"
        except Exception as e:
            return f"Error typing into {selector}: {str(e)}"

    @kernel_function(
        name="press_key",
        description="Press a keyboard key (e.g., Enter, Tab, Escape)"
    )
    async def press_key(
        self,
        key: Annotated[str, "Key to press (e.g., 'Enter', 'Tab', 'Escape')"]
    ) -> Annotated[str, "The result of the key press"]:
        """Press a keyboard key."""
        await self.initialize()
        try:
            await self.page.keyboard.press(key)
            return f"Successfully pressed key: {key}"
        except Exception as e:
            return f"Error pressing key {key}: {str(e)}"
