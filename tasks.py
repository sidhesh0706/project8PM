import json
from pathlib import Path

from models import ACTION_TYPES, INVESTIGATION_ACTIONS, TERMINAL_ACTIONS

REPO_ROOT = Path(__file__).resolve().parent
DATASET_DIR = REPO_ROOT / "dataset"
TASKS: dict[str, dict] = {}
TASK_ORDER = ("easy", "medium", "hard", "security")
VALID_ACTIONS = set(ACTION_TYPES)
VALID_INVESTIGATION_ACTIONS = set(INVESTIGATION_ACTIONS)
VALID_TERMINAL_ACTIONS = set(TERMINAL_ACTIONS)


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _validate_case(case: dict, seen_ids: set[str], tier_name: str) -> None:
    case_id = case.get("id")
    if case_id in seen_ids:
        raise ValueError(f"Duplicate case id '{case_id}' found in task '{tier_name}'.")

    available_actions = case.get("available_actions", [])
    invalid_available = sorted(set(available_actions) - VALID_ACTIONS)
    if invalid_available:
        raise ValueError(
            f"Task '{tier_name}' case '{case_id}' contains invalid available_actions: {', '.join(invalid_available)}"
        )

    expected = case.get("expected_resolution", {})
    expected_action = expected.get("action_type")
    if expected_action is not None and expected_action not in VALID_TERMINAL_ACTIONS:
        raise ValueError(
            f"Task '{tier_name}' case '{case_id}' uses invalid terminal action '{expected_action}' in expected_resolution."
        )
    if expected_action is not None and expected_action not in available_actions:
        raise ValueError(
            f"Task '{tier_name}' case '{case_id}' expected action '{expected_action}' is not listed in available_actions."
        )

    for field_name in ("good_actions", "optional_actions", "disallowed_actions"):
        invalid_actions = sorted(set(expected.get(field_name, [])) - VALID_ACTIONS)
        if invalid_actions:
            raise ValueError(
                f"Task '{tier_name}' case '{case_id}' contains invalid {field_name}: {', '.join(invalid_actions)}"
            )

    facts_by_action = case.get("facts_by_action", {})
    invalid_fact_actions = sorted(set(facts_by_action) - VALID_INVESTIGATION_ACTIONS)
    if invalid_fact_actions:
        raise ValueError(
            f"Task '{tier_name}' case '{case_id}' defines facts for non-investigation actions: {', '.join(invalid_fact_actions)}"
        )


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
        seen_ids: set[str] = set()
        for case in cases:
            if not case.get("id") or not case.get("title"):
                continue
            _validate_case(case, seen_ids, tier_name)
            seen_ids.add(case["id"])
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
