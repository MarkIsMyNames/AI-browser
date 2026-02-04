# Browser Automation Agent - MVP

A browser-controlling AI agent built with **Semantic Kernel** and **Azure OpenAI** that can perform web tasks using natural language commands.

## Features

- Natural language task execution (e.g., "book me flights to seville leaving on tuesday")
- Powered by Azure OpenAI and Semantic Kernel
- Two browser automation modes:
  - **MCP Mode (Recommended)**: Enhanced mode using Playwright MCP server with 22 advanced tools
  - **Basic Mode**: Direct Playwright integration
- Auto function calling for intelligent action selection
- CLI interface for easy interaction
- Comprehensive browser control (navigation, interactions, screenshots, accessibility snapshots)
- Advanced features: tab management, dialog handling, file uploads, drag & drop

## Prerequisites

- Python 3.10 or higher
- Azure subscription with Azure OpenAI service
- Azure OpenAI deployment (GPT-4, GPT-4o, or compatible model)
- Node.js 18+ (required for MCP mode)

## Setup

### 1. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 2. Configure Azure OpenAI

1. Create an Azure OpenAI resource in [Azure Portal](https://portal.azure.com)
2. Deploy a model (recommended: GPT-4o or GPT-4)
3. Get your endpoint URL and API key

### 3. Set Up Environment Variables

```bash
# Copy the template
cp .env.template .env

# Edit .env and fill in your Azure OpenAI credentials
```

Your `.env` file should look like:

```env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name
AZURE_OPENAI_API_VERSION=2024-02-15-preview
HEADLESS_MODE=false
```

## Usage

### Basic Usage (Non-MCP Mode)

```bash
python main.py "book me flights to seville leaving on tuesday"
```

### Enhanced MCP Mode (Recommended)

```bash
python main.py "search for python tutorials on youtube" --mcp
```

### Run in Headless Mode

```bash
python main.py "find the top 3 news articles about AI on BBC" --headless
```

### Example Commands

```bash
# Enhanced MCP mode (recommended)
python main.py "book me flights to seville leaving on tuesday" --mcp

# Search for information
python main.py "find the top 3 news articles about AI on BBC" --mcp

# YouTube search
python main.py "search for python tutorials on youtube and show me the top 3" --mcp

# Shopping
python main.py "search for laptops under $1000 on amazon" --mcp

# Non-MCP mode (basic)
python main.py "navigate to example.com and click the login button" --headless
```

## How It Works

1. **User Input**: You provide a natural language task
2. **Semantic Kernel**: Orchestrates the agent's reasoning and action selection
3. **Browser Plugin**: Exposes browser automation functions (navigate, click, fill forms, etc.)
4. **Auto Function Calling**: Azure OpenAI automatically decides which browser functions to call
5. **Iterative Execution**: Agent repeats the process until the task is complete

## Architecture

```
browser-agent-mvp/
├── agent/
│   ├── browser_agent.py      # Core agent logic with SK orchestration
│   └── plugins/
│       └── browser_plugin.py # Playwright functions as SK plugin
├── main.py                    # CLI entry point
├── requirements.txt           # Python dependencies
└── .env                       # Configuration (not in git)
```

## Available Browser Functions

### MCP Mode (22 Enhanced Functions)

**Navigation & Page Management:**
- `browser_navigate`: Navigate to a specific URL
- `browser_navigate_back`: Go back in browser history
- `browser_tabs`: List, create, close, or select browser tabs
- `browser_close`: Close the current page/tab

**Page Inspection & Analysis:**
- `browser_snapshot`: Get structured accessibility tree (best for understanding page structure)
- `browser_take_screenshot`: Take screenshots of page or specific elements
- `browser_console_messages`: Get all console messages
- `browser_network_requests`: Get all network requests since page load

**User Interactions:**
- `browser_click`: Click elements (supports CSS selectors and ARIA roles)
- `browser_type`: Type text into editable elements
- `browser_fill_form`: Fill multiple form fields at once
- `browser_select_option`: Select dropdown options
- `browser_hover`: Hover over elements
- `browser_drag`: Perform drag and drop operations
- `browser_press_key`: Press keyboard keys (Enter, Tab, Escape, etc.)
- `browser_file_upload`: Upload files to file inputs

**Advanced Features:**
- `browser_evaluate`: Execute JavaScript in browser context
- `browser_run_code`: Run Playwright code snippets directly
- `browser_handle_dialog`: Handle alerts, confirms, and prompts
- `browser_resize`: Resize the browser window
- `browser_wait_for`: Wait for text to appear/disappear or specific time
- `browser_install`: Install browser if not already installed

### Basic Mode (8 Functions)

- `navigate_to_url`: Navigate to a specific URL
- `get_page_state`: Get current page information (URL, title, buttons, links)
- `get_page_content`: Extract text content from the page
- `click_element`: Click on elements (by CSS selector or visible text)
- `fill_input`: Fill form input fields
- `type_text`: Type text character by character
- `press_key`: Press keyboard keys (Enter, Tab, etc.)
- `wait_for_navigation`: Wait for page loads

## Troubleshooting

### "AZURE_OPENAI_ENDPOINT environment variable is required"

Make sure you've:
1. Copied `.env.template` to `.env`
2. Filled in all required values in `.env`

### Browser doesn't open

- If using headless mode, the browser runs in the background (no window)
- Set `HEADLESS_MODE=false` in `.env` to see the browser

### Playwright not installed

Run: `playwright install chromium`

### Module not found errors

Make sure you're running from the project root and have installed dependencies:
```bash
pip install -r requirements.txt
```

## Limitations

- Max 15 iterations per task (configurable with `--max-iterations`)
- No session persistence between runs
- Limited to Chromium browser
- Screenshot analysis requires additional vision capabilities

## Recent Enhancements

- ✅ Complete Playwright MCP server integration with 22 tools
- ✅ Accessibility tree snapshots for reliable page inspection
- ✅ Screenshot capture capability
- ✅ Advanced interactions (drag & drop, file uploads, dialog handling)
- ✅ Console and network debugging tools
- ✅ Tab management and navigation history

## Future Enhancements

- Vision capabilities for screenshot analysis (GPT-4 Vision integration)
- Session persistence and cookie management
- Multi-page workflows with context preservation
- Better error recovery and retry logic
- Support for complex authentication flows
- Integration with Azure AI Foundry agents

## License

MIT License

## Contributing

This is an MVP. Contributions and improvements are welcome.

## Support

For issues related to:
- **Azure OpenAI**: Check [Azure OpenAI documentation](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- **Semantic Kernel**: Check [SK documentation](https://learn.microsoft.com/en-us/semantic-kernel/)
- **Playwright**: Check [Playwright documentation](https://playwright.dev/python/)

# Probabilistic Browser Agent

A local-first, privacy-focused browser agent using Semantic Kernel, Playwright, and local LLMs (Ollama + Llama 3.2 Vision).

## Architecture
- **Orchestration**: Semantic Kernel (handling state, plugins, planning)
- **Execution**: Playwright (Shadow DOM access, fast CDP control)
- **Perception**: DOM Distillation + Set-of-Marks (simulated in this basic version)
- **Security**: Shadow Injection for secrets

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   playwright install
   ```

2. **Configure AI Backend**
   
   The agent supports interchangeable backends via `app/config.py`.
   
   **Option A: Ollama (Recommended for Privacy)**
   1. Install Ollama: https://ollama.com/
   2. Pull the model: `ollama pull llama3.2-vision`
   3. Run the server: `ollama serve`
   4. Default config uses `LLM_PROVIDER="ollama"`.

   **Option B: Azure / OpenAI**
   1. Set environment variables or edit `.env`:
      ```
      LLM_PROVIDER=openai
      OPENAI_API_KEY=sk-...
      ```

3. **Run the Agent**
   ```bash
   python main.py
   ```
