"""
Background worker that runs the BrowserAgent in a QThread,
emitting signals for the GUI to consume.
"""

import asyncio
import traceback
from typing import Optional

from PySide6.QtCore import QThread, Signal

from agent.browser_agent import BrowserAgent
from app.core.llm_factory import LLMFactory


MAX_HISTORY = 20


class AgentWorker(QThread):
    """Runs the BrowserAgent in a background thread."""

    # Signals
    agent_message = Signal(str)          # Agent response text
    function_call = Signal(str)          # Function name + args being called
    thinking = Signal(str)               # Status/thinking updates
    error = Signal(str)                  # Error messages
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

        agent = BrowserAgent(kernel=kernel, use_mcp=True)

        worker = self

        def on_thinking(msg: str):
            worker.thinking.emit(msg)

        def on_agent_message(msg: str):
            worker.agent_message.emit(msg)

        async def on_request_help(question: str) -> Optional[str]:
            # Emit as an agent message so the user sees what's blocking the agent,
            # then stop so they can reply via the normal chat input.
            worker.agent_message.emit(f"I need your help to continue:\n\n{question}")
            return None

        async def on_task_complete(summary: str) -> Optional[str]:
            # Emit the final answer and stop — no confirmation prompt needed in the GUI.
            worker.agent_message.emit(summary)
            return None

        history = self._chat_history_items[-MAX_HISTORY:]

        try:
            await agent.run(
                self.user_message,
                history=history,
                on_thinking=on_thinking,
                on_agent_message=on_agent_message,
                on_request_help=on_request_help,
                on_task_complete=on_task_complete,
                should_stop=lambda: worker._stop_requested,
            )
        except Exception as e:
            err_str = str(e)
            if "connect" in err_str.lower():
                self.error.emit(f"Cannot connect to LLM server: {e}")
            else:
                self.error.emit(f"Agent error: {e}\n{traceback.format_exc()}")
