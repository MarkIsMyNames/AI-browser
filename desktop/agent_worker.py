"""
Background worker that runs the Semantic Kernel agent in a QThread,
emitting signals for the GUI to consume.
"""

import asyncio
import traceback
from PySide6.QtCore import QThread, Signal

from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.agents import ChatCompletionAgent

from app.core.llm_factory import LLMFactory
from app.plugins.browser_plugin import BrowserPlugin
from app.plugins.cdp_perception_plugin import CDPPerceptionPlugin


class AgentWorker(QThread):
    """Runs the SK agent loop in a background thread."""

    # Signals
    agent_message = Signal(str)          # Agent response text
    function_call = Signal(str)          # Function name + args being called
    perception_update = Signal(str)      # Perception/observation output
    error = Signal(str)                  # Error messages
    thinking = Signal(str)               # Status/thinking updates
    finished_signal = Signal()           # Done

    def __init__(self, user_message: str, chat_history_items: list = None, parent=None):
        super().__init__(parent)
        self.user_message = user_message
        self._chat_history_items = chat_history_items or []
        self._stop_requested = False

    def request_stop(self):
        self._stop_requested = True

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._run_agent())
        except Exception as e:
            self.error.emit(f"Fatal error: {e}\n{traceback.format_exc()}")
        finally:
            loop.close()
            self.finished_signal.emit()

    async def _run_agent(self):
        self.thinking.emit("Initializing kernel...")

        try:
            kernel = LLMFactory.create_kernel()
        except Exception as e:
            self.error.emit(f"Kernel init failed: {e}")
            return

        browser = BrowserPlugin()
        perception = CDPPerceptionPlugin(browser)

        # Wrap perception to capture output
        original_observe = perception.observe.__func__ if hasattr(perception.observe, '__func__') else None

        plugin_self = self

        class InstrumentedPerception(CDPPerceptionPlugin):
            async def observe(self_inner) -> str:
                plugin_self.function_call.emit("CDPPerceptionPlugin.observe()")
                result = await super().observe()
                plugin_self.perception_update.emit(result)
                return result

        instrumented_perception = InstrumentedPerception(browser)

        agent = ChatCompletionAgent(
            kernel=kernel,
            name="BrowserAgent",
            instructions="""You are an autonomous browser agent. Your goal is to help the user achieve their task by interacting with the browser.

You have two primary capabilities:
1. Perception: Call observe() to see interactive elements on the current page (via CDP accessibility tree).
2. Browser: navigate, click, type_text.

Standard loop:
1. Call observe() to see what's on screen.
2. Decide the next action based on the observation.
3. If the goal is achieved, answer the user.

Always observe before acting. Use the numeric IDs from observation.""",
            plugins=[browser, instrumented_perception],
            function_choice_behavior=FunctionChoiceBehavior.Auto(),
        )

        self.thinking.emit("Agent ready. Sending message...")

        chat_history = ChatHistory()
        for item in self._chat_history_items:
            if item["role"] == "user":
                chat_history.add_user_message(item["content"])
            else:
                chat_history.add_assistant_message(item["content"])

        chat_history.add_user_message(self.user_message)

        try:
            async for response in agent.invoke(chat_history):
                if self._stop_requested:
                    break
                if response.content:
                    self.agent_message.emit(response.content)
        except Exception as e:
            err_str = str(e)
            if "connect" in err_str.lower():
                self.error.emit(f"Cannot connect to LLM server: {e}")
            else:
                self.error.emit(f"Agent error: {e}\n{traceback.format_exc()}")
        finally:
            await browser.close()
