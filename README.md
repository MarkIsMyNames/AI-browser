# AI Browser Agent — Desktop Frontend

A modern desktop application for the AI Browser Agent, built with **PySide6** (Qt) and **Semantic Kernel**.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![PySide6](https://img.shields.io/badge/UI-PySide6-green) ![SK](https://img.shields.io/badge/AI-Semantic%20Kernel-purple)

## Features

- **Chat Interface** — Real-time conversation with the browser agent
- **CDP Perception** — Live accessibility tree extraction via Chrome DevTools Protocol (ported from V1.py)
- **Function Call Viewer** — See exactly what the agent is calling and when
- **Thinking Panel** — Agent status and reasoning updates
- **Settings Panel** — Configure LLM provider (Ollama / OpenAI / Azure OpenAI) with credentials
- **Dark Theme** — Modern Catppuccin-inspired dark UI
- **Stop Button** — Interrupt the agent mid-execution

## Architecture

```
desktop_app.py          ← Entry point
desktop/
  main_window.py        ← Main UI (chat, perception, functions, thinking tabs)
  agent_worker.py       ← QThread worker that runs the SK agent async loop
  settings_dialog.py    ← LLM provider configuration dialog
  styles.py             ← Dark theme stylesheet
app/
  config.py             ← Environment-based configuration
  core/llm_factory.py   ← Semantic Kernel kernel/LLM factory
  plugins/
    browser_plugin.py       ← Playwright browser control
    cdp_perception_plugin.py ← CDP accessibility tree perception (from V1.py)
    perception_plugin.py    ← Original mock perception (kept for reference)
V1.py                   ← Original standalone CDP scraper script
```

## Quick Start

### 1. Install dependencies

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure LLM provider

Copy `.env.example` to `.env` and fill in your provider details, **or** use the in-app Settings panel.

```bash
cp .env.example .env
# Edit .env with your preferred provider
```

### 3. Run the desktop app

```bash
python desktop_app.py
```

### 4. Run the original CLI (optional)

```bash
python main.py
```

## LLM Provider Options

| Provider | Required Config |
|----------|----------------|
| **Ollama** (default) | `OLLAMA_BASE_URL`, `OLLAMA_MODEL_ID` |
| **OpenAI** | `OPENAI_API_KEY`, `OPENAI_MODEL_ID` |
| **Azure OpenAI** | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT_NAME` |

## How It Works

1. User types a goal in the chat input (e.g., "Go to example.com and find the login form")
2. The Semantic Kernel `ChatCompletionAgent` processes the goal with auto function calling
3. The agent calls `CDPPerceptionPlugin.observe()` to get the page's accessibility tree via CDP
4. Based on observed elements, the agent calls `BrowserPlugin` methods (navigate, click, type_text)
5. All function calls, perception results, and agent thinking are displayed in real-time in separate panels

## License

See [LICENSE](LICENSE).
