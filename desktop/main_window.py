"""Main window — styled to match Microsoft_UI.html."""

from datetime import datetime
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTextEdit, QPushButton, QLabel, QSizePolicy,
)
from PySide6.QtCore import Qt, QSize, QEvent
from PySide6.QtGui import QTextCursor, QKeyEvent

from desktop.agent_worker import AgentWorker
from desktop.settings_dialog import SettingsDialog
from desktop.stickman_widget import StickmanWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Browser Agent")
        self.setMinimumSize(QSize(900, 640))
        self._worker = None
        self._chat_history = []
        self._build_ui()

    # ── UI Construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        # Outer background widget
        outer = QWidget()
        outer.setObjectName("outerBg")
        self.setCentralWidget(outer)
        outer_layout = QHBoxLayout(outer)
        outer_layout.setContentsMargins(20, 20, 20, 20)
        outer_layout.setSpacing(12)

        # ── Left: chat card ───────────────────────────────────────────────────
        chat_card = QWidget()
        chat_card.setObjectName("chatCard")
        chat_card.setMinimumWidth(420)
        card_layout = QVBoxLayout(chat_card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # Header
        header_widget = QWidget()
        header_widget.setObjectName("chatCard")
        header_widget.setFixedHeight(60)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 10, 16, 10)

        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        name_lbl = QLabel("AI Browser Agent")
        name_lbl.setObjectName("appName")
        tagline_lbl = QLabel("Distinguished Browser Assistant")
        tagline_lbl.setObjectName("appTagline")
        text_col.addWidget(name_lbl)
        text_col.addWidget(tagline_lbl)
        header_layout.addLayout(text_col)
        header_layout.addStretch()

        settings_btn = QPushButton("⚙ Settings")
        settings_btn.setObjectName("settingsBtn")
        settings_btn.setFixedHeight(28)
        settings_btn.clicked.connect(self._open_settings)
        header_layout.addWidget(settings_btn)
        card_layout.addWidget(header_widget)

        # Separator line
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #e8e0d4;")
        card_layout.addWidget(sep)

        # Messages area
        self.chat_display = QTextEdit()
        self.chat_display.setObjectName("chatDisplay")
        self.chat_display.setReadOnly(True)
        self.chat_display.document().setDefaultStyleSheet(
            "body { font-family: 'DM Sans', 'Segoe UI', sans-serif; font-size: 13px; }"
        )
        card_layout.addWidget(self.chat_display, 1)

        # Input bar
        input_bar = QWidget()
        input_bar.setObjectName("chatCard")
        input_bar_layout = QHBoxLayout(input_bar)
        input_bar_layout.setContentsMargins(12, 10, 12, 12)
        input_bar_layout.setSpacing(10)

        # Stickman
        self.stickman = StickmanWidget()
        input_bar_layout.addWidget(self.stickman, 0, Qt.AlignVCenter)

        # Pill input wrapper
        input_wrap = QWidget()
        input_wrap.setObjectName("inputWrap")
        input_wrap_layout = QHBoxLayout(input_wrap)
        input_wrap_layout.setContentsMargins(14, 6, 8, 6)
        input_wrap_layout.setSpacing(8)

        self.input_field = QTextEdit()
        self.input_field.setObjectName("inputField")
        self.input_field.setFixedHeight(36)
        self.input_field.setPlaceholderText("Ask something…")
        self.input_field.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.input_field.installEventFilter(self)   # catch Enter key
        input_wrap_layout.addWidget(self.input_field)

        self.send_btn = QPushButton("➤")
        self.send_btn.setObjectName("sendBtn")
        self.send_btn.clicked.connect(self._send_message)
        input_wrap_layout.addWidget(self.send_btn, 0, Qt.AlignVCenter)

        self.stop_btn = QPushButton("■")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.clicked.connect(self._stop_agent)
        self.stop_btn.setEnabled(False)
        input_wrap_layout.addWidget(self.stop_btn, 0, Qt.AlignVCenter)

        input_bar_layout.addWidget(input_wrap, 1)
        card_layout.addWidget(input_bar)

        # Separator above input
        sep2 = QWidget()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet("background-color: #e8e0d4;")
        card_layout.insertWidget(card_layout.count() - 1, sep2)

        # ── Right: thinking panel ─────────────────────────────────────────────
        right_panel = QWidget()
        right_panel.setObjectName("chatCard")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        thinking_header = QWidget()
        thinking_header.setObjectName("chatCard")
        thinking_header.setFixedHeight(44)
        th_layout = QHBoxLayout(thinking_header)
        th_layout.setContentsMargins(16, 0, 16, 0)
        thinking_lbl = QLabel("Thought Process")
        thinking_lbl.setObjectName("appName")
        th_layout.addWidget(thinking_lbl)
        right_layout.addWidget(thinking_header)

        th_sep = QWidget()
        th_sep.setFixedHeight(1)
        th_sep.setStyleSheet("background-color: #e8e0d4;")
        right_layout.addWidget(th_sep)

        self.thinking_view = self._make_log_view("Agent status updates will appear here…")
        right_layout.addWidget(self.thinking_view, 1)

        # ── Splitter ──────────────────────────────────────────────────────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(chat_card)
        splitter.addWidget(right_panel)
        splitter.setSizes([520, 380])
        splitter.setStyleSheet("QSplitter { background: #f0ebe1; }")

        outer_layout.addWidget(splitter)

        # Status bar
        self.statusBar().showMessage("Ready")
        self.statusBar().setStyleSheet(
            "QStatusBar { background: #f0ebe1; color: #9a8a78; font-size: 11px; border: none; }"
        )

        # Welcome message
        self._append_bot("Good day. How may I be of service?")

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _make_log_view(self, placeholder: str) -> QTextEdit:
        view = QTextEdit()
        view.setObjectName("logView")
        view.setReadOnly(True)
        view.setPlaceholderText(placeholder)
        return view

    def _append_bot(self, text: str):
        ts = datetime.now().strftime("%H:%M")
        html = (
            f'<div style="margin: 6px 0; display:flex;">'
            f'<div style="max-width:72%; background:#ede7dc; color:#3a2e22; '
            f'padding:10px 15px; border-radius:16px 16px 16px 4px; '
            f'font-size:13px; line-height:1.5;">'
            f'{text}'
            f'<span style="display:block;font-size:10px;color:#9a8a78;margin-top:4px;">{ts}</span>'
            f'</div></div>'
        )
        self.chat_display.append(html)
        self.chat_display.moveCursor(QTextCursor.End)

    def _append_user(self, text: str):
        ts = datetime.now().strftime("%H:%M")
        html = (
            f'<div style="margin: 6px 0; text-align:right;">'
            f'<div style="display:inline-block; max-width:72%; background:#3a2e22; color:#f0ebe1; '
            f'padding:10px 15px; border-radius:16px 16px 4px 16px; '
            f'font-size:13px; line-height:1.5;">'
            f'{text}'
            f'<span style="display:block;font-size:10px;color:#9a8a78;margin-top:4px;">{ts}</span>'
            f'</div></div>'
        )
        self.chat_display.append(html)
        self.chat_display.moveCursor(QTextCursor.End)

    def _append_log(self, view: QTextEdit, text: str):
        ts = datetime.now().strftime("%H:%M:%S")
        view.append(f'<span style="color:#9a8a78;">[{ts}]</span> {text}')
        view.moveCursor(QTextCursor.End)

    # ── Event filter: Enter to send ───────────────────────────────────────────
    def eventFilter(self, obj, event):
        if obj is self.input_field and event.type() == QEvent.KeyPress:
            key_event = QKeyEvent(event)
            if key_event.key() == Qt.Key_Return and not (key_event.modifiers() & Qt.ShiftModifier):
                self._send_message()
                return True
        return super().eventFilter(obj, event)

    # ── Actions ───────────────────────────────────────────────────────────────
    def _open_settings(self):
        SettingsDialog(self).exec()

    def _send_message(self):
        text = self.input_field.toPlainText().strip()
        if not text or self._worker:
            return

        self.input_field.clear()
        self._append_user(text)
        self._chat_history.append({"role": "user", "content": text})

        self.stickman.set_loading(True)
        self.send_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.statusBar().showMessage("Agent running…")

        self._worker = AgentWorker(text, list(self._chat_history[:-1]))
        self._worker.agent_message.connect(self._on_agent_message)
        self._worker.thinking.connect(lambda s: self._append_log(self.thinking_view, s))
        self._worker.error.connect(lambda s: self._append_bot(f"⚠ {s}"))
        self._worker.finished_signal.connect(self._on_finished)
        self._worker.start()

    def _on_agent_message(self, text: str):
        self._append_bot(text)
        self._chat_history.append({"role": "assistant", "content": text})

    def _stop_agent(self):
        if self._worker:
            self._worker.request_stop()
            self.statusBar().showMessage("Stopping…")

    def _on_finished(self):
        self.stickman.set_loading(False)
        self.send_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.statusBar().showMessage("Ready")
        self._worker = None
        self._chat_history = []