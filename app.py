import json
from pathlib import Path
from uuid import uuid4

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from env import HelpdeskOpsEnv
from graders import grade_task
from models import ACTION_TYPES, Action, Observation, PRIORITIES, ResetRequest, State, StepRequest, StepResult
from tasks import TASKS

app = FastAPI(
    title="IT Helpdesk Operations Environment",
    description="An OpenEnv benchmark where agents investigate support tickets, gather evidence, and resolve or escalate them safely.",
    version="2.0.0",
)

envs: dict[str, HelpdeskOpsEnv] = {}
TASK_NAMES = list(TASKS.keys())
SCORES_PATH = Path("scores.json")


def load_baseline_scores() -> dict[str, float] | None:
    if not SCORES_PATH.exists():
        return None
    try:
        data = json.loads(SCORES_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return {str(key): float(value) for key, value in data.items()}


def get_env(session_id: str) -> HelpdeskOpsEnv:
    env = envs.get(session_id)
    if env is None:
        raise HTTPException(
            status_code=400,
            detail="Unknown session_id. Call /reset first to start a new episode.",
        )
    return env


@app.get("/")
def root():
    return {
        "name": "it-helpdesk-ops-env",
        "version": "2.0.0",
        "tasks": TASK_NAMES,
        "domains": ["identity", "endpoint", "network", "saas_access", "security"],
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/reset", response_model=Observation)
def reset(task_name: str = "easy", payload: ResetRequest | None = Body(default=None)):
    selected_task = payload.task_name if payload is not None else task_name
    if selected_task not in TASKS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown task '{selected_task}'. Choose from: {', '.join(TASK_NAMES)}",
        )
    session_id = uuid4().hex
    env = HelpdeskOpsEnv(task_name=selected_task, session_id=session_id)
    envs[session_id] = env
    return env.reset()


@app.post("/step", response_model=StepResult)
def step(session_id: str | None = None, payload: dict | None = Body(default=None)):
    resolved_session_id = session_id
    resolved_action: Action | None = None

    if payload is not None:
        parsed = StepRequest(**payload)
        if parsed.session_id:
            resolved_session_id = parsed.session_id
        if parsed.operations is not None:
            resolved_action = Action(operations=parsed.operations)
        elif parsed.action is not None:
            resolved_action = parsed.action
        else:
            resolved_action = Action(**payload)

    if resolved_session_id is None:
        raise HTTPException(
            status_code=422,
            detail="Missing session_id. Provide it as query param or in request body.",
        )
    if resolved_action is None:
        raise HTTPException(
            status_code=422,
            detail="Missing operations. Provide operations in request body.",
        )

    env = get_env(resolved_session_id)
    try:
        return env.step(resolved_action)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/state", response_model=State)
def state(session_id: str):
    return get_env(session_id).state()


@app.get("/tasks")
def list_tasks():
    return {
        name: {
            "description": info["description"],
            "num_cases": len(info["cases"]),
            "num_snippets": len(info["cases"]),
        }
        for name, info in TASKS.items()
    }


@app.get("/manifest")
def manifest():
    baseline_scores = load_baseline_scores()
    return {
        "name": "it-helpdesk-ops-env",
        "version": "2.0.0",
        "openenv_api": ["reset", "step", "state"],
        "task_names": TASK_NAMES,
        "task_counts": {name: len(info["cases"]) for name, info in TASKS.items()},
        "domains": ["identity", "endpoint", "network", "saas_access", "security", "data_handling"],
        "action_types": list(ACTION_TYPES),
        "priorities": list(PRIORITIES),
        "baseline_scores": baseline_scores,
        "extra_endpoints": ["/tasks", "/grade", "/report", "/sessions/summary", "/health", "/manifest", "/web"],
    }


@app.get("/report")
def report(session_id: str):
    return get_env(session_id).episode_report()


@app.get("/sessions/summary")
def sessions_summary():
    reports = [env.episode_report() for env in envs.values()]
    completed = [report for report in reports if report["done"]]
    average = round(
        sum(report["cumulative_score"] for report in completed) / len(completed),
        2,
    ) if completed else 0.0
    return {
        "total_sessions": len(reports),
        "completed_sessions": len(completed),
        "average_completed_score": average,
        "by_task": {
            task: len([report for report in reports if report["task_name"] == task])
            for task in TASK_NAMES
        },
    }


@app.get("/web", response_class=HTMLResponse)
def web_view():
    baseline_scores = load_baseline_scores()
    cards = "".join(
        f"""
        <article class="card">
            <h2>{name.title()}</h2>
            <p>{info["description"]}</p>
            <div class="meta">Cases: {len(info["cases"])}</div>
            <div class="meta">Baseline: {baseline_scores.get(name, 0.0):.2f}</div>
        </article>
        """
        for name, info in TASKS.items()
    )

    workflow = "".join(
        """
        <li><strong>Investigate</strong>: use identity, device, policy, knowledge-base, or login-risk lookups.</li>
        <li><strong>Interpret</strong>: combine the revealed facts with the user ticket and escalation boundaries.</li>
        <li><strong>Act safely</strong>: resolve, deny, revoke, or escalate with a clear customer-facing response.</li>
        """
    )

    highlights = "".join(
        """
        <li>Multi-step operational reasoning instead of one-shot classification.</li>
        <li>Deterministic grading with evidence quality, resolution quality, and safety quality.</li>
        <li>Coverage across identity, endpoint, SaaS access, incident response, and data-handling cases.</li>
        """
    )

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>IT Helpdesk Operations Environment</title>
        <style>
            :root {{
                --bg: #08111d;
                --panel: rgba(13, 24, 43, 0.86);
                --border: rgba(255, 255, 255, 0.1);
                --text: #eef4ff;
                --muted: #aab7d3;
                --accent: #7cf0c9;
                --accent-2: #7da9ff;
            }}
            * {{ box-sizing: border-box; }}
            body {{
                margin: 0;
                color: var(--text);
                font-family: "Segoe UI", system-ui, sans-serif;
                background:
                    radial-gradient(circle at top left, rgba(124, 240, 201, 0.16), transparent 30%),
                    radial-gradient(circle at top right, rgba(125, 169, 255, 0.18), transparent 28%),
                    linear-gradient(180deg, #08111d 0%, #0f1727 100%);
            }}
            .wrap {{
                max-width: 1080px;
                margin: 0 auto;
                padding: 40px 20px 56px;
            }}
            .hero {{
                border: 1px solid var(--border);
                border-radius: 26px;
                padding: 28px;
                background: linear-gradient(180deg, rgba(13, 24, 43, 0.95), rgba(9, 17, 29, 0.92));
                box-shadow: 0 18px 50px rgba(0, 0, 0, 0.28);
            }}
            .eyebrow {{
                display: inline-block;
                padding: 6px 12px;
                border-radius: 999px;
                background: rgba(124, 240, 201, 0.12);
                color: var(--accent);
                font-size: 12px;
                letter-spacing: 0.08em;
                text-transform: uppercase;
            }}
            h1 {{
                margin: 16px 0 10px;
                font-size: clamp(34px, 6vw, 56px);
                line-height: 1.02;
            }}
            .lede {{
                max-width: 760px;
                color: var(--muted);
                font-size: 18px;
                line-height: 1.65;
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
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid var(--border);
                padding: 12px 16px;
                border-radius: 14px;
            }}
            .actions a.primary {{
                color: #08111d;
                font-weight: 700;
                background: linear-gradient(135deg, var(--accent), var(--accent-2));
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
                gap: 16px;
                margin-top: 28px;
            }}
            .card {{
                padding: 18px;
                border-radius: 18px;
                background: var(--panel);
                border: 1px solid var(--border);
            }}
            .card p {{
                color: var(--muted);
                line-height: 1.55;
                min-height: 92px;
            }}
            .meta {{
                margin-top: 14px;
                color: var(--accent);
                font-size: 14px;
            }}
            .footer {{
                margin-top: 24px;
                color: var(--muted);
            }}
            .section {{
                margin-top: 28px;
                padding: 20px;
                border-radius: 18px;
                background: var(--panel);
                border: 1px solid var(--border);
            }}
            ul {{
                margin: 12px 0 0;
                padding-left: 18px;
                color: var(--muted);
                line-height: 1.7;
            }}
            code {{
                background: rgba(255, 255, 255, 0.06);
                padding: 2px 6px;
                border-radius: 8px;
            }}
        </style>
    </head>
    <body>
        <main class="wrap">
            <section class="hero">
                <span class="eyebrow">OpenEnv Benchmark</span>
                <h1>IT Helpdesk Operations Environment</h1>
                <p class="lede">
                    A multi-step benchmark for operational AI agents. Each episode contains helpdesk or
                    security tickets that require evidence gathering, policy checks, and a safe final action
                    such as unlock, revoke, deny, or escalate.
                </p>
                <div class="actions">
                    <a class="primary" href="/docs">Open API Docs</a>
                    <a href="/tasks">Task Catalog</a>
                    <a href="/manifest">Manifest</a>
                    <a href="/sessions/summary">Session Summary</a>
                    <a href="/health">Health</a>
                </div>
            </section>
            <section class="grid">{cards}</section>
            <section class="section">
                <h2>Agent Workflow</h2>
                <ul>{workflow}</ul>
            </section>
            <section class="section">
                <h2>Why This Benchmark Is Useful</h2>
                <ul>{highlights}</ul>
            </section>
            <p class="footer">
                Start with <code>POST /reset?task_name=easy</code>, inspect the active ticket, then send
                a single operation to <code>POST /step</code> until the case is resolved or escalated.
            </p>
        </main>
    </body>
    </html>
    """


@app.post("/grade")
def grade(action: Action, task_name: str = "easy"):
    if task_name not in TASKS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown task '{task_name}'. Choose from: {', '.join(TASK_NAMES)}",
        )
    return grade_task(task_name, action.operations)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7860)
