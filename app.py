from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from env import CodeReviewEnv
from models import Action, Observation, State, StepResult
from graders import grade_task
from tasks import TASKS

app = FastAPI(
    title="Code Review Environment",
    description="An OpenEnv environment where an agent reviews Python and JavaScript code for bugs.",
    version="1.0.0",
)

# One env instance per session — stored in memory
envs: dict[str, CodeReviewEnv] = {}
TASK_NAMES = list(TASKS.keys())


def get_env(session_id: str) -> CodeReviewEnv:
    env = envs.get(session_id)
    if env is None:
        raise HTTPException(
            status_code=400,
            detail="Unknown session_id. Call /reset first to start a new episode.",
        )
    return env


# ─── HEALTH CHECK ─────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "name": "code-review-env",
        "version": "1.0.0",
        "tasks": TASK_NAMES,
        "languages": ["python", "javascript"],
        "status": "running",
    }


# ─── OPENENV ENDPOINTS ────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/reset", response_model=Observation)
def reset(task_name: str = "easy"):
    """Start a fresh episode for the given task."""
    if task_name not in TASKS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown task '{task_name}'. Choose from: {', '.join(TASK_NAMES)}"
        )
    session_id = uuid4().hex
    env = CodeReviewEnv(task_name=task_name, session_id=session_id)
    envs[session_id] = env
    obs = env.reset()
    return obs


@app.post("/step", response_model=StepResult)
def step(action: Action, session_id: str):
    """Submit bug reports for the current episode."""
    env = get_env(session_id)
    try:
        result = env.step(action)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@app.get("/state", response_model=State)
def state(session_id: str):
    """Get the current episode state without advancing the episode."""
    env = get_env(session_id)
    return env.state()


@app.get("/tasks")
def list_tasks():
    """List all available tasks and their descriptions."""
    return {
        name: {
            "description": info["description"],
            "num_snippets": len(info["snippets"]),
        }
        for name, info in TASKS.items()
    }


@app.get("/web", response_class=HTMLResponse)
def web_view():
    task_cards = "".join(
        f"""
        <article class="card">
            <h2>{name.title()}</h2>
            <p>{info["description"]}</p>
            <div class="meta">Snippets: {len(info["snippets"])}</div>
        </article>
        """
        for name, info in TASKS.items()
    )

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Code Review Environment</title>
        <style>
            :root {{
                --bg: #0b1020;
                --panel: #121933;
                --panel-2: #1b2550;
                --text: #edf2ff;
                --muted: #a9b5d6;
                --accent: #66e3c4;
                --accent-2: #8cb6ff;
                --border: rgba(255,255,255,0.08);
            }}
            * {{
                box-sizing: border-box;
            }}
            body {{
                margin: 0;
                font-family: "Segoe UI", system-ui, sans-serif;
                background:
                    radial-gradient(circle at top left, rgba(102, 227, 196, 0.14), transparent 28%),
                    radial-gradient(circle at top right, rgba(140, 182, 255, 0.16), transparent 30%),
                    linear-gradient(180deg, #0b1020 0%, #10162d 100%);
                color: var(--text);
            }}
            .wrap {{
                max-width: 1040px;
                margin: 0 auto;
                padding: 40px 20px 56px;
            }}
            .hero {{
                padding: 28px;
                border: 1px solid var(--border);
                border-radius: 24px;
                background: linear-gradient(180deg, rgba(18, 25, 51, 0.96), rgba(16, 22, 45, 0.92));
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.28);
            }}
            .eyebrow {{
                display: inline-block;
                padding: 6px 12px;
                border-radius: 999px;
                background: rgba(102, 227, 196, 0.12);
                color: var(--accent);
                font-size: 12px;
                letter-spacing: 0.08em;
                text-transform: uppercase;
            }}
            h1 {{
                margin: 16px 0 10px;
                font-size: clamp(32px, 6vw, 52px);
                line-height: 1.05;
            }}
            .lede {{
                max-width: 720px;
                color: var(--muted);
                font-size: 18px;
                line-height: 1.6;
            }}
            .actions {{
                display: flex;
                flex-wrap: wrap;
                gap: 12px;
                margin-top: 24px;
            }}
            .actions a {{
                text-decoration: none;
                color: var(--text);
                background: var(--panel-2);
                border: 1px solid var(--border);
                padding: 12px 16px;
                border-radius: 14px;
            }}
            .actions a.primary {{
                background: linear-gradient(135deg, var(--accent), var(--accent-2));
                color: #08101e;
                font-weight: 600;
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 16px;
                margin-top: 28px;
            }}
            .card {{
                padding: 18px;
                border-radius: 18px;
                border: 1px solid var(--border);
                background: rgba(18, 25, 51, 0.88);
            }}
            .card h2 {{
                margin: 0 0 10px;
                font-size: 20px;
            }}
            .card p {{
                margin: 0;
                color: var(--muted);
                line-height: 1.55;
                min-height: 72px;
            }}
            .meta {{
                margin-top: 14px;
                color: var(--accent);
                font-size: 14px;
            }}
            .footer {{
                margin-top: 24px;
                color: var(--muted);
                font-size: 14px;
            }}
            code {{
                background: rgba(255,255,255,0.06);
                padding: 2px 6px;
                border-radius: 8px;
            }}
        </style>
    </head>
    <body>
        <main class="wrap">
            <section class="hero">
                <span class="eyebrow">OpenEnv Benchmark</span>
                <h1>Code Review Environment</h1>
                <p class="lede">
                    A deployable benchmark where agents review Python and JavaScript snippets,
                    classify bugs, assign severity, and suggest fixes across easy, medium, hard,
                    and security-focused tasks.
                </p>
                <div class="actions">
                    <a class="primary" href="/docs">Open API Docs</a>
                    <a href="/tasks">View Tasks JSON</a>
                    <a href="/openapi.json">OpenAPI Schema</a>
                    <a href="/health">Health Check</a>
                </div>
            </section>
            <section class="grid">
                {task_cards}
            </section>
            <p class="footer">
                Start an episode with <code>POST /reset?task_name=easy</code> and continue it with
                <code>POST /step?session_id=...</code>.
            </p>
        </main>
    </body>
    </html>
    """


@app.post("/grade")
def grade(action: Action, task_name: str = "easy"):
    """Grade a full-task submission without stepping through the live environment."""
    if task_name not in TASKS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown task '{task_name}'. Choose from: {', '.join(TASK_NAMES)}",
        )
    return grade_task(task_name, action.reports)


# ─── RUN ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
