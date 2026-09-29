import logging
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .prompt import GREETING, SYSTEM_PROMPT

load_dotenv()

PROVIDER = os.getenv("PROVIDER", "claude").lower()
MAX_TURNS = 60

STATIC_DIR = Path(__file__).parent / "static"

BUSY_MSG = "\n\n_The service is busy right now. Please try again in a moment._"
ERROR_MSG = "\n\n_Something went wrong on our side. Please try again._"
CONNECTION_MSG = "\n\n_Couldn't reach the AI service. Check the connection and try again._"

log = logging.getLogger("confusionsolver")
app = FastAPI(title="ConfusionSolver")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.middleware("http")
async def revalidate_static(request, call_next):
    # Make browsers re-check the page and its JS/CSS (cheap via ETag) so updates show up.
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    return response


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=MAX_TURNS)


if PROVIDER == "groq":
    import groq

    GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    groq_client = groq.Groq()

    def stream_reply(messages: list[dict]) -> Iterator[str]:
        try:
            stream = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, *messages],
                max_completion_tokens=8000,
                stream=True,
            )
            finish_reason = None
            for chunk in stream:
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                if choice.delta.content:
                    yield choice.delta.content
                finish_reason = choice.finish_reason or finish_reason
            if finish_reason == "length":
                yield "\n\n_(Response was cut short. Ask me to continue.)_"
        except groq.RateLimitError:
            yield BUSY_MSG
        except groq.APIStatusError as e:
            log.error("Groq API error %s: %s", e.status_code, e.message)
            yield ERROR_MSG
        except groq.APIConnectionError:
            log.exception("Could not reach Groq API")
            yield CONNECTION_MSG

elif PROVIDER == "claude":
    import anthropic

    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5")
    CLAUDE_EFFORT = os.getenv("CLAUDE_EFFORT", "medium")
    claude_client = anthropic.Anthropic()

    def stream_reply(messages: list[dict]) -> Iterator[str]:
        try:
            with claude_client.beta.messages.stream(
                model=CLAUDE_MODEL,
                max_tokens=16000,
                system=[{
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=messages,
                thinking={"type": "adaptive"},
                output_config={"effort": CLAUDE_EFFORT},
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
            yield BUSY_MSG
        except anthropic.APIStatusError as e:
            log.error("Claude API error %s: %s", e.status_code, e.message)
            yield ERROR_MSG
        except anthropic.APIConnectionError:
            log.exception("Could not reach Claude API")
            yield CONNECTION_MSG

else:
    raise RuntimeError(f"Unknown PROVIDER {PROVIDER!r}; use 'claude' or 'groq'")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    # Some browsers request /favicon.ico directly, ignoring the <link rel="icon">.
    return FileResponse(STATIC_DIR / "favicon.svg", media_type="image/svg+xml")


@app.get("/api/greeting")
def greeting():
    return {"greeting": GREETING}


@app.get("/healthz")
def healthz():
    return {"ok": True, "provider": PROVIDER}


@app.post("/api/chat")
def chat(req: ChatRequest):
    messages = [m.model_dump() for m in req.messages]
    return StreamingResponse(
        stream_reply(messages),
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
