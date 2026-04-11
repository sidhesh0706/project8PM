import json
from pathlib import Path


DATASET_DIR = Path("dataset")
TASKS: dict[str, dict] = {}


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def build_tasks() -> None:
    TASKS.clear()
    if not DATASET_DIR.exists():
        return

    for tier_dir in sorted(DATASET_DIR.iterdir()):
        if not tier_dir.is_dir():
            continue

        cases = _read_json(tier_dir / "cases.json", [])
        if not cases:
            continue

        config = _read_json(tier_dir / "config.json", {})
        description = config.get(
            "description",
            f"{tier_dir.name.capitalize()} tier IT helpdesk and incident triage cases.",
        )

        normalized_cases = []
        for case in cases:
            if not case.get("id") or not case.get("title"):
                continue
            normalized_case = {
                "id": case["id"],
                "title": case["title"],
                "requester": case.get("requester", "Unknown user"),
                "department": case.get("department", "Unknown"),
                "priority": case.get("priority", "medium"),
                "category": case.get("category", "general"),
                "user_message": case.get("user_message", ""),
                "visible_context": case.get("visible_context", []),
                "available_actions": case.get("available_actions", []),
                "facts_by_action": case.get("facts_by_action", {}),
                "expected_resolution": case.get("expected_resolution", {}),
            }
            normalized_cases.append(normalized_case)

        if not normalized_cases:
            continue

        TASKS[tier_dir.name] = {
            "description": description,
            "config": config,
            "cases": normalized_cases,
            # Compatibility alias so validator-facing helpers can still reference "snippets".
            "snippets": normalized_cases,
        }


build_tasks()
