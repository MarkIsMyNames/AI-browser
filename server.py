#!/usr/bin/env python3
"""
Web server for the Browser Automation Agent.
Serves the chat UI and exposes /api/chat for the BrowserAgent.

Run with:
    uvicorn server:app --host 0.0.0.0 --port 8000 --reload

Or directly:
    python server.py
"""

import os
import asyncio
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from agent.browser_agent import create_agent_from_env

# ── Load .env ─────────────────────────────────────────────────────────────────
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    print("[Warning] .env not found — relying on environment variables.")

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Browser Agent API")

# Allow browser requests if you ever serve the UI from a different origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Serve the chat UI at / ────────────────────────────────────────────────────
UI_FILE = Path(__file__).parent / "Microsoft_UI.html"


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the chat UI."""
    if not UI_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="Microsoft_UI.html not found next to server.py"
        )
    return HTMLResponse(content=UI_FILE.read_text(encoding="utf-8"))


# ── Request / Response models ─────────────────────────────────────────────────
class Message(BaseModel):
    role: str        # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Message]] = []


class ChatResponse(BaseModel):
    reply: str


# ── /api/chat ─────────────────────────────────────────────────────────────────
@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Run the BrowserAgent on the user's message and return its final reply.

    The agent may open a real browser window, browse the web, fill forms, etc.
    This endpoint blocks until the agent calls task_complete() or hits the
    max-iteration limit — the UI's stickman will keep spinning until then.
    """
    # Convert Pydantic models → plain dicts the agent expects
    history = [{"role": m.role, "content": m.content} for m in (req.history or [])]

    # Collect status/progress lines so we could log or stream them later
    thinking_log: list[str] = []

    def on_thinking(msg: str):
        thinking_log.append(msg)
        print(f"  [thinking] {msg}")

    def on_agent_message(msg: str):
        print(f"  [agent]    {msg}")

    # When the agent needs human input mid-task, return None so the agent
    # stops and its last message becomes the reply sent back to the UI.
    async def on_request_help(question: str) -> Optional[str]:
        print(f"  [help?]    {question}")
        return None  # signals the agent to stop; UI user can reply next turn

    # When the agent calls task_complete(), accept the summary as the final reply
    async def on_task_complete(summary: str) -> Optional[str]:
        print(f"  [done]     {summary[:120]}...")
        return None  # signals success — stop the agent loop

    try:
        agent = await create_agent_from_env()
        reply = await agent.run(
            user_goal=req.message,
            history=history,
            max_iterations=int(os.getenv("MAX_ITERATIONS", "15")),
            on_thinking=on_thinking,
            on_agent_message=on_agent_message,
            on_request_help=on_request_help,
            on_task_complete=on_task_complete,
        )
        return ChatResponse(reply=reply)

    except ValueError as exc:
        # Missing env vars — give the user a clear message in the chat bubble
        raise HTTPException(status_code=500, detail=str(exc))

    except Exception as exc:
        print(f"[ERROR] {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Agent encountered an error: {exc}"
        )


# ── Dev entrypoint ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,         # auto-reload on file changes
        log_level="info",
    )
