from fastapi import FastAPI, HTTPException
from models import Action, Observation, StepResult
from env import CodeReviewEnv

app = FastAPI(
    title="Code Review Environment",
    description="An OpenEnv environment where an agent reviews Python code for bugs.",
    version="1.0.0",
)

# One env instance per task — stored in memory
envs: dict[str, CodeReviewEnv] = {}


def get_env(task_name: str) -> CodeReviewEnv:
    if task_name not in envs:
        envs[task_name] = CodeReviewEnv(task_name=task_name)
    return envs[task_name]


# ─── HEALTH CHECK ─────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "name": "code-review-env",
        "version": "1.0.0",
        "tasks": ["easy", "medium", "hard", "security"],
        "languages": ["python", "javascript"],
        "status": "running",
    }


# ─── OPENENV ENDPOINTS ────────────────────────────────────────

@app.post("/reset", response_model=Observation)
def reset(task_name: str = "easy"):
    """Start a fresh episode for the given task."""
    if task_name not in ["easy", "medium", "hard"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown task '{task_name}'. Choose from: easy, medium, hard"
        )
    env = get_env(task_name)
    obs = env.reset()
    return obs


@app.post("/step", response_model=StepResult)
def step(action: Action, task_name: str = "easy"):
    """Submit bug reports for the current episode."""
    if task_name not in envs:
        raise HTTPException(
            status_code=400,
            detail="Call /reset first before /step"
        )
    env = get_env(task_name)
    try:
        result = env.step(action)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@app.get("/state", response_model=Observation)
def state(task_name: str = "easy"):
    """Get the current observation without advancing the episode."""
    if task_name not in envs:
        raise HTTPException(
            status_code=400,
            detail="Call /reset first before /state"
        )
    env = get_env(task_name)
    return env.state()


@app.get("/tasks")
def list_tasks():
    """List all available tasks and their descriptions."""
    from tasks import TASKS
    return {
        name: {
            "description": info["description"],
            "num_snippets": len(info["snippets"]),
        }
        for name, info in TASKS.items()
    }


# ─── RUN ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)