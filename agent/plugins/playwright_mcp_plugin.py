"""Playwright MCP Plugin for Semantic Kernel."""
import json
from typing import Annotated, Any, Dict, List, Optional
from semantic_kernel.functions import kernel_function
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class PlaywrightMCPPlugin:
    """Plugin that provides browser automation via Playwright MCP server."""

    def __init__(self):
        """Initialize the Playwright MCP plugin."""
        self.session: Optional[ClientSession] = None
        self.read_stream = None
        self.write_stream = None
        self._stdio_context = None
        self._initialized = False
        self._available_tools: List[Dict[str, Any]] = []

    async def initialize(self):
        """Initialize connection to Playwright MCP server."""
        if not self._initialized:
            # Start the MCP server as a subprocess
            # Use firefox (or change to "chromium" or "webkit" as preferred)
            # Omitting --headless flag makes the browser visible (headed mode)
            server_params = StdioServerParameters(
                command="npx",
                args=["-y", "@playwright/mcp@latest", "--browser", "firefox"],
                env=None
            )

            # Create stdio client connection (it's a context manager)
            self._stdio_context = stdio_client(server_params)
            self.read_stream, self.write_stream = await self._stdio_context.__aenter__()
            self.session = ClientSession(self.read_stream, self.write_stream)

            # Initialize the session
            await self.session.__aenter__()

            # Initialize the connection
            await self.session.initialize()

            # Get available tools from the server
            tools_response = await self.session.list_tools()
            self._available_tools = tools_response.tools if hasattr(tools_response, 'tools') else []

            print(f"[MCP] Connected to Playwright MCP server with {len(self._available_tools)} tools")
            self._initialized = True

    async def cleanup(self):
        """Clean up MCP server connection."""
        if self.session:
            try:
                await self.session.__aexit__(None, None, None)
            except Exception as e:
                print(f"[MCP] Error closing session: {e}")

        if self._stdio_context:
            try:
                await self._stdio_context.__aexit__(None, None, None)
            except Exception as e:
                print(f"[MCP] Error closing stdio context: {e}")

        self._initialized = False

    async def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool

        Returns:
            The result from the tool as a string
        """
        await self.initialize()

        try:
            result = await self.session.call_tool(tool_name, arguments=arguments)

            # Extract content from result
            if hasattr(result, 'content') and result.content:
                content_parts = []
                for item in result.content:
                    if hasattr(item, 'text'):
                        content_parts.append(item.text)
                    elif hasattr(item, 'data'):
                        content_parts.append(str(item.data))
                return "\n".join(content_parts) if content_parts else "Success"

            return str(result)
        except Exception as e:
            return f"Error calling {tool_name}: {str(e)}"

    @kernel_function(
        name="browser_navigate",
        description="Navigate to a URL in the browser"
    )
    async def navigate(
        self,
        url: Annotated[str, "The URL to navigate to"]
    ) -> Annotated[str, "The result of the navigation"]:
        """Navigate to a URL."""
        return await self._call_tool("browser_navigate", {"url": url})

    @kernel_function(
        name="browser_take_screenshot",
        description="Take a screenshot of the current page or a specific element"
    )
    async def screenshot(
        self,
        name: Annotated[str, "Name for the screenshot"],
        selector: Annotated[str, "CSS selector for element to screenshot (optional, leave empty for full page)"] = "",
        width: Annotated[int, "Screenshot width"] = 800,
        height: Annotated[int, "Screenshot height"] = 600
    ) -> Annotated[str, "The result of taking the screenshot"]:
        """Take a screenshot."""
        args = {"name": name, "width": width, "height": height}
        if selector:
            args["selector"] = selector
        return await self._call_tool("browser_take_screenshot", args)

    @kernel_function(
        name="browser_click",
        description="Click on an element on the page"
    )
    async def click(
        self,
        selector: Annotated[str, "CSS selector or ARIA role of the element to click"]
    ) -> Annotated[str, "The result of the click action"]:
        """Click an element."""
        return await self._call_tool("browser_click", {"selector": selector})

    @kernel_function(
        name="browser_type",
        description="Type text into an editable element"
    )
    async def type_text(
        self,
        selector: Annotated[str, "CSS selector or ARIA role of the input field"],
        text: Annotated[str, "The text to type"]
    ) -> Annotated[str, "The result of the type action"]:
        """Type text into a field."""
        return await self._call_tool("browser_type", {"selector": selector, "text": text})

    @kernel_function(
        name="browser_fill_form",
        description="Fill multiple form fields at once"
    )
    async def fill_form(
        self,
        fields: Annotated[str, "JSON object mapping selectors to values, e.g. {'#email': 'test@example.com', '#password': 'pass123'}"]
    ) -> Annotated[str, "The result of filling the form"]:
        """Fill multiple form fields."""
        import json
        try:
            fields_dict = json.loads(fields) if isinstance(fields, str) else fields
            return await self._call_tool("browser_fill_form", {"fields": fields_dict})
        except json.JSONDecodeError as e:
            return f"Error parsing fields JSON: {str(e)}"

    @kernel_function(
        name="browser_select_option",
        description="Select an option from a dropdown"
    )
    async def select(
        self,
        selector: Annotated[str, "CSS selector for the select element"],
        value: Annotated[str, "The value to select"]
    ) -> Annotated[str, "The result of the select action"]:
        """Select a dropdown option."""
        return await self._call_tool("browser_select_option", {"selector": selector, "value": value})

    @kernel_function(
        name="browser_hover",
        description="Hover over an element"
    )
    async def hover(
        self,
        selector: Annotated[str, "CSS selector or ARIA role of the element to hover over"]
    ) -> Annotated[str, "The result of the hover action"]:
        """Hover over an element."""
        return await self._call_tool("browser_hover", {"selector": selector})

    @kernel_function(
        name="browser_evaluate",
        description="Execute JavaScript code in the browser context"
    )
    async def evaluate(
        self,
        script: Annotated[str, "JavaScript code to execute"]
    ) -> Annotated[str, "The result of the JavaScript execution"]:
        """Execute JavaScript."""
        return await self._call_tool("browser_evaluate", {"expression": script})

    @kernel_function(
        name="browser_snapshot",
        description="Get the accessibility tree snapshot of the current page (structured DOM information)"
    )
    async def get_snapshot(self) -> Annotated[str, "The accessibility tree snapshot"]:
        """Get accessibility snapshot of the page."""
        return await self._call_tool("browser_snapshot", {})

    @kernel_function(
        name="browser_close",
        description="Close the current browser page/tab"
    )
    async def close(self) -> Annotated[str, "The result of closing the page"]:
        """Close the browser page."""
        return await self._call_tool("browser_close", {})

    @kernel_function(
        name="browser_resize",
        description="Resize the browser window to specified dimensions"
    )
    async def resize(
        self,
        width: Annotated[int, "Window width in pixels"],
        height: Annotated[int, "Window height in pixels"]
    ) -> Annotated[str, "The result of resizing the browser"]:
        """Resize the browser window."""
        return await self._call_tool("browser_resize", {"width": width, "height": height})

    @kernel_function(
        name="browser_console_messages",
        description="Get all console messages from the browser"
    )
    async def console_messages(self) -> Annotated[str, "All console messages"]:
        """Get console messages."""
        return await self._call_tool("browser_console_messages", {})

    @kernel_function(
        name="browser_handle_dialog",
        description="Handle a browser dialog (alert, confirm, prompt)"
    )
    async def handle_dialog(
        self,
        action: Annotated[str, "Action to take: 'accept' or 'dismiss'"],
        prompt_text: Annotated[str, "Text to enter in prompt dialog (optional)"] = ""
    ) -> Annotated[str, "The result of handling the dialog"]:
        """Handle a browser dialog."""
        args = {"action": action}
        if prompt_text:
            args["promptText"] = prompt_text
        return await self._call_tool("browser_handle_dialog", args)

    @kernel_function(
        name="browser_file_upload",
        description="Upload one or multiple files to a file input"
    )
    async def file_upload(
        self,
        selector: Annotated[str, "CSS selector for the file input element"],
        file_paths: Annotated[str, "Comma-separated list of file paths to upload"]
    ) -> Annotated[str, "The result of the file upload"]:
        """Upload files to a file input."""
        paths = [p.strip() for p in file_paths.split(",")]
        return await self._call_tool("browser_file_upload", {"selector": selector, "filePaths": paths})

    @kernel_function(
        name="browser_press_key",
        description="Press a keyboard key"
    )
    async def press_key(
        self,
        key: Annotated[str, "The key to press (e.g., 'Enter', 'Escape', 'Tab', 'ArrowDown')"]
    ) -> Annotated[str, "The result of pressing the key"]:
        """Press a keyboard key."""
        return await self._call_tool("browser_press_key", {"key": key})

    @kernel_function(
        name="browser_navigate_back",
        description="Navigate back to the previous page in browser history"
    )
    async def navigate_back(self) -> Annotated[str, "The result of navigating back"]:
        """Navigate back in browser history."""
        return await self._call_tool("browser_navigate_back", {})

    @kernel_function(
        name="browser_network_requests",
        description="Get all network requests made since page load"
    )
    async def network_requests(self) -> Annotated[str, "All network requests"]:
        """Get network requests."""
        return await self._call_tool("browser_network_requests", {})

    @kernel_function(
        name="browser_run_code",
        description="Run a Playwright code snippet directly"
    )
    async def run_code(
        self,
        code: Annotated[str, "Playwright code snippet to execute"]
    ) -> Annotated[str, "The result of running the code"]:
        """Run Playwright code snippet."""
        return await self._call_tool("browser_run_code", {"code": code})

    @kernel_function(
        name="browser_drag",
        description="Perform drag and drop operation between two elements"
    )
    async def drag(
        self,
        source: Annotated[str, "CSS selector of the element to drag"],
        target: Annotated[str, "CSS selector of the drop target"]
    ) -> Annotated[str, "The result of the drag operation"]:
        """Drag and drop an element."""
        return await self._call_tool("browser_drag", {"source": source, "target": target})

    @kernel_function(
        name="browser_tabs",
        description="Manage browser tabs (list, create, close, or select)"
    )
    async def tabs(
        self,
        action: Annotated[str, "Action to perform: 'list', 'create', 'close', or 'select'"],
        tab_id: Annotated[str, "Tab ID for close or select actions (optional)"] = ""
    ) -> Annotated[str, "The result of the tabs operation"]:
        """Manage browser tabs."""
        args = {"action": action}
        if tab_id:
            args["tabId"] = tab_id
        return await self._call_tool("browser_tabs", args)

    @kernel_function(
        name="browser_wait_for",
        description="Wait for text to appear, disappear, or for a specified time"
    )
    async def wait_for(
        self,
        condition: Annotated[str, "What to wait for: 'text_appear', 'text_disappear', or 'time'"],
        text: Annotated[str, "Text to wait for (if condition is text_appear or text_disappear)"] = "",
        timeout: Annotated[int, "Timeout in milliseconds"] = 5000
    ) -> Annotated[str, "The result of the wait operation"]:
        """Wait for a condition."""
        args = {"condition": condition, "timeout": timeout}
        if text:
            args["text"] = text
        return await self._call_tool("browser_wait_for", args)

    @kernel_function(
        name="browser_install",
        description="Install the browser specified in config (call if browser not installed error occurs)"
    )
    async def install_browser(self) -> Annotated[str, "The result of installing the browser"]:
        """Install the browser."""
        return await self._call_tool("browser_install", {})

    @kernel_function(
        name="browser_dismiss_cookie_consent",
        description="Automatically detect and dismiss common cookie consent banners by clicking Accept/Agree buttons. Works with Google, Bing, and most cookie dialogs."
    )
    async def dismiss_cookie_consent(self) -> Annotated[str, "The result of dismissing cookie consent"]:
        """Automatically dismiss cookie consent banners using Playwright selectors and JavaScript."""

        # Strategy 1: Try browser_click with Playwright text selectors
        text_selectors = [
            "text=Accept all",
            "text=I agree",
            "text=Accept",
            "text=Agree",
            "text=Continue",
            "text=OK"
        ]

        for selector in text_selectors:
            try:
                result = await self._call_tool("browser_click", {"selector": selector})
                if result and "error" not in result.lower() and "not found" not in result.lower():
                    print(f"[DEBUG] Successfully clicked with selector: {selector}")
                    return f"Clicked cookie consent button with: {selector}"
            except Exception as e:
                print(f"[DEBUG] Failed clicking {selector}: {str(e)}")
                continue

        # Strategy 2: Try ID-based selectors (Google-specific)
        id_selectors = [
            'button[id="L2AGLb"]',  # Google "Accept all" button
            '#W0wltc',  # Google "Reject all" button alternative
            'form[action*="consent"] button'
        ]

        for selector in id_selectors:
            try:
                result = await self._call_tool("browser_click", {"selector": selector})
                if result and "error" not in result.lower() and "not found" not in result.lower():
                    print(f"[DEBUG] Successfully clicked with selector: {selector}")
                    return f"Clicked cookie consent button with ID selector"
            except Exception as e:
                print(f"[DEBUG] Failed clicking {selector}: {str(e)}")
                continue

        # Strategy 3: JavaScript fallback with VALID DOM methods
        print("[DEBUG] Text and ID selectors failed, trying JavaScript fallback")
        javascript_fallback = """
        (function() {
            // Common button text patterns (case-insensitive)
            const acceptPatterns = [
                'accept all', 'accept cookies', 'accept',
                'agree', 'i agree', 'consent',
                'allow all', 'continue', 'got it', 'ok'
            ];

            // Search all buttons
            const buttons = Array.from(document.querySelectorAll('button, a[role="button"], div[role="button"], input[type="button"]'));

            for (const button of buttons) {
                const text = (button.textContent || button.innerText || '').toLowerCase().trim();
                const ariaLabel = (button.getAttribute('aria-label') || '').toLowerCase();
                const value = (button.getAttribute('value') || '').toLowerCase();
                const combinedText = text + ' ' + ariaLabel + ' ' + value;

                for (const pattern of acceptPatterns) {
                    if (combinedText.includes(pattern)) {
                        // Check if visible
                        const rect = button.getBoundingClientRect();
                        const style = window.getComputedStyle(button);
                        const isVisible = rect.width > 0 && rect.height > 0 &&
                                        style.visibility !== 'hidden' &&
                                        style.display !== 'none' &&
                                        style.opacity !== '0';

                        if (isVisible) {
                            button.click();
                            return `Clicked cookie consent: "${text.substring(0, 50)}"`;
                        }
                    }
                }
            }

            return 'No visible cookie consent button found';
        })();
        """

        result = await self._call_tool("browser_evaluate", {"expression": javascript_fallback})
        print(f"[DEBUG] JavaScript fallback result: {result}")
        return result
