#!/usr/bin/env python3
"""
AI Browser Agent — Desktop (HTML UI)

Starts the FastAPI backend (web_app.py) on localhost and embeds the HTML UI
in a PySide6 QWebEngineView so it behaves like a desktop app.
"""

import sys
import threading
from typing import Optional

import uvicorn
from PySide6.QtCore import QUrl, QSize
from PySide6.QtWidgets import QApplication, QMainWindow

# Qt WebEngine (Chromium-based view)
from PySide6.QtWebEngineWidgets import QWebEngineView

from web_app import app as fastapi_app


class UvicornThread(threading.Thread):
    def __init__(self, host: str = "127.0.0.1", port: int = 8000):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self._server: Optional[uvicorn.Server] = None

    def run(self) -> None:
        config = uvicorn.Config(
            fastapi_app,
            host=self.host,
            port=self.port,
            log_level="warning",
            reload=False,
        )
        self._server = uvicorn.Server(config)
        self._server.run()

    def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True


class WebMainWindow(QMainWindow):
    def __init__(self, server_thread: UvicornThread, url: str):
        super().__init__()
        self._server_thread = server_thread

        self.setWindowTitle("AI Browser Agent — Desktop UI")
        self.setMinimumSize(QSize(1000, 740))

        view = QWebEngineView()
        view.setUrl(QUrl(url))
        self.setCentralWidget(view)

    def closeEvent(self, event):  # noqa: N802 (Qt naming convention)
        # Ensure the local server is asked to stop when the window closes.
        try:
            self._server_thread.stop()
        finally:
            super().closeEvent(event)


def main() -> int:
    host = "127.0.0.1"
    port = 8000
    url = f"http://{host}:{port}/"

    # Start backend server in background thread
    server_thread = UvicornThread(host=host, port=port)
    server_thread.start()

    # Start Qt app and embed the web UI
    app = QApplication(sys.argv)
    app.setApplicationName("AI Browser Agent (Web UI)")

    window = WebMainWindow(server_thread, url)
    window.show()

    exit_code = app.exec()

    # Best-effort stop on exit as well
    server_thread.stop()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

