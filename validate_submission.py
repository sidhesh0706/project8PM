import json
import os
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app import app
from tasks import TASKS


REPO_ROOT = Path(__file__).resolve().parent
OPENENV_PATH = REPO_ROOT / "openenv.yaml"
SCORES_PATH = REPO_ROOT / "scores.json"
INFERENCE_PATH = REPO_ROOT / "inference.py"

FAILURES: list[str] = []
PASSES: list[str] = []


def fail(message: str) -> None:
    FAILURES.append(message)
    print(f"[FAIL] {message}")


def ok(message: str) -> None:
    PASSES.append(message)
    print(f"[PASS] {message}")


def assert_true(condition: bool, message: str) -> None:
    if condition:
        ok(message)
    else:
        fail(message)


def parse_openenv_task_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    current_task: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("- name:"):
            current_task = line.split(":", 1)[1].strip()
        elif line.startswith("num_cases:") and current_task is not None:
            value = line.split(":", 1)[1].strip()
            try:
                counts[current_task] = int(value)
            except ValueError:
                pass
    return counts


def parse_openenv_endpoints(text: str) -> list[str]:
    endpoints: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("- ") and "/" in line:
            endpoint = line[2:].strip()
            if endpoint.startswith(("GET ", "POST ", "PUT ", "PATCH ", "DELETE ")):
                endpoints.append(endpoint)
    return endpoints


def validate_structure() -> None:
    assert_true(OPENENV_PATH.exists(), "openenv.yaml exists")
    assert_true(INFERENCE_PATH.exists(), "inference.py exists")
    assert_true(len(TASKS) >= 3, "at least 3 tasks are available")

    for task_name, task in TASKS.items():
        cases = task["cases"]
        assert_true(len(cases) > 0, f"{task_name}: has cases")
        assert_true(all("expected_resolution" in case for case in cases), f"{task_name}: cases define expected resolutions")


def validate_openenv_alignment() -> None:
    content = OPENENV_PATH.read_text(encoding="utf-8")
    yaml_counts = parse_openenv_task_counts(content)
    actual_counts = {name: len(info["cases"]) for name, info in TASKS.items()}
    assert_true(yaml_counts == actual_counts, "openenv task counts match dataset")

    endpoints = set(parse_openenv_endpoints(content))
    required_endpoints = {
        "POST /reset",
        "POST /step",
        "GET /state",
        "GET /tasks",
        "GET /manifest",
        "GET /",
    }
    assert_true(required_endpoints.issubset(endpoints), "openenv lists required API endpoints")


def validate_api_runtime() -> None:
    client = TestClient(app)

    root = client.get("/")
    assert_true(root.status_code == 200, "GET / returns 200")
    assert_true(root.json().get("status") == "running", "GET / reports running status")

    tasks_resp = client.get("/tasks")
    assert_true(tasks_resp.status_code == 200, "GET /tasks returns 200")
    assert_true(set(tasks_resp.json().keys()) == set(TASKS.keys()), "GET /tasks keys match loaded tasks")

    reset_resp = client.post("/reset", json={"task_name": "easy"})
    assert_true(reset_resp.status_code == 200, "POST /reset accepts body payload")
    observation = reset_resp.json()
    session_id = observation.get("session_id")
    assert_true(bool(session_id), "/reset returns session_id")
    tickets = observation.get("tickets", [])
    assert_true(len(tickets) == 1, "/reset exposes one active ticket")

    first_ticket_id = tickets[0]["id"] if tickets else None
    step_resp = client.post(
        "/step",
        json={
            "session_id": session_id,
            "operations": [
                {
                    "case_id": first_ticket_id,
                    "action_type": "lookup_user",
                    "target": "account",
                    "note": "Validation probe investigation step.",
                    "customer_message": "I'm checking the account details now.",
                }
            ],
        },
    )
    assert_true(step_resp.status_code == 200, "POST /step accepts operation payload")
    step_json = step_resp.json()
    assert_true("reward" in step_json, "/step returns reward")
    assert_true("done" in step_json, "/step returns done")
    assert_true("info" in step_json, "/step returns info")

    state_resp = client.get("/state", params={"session_id": session_id})
    assert_true(state_resp.status_code == 200, "GET /state returns 200 for active session")

    report_resp = client.get("/report", params={"session_id": session_id})
    assert_true(report_resp.status_code == 200, "GET /report returns 200")
    report_json = report_resp.json()
    assert_true("trajectory" in report_json, "/report returns trajectory")
    assert_true("resolution_accuracy" in report_json, "/report returns resolution_accuracy")

    summary_resp = client.get("/sessions/summary")
    assert_true(summary_resp.status_code == 200, "GET /sessions/summary returns 200")

    manifest_resp = client.get("/manifest")
    assert_true(manifest_resp.status_code == 200, "GET /manifest returns 200")
    manifest_json = manifest_resp.json()
    assert_true("task_counts" in manifest_json, "/manifest returns task_counts")
    assert_true("action_types" in manifest_json, "/manifest returns action_types")


def validate_baseline() -> None:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["API_KEY"] = ""
    env["HF_TOKEN"] = ""

    proc = subprocess.run(
        [sys.executable, "inference.py"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    assert_true(proc.returncode == 0, "inference.py exits successfully")
    assert_true("[START]" in output, "inference logs contain [START]")
    assert_true("[STEP]" in output, "inference logs contain [STEP]")
    assert_true("[END]" in output, "inference logs contain [END]")

    assert_true(SCORES_PATH.exists(), "scores.json is generated")
    if SCORES_PATH.exists():
        try:
            scores = json.loads(SCORES_PATH.read_text(encoding="utf-8"))
            expected = set(TASKS.keys())
            assert_true(set(scores.keys()) == expected, "scores.json contains all task keys")
            in_range = all(isinstance(v, (int, float)) and 0.0 <= float(v) <= 1.0 for v in scores.values())
            assert_true(in_range, "all scores are numeric in range [0.0, 1.0]")
        except json.JSONDecodeError:
            fail("scores.json is valid JSON")


def main() -> int:
    print("=== Submission Validation ===")
    validate_structure()
    validate_openenv_alignment()
    validate_api_runtime()
    validate_baseline()

    print("\n=== Summary ===")
    print(f"Passed checks: {len(PASSES)}")
    print(f"Failed checks: {len(FAILURES)}")
    if FAILURES:
        print("Validation status: FAILED")
        return 1
    print("Validation status: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
