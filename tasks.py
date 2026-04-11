import json
from pathlib import Path


DATASET_DIR = Path("dataset")
TASKS: dict[str, dict] = {}
TASK_ORDER = ("easy", "medium", "hard", "security")


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

    tier_dirs = {tier_dir.name: tier_dir for tier_dir in DATASET_DIR.iterdir() if tier_dir.is_dir()}
    ordered_names = [name for name in TASK_ORDER if name in tier_dirs]
    remaining_names = sorted(name for name in tier_dirs if name not in TASK_ORDER)

    for tier_name in [*ordered_names, *remaining_names]:
        tier_dir = tier_dirs[tier_name]
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
                "correlation_tags": case.get("correlation_tags", []),
                "related_services": case.get("related_services", []),
                "sla_minutes": case.get("sla_minutes", 0),
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
