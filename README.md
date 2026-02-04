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

## Key Files
- `app/core/llm_factory.py`: Switches between Ollama/OpenAI dynamically.
- `app/plugins/browser_plugin.py`: Handles browser interactions and "Shadow Injection" of secrets.
- `app/plugins/perception_plugin.py`: Simulates the "Vision" aspect, reducing DOM noise.