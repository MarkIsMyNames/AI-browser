"""Browser Agent using Semantic Kernel for orchestration."""
import os
import asyncio
from typing import Annotated, Awaitable, Callable, List, Optional
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents import AuthorRole
from semantic_kernel.functions import KernelArguments

from agent.plugins.browser_plugin import BrowserPlugin
from agent.plugins.playwright_mcp_plugin import PlaywrightMCPPlugin

MAX_HISTORY = 20


class BrowserAgent:
    """AI Agent that controls a web browser using Semantic Kernel."""

    def __init__(
        self,
        azure_endpoint: str = None,
        azure_api_key: str = None,
        deployment_name: str = None,
        api_version: str = "2024-02-15-preview",
        headless: bool = False,
        use_mcp: bool = False,
        kernel: Kernel = None,
    ):
        """Initialize the Browser Agent.

        Args:
            azure_endpoint: Azure OpenAI endpoint URL (ignored if kernel is provided)
            azure_api_key: Azure OpenAI API key (ignored if kernel is provided)
            deployment_name: Azure OpenAI deployment name (ignored if kernel is provided)
            api_version: Azure OpenAI API version (ignored if kernel is provided)
            headless: Whether to run browser in headless mode (only for non-MCP mode)
            use_mcp: Whether to use Playwright MCP server (recommended)
            kernel: Pre-built Semantic Kernel instance. If provided, Azure params are ignored.
        """
        self.use_mcp = use_mcp

        if kernel is not None:
            self.kernel = kernel
        else:
            self.kernel = Kernel()
            self.kernel.add_service(
                AzureChatCompletion(
                    service_id="chat_completion",
                    endpoint=azure_endpoint,
                    api_key=azure_api_key,
                    deployment_name=deployment_name,
                    api_version=api_version
                )
            )

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
- Refs (e45, e123, etc.) are only valid for the CURRENT snapshot only
- Refs become INVALID the moment you navigate to a new page

Multi-page research strategy (use this for tasks requiring info from multiple pages):
1. Search: browser_navigate to https://duckduckgo.com/?q=your+query
2. Snapshot the search results page
3. COLLECT multiple URLs from the snapshot (read the href/link text, note 5+ candidate URLs as plain text)
4. For each URL you collected, use browser_navigate(url="https://...") directly — never navigate back or reuse old refs
5. Snapshot the new page → extract information → move to the next collected URL
6. Repeat until you have ALL required information

Error recovery — if a page fails or has no useful info:
- Move on immediately to the next URL from your list
- If your URL list runs out, do another DuckDuckGo search with different keywords

Form filling rules:
- Use browser_fill_form to fill forms. Pass a JSON object of field label → value pairs, e.g. {"Email": "john@example.com", "First Name": "John"}. Refs are resolved automatically — do NOT look up or pass refs yourself.
- Only use browser_type directly for single fields on non-form pages where browser_fill_form is not applicable.

CRITICAL RULES:
- Count what you have. If the task requires 3 items, you must have exactly 3 before calling task_complete.
- NEVER call task_complete with partial results. "I found 1 of 3" is NOT complete.
- Do NOT say "I will do X" — actually do it using the tools right now.
- Do NOT use browser_navigate_back to return to search results — you will have stale refs. Use browser_navigate with the next URL instead.
- Make all decisions autonomously. Do NOT ask the user questions in your response text — there is nobody reading it mid-task.
- When you face multiple options or paths, pick one yourself and act on it immediately. Never present a list of options and ask the user to choose.
- If you are genuinely blocked after trying multiple approaches, call request_help(question="...") to pause and get user input. This is a last resort, not a first response to difficulty.
- When you genuinely have ALL required information, call task_complete(summary="...") with the complete answer.

Be methodical, persistent, and thorough. One page failure is not a reason to stop."""
        else:
            self.system_prompt = """You are a browser automation agent. Help users complete web tasks by controlling a browser.

