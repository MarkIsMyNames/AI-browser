import re
import asyncio
from typing import Annotated
from semantic_kernel.functions import kernel_function
from playwright.async_api import async_playwright, Page, BrowserContext
from app.config import Config

class BrowserPlugin:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context: BrowserContext = None
        self.page: Page = None
        self.is_initialized = False

    async def ensure_initialized(self):
        if not self.is_initialized:
            self.playwright = await async_playwright().start()
            # Launch in headless=False to see what's happening (optional)
            self.browser = await self.playwright.chromium.launch(headless=False) 
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()
            self.is_initialized = True

    @kernel_function(description="Navigates the browser to a specific URL")
    async def navigate(self, url: Annotated[str, "The URL to navigate to"]):
        await self.ensure_initialized()
        print(f"[BrowserPlugin] Navigating to: {url}")
        await self.page.goto(url)
        # Wait for load state to be roughly ready
        await self.page.wait_for_load_state("domcontentloaded")

    @kernel_function(description="Clicks an element on the page identified by its unique numeric ID from the perception system")
    async def click(self, element_id: Annotated[int, "The numeric ID of the element to click"]):
        await self.ensure_initialized()
        print(f"[BrowserPlugin] Clicking element ID: {element_id}")
        
        # In a real system, we would map the ID back to a Playwright locator or x/y coordinates
        # preserved from the Perception phase. 
        # For this prototype, we'll assume a custom attribute 'data-agent-id' was injected 
        # or we simulate the finding logic.
        
        # Simulation: Attempt to select based on a hypothetical attribute that might have been added
        # or just fail gracefully if it's a mock.
        # selector = f"[data-agent-id='{element_id}']"
        
        # REALISTIC MOCK:
        # We don't have the 'Set-of-Marks' JS overlay running here to assign IDs to DOM elements yet.
        # So we will just log the action. In a full implementation, `perception_plugin` would 
        # inject JS that assigns these IDs, and `click` would use them.
        print(f" -> executed click on ID {element_id} (simulated)")
        # await self.page.click(selector) 

    @kernel_function(description="Types text into an input field. Supports secure placeholders like {{PASSWORD}}.")
    async def type_text(
        self, 
        element_id: Annotated[int, "The numeric ID of the input element"], 
        text: Annotated[str, "The text to type. Can include {{KEY}} for secrets."]
    ):
        await self.ensure_initialized()
        
        # SHADOW INJECTION LOGIC
        # 1. Parse for placeholders
        final_text = text
        placeholders = re.findall(r"\{\{([A-Z0-9_]+)\}\}", text)
        
        for placeholder in placeholders:
            secret_value = Config.get_secret(placeholder)
            if secret_value:
                print(f"[BrowserPlugin] Injecting secret for {{{{{placeholder}}}}}")
                final_text = final_text.replace(f"{{{{{placeholder}}}}}", secret_value)
            else:
                print(f"[BrowserPlugin] WARNING: Secret for {{{{{placeholder}}}}} not found!")

        print(f"[BrowserPlugin] Typing into ID {element_id}: '{final_text}'") # Be careful logging secrets in prod!
        
        # Execute Playwright action (simulated selector)
        # selector = f"[data-agent-id='{element_id}']"
        # await self.page.fill(selector, final_text)
        print(f" -> executed type on ID {element_id} (simulated)")

    @kernel_function(description="Gets the current page content for perception")
    async def get_raw_html(self) -> str:
        await self.ensure_initialized()
        return await self.page.content()
    
    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
