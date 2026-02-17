"""Settings dialog for LLM provider configuration."""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QGroupBox, QMessageBox,
)
from PySide6.QtCore import Qt


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings — AI Browser Agent")
        self.setMinimumWidth(500)
        self._build_ui()
        self._load_current()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Provider selection
        provider_layout = QHBoxLayout()
        provider_layout.addWidget(QLabel("LLM Provider:"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["ollama", "openai", "azure"])
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        provider_layout.addWidget(self.provider_combo)
        layout.addLayout(provider_layout)

        # Ollama group
        self.ollama_group = QGroupBox("Ollama")
        ol = QFormLayout(self.ollama_group)
        self.ollama_url = QLineEdit()
        self.ollama_url.setPlaceholderText("http://localhost:11434/v1")
        self.ollama_model = QLineEdit()
        self.ollama_model.setPlaceholderText("llama3.2-vision")
        ol.addRow("Base URL:", self.ollama_url)
        ol.addRow("Model:", self.ollama_model)
        layout.addWidget(self.ollama_group)

        # OpenAI group
        self.openai_group = QGroupBox("OpenAI")
        oa = QFormLayout(self.openai_group)
        self.openai_key = QLineEdit()
        self.openai_key.setEchoMode(QLineEdit.Password)
        self.openai_org = QLineEdit()
        self.openai_model = QLineEdit()
        self.openai_model.setPlaceholderText("gpt-4-turbo")
        oa.addRow("API Key:", self.openai_key)
        oa.addRow("Org ID:", self.openai_org)
        oa.addRow("Model:", self.openai_model)
        layout.addWidget(self.openai_group)

        # Azure group
        self.azure_group = QGroupBox("Azure OpenAI")
        az = QFormLayout(self.azure_group)
        self.azure_endpoint = QLineEdit()
        self.azure_key = QLineEdit()
        self.azure_key.setEchoMode(QLineEdit.Password)
        self.azure_deployment = QLineEdit()
        self.azure_version = QLineEdit()
        self.azure_version.setPlaceholderText("2023-05-15")
        az.addRow("Endpoint:", self.azure_endpoint)
        az.addRow("API Key:", self.azure_key)
        az.addRow("Deployment:", self.azure_deployment)
        az.addRow("API Version:", self.azure_version)
        layout.addWidget(self.azure_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background-color: #45475a; color: #cdd6f4;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _on_provider_changed(self, provider):
        self.ollama_group.setVisible(provider == "ollama")
        self.openai_group.setVisible(provider == "openai")
        self.azure_group.setVisible(provider == "azure")

    def _load_current(self):
        from app.config import Config
        self.provider_combo.setCurrentText(Config.LLM_PROVIDER)
        self.ollama_url.setText(Config.OLLAMA_BASE_URL)
        self.ollama_model.setText(Config.OLLAMA_MODEL_ID)
        self.openai_key.setText(Config.OPENAI_API_KEY or "")
        self.openai_org.setText(Config.OPENAI_ORG_ID or "")
        self.openai_model.setText(Config.OPENAI_MODEL_ID)
        self.azure_endpoint.setText(Config.AZURE_OPENAI_ENDPOINT or "")
        self.azure_key.setText(Config.AZURE_OPENAI_API_KEY or "")
        self.azure_deployment.setText(Config.AZURE_OPENAI_DEPLOYMENT_NAME or "")
        self.azure_version.setText(Config.AZURE_OPENAI_API_VERSION)
        self._on_provider_changed(Config.LLM_PROVIDER)

    def _save(self):
        provider = self.provider_combo.currentText()

        # Write to .env file
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        lines = [
            f"LLM_PROVIDER={provider}",
            f"OLLAMA_BASE_URL={self.ollama_url.text() or 'http://localhost:11434/v1'}",
            f"OLLAMA_MODEL_ID={self.ollama_model.text() or 'llama3.2-vision'}",
            f"OPENAI_API_KEY={self.openai_key.text()}",
            f"OPENAI_ORG_ID={self.openai_org.text()}",
            f"OPENAI_MODEL_ID={self.openai_model.text() or 'gpt-4-turbo'}",
            f"AZURE_OPENAI_ENDPOINT={self.azure_endpoint.text()}",
            f"AZURE_OPENAI_API_KEY={self.azure_key.text()}",
            f"AZURE_OPENAI_DEPLOYMENT_NAME={self.azure_deployment.text()}",
            f"AZURE_OPENAI_API_VERSION={self.azure_version.text() or '2023-05-15'}",
        ]
        with open(env_path, "w") as f:
            f.write("\n".join(lines) + "\n")

        # Also update Config in-memory
        from app.config import Config
        Config.LLM_PROVIDER = provider
        Config.OLLAMA_BASE_URL = self.ollama_url.text() or Config.OLLAMA_BASE_URL
        Config.OLLAMA_MODEL_ID = self.ollama_model.text() or Config.OLLAMA_MODEL_ID
        Config.OPENAI_API_KEY = self.openai_key.text() or None
        Config.OPENAI_ORG_ID = self.openai_org.text() or None
        Config.OPENAI_MODEL_ID = self.openai_model.text() or Config.OPENAI_MODEL_ID
        Config.AZURE_OPENAI_ENDPOINT = self.azure_endpoint.text() or None
        Config.AZURE_OPENAI_API_KEY = self.azure_key.text() or None
        Config.AZURE_OPENAI_DEPLOYMENT_NAME = self.azure_deployment.text() or None
        Config.AZURE_OPENAI_API_VERSION = self.azure_version.text() or Config.AZURE_OPENAI_API_VERSION

        QMessageBox.information(self, "Saved", f"Settings saved. Provider: {provider}")
        self.accept()
