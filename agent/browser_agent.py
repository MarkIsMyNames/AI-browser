"""Browser Agent using Semantic Kernel for orchestration."""
import os
import asyncio
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.functions import KernelArguments

from agent.plugins.browser_plugin import BrowserPlugin
from agent.plugins.playwright_mcp_plugin import PlaywrightMCPPlugin


class BrowserAgent:
    """AI Agent that controls a web browser using Semantic Kernel."""

    def __init__(
        self,
        azure_endpoint: str,
        azure_api_key: str,
        deployment_name: str,
        api_version: str = "2024-02-15-preview",
        headless: bool = False,
        use_mcp: bool = False
    ):
        """Initialize the Browser Agent.

        Args:
            azure_endpoint: Azure OpenAI endpoint URL
            azure_api_key: Azure OpenAI API key
            deployment_name: Azure OpenAI deployment name
            api_version: Azure OpenAI API version
            headless: Whether to run browser in headless mode (only for non-MCP mode)
            use_mcp: Whether to use Playwright MCP server (recommended)
        """
        self.kernel = Kernel()
        self.use_mcp = use_mcp
        self.chat_history = ChatHistory()

        # Choose browser plugin based on mode
        if use_mcp:
            self.browser_plugin = PlaywrightMCPPlugin(headless=headless)
            plugin_name = "playwright_mcp"
            mode_desc = "headless" if headless else "headed (visible)"
            print(f"[Browser Agent] Using Playwright MCP Server (enhanced mode, {mode_desc})")
        else:
            self.browser_plugin = BrowserPlugin(headless=headless)
            plugin_name = "browser"
            mode_desc = "headless" if headless else "headed (visible)"
            print(f"[Browser Agent] Using direct Playwright integration (basic mode, {mode_desc})")

        # Add Azure OpenAI Chat Completion service
        self.kernel.add_service(
            AzureChatCompletion(
                service_id="chat_completion",
                endpoint=azure_endpoint,
                api_key=azure_api_key,
                deployment_name=deployment_name,
                api_version=api_version
            )
        )

        # Register the browser plugin
        self.kernel.add_plugin(
            self.browser_plugin,
            plugin_name=plugin_name
        )

        # System prompt for the agent (varies based on MCP usage)
        if use_mcp:
            self.system_prompt = """You are a browser automation agent powered by Playwright MCP. Your goal is to help users complete tasks on the web by controlling a browser.

You have access to comprehensive browser control functions:

Navigation & Page Management:
- browser_navigate: Navigate to a specific URL
- browser_navigate_back: Go back in browser history
- browser_tabs: List, create, close, or select browser tabs
- browser_close: Close the current page/tab

Page Inspection & Analysis:
- browser_snapshot: Get structured accessibility tree (best for understanding page structure)
- browser_take_screenshot: Take screenshots of page or specific elements
- browser_console_messages: Get all console messages
- browser_network_requests: Get all network requests since page load

User Interactions:
- browser_click: Click elements (supports CSS selectors and ARIA roles)
- browser_type: Type text into editable elements
- browser_fill_form: Fill multiple form fields at once
- browser_select_option: Select dropdown options
- browser_hover: Hover over elements
- browser_drag: Perform drag and drop operations
- browser_press_key: Press keyboard keys (Enter, Tab, Escape, etc.)
- browser_file_upload: Upload files to file inputs

Advanced Features:
- browser_evaluate: Execute JavaScript in browser context
- browser_run_code: Run Playwright code snippets directly
- browser_handle_dialog: Handle alerts, confirms, and prompts
- browser_resize: Resize the browser window
- browser_wait_for: Wait for text to appear/disappear or specific time
- browser_install: Install browser if not already installed
- browser_dismiss_cookie_consent: RECOMMENDED - Automatically detect and dismiss cookie consent banners

Strategy:
1. Always start by navigating to a relevant website
   - For web searches: ALWAYS use DuckDuckGo (https://duckduckgo.com) - it has no cookie consent dialogs
   - DuckDuckGo search URL format: https://duckduckgo.com/?q=your+search+query
   - Example: https://duckduckgo.com/?q=playwright+tutorial
2. Use browser_snapshot to understand page structure (more reliable than visual inspection)
3. Take actions step by step using ARIA roles and semantic selectors when possible
4. Use browser_take_screenshot if you need to visually inspect something
5. Use browser_console_messages or browser_network_requests for debugging
6. Continue until the user's goal is achieved

Cookie Consent Handling Tips:
- Google often shows "Before you continue to Google" with "Accept all" or "Reject all" buttons
- Bing/Microsoft shows cookie consent with "Accept" button
- DuckDuckGo typically doesn't have cookie consent dialogs

Fallback if browser_dismiss_cookie_consent doesn't work:
1. Use browser_snapshot to see the page structure
2. Look for buttons containing "Accept", "I agree", "Consent" in the snapshot
3. Use browser_click with a specific selector like: button#L2AGLb (Google's Accept All button)
4. Or use text-based clicking if you see the button text in the snapshot
5. If all else fails, try a different search engine (e.g., DuckDuckGo has no cookie dialogs)

The MCP server provides deterministic, structured access to the page. Prefer using ARIA roles and semantic selectors over generic CSS selectors.

Be methodical and explain what you're doing. If you encounter issues, describe them clearly.
If you need more information from the user, ask for it.
"""
        else:
            self.system_prompt = """You are a browser automation agent. Your goal is to help users complete tasks on the web by controlling a browser.

You have access to browser control functions:
- navigate_to_url: Navigate to a specific URL
- get_page_state: Get current page state (URL, title, buttons, links, inputs)
- get_page_content: Get text content from the page
- click_element: Click an element (by CSS selector or visible text)
- fill_input: Fill an input field (by CSS selector)
- type_text: Type text character by character
- press_key: Press a keyboard key (e.g., 'Enter')
- wait_for_navigation: Wait for page to load

Strategy:
1. Always start by navigating to a relevant website
   - For web searches: ALWAYS use DuckDuckGo (https://duckduckgo.com) - it has no cookie consent dialogs
   - DuckDuckGo search URL format: https://duckduckgo.com/?q=your+search+query
   - Example: https://duckduckgo.com/?q=playwright+tutorial
2. Use get_page_state to understand what's on the page
3. Take actions step by step (click, fill forms, etc.)
4. After each action, check the page state again
5. Continue until the user's goal is achieved

Be methodical and explain what you're doing. If you encounter issues, describe them clearly.
If you need more information from the user, ask for it.
"""

    async def run(self, user_goal: str, max_iterations: int = 15) -> str:
        """Run the agent to accomplish a user goal.

        Args:
            user_goal: The goal the user wants to accomplish
            max_iterations: Maximum number of agent iterations

        Returns:
            Final response from the agent
        """
        print(f"\n{'='*60}")
        print(f"Agent Goal: {user_goal}")
        print(f"{'='*60}\n")

        # Initialize chat history with system prompt
        self.chat_history.add_system_message(self.system_prompt)
        self.chat_history.add_user_message(user_goal)

        # Get the chat completion service
        chat_completion: ChatCompletionClientBase = self.kernel.get_service(
            service_id="chat_completion"
        )

        # Configure auto function calling
        execution_settings = chat_completion.get_prompt_execution_settings_class()(
            service_id="chat_completion"
        )
        execution_settings.function_choice_behavior = FunctionChoiceBehavior.Auto()

        iteration = 0
        try:
            while iteration < max_iterations:
                iteration += 1
                print(f"\n--- Iteration {iteration}/{max_iterations} ---")

                # Get response from LLM (with auto function calling)
                response = await chat_completion.get_chat_message_contents(
                    chat_history=self.chat_history,
                    settings=execution_settings,
                    kernel=self.kernel,
                    arguments=KernelArguments()
                )

                if not response:
                    print("No response from LLM")
                    break

                # Get the first response
                message = response[0]

                # Add assistant's response to chat history
                self.chat_history.add_assistant_message(str(message))

                # Print the agent's reasoning
                if message.content:
                    print(f"\n[Agent]: {message.content}")

                # Check if there were function calls
                if hasattr(message, 'function_call') and message.function_call:
                    print(f"[Function Call]: {message.function_call.name}")

                # Check if agent thinks it's done (no more function calls and has content)
                if message.content and "done" in message.content.lower():
                    print("\n[Agent indicates task completion]")
                    break

                # Small delay to make output readable
                await asyncio.sleep(0.5)

            print(f"\n{'='*60}")
            print("Agent execution completed")
            print(f"{'='*60}\n")

            return str(message.content) if message.content else "Task completed"

        except Exception as e:
            error_msg = f"Error during agent execution: {str(e)}"
            print(f"\n[ERROR]: {error_msg}")
            return error_msg

        finally:
            # Clean up browser resources
            await self.browser_plugin.cleanup()

    async def cleanup(self):
        """Clean up agent resources."""
        await self.browser_plugin.cleanup()


async def create_agent_from_env(headless: bool = None, use_mcp: bool = None) -> BrowserAgent:
    """Create a BrowserAgent from environment variables.

    Args:
        headless: Override headless mode setting (uses env var if None)
        use_mcp: Override MCP mode setting (uses env var if None)

    Returns:
        Configured BrowserAgent instance
    """
    # Load environment variables
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")

    # Validate required environment variables
    if not azure_endpoint:
        raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is required")
    if not azure_api_key:
        raise ValueError("AZURE_OPENAI_API_KEY environment variable is required")
    if not deployment_name:
        raise ValueError("AZURE_OPENAI_DEPLOYMENT_NAME environment variable is required")

    # Get headless mode from env if not specified
    if headless is None:
        headless = os.getenv("HEADLESS_MODE", "false").lower() == "true"

    # Get MCP mode from env if not specified
    if use_mcp is None:
        use_mcp = os.getenv("USE_MCP", "false").lower() == "true"

    return BrowserAgent(
        azure_endpoint=azure_endpoint,
        azure_api_key=azure_api_key,
        deployment_name=deployment_name,
        api_version=api_version,
        headless=headless,
        use_mcp=use_mcp
    )
