"""Main window for the AI Browser Desktop App."""

from datetime import datetime
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTextEdit, QLineEdit, QPushButton, QTabWidget, QLabel, QStatusBar,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QTextCursor, QIcon

from desktop.agent_worker import AgentWorker
from desktop.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Browser Agent")
        self.setMinimumSize(QSize(1000, 700))
        self._worker = None
        self._chat_history = []
        self._build_ui()
        self._update_status_label()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # Header
        header = QHBoxLayout()
        title = QLabel("🌐 AI Browser Agent")
        title.setObjectName("sectionHeader")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.addWidget(title)
        header.addStretch()

        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        header.addWidget(self.status_label)

        settings_btn = QPushButton("⚙ Settings")
        settings_btn.setFixedWidth(110)
        settings_btn.clicked.connect(self._open_settings)
        header.addWidget(settings_btn)
        root.addLayout(header)

        # Main splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left: Chat panel
        chat_panel = QWidget()
        chat_layout = QVBoxLayout(chat_panel)
        chat_layout.setContentsMargins(0, 0, 0, 0)

        chat_label = QLabel("💬 Chat")
        chat_label.setFont(QFont("Segoe UI", 13, QFont.Bold))
        chat_layout.addWidget(chat_label)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setPlaceholderText("Chat with the browser agent...")
        chat_layout.addWidget(self.chat_display, 1)

        # Input row
        input_row = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type a goal or command...")
        self.input_field.returnPressed.connect(self._send_message)
        input_row.addWidget(self.input_field)

        self.send_btn = QPushButton("Send ▶")
        self.send_btn.setFixedWidth(90)
        self.send_btn.clicked.connect(self._send_message)
        input_row.addWidget(self.send_btn)

        self.stop_btn = QPushButton("Stop ■")
        self.stop_btn.setFixedWidth(70)
        self.stop_btn.setStyleSheet("background-color: #f38ba8; color: #1e1e2e;")
        self.stop_btn.clicked.connect(self._stop_agent)
        self.stop_btn.setEnabled(False)
        input_row.addWidget(self.stop_btn)

        chat_layout.addLayout(input_row)
        splitter.addWidget(chat_panel)

        # Right: Tabs for perception, function calls, thinking
        right_tabs = QTabWidget()

        # Perception tab
        self.perception_view = QTextEdit()
        self.perception_view.setReadOnly(True)
        self.perception_view.setPlaceholderText("Perception output (CDP accessibility tree) will appear here...")
        right_tabs.addTab(self.perception_view, "🔍 Perception")

        # Function calls tab
        self.functions_view = QTextEdit()
        self.functions_view.setReadOnly(True)
        self.functions_view.setPlaceholderText("Function calls made by the agent...")
        right_tabs.addTab(self.functions_view, "⚡ Functions")

        # Thinking tab
        self.thinking_view = QTextEdit()
        self.thinking_view.setReadOnly(True)
        self.thinking_view.setPlaceholderText("Agent thinking / status updates...")
        right_tabs.addTab(self.thinking_view, "🧠 Thinking")

        splitter.addWidget(right_tabs)
        splitter.setSizes([500, 500])

        root.addWidget(splitter, 1)

        # Status bar
        self.statusBar().showMessage("Ready")

    def _update_status_label(self):
        from app.config import Config
        self.status_label.setText(f"Provider: {Config.LLM_PROVIDER}")

    def _open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            self._update_status_label()

    def _append_chat(self, role: str, text: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        if role == "user":
            color = "#89b4fa"
            prefix = "You"
        elif role == "agent":
            color = "#a6e3a1"
            prefix = "Agent"
        else:
            color = "#f38ba8"
            prefix = "System"

        html = (
            f'<div style="margin-bottom:8px;">'
            f'<span style="color:{color};font-weight:bold;">[{timestamp}] {prefix}:</span> '
            f'<span style="color:#cdd6f4;">{text}</span></div>'
        )
        self.chat_display.append(html)
        self.chat_display.moveCursor(QTextCursor.End)

    def _append_log(self, view: QTextEdit, text: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        view.append(f"[{timestamp}] {text}")
        view.moveCursor(QTextCursor.End)

    def _send_message(self):
        text = self.input_field.text().strip()
        if not text:
            return
        self.input_field.clear()
        self._append_chat("user", text)
        self._chat_history.append({"role": "user", "content": text})

        # Start agent worker
        self._worker = AgentWorker(text, self._chat_history[:-1])  # pass history minus current
        self._worker.agent_message.connect(self._on_agent_message)
        self._worker.function_call.connect(lambda s: self._append_log(self.functions_view, s))
        self._worker.thinking.connect(lambda s: self._append_log(self.thinking_view, s))
        self._worker.error.connect(lambda s: self._append_chat("error", s))
        self._worker.finished_signal.connect(self._on_finished)

        self.send_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.statusBar().showMessage("Agent running...")
        self._worker.start()

    def _on_agent_message(self, text):
        self._append_chat("agent", text)
        self._chat_history.append({"role": "assistant", "content": text})

    def _on_perception(self, text):
        self.perception_view.clear()
        self.perception_view.setPlainText(text)

    def _stop_agent(self):
        if self._worker:
            self._worker.request_stop()
            self.statusBar().showMessage("Stopping...")

    def _on_finished(self):
        self.send_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.statusBar().showMessage("Ready")
        self._worker = None
