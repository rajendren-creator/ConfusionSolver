import logging
import os
from pathlib import Path
from typing import Literal

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .prompt import GREETING, SYSTEM_PROMPT

load_dotenv()

MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5")
EFFORT = os.getenv("CLAUDE_EFFORT", "medium")
MAX_TURNS = 60

STATIC_DIR = Path(__file__).parent / "static"

log = logging.getLogger("confusionsolver")
client = anthropic.Anthropic()
app = FastAPI(title="ConfusionSolver")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=MAX_TURNS)


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/greeting")
def greeting():
    return {"greeting": GREETING}


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.post("/api/chat")
def chat(req: ChatRequest):
    messages = [m.model_dump() for m in req.messages]

    def generate():
        try:
            with client.beta.messages.stream(
                model=MODEL,
                max_tokens=16000,
                system=[{
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=messages,
                thinking={"type": "adaptive"},
                output_config={"effort": EFFORT},
                # On a safety-classifier decline, the API retries on Anthropic's
                # recommended fallback model instead of returning a refusal.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            ) as stream:
                for text in stream.text_stream:
                    yield text
                final = stream.get_final_message()

            if final.stop_reason == "refusal":
                yield (
                    "\n\nI'm not able to continue with that request. If you're going "
                    "through something difficult, please consider reaching out to "
                    "someone you trust or a local support line."
                )
            elif final.stop_reason == "max_tokens":
                yield "\n\n_(Response was cut short. Ask me to continue.)_"
        except anthropic.RateLimitError:
            yield "\n\n_The service is busy right now. Please try again in a moment._"
        except anthropic.APIStatusError as e:
            log.error("Claude API error %s: %s", e.status_code, e.message)
            yield "\n\n_Something went wrong on our side. Please try again._"
        except anthropic.APIConnectionError:
            log.exception("Could not reach Claude API")
            yield "\n\n_Couldn't reach the AI service. Check the connection and try again._"

    return StreamingResponse(
        generate(),
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