Strategy:
1. Navigate to relevant sites (for searches use DuckDuckGo: https://duckduckgo.com/?q=query)
2. Use get_page_state to understand page structure
3. Take actions step by step (click, fill forms, etc.)
4. Continue until goal achieved

Be methodical and explain your actions."""

    async def run(
        self,
        user_goal: str,
        max_iterations: int = 15,
        history: List[dict] = None,
        on_thinking: Callable[[str], None] = None,
        on_agent_message: Callable[[str], None] = None,
        on_request_help: Callable[[str], Awaitable[Optional[str]]] = None,
        on_task_complete: Callable[[str], Awaitable[Optional[str]]] = None,
        should_stop: Callable[[], bool] = None,
    ) -> str:
        """Run the agent to accomplish a user goal.

        Args:
            user_goal: The goal the user wants to accomplish
            max_iterations: Maximum number of agent iterations
            history: Prior conversation as list of {"role": "user"/"assistant", "content": str}
            on_thinking: Called with status/progress messages
            on_agent_message: Called with each LLM text response
            on_request_help: Called when agent needs user input; return the response string,
                             or None to stop the agent (GUI mode)
            on_task_complete: Called when agent signals completion with its summary; return None
                              to stop, or a feedback string to continue (CLI mode)
            should_stop: Called each iteration; return True to abort

        Returns:
            Final response from the agent
        """
        # Default callbacks preserve original CLI behaviour
        async def _default_request_help(question: str) -> Optional[str]:
            print(f"\n[Agent needs help]: {question}")
            try:
                user_input = (await asyncio.to_thread(
                    input, "\nYour response (press Enter to let the agent continue trying): "
                )).strip()
                return user_input or "Continue and try a different approach."
            except (EOFError, KeyboardInterrupt):
                return "Continue and try a different approach."

        async def _default_task_complete(summary: str) -> Optional[str]:
            print(f"\n[Final Answer]:\n{summary}")
            try:
                user_response = (await asyncio.to_thread(
                    input, "\nAre you satisfied with this result? (yes/no/feedback): "
                )).strip().lower()
                if user_response in ['yes', 'y', '']:
                    return None
                return user_response
            except (EOFError, KeyboardInterrupt):
                return None

        _on_thinking = on_thinking or (lambda msg: print(f"\n--- {msg} ---"))
        _on_agent_message = on_agent_message or (lambda msg: print(f"\n[Agent]: {msg}"))
        _on_request_help = on_request_help or _default_request_help
        _on_task_complete = on_task_complete or _default_task_complete

        _on_thinking(f"Agent Goal: {user_goal}")

        # Eagerly initialize the browser/MCP server before the first LLM call
        await self.browser_plugin.initialize()

        # Build chat history: system prompt + optional prior turns + current goal
        self.chat_history = ChatHistory()
        self.chat_history.add_system_message(self.system_prompt)
        if history:
            for item in history:
                if item["role"] == "user":
                    self.chat_history.add_user_message(item["content"])
                else:
                    self.chat_history.add_assistant_message(item["content"])
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
        message = None
        try:
            while iteration < max_iterations:
                if should_stop and should_stop():
                    break

                iteration += 1
                _on_thinking(f"Iteration {iteration}/{max_iterations}")

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

                # Sliding-window trim to prevent unbounded history growth
                if len(self.chat_history) > MAX_HISTORY + 1:
                    system_msg = self.chat_history[0]
                    goal_msg = self.chat_history[1]
                    tail = list(self.chat_history)[-(MAX_HISTORY - 2):]
                    # Strip leading tool messages — they reference tool_calls that were
                    # trimmed away, which the API rejects as an invalid message sequence.
                    while tail and getattr(tail[0], 'role', None) == AuthorRole.TOOL:
                        tail = tail[1:]
                    self.chat_history = ChatHistory()
                    self.chat_history.add_message(system_msg)
                    self.chat_history.add_message(goal_msg)
                    for msg in tail:
                        self.chat_history.add_message(msg)

                if message.content:
                    _on_agent_message(str(message.content))

                # Check if agent called request_help() — pause and get user input
                if self.browser_plugin.help_requested:
                    question = self.browser_plugin.help_question
                    self.browser_plugin.help_requested = False
                    self.browser_plugin.help_question = ""
                    user_input = await _on_request_help(question)
                    if user_input is None:
                        break  # GUI: stop agent so user can reply via the chat input
                    self.chat_history.add_user_message(user_input)

                # Check if agent explicitly signalled task completion via task_complete()
                if self.browser_plugin.task_completed:
                    summary = self.browser_plugin.task_summary
                    self.browser_plugin.task_completed = False
                    feedback = await _on_task_complete(summary)
                    if feedback is None:
                        break  # Done
                    else:
                        self.browser_plugin.task_summary = ""
                        self.chat_history.add_user_message(
                            f"Please continue. User feedback: {feedback}"
                        )

                # Small delay to make output readable
                await asyncio.sleep(0.5)

            _on_thinking("Agent execution completed")

            if self.browser_plugin.task_summary:
                return self.browser_plugin.task_summary
            if message is not None and message.content:
                return str(message.content)
            return "Task completed"

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
        use_mcp = os.getenv("USE_MCP", "true").lower() == "true"

    return BrowserAgent(
        azure_endpoint=azure_endpoint,
        azure_api_key=azure_api_key,
        deployment_name=deployment_name,
        api_version=api_version,
        headless=headless,
        use_mcp=use_mcp
    )
