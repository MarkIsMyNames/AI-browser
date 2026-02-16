"""Playwright MCP Plugin for Semantic Kernel."""
import json
from typing import Annotated, Any, Dict, List, Optional
from semantic_kernel.functions import kernel_function
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class PlaywrightMCPPlugin:
    """Plugin that provides browser automation via Playwright MCP server."""

    def __init__(self, headless: bool = False):
        """Initialize the Playwright MCP plugin.

        Args:
            headless: Whether to run browser in headless mode (default: False = visible browser)
        """
        self.session: Optional[ClientSession] = None
        self.read_stream = None
        self.write_stream = None
        self._stdio_context = None
        self._initialized = False
        self._available_tools: List[Dict[str, Any]] = []
        self.headless = headless

    async def initialize(self):
        """Initialize connection to Playwright MCP server."""
        if not self._initialized:
            # Start the MCP server as a subprocess
            # Use firefox (or change to "chromium" or "webkit" as preferred)
            # Build args based on headless mode
            mcp_args = ["-y", "@playwright/mcp@latest", "--browser", "firefox"]
            # MCP defaults to headed (visible browser), only add --headless flag if requested
            if self.headless:
                mcp_args.append("--headless")

            # Add environment variables to ensure display works
            import os
            env = os.environ.copy()
            # Ensure DISPLAY is set for X11
            if 'DISPLAY' not in env:
                env['DISPLAY'] = ':0'

            server_params = StdioServerParameters(
                command="npx",
                args=mcp_args,
                env=env
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
            error_msg = f"Error calling {tool_name}: {str(e)}"
            return error_msg

    @kernel_function(
        name="browser_navigate",
        description="Navigate to URL"
    )
    async def navigate(
        self,
        url: Annotated[str, "URL"]
    ) -> str:
        """Navigate to a URL."""
        return await self._call_tool("browser_navigate", {"url": url})

    @kernel_function(
        name="browser_take_screenshot",
        description="Take screenshot"
    )
    async def screenshot(
        self,
        name: Annotated[str, "Name"],
        selector: Annotated[str, "Selector (optional)"] = "",
        width: Annotated[int, "Width"] = 800,
        height: Annotated[int, "Height"] = 600
    ) -> str:
        """Take a screenshot."""
        args = {"name": name, "width": width, "height": height}
        if selector:
            args["selector"] = selector
        return await self._call_tool("browser_take_screenshot", args)

    @kernel_function(
        name="browser_click",
        description="Click element by ref"
    )
    async def click(
        self,
        ref: Annotated[str, "Element ref from snapshot"],
        element: Annotated[str, "Element description"] = ""
    ) -> str:
        """Click an element using its ref from browser_snapshot."""
        args = {"ref": ref}
        if element:
            args["element"] = element
        return await self._call_tool("browser_click", args)

    @kernel_function(
        name="browser_type",
        description="Type text"
    )
    async def type_text(
        self,
        ref: Annotated[str, "Element ref from snapshot"],
        text: Annotated[str, "Text to type"],
        element: Annotated[str, "Element description"] = ""
    ) -> str:
        """Type text into a field using its ref from browser_snapshot."""
        args = {"ref": ref, "text": text}
        if element:
            args["element"] = element
        return await self._call_tool("browser_type", args)

    @kernel_function(
        name="browser_fill_form",
        description="Fill form fields"
    )
    async def fill_form(
        self,
        fields: Annotated[str, "JSON selector map"]
    ) -> str:
        """Fill multiple form fields."""
        import json
        try:
            fields_dict = json.loads(fields) if isinstance(fields, str) else fields
            return await self._call_tool("browser_fill_form", {"fields": fields_dict})
        except json.JSONDecodeError as e:
            return f"Error parsing fields JSON: {str(e)}"

    @kernel_function(
        name="browser_select_option",
        description="Select dropdown option"
    )
    async def select(
        self,
        ref: Annotated[str, "Element ref from snapshot"],
        values: Annotated[str, "Values to select"],
        element: Annotated[str, "Element description"] = ""
    ) -> str:
        """Select dropdown options using ref from browser_snapshot."""
        args = {"ref": ref, "values": [values]}  # MCP expects array
        if element:
            args["element"] = element
        return await self._call_tool("browser_select_option", args)

    @kernel_function(
        name="browser_hover",
        description="Hover over element"
    )
    async def hover(
        self,
        ref: Annotated[str, "Element ref from snapshot"],
        element: Annotated[str, "Element description"] = ""
    ) -> str:
        """Hover over an element using its ref from browser_snapshot."""
        args = {"ref": ref}
        if element:
            args["element"] = element
        return await self._call_tool("browser_hover", args)

    @kernel_function(
        name="browser_evaluate",
        description="Execute JavaScript"
    )
    async def evaluate(
        self,
        script: Annotated[str, "JS code"]
    ) -> str:
        """Execute JavaScript."""
        return await self._call_tool("browser_evaluate", {"expression": script})

    @kernel_function(
        name="browser_snapshot",
        description="Get page accessibility tree"
    )
    async def get_snapshot(self) -> str:
        """Get accessibility snapshot of the page."""
        return await self._call_tool("browser_snapshot", {})

    @kernel_function(
        name="browser_close",
        description="Close page"
    )
    async def close(self) -> str:
        """Close the browser page."""
        return await self._call_tool("browser_close", {})

    @kernel_function(
        name="browser_resize",
        description="Resize window"
    )
    async def resize(
        self,
        width: Annotated[int, "Width px"],
        height: Annotated[int, "Height px"]
    ) -> str:
        """Resize the browser window."""
        return await self._call_tool("browser_resize", {"width": width, "height": height})

    @kernel_function(
        name="browser_console_messages",
        description="Get console messages"
    )
    async def console_messages(self) -> str:
        """Get console messages."""
        return await self._call_tool("browser_console_messages", {})

    @kernel_function(
        name="browser_handle_dialog",
        description="Handle dialog"
    )
    async def handle_dialog(
        self,
        action: Annotated[str, "accept/dismiss"],
        prompt_text: Annotated[str, "Text (optional)"] = ""
    ) -> str:
        """Handle a browser dialog."""
        args = {"action": action}
        if prompt_text:
            args["promptText"] = prompt_text
        return await self._call_tool("browser_handle_dialog", args)

    @kernel_function(
        name="browser_file_upload",
        description="Upload files"
    )
    async def file_upload(
        self,
        selector: Annotated[str, "Selector"],
        file_paths: Annotated[str, "Paths (comma-sep)"]
    ) -> str:
        """Upload files to a file input."""
        paths = [p.strip() for p in file_paths.split(",")]
        return await self._call_tool("browser_file_upload", {"selector": selector, "filePaths": paths})

    @kernel_function(
        name="browser_press_key",
        description="Press key"
    )
    async def press_key(
        self,
        key: Annotated[str, "Key name"]
    ) -> str:
        """Press a keyboard key."""
        return await self._call_tool("browser_press_key", {"key": key})

    @kernel_function(
        name="browser_navigate_back",
        description="Navigate back"
    )
    async def navigate_back(self) -> str:
        """Navigate back in browser history."""
        return await self._call_tool("browser_navigate_back", {})

    @kernel_function(
        name="browser_network_requests",
        description="Get network requests"
    )
    async def network_requests(self) -> str:
        """Get network requests."""
        return await self._call_tool("browser_network_requests", {})

    @kernel_function(
        name="browser_run_code",
        description="Run Playwright code"
    )
    async def run_code(
        self,
        code: Annotated[str, "Code snippet"]
    ) -> str:
        """Run Playwright code snippet."""
        return await self._call_tool("browser_run_code", {"code": code})

    @kernel_function(
        name="browser_drag",
        description="Drag and drop"
    )
    async def drag(
        self,
        source: Annotated[str, "Source selector"],
        target: Annotated[str, "Target selector"]
    ) -> str:
        """Drag and drop an element."""
        return await self._call_tool("browser_drag", {"source": source, "target": target})

    @kernel_function(
        name="browser_tabs",
        description="Manage tabs"
    )
    async def tabs(
        self,
        action: Annotated[str, "list/create/close/select"],
        tab_id: Annotated[str, "Tab ID (optional)"] = ""
    ) -> str:
        """Manage browser tabs."""
        args = {"action": action}
        if tab_id:
            args["tabId"] = tab_id
        return await self._call_tool("browser_tabs", args)

    @kernel_function(
        name="browser_wait_for",
        description="Wait for condition"
    )
    async def wait_for(
        self,
        condition: Annotated[str, "Condition type"],
        text: Annotated[str, "Text (optional)"] = "",
        timeout: Annotated[int, "Timeout ms"] = 5000
    ) -> str:
        """Wait for a condition."""
        args = {"condition": condition, "timeout": timeout}
        if text:
            args["text"] = text
        return await self._call_tool("browser_wait_for", args)

    @kernel_function(
        name="browser_install",
        description="Install browser"
    )
    async def install_browser(self) -> str:
        """Install the browser."""
        return await self._call_tool("browser_install", {})

    @kernel_function(
        name="browser_dismiss_cookie_consent",
        description="Dismiss cookie consent"
    )
    async def dismiss_cookie_consent(self) -> str:
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
