import asyncio
from pathlib import Path

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core.llm_factory import LLMFactory
from agent.browser_agent import BrowserAgent


BASE_DIR = Path(__file__).parent
WEB_DIR = BASE_DIR / "web"
INDEX_HTML = WEB_DIR / "index.html"
# User's custom UI
USER_UI_HTML = Path(r"C:\Users\5090d\OneDrive\Desktop\Microsoft UI.html")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str


app = FastAPI(title="AI Browser Agent Web UI")

# Add CORS middleware to allow requests from the HTML file
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=FileResponse)
async def root() -> FileResponse:
    """
    Serve the user's custom chat UI.

    Open http://127.0.0.1:8000/ in your browser after starting web_app.py.
    """
    # Serve the user's custom UI if it exists, otherwise fall back to default
    if USER_UI_HTML.exists():
        return FileResponse(USER_UI_HTML)
    return FileResponse(INDEX_HTML)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """
    Chat endpoint: forwards the user message (and optional history)
    to the BrowserAgent and returns the final reply.
    """
    # Build history in the format expected by BrowserAgent
    history = [{"role": m.role, "content": m.content} for m in req.history]

    agent = None
    try:
        # Create kernel and agent (mirrors desktop AgentWorker behaviour)
        kernel = LLMFactory.create_kernel()
        agent = BrowserAgent(kernel=kernel, use_mcp=True)

        # Run the agent to get a final reply
        reply = await agent.run(
            user_goal=req.message,
            history=history,
        )
        return ChatResponse(reply=reply)
    except Exception as e:
        # Surface a helpful error to the UI (instead of a silent connection error).
        raise HTTPException(
            status_code=500,
            detail=(
                "Agent failed to run. This is usually due to missing/incorrect LLM configuration "
                "(no `AI-browser/local_settings` file, or wrong Azure/OpenAI/Ollama settings), "
                f"or the provider server being offline. Error: {e}"
            ),
        )
    finally:
        if agent is not None:
            try:
                await agent.cleanup()
            except Exception:
                # Don't mask the main error with cleanup issues.
                pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "web_app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )

