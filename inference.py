import os
import json
from typing import List, Optional
from dotenv import load_dotenv
from openai import OpenAI
from models import Action, BugReport
from env import CodeReviewEnv
from tasks import TASKS

load_dotenv()

# ─── CONFIG ───────────────────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.groq.com/openai/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")
HF_TOKEN = os.getenv("HF_TOKEN", "")
BENCHMARK = "code-review-env"
SUCCESS_SCORE_THRESHOLD = 0.5

client = OpenAI(
    api_key=HF_TOKEN if HF_TOKEN else "dummy-key",
    base_url=API_BASE_URL,
)


# ─── STRUCTURED LOGGING ───────────────────────────────────────

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


# ─── PROMPT ───────────────────────────────────────────────────

def build_prompt(snippets) -> str:
    bug_types = [
        "off_by_one", "wrong_variable", "missing_return",
        "mutable_default_arg", "wrong_logic",
        "missing_edge_case", "incorrect_exception_handling", "no_bug"
    ]
    severities = ["low", "medium", "high"]

    snippets_text = ""
    for s in snippets:
        snippets_text += f"\n--- Snippet ID: {s.id} ---\n{s.code}\n"

    return f"""You are an expert Python code reviewer.

Review each code snippet below and identify the bug in each one.
Some snippets may have no bug — in that case use bug_type "no_bug".

Available bug types: {', '.join(bug_types)}
Available severities: {', '.join(severities)}

{snippets_text}

Respond ONLY with a valid JSON array. Each element must have:
- snippet_id: the ID of the snippet
- bug_type: one of the bug types listed above
- explanation: a brief explanation of the bug
- severity: one of the severities listed above
- suggested_fix: the corrected line(s) of code that fix the bug

Example format:
[
  {{
    "snippet_id": "e1",
    "bug_type": "off_by_one",
    "explanation": "Index out of range, should be len(lst)-1",
    "severity": "high",
    "suggested_fix": "return lst[-1]"
  }}
]

Return ONLY the JSON array, no other text.
"""


# ─── AGENT ────────────────────────────────────────────────────

def get_llm_action(snippets) -> Action:
    prompt = build_prompt(snippets)
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        raw = response.choices[0].message.content.strip()
        reports_data = json.loads(raw)
        reports = [BugReport(**r) for r in reports_data]
        return Action(reports=reports)
    except Exception as e:
        print(f"[DEBUG] LLM call failed: {e}", flush=True)
        return _random_action(snippets)


def _random_action(snippets) -> Action:
    import random
    random.seed(42)
    bug_types = [
        "off_by_one", "wrong_variable", "missing_return",
        "mutable_default_arg", "wrong_logic",
        "missing_edge_case", "incorrect_exception_handling", "no_bug"
    ]
    return Action(reports=[
        BugReport(
            snippet_id=s.id,
            bug_type=random.choice(bug_types),
            explanation="Random guess",
            severity=random.choice(["low", "medium", "high"]),
            suggested_fix="Unknown",
        )
        for s in snippets
    ])


# ─── MAIN RUNNER ──────────────────────────────────────────────

def run_task(task_name: str) -> dict:
    env = CodeReviewEnv(task_name=task_name)
    obs = env.reset()

    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False
    error = None

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        step = 1
        done = False

        while not done:
            action = get_llm_action(obs.snippets)
            action_str = f"review({len(action.reports)}_snippets)"

            result = env.step(action)
            obs = result.observation
            reward = result.reward
            done = result.done

            rewards.append(reward)
            steps_taken = step

            log_step(
                step=step,
                action=action_str,
                reward=reward,
                done=done,
                error=error,
            )

            step += 1

        score = sum(rewards) / len(rewards) if rewards else 0.0
        score = min(max(score, 0.0), 1.0)
        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as e:
        error = str(e)
        print(f"[DEBUG] Task error: {e}", flush=True)

    finally:
        log_end(
            success=success,
            steps=steps_taken,
            score=score,
            rewards=rewards,
        )

    return {
        "task": task_name,
        "score": score,
        "success": success,
    }


# ─── ENTRY POINT ──────────────────────────────────────────────

if __name__ == "__main__":
    all_scores = {}

    for task_name in ["easy", "medium", "hard"]:
        result = run_task(task_name)
        all_scores[task_name] = result["score"]

    with open("scores.json", "w") as f:
        json.dump(all_scores, f, indent=2)