import json
import os
from pathlib import Path
import time
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
env_access_times: dict[str, float] = {}
TASK_NAMES = list(TASKS.keys())
REPO_ROOT = Path(__file__).resolve().parent
SCORES_PATH = REPO_ROOT / "scores.json"
WEB_TEMPLATE_PATH = REPO_ROOT / "server" / "web_template.html"
SESSION_TTL_SECONDS = max(int(os.getenv("SESSION_TTL_SECONDS", "3600")), 0)


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


def _cleanup_expired_sessions() -> None:
    if SESSION_TTL_SECONDS <= 0:
        expired_ids = list(envs.keys())
    else:
        cutoff = time.time() - SESSION_TTL_SECONDS
        expired_ids = [session_id for session_id, last_access in env_access_times.items() if last_access < cutoff]

    for session_id in expired_ids:
        envs.pop(session_id, None)
        env_access_times.pop(session_id, None)


def _touch_session(session_id: str) -> None:
    env_access_times[session_id] = time.time()


def get_env(session_id: str) -> HelpdeskOpsEnv:
    _cleanup_expired_sessions()
    env = envs.get(session_id)
    if env is None:
        raise HTTPException(
            status_code=400,
            detail="Unknown session_id. Call /reset first to start a new episode.",
        )
    _touch_session(session_id)
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
    _cleanup_expired_sessions()
    selected_task = payload.task_name if payload is not None else task_name
    if selected_task not in TASKS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown task '{selected_task}'. Choose from: {', '.join(TASK_NAMES)}",
        )
    session_id = uuid4().hex
    env = HelpdeskOpsEnv(task_name=selected_task, session_id=session_id)
    envs[session_id] = env
    _touch_session(session_id)
    return env.reset()


@app.post("/step", response_model=StepResult)
def step(session_id: str | None = None, payload: StepRequest | None = Body(default=None)):
    resolved_session_id = session_id
    resolved_action: Action | None = None

    if payload is not None:
        if payload.session_id:
            resolved_session_id = payload.session_id
        if payload.operations is not None:
            resolved_action = Action(operations=payload.operations)
        elif payload.action is not None:
            resolved_action = payload.action
        elif payload.case_id and payload.action_type is not None:
            resolved_action = Action(
                operations=[
                    {
                        "case_id": payload.case_id,
                        "action_type": payload.action_type,
                        "target": payload.target,
                        "note": payload.note,
                        "customer_message": payload.customer_message,
                    }
                ]
            )
        else:
            resolved_action = None

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
    baseline_scores = load_baseline_scores() or {}
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
        "stateful_features": [
            "persistent_org_state",
            "license_inventory",
            "incident_correlation",
            "approval_and_policy_checks",
            "compliance_flags",
            "action_side_effects",
        ],
        "extra_endpoints": ["/tasks", "/grade", "/report", "/sessions/summary", "/health", "/manifest", "/web"],
    }


@app.get("/report")
def report(session_id: str):
    return get_env(session_id).episode_report()


@app.get("/sessions/summary")
def sessions_summary():
    _cleanup_expired_sessions()
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
    baseline_scores = load_baseline_scores() or {}
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

    template = WEB_TEMPLATE_PATH.read_text(encoding="utf-8")
    return (
        template.replace("__CARDS__", cards)
        .replace("__WORKFLOW__", workflow)
        .replace("__HIGHLIGHTS__", highlights)
    )


@app.post("/grade")
def grade(action: Action, task_name: str = "easy"):
    if task_name not in TASKS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown task '{task_name}'. Choose from: {', '.join(TASK_NAMES)}",
        )
    report = grade_task(task_name, action.operations)
    report.setdefault("fully_replayed", False)
    return report


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7860)
