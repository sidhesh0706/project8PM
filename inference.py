import os
import json
import random
from dotenv import load_dotenv
from openai import OpenAI
from models import Action, BugReport
from env import CodeReviewEnv
from tasks import TASKS

load_dotenv()

# ─── CONFIG ───────────────────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.groq.com/openai/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3-8b-8192")
HF_TOKEN = os.getenv("HF_TOKEN", "")

client = OpenAI(
    api_key=HF_TOKEN if HF_TOKEN else "dummy-key",
    base_url=API_BASE_URL,
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

Example format:
[
  {{
    "snippet_id": "e1",
    "bug_type": "off_by_one",
    "explanation": "Index out of range, should be len(lst)-1",
    "severity": "high"
  }}
]

Return ONLY the JSON array, no other text.
"""


# ─── AGENT ────────────────────────────────────────────────────

def run_agent(task_name: str) -> dict:
    env = CodeReviewEnv(task_name=task_name)
    obs = env.reset()

    print(f"\n{'='*50}")
    print(f"Task: {task_name.upper()} — {len(obs.snippets)} snippets")
    print(f"{'='*50}")

    prompt = build_prompt(obs.snippets)

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        raw = response.choices[0].message.content.strip()
        print(f"LLM response:\n{raw}\n")

        # Parse the JSON response
        reports_data = json.loads(raw)
        reports = [BugReport(**r) for r in reports_data]

    except Exception as e:
        print(f"LLM call failed: {e}")
        print("Falling back to random agent...")
        reports = _random_agent(obs.snippets)

    action = Action(reports=reports)
    result = env.step(action)

    print(f"Score: {result.reward}")
    print(f"Breakdown: {result.info['breakdown']}")

    return {
        "task": task_name,
        "score": result.reward,
        "breakdown": result.info["breakdown"],
    }


def _random_agent(snippets) -> list:
    """Fallback agent that picks random labels — used if LLM call fails."""
    bug_types = [
        "off_by_one", "wrong_variable", "missing_return",
        "mutable_default_arg", "wrong_logic",
        "missing_edge_case", "incorrect_exception_handling", "no_bug"
    ]
    random.seed(42)
    return [
        BugReport(
            snippet_id=s.id,
            bug_type=random.choice(bug_types),
            explanation="Random guess",
            severity=random.choice(["low", "medium", "high"]),
        )
        for s in snippets
    ]


# ─── MAIN ─────────────────────────────────────────────────────

if __name__ == "__main__":
    all_scores = {}

    for task_name in ["easy", "medium", "hard"]:
        result = run_agent(task_name)
        all_scores[task_name] = result["score"]

    print(f"\n{'='*50}")
    print("FINAL SCORES")
    print(f"{'='*50}")
    for task, score in all_scores.items():
        print(f"  {task}: {score}")

    with open("scores.json", "w") as f:
        json.dump(all_scores, f, indent=2)

    print(f"\nScores saved to scores.json")