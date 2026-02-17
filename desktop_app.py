#!/usr/bin/env python3
"""
AI Browser Agent — Desktop Frontend
Launch this to start the PySide6 desktop application.
"""

import sys
from PySide6.QtWidgets import QApplication
from desktop.main_window import MainWindow
from desktop.styles import DARK_THEME


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("AI Browser Agent")
    app.setStyleSheet(DARK_THEME)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
