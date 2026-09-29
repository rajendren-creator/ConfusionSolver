# ConfusionSolver

A **Logical Reflection Companion**: a web chat that guides people through a structured,
Socratic inquiry when they're confused, stressed, or stuck on a decision.

It works like this:

1. It asks the user to describe their main challenge and explains the process.
2. It asks a mix of Yes/No questions and deeper clarifying questions.
3. It helps the user examine counterproductive patterns: grudges, impulsive reactions,
   expecting others to change, and perfectionism.
4. It steers toward forgiveness, personal responsibility, and seeking wise counsel.
5. It ends with a **Reflection Summary** of the user's insights and concrete next steps.

Built with FastAPI, with streaming replies from either the Claude API (`claude-opus-5`)
or Groq (free tier, open models). The companion's behaviour is defined in
[`app/prompt.py`](app/prompt.py).

## Run locally

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt   # Windows
copy .env.example .env                          # then set PROVIDER and that provider's key
.venv\Scripts\python run.py
```

Open http://localhost:8010.

## Configuration

| Variable            | Default                | Notes                                              |
|---------------------|------------------------|----------------------------------------------------|
| `PROVIDER`          | `claude`               | `claude` or `groq`                                 |
| `ANTHROPIC_API_KEY` | (needed for `claude`)  | Get one at console.anthropic.com (paid credits)    |
| `CLAUDE_MODEL`      | `claude-opus-5`        | Model ID                                           |
| `CLAUDE_EFFORT`     | `medium`               | `low` / `medium` / `high`. Lower is faster and cheaper |
| `GROQ_API_KEY`      | (needed for `groq`)    | Get one free at console.groq.com                   |
| `GROQ_MODEL`        | `openai/gpt-oss-120b`  | Any Groq chat model, e.g. `llama-3.3-70b-versatile`. Groq retires models over time |

With Claude, refusal fallbacks (`fallbacks: "default"`) are enabled. If Claude's safety
classifiers decline a message, the API retries it on Anthropic's recommended fallback
model instead of returning a refusal.

Groq's free tier has per-minute and per-day request limits. When they're hit, users see
"The service is busy right now".

## Deploy (Render)

`render.yaml` defines a web service. Create a Blueprint from this repo in Render, then in
the dashboard set `PROVIDER` and the matching API key.

## Notes

- The server is stateless. The browser keeps the conversation and sends it with each
  message, and nothing is stored.
- This is a reflection aid, not therapy. The prompt tells the companion to pause and
  point people to crisis support (Malaysia: 999, Befrienders KL 03-7627 2929) if they
  mention self-harm or danger.
