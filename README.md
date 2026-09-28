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

Built with FastAPI and the Claude API (`claude-opus-5`, with streaming replies). The
companion's behaviour is defined in [`app/prompt.py`](app/prompt.py).

## Run locally

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt   # Windows
copy .env.example .env                          # then put your ANTHROPIC_API_KEY in .env
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8010
```

Open http://localhost:8010.

## Configuration

| Variable            | Default          | Notes                                              |
|---------------------|------------------|----------------------------------------------------|
| `ANTHROPIC_API_KEY` | (required)       | Get one at console.anthropic.com                   |
| `CLAUDE_MODEL`      | `claude-opus-5`  | Model ID                                           |
| `CLAUDE_EFFORT`     | `medium`         | `low` / `medium` / `high`. Lower is faster and cheaper |

Refusal fallbacks (`fallbacks: "default"`) are enabled. If Claude's safety classifiers
decline a message, the API retries it on Anthropic's recommended fallback model instead
of returning a refusal.

## Deploy (Render)

`render.yaml` defines a web service. Create a Blueprint from this repo in Render and set
`ANTHROPIC_API_KEY` in the dashboard.

## Notes

- The server is stateless. The browser keeps the conversation and sends it with each
  message, and nothing is stored.
- This is a reflection aid, not therapy. The prompt tells the companion to pause and
  point people to crisis support (Malaysia: 999, Befrienders KL 03-7627 2929) if they
  mention self-harm or danger.
