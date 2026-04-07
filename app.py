from uuid import uuid4

from fastapi import FastAPI, HTTPException

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
