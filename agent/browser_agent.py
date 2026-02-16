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
            self.system_prompt = """You are a browser automation agent. Help users complete web tasks by controlling a browser.

CRITICAL - Snapshot Workflow:
- ALWAYS call browser_snapshot BEFORE interacting with ANY elements
- ALWAYS call browser_snapshot AGAIN after navigation/page changes
- Refs (e45, e123, etc.) are only valid for the current snapshot
- Refs become INVALID after navigating to a new page

How to use snapshots:
1. Navigate: browser_navigate(url="...")
2. Snapshot: browser_snapshot() → Returns elements like: link "Home" [ref=e7]
3. Extract ref: Find the element you need and note its ref (e.g., e7)
4. Interact: browser_click(ref="e7", element="Home link")
5. After any navigation/click that changes the page → GO BACK TO STEP 2

Example workflow:
- Navigate to search page → snapshot → click result link (ref=e45)
- NEW PAGE LOADED → snapshot again → click button (ref=e12 from new snapshot)
- ANOTHER PAGE → snapshot again → etc.

Never reuse refs from an old snapshot after the page has changed!

Strategy:
1. Navigate to DuckDuckGo: https://duckduckgo.com/?q=query
2. Get snapshot, find link, click using ref
3. After navigation: Get NEW snapshot for new page
4. Continue until goal achieved

Be methodical and explain your actions."""
        else:
            self.system_prompt = """You are a browser automation agent. Help users complete web tasks by controlling a browser.

Strategy:
1. Navigate to relevant sites (for searches use DuckDuckGo: https://duckduckgo.com/?q=query)
2. Use get_page_state to understand page structure
3. Take actions step by step (click, fill forms, etc.)
4. Continue until goal achieved

Be methodical and explain your actions."""

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

                # Check if there were any function calls in this iteration
                has_function_calls = False
                if hasattr(message, 'items') and message.items:
                    for item in message.items:
                        if hasattr(item, 'function_name') or type(item).__name__ == 'FunctionCallContent':
                            has_function_calls = True
                            break

                # Add assistant's response to chat history
                self.chat_history.add_assistant_message(str(message))

                # Print the agent's reasoning
                if message.content:
                    print(f"\n[Agent]: {message.content}")

                # If no function calls and has content, agent likely thinks it's done
                if not has_function_calls and message.content:
                    print("\n[Agent appears to have completed the task]")

                    # Ask user if they're satisfied
                    try:
                        user_response = input("\nAre you satisfied with this result? (yes/no/feedback): ").strip().lower()

                        if user_response in ['yes', 'y']:
                            print("[Task completed successfully]")
                            break
                        elif user_response in ['no', 'n']:
                            feedback = input("What would you like me to change or fix? ")
                            self.chat_history.add_user_message(f"Please continue. User feedback: {feedback}")
                            print("\n[Continuing with user feedback...]")
                        else:
                            # Treat anything else as feedback
                            self.chat_history.add_user_message(f"Please continue. User feedback: {user_response}")
                            print("\n[Continuing with user feedback...]")
                    except (EOFError, KeyboardInterrupt):
                        print("\n[No user input - assuming task complete]")
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
