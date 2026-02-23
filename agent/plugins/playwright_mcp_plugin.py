"""Playwright MCP Plugin for Semantic Kernel."""
import asyncio
import json
import os
import time
from typing import Annotated, Any, Dict, List, Optional
from semantic_kernel.functions import kernel_function
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PLAYWRIGHT_MCP_VERSION = os.environ.get("PLAYWRIGHT_MCP_VERSION", "0.0.68")


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
        self.task_completed = False
        self.task_summary = ""
        self.help_requested = False
        self.help_question = ""

    async def initialize(self):
        """Initialize connection to Playwright MCP server."""
        if not self._initialized:
            t_start = time.monotonic()

            # Build args based on headless mode
            # Use chromium (faster startup than firefox)
            mcp_args = ["-y", f"@playwright/mcp@{PLAYWRIGHT_MCP_VERSION}", "--browser", "chromium"]
            if self.headless:
                mcp_args.append("--headless")

            # Add environment variables to ensure display works
            env = os.environ.copy()
            if 'DISPLAY' not in env:
                env['DISPLAY'] = ':0'

            server_params = StdioServerParameters(
                command="npx",
                args=mcp_args,
                env=env
            )

            # Step 1: spawn npx subprocess + stdio handshake
            print("[MCP] Starting MCP server via npx...")
            t1 = time.monotonic()
            self._stdio_context = stdio_client(server_params)
            self.read_stream, self.write_stream = await self._stdio_context.__aenter__()
            print(f"[MCP] stdio ready ({time.monotonic() - t1:.1f}s)")

            # Step 2: MCP session init
            t2 = time.monotonic()
            self.session = ClientSession(self.read_stream, self.write_stream)
            await self.session.__aenter__()
            await self.session.initialize()
            print(f"[MCP] Session initialised ({time.monotonic() - t2:.1f}s)")

            # Step 3: list tools
            t3 = time.monotonic()
            tools_response = await self.session.list_tools()
            self._available_tools = tools_response.tools if hasattr(tools_response, 'tools') else []
            print(f"[MCP] Tools listed ({time.monotonic() - t3:.1f}s)")

            print(f"[MCP] Connected — {len(self._available_tools)} tools available  (total init: {time.monotonic() - t_start:.1f}s)")
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
            try:
                result = await asyncio.wait_for(
                    self.session.call_tool(tool_name, arguments=arguments),
                    timeout=60.0
                )
            except asyncio.TimeoutError:
                return f"Error calling {tool_name}: timed out after 60 seconds"

            # Extract content from result
            if hasattr(result, 'content') and result.content:
                content_parts = []
                for item in result.content:
                    if hasattr(item, 'text'):
                        content_parts.append(item.text)
                    elif hasattr(item, 'data'):
                        content_parts.append(str(item.data))

                output = "\n".join(content_parts) if content_parts else "Success"

                return output

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
        description='Fill form fields by label. Pass a JSON object mapping visible field labels to values, e.g. {"Email": "john@example.com", "First Name": "John"}. Do NOT include refs — they are resolved automatically.'
    )
    async def fill_form(
        self,
        fields: Annotated[str, 'JSON string of field labels to values. MUST be a JSON string, not an object. Example: \'{"Email": "john@example.com", "First Name": "John"}\'']
    ) -> str:
        """Fill form fields using a three-level fallback strategy to resolve labels to refs."""
        import re, json
        if isinstance(fields, dict):
            fields_dict = fields
        elif isinstance(fields, str):
            try:
                fields_dict = json.loads(fields)
            except json.JSONDecodeError as e:
                return f"Error parsing fields JSON: {str(e)}"
        else:
            return f"Unexpected fields type: {type(fields)}"

        snapshot = await self._call_tool("browser_snapshot", {})
        ref_map = {}

        # Level 1: inputs that already carry their label in the snapshot
        # e.g. textbox "Email address" [ref=e14]  (proper <label>, aria-label, or placeholder)
        for kind, label, ref in re.findall(
            r'(textbox|combobox|select) "([^"]+)" \[ref=(\w+)\]', snapshot
        ):
            ref_map[label.strip().lower()] = (ref, kind)

        # Level 2: sibling generic label pattern (div-wrapped custom labels, no HTML association)
        # e.g.  - generic: "Email"\n  - textbox [ref=e14]
        for label, kind, ref in re.findall(
            r'- generic \[ref=\w+\]: ([^\n\[]+)\n\s+- (textbox|combobox|select) \[ref=(\w+)\]',
            snapshot
        ):
            key = label.strip().lower()
            if key not in ref_map:
                ref_map[key] = (ref, kind)

        def find_ref(label):
            """Exact then fuzzy lookup against ref_map."""
            key = label.lower().strip()
            if key in ref_map:
                return ref_map[key]
            for snap_label, entry in ref_map.items():
                if key in snap_label or snap_label in key:
                    return entry
            return None

        resolved, js_fallback = [], {}
        for label, value in fields_dict.items():
            match = find_ref(label)
            if match:
                ref, kind = match
                resolved.append({"name": label, "type": kind, "ref": ref, "value": value})
            else:
                js_fallback[label] = value

        results = []

        # Fill all snapshot-resolved fields in one MCP call
        if resolved:
            results.append(await self._call_tool("browser_fill_form", {"fields": resolved}))

        # Level 3: JS DOM search for anything the snapshot couldn't resolve
        # Tries name/id attribute, input type, placeholder, then nearest text node
        for label, value in js_fallback.items():
            js = """(args) => {
                const label = args.label.toLowerCase();
                const value = args.value;

                function fill(el) {
                    if (!el || el.disabled || el.readOnly) return false;
                    if (el.tagName === 'SELECT') {
                        const opt = Array.from(el.options).find(o =>
                            o.text.toLowerCase().includes(value.toLowerCase()) ||
                            o.value.toLowerCase() === value.toLowerCase()
                        );
                        el.value = opt ? opt.value : value;
                    } else {
                        el.value = value;
                    }
                    el.dispatchEvent(new Event('input', {bubbles: true}));
                    el.dispatchEvent(new Event('change', {bubbles: true}));
                    return true;
                }

                const inputs = Array.from(document.querySelectorAll('input, select, textarea'));

                // name / id attribute
                for (const el of inputs) {
                    const attr = ((el.name || '') + ' ' + (el.id || '')).toLowerCase().replace(/[_\\-]/g, ' ');
                    if (attr.includes(label) && fill(el)) return 'filled via name/id: ' + (el.name || el.id);
                }
                // placeholder
                for (const el of inputs) {
                    if ((el.placeholder || '').toLowerCase().includes(label) && fill(el))
                        return 'filled via placeholder: ' + el.placeholder;
                }
                // input type (e.g. label="email" → type="email")
                for (const el of inputs) {
                    if ((el.type || '').toLowerCase() === label && fill(el))
                        return 'filled via input type: ' + el.type;
                }
                // nearest visible text node in parent chain
                for (const el of inputs) {
                    let node = el.parentElement;
                    for (let i = 0; i < 3 && node; i++, node = node.parentElement) {
                        if (node.textContent.toLowerCase().includes(label) && fill(el))
                            return 'filled via nearby text for: ' + args.label;
                    }
                }
                return 'not found: ' + args.label;
            }"""
            result = await self._call_tool(
                "browser_evaluate", {"function": js, "arg": {"label": label, "value": value}}
            )
            results.append(f"[JS fallback] {label}: {result}")

        return "\n".join(results) if results else "No fields filled"

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
        return await self._call_tool("browser_evaluate", {"function": script})

    @kernel_function(
        name="browser_snapshot",
        description="Get page accessibility tree"
    )
    async def get_snapshot(self) -> str:
        """Get accessibility snapshot of the page, with a form field summary appended."""
        import re
        result = await self._call_tool("browser_snapshot", {})

        # Labels on some pages are sibling generic elements rather than being
        # part of the textbox/combobox accessible name. Parse the tree to build
        # a clean "Label → ref" table so the LLM doesn't have to infer it.
        pattern = r'- generic \[ref=\w+\]: ([^\n\[]+)\n\s+- (textbox|combobox|select) \[ref=(\w+)\]'
        matches = re.findall(pattern, result)
        if matches:
            lines = [f'  "{label.strip()}" → ref={ref} ({kind})'
                     for label, kind, ref in matches]
            result += (
                "\n\n### Form Fields (use these refs with browser_type / browser_select_option)\n"
                + "\n".join(lines) + "\n"
            )

        return result

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

        # JavaScript fallback with VALID DOM methods
        print("[DEBUG] Attempting JavaScript cookie consent dismissal")
        javascript_fallback = """() => {
            const acceptPatterns = [
                'accept all', 'accept cookies', 'accept',
                'agree', 'i agree', 'consent',
                'allow all', 'continue', 'got it', 'ok'
            ];

            const buttons = Array.from(document.querySelectorAll('button, a[role="button"], div[role="button"], input[type="button"]'));

            for (const button of buttons) {
                const text = (button.textContent || button.innerText || '').toLowerCase().trim();
                const ariaLabel = (button.getAttribute('aria-label') || '').toLowerCase();
                const value = (button.getAttribute('value') || '').toLowerCase();
                const combinedText = text + ' ' + ariaLabel + ' ' + value;

                for (const pattern of acceptPatterns) {
                    if (combinedText.includes(pattern)) {
                        const rect = button.getBoundingClientRect();
                        const style = window.getComputedStyle(button);
                        const isVisible = rect.width > 0 && rect.height > 0 &&
                                        style.visibility !== 'hidden' &&
                                        style.display !== 'none' &&
                                        style.opacity !== '0';

                        if (isVisible) {
                            button.click();
                            return 'Clicked cookie consent: "' + text.substring(0, 50) + '"';
                        }
                    }
                }
            }

            return 'No visible cookie consent button found';
        }"""

        result = await self._call_tool("browser_evaluate", {"function": javascript_fallback})
        print(f"[DEBUG] JavaScript fallback result: {result}")
        return result

    @kernel_function(
        name="request_help",
        description="Request input from the user when you are genuinely stuck and cannot proceed autonomously. Only call this after you have already tried multiple approaches and exhausted your options. Describe exactly what is blocking you."
    )
    async def request_help(
        self,
        question: Annotated[str, "A clear description of what is blocking you and what you need from the user to continue"]
    ) -> str:
        """Pause execution and request user input for a genuine blocker."""
        self.help_requested = True
        self.help_question = question
        return "Help request recorded. Waiting for user input."

    @kernel_function(
        name="task_complete",
        description="Signal that the task is fully complete. Call this ONLY when you have gathered ALL required information and are ready to present a final answer to the user."
    )
    async def task_complete(
        self,
        summary: Annotated[str, "The complete final answer to present to the user, including all gathered information"]
    ) -> str:
        """Signal task completion with a final summary."""
        self.task_completed = True
        self.task_summary = summary
        return "Task marked as complete. Summary recorded."
