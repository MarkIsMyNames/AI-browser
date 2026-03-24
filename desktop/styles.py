"""Warm beige stylesheet matching the Microsoft_UI.html design."""

# kept for any legacy imports
DARK_THEME = ""

WARM_THEME = """
QMainWindow {
    background-color: #f0ebe1;
}
QWidget {
    background-color: #f0ebe1;
    color: #3a2e22;
    font-family: 'DM Sans', 'Segoe UI', 'Helvetica Neue', sans-serif;
    font-size: 13px;
}
QWidget#chatCard {
    background-color: #faf8f3;
    border-radius: 16px;
}
QLabel#appName {
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 15px;
    font-style: italic;
    color: #3a2e22;
    background: transparent;
}
QLabel#appTagline {
    font-size: 10px;
    color: #9a8a78;
    letter-spacing: 1px;
    background: transparent;
}
QTextEdit#chatDisplay {
    background-color: #faf8f3;
    border: none;
    color: #3a2e22;
    font-family: 'DM Sans', 'Segoe UI', sans-serif;
    font-size: 13px;
    padding: 8px;
    selection-background-color: #d4c8b8;
}
QWidget#inputWrap {
    background-color: #ede7dc;
    border-radius: 24px;
}
QTextEdit#inputField {
    background-color: transparent;
    border: none;
    color: #3a2e22;
    font-family: 'DM Sans', 'Segoe UI', sans-serif;
    font-size: 13px;
    padding: 0px;
}
QPushButton#sendBtn {
    background-color: #3a2e22;
    color: #f0ebe1;
    border: none;
    border-radius: 17px;
    font-size: 16px;
    font-weight: bold;
    min-width: 34px;
    max-width: 34px;
    min-height: 34px;
    max-height: 34px;
}
QPushButton#sendBtn:hover  { background-color: #5c4733; }
QPushButton#sendBtn:disabled { background-color: #c4b8a8; }
QPushButton#stopBtn {
    background-color: #c4b8a8;
    color: #3a2e22;
    border: none;
    border-radius: 17px;
    font-size: 11px;
    min-width: 34px;
    max-width: 34px;
    min-height: 34px;
    max-height: 34px;
}
QPushButton#stopBtn:hover    { background-color: #b8a898; }
QPushButton#stopBtn:disabled { background-color: #ddd5c8; color: #a89a88; }
QPushButton#settingsBtn {
    background-color: transparent;
    color: #9a8a78;
    border: 1px solid #d4c8b8;
    border-radius: 14px;
    padding: 4px 14px;
    font-size: 12px;
}
QPushButton#settingsBtn:hover { background-color: #ede7dc; color: #3a2e22; }
QTabWidget#rightTabs::pane {
    border: 1px solid #e8e0d4;
    background-color: #faf8f3;
    border-radius: 8px;
}
QTabBar::tab {
    background-color: #ede7dc;
    color: #9a8a78;
    padding: 7px 16px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-size: 12px;
}
QTabBar::tab:selected { background-color: #faf8f3; color: #3a2e22; font-weight: bold; }
QTextEdit#logView {
    background-color: #faf8f3;
    border: none;
    color: #6b5a4a;
    font-family: 'Consolas', 'Fira Code', monospace;
    font-size: 11px;
    padding: 8px;
}
QSplitter::handle { background-color: #e8e0d4; width: 1px; }
QScrollBar:vertical { background: transparent; width: 6px; }
QScrollBar::handle:vertical { background: #d4c8b8; border-radius: 3px; min-height: 20px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { height: 0; }
QStatusBar { background: #faf8f3; color: #9a8a78; font-size: 11px; border-top: 1px solid #e8e0d4; }
QDialog { background-color: #faf8f3; }
QGroupBox {
    border: 1px solid #e8e0d4;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: bold;
    color: #3a2e22;
    background-color: #faf8f3;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #6b5a4a; }
QLineEdit {
    background-color: #ede7dc;
    color: #3a2e22;
    border: 1px solid #d4c8b8;
    border-radius: 8px;
    padding: 7px 12px;
}
QLineEdit:focus { border: 1px solid #9a8a78; }
QComboBox {
    background-color: #ede7dc;
    color: #3a2e22;
    border: 1px solid #d4c8b8;
    border-radius: 8px;
    padding: 6px 12px;
}
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView { background-color: #faf8f3; color: #3a2e22; selection-background-color: #ede7dc; }
QLabel { background: transparent; color: #6b5a4a; }
QPushButton#dlgSave {
    background-color: #3a2e22;
    color: #f0ebe1;
    border: none;
    border-radius: 8px;
    padding: 8px 24px;
    font-weight: bold;
}
QPushButton#dlgSave:hover { background-color: #5c4733; }
QPushButton#dlgCancel {
    background-color: transparent;
    color: #9a8a78;
    border: 1px solid #d4c8b8;
    border-radius: 8px;
    padding: 8px 24px;
}
QPushButton#dlgCancel:hover { background-color: #ede7dc; color: #3a2e22; }
"""
