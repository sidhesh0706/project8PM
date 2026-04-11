import re
from typing import Iterable

from models import INVESTIGATION_ACTIONS, TERMINAL_ACTIONS, ResolutionOperation


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _coverage_score(values: Iterable[str], reference: Iterable[str]) -> float:
    reference_list = [item for item in reference if item]
    if not reference_list:
        return 1.0
    normalized_values = {_normalize(item) for item in values}
    hits = 0
    for item in reference_list:
        normalized_item = _normalize(item)
        if normalized_item in normalized_values:
            hits += 1
    return hits / len(reference_list)


def _term_score(text: str, terms: Iterable[str]) -> float:
    term_list = [term for term in terms if term]
    if not term_list:
        return 1.0
    normalized = _normalize(text)
    hits = sum(1 for term in term_list if _normalize(term) in normalized)
    return hits / len(term_list)


def score_investigation(
    case: dict,
    operation: ResolutionOperation,
    gathered_facts: list[str],
    action_history: list[str],
) -> dict:
    facts_by_action = case.get("facts_by_action", {})
    expected = case.get("expected_resolution", {})
    revealed_facts = facts_by_action.get(operation.action_type, [])
    newly_revealed = [fact for fact in revealed_facts if fact not in gathered_facts]
    good_actions = set(expected.get("good_actions", []))
    optional_actions = set(expected.get("optional_actions", []))

    if operation.action_type not in INVESTIGATION_ACTIONS:
        return {
            "reward": 0.0,
            "reason": "invalid investigation action",
            "new_facts": [],
            "evidence_quality": 0.0,
            "resolution_quality": 0.0,
            "safety_quality": 0.0,
        }

    if operation.action_type in action_history:
        return {
            "reward": 0.05,
            "reason": "repeated investigation step",
            "new_facts": [],
            "evidence_quality": 0.1,
            "resolution_quality": 0.0,
            "safety_quality": 1.0,
        }

    if newly_revealed:
        reward = 0.35 if operation.action_type in good_actions else 0.2
        if operation.action_type in optional_actions and operation.action_type not in good_actions:
            reward = max(reward, 0.2)
        return {
            "reward": reward,
            "reason": "useful evidence gathered",
            "new_facts": newly_revealed,
            "evidence_quality": 1.0 if operation.action_type in good_actions else 0.7,
            "resolution_quality": 0.0,
            "safety_quality": 1.0,
        }

    if operation.action_type in good_actions or operation.action_type in optional_actions:
        return {
            "reward": 0.1,
            "reason": "safe but low-yield investigation step",
            "new_facts": [],
            "evidence_quality": 0.4,
            "resolution_quality": 0.0,
            "safety_quality": 1.0,
        }

    return {
        "reward": 0.0,
        "reason": "irrelevant investigation step",
        "new_facts": [],
        "evidence_quality": 0.0,
        "resolution_quality": 0.0,
        "safety_quality": 1.0,
    }


def score_resolution(
    case: dict,
    operation: ResolutionOperation,
    gathered_facts: list[str],
    action_history: list[str],
) -> dict:
    expected = case.get("expected_resolution", {})
    required_facts = expected.get("required_facts", [])
    good_actions = expected.get("good_actions", [])
    disallowed_actions = set(expected.get("disallowed_actions", []))
    customer_terms = expected.get("customer_terms", [])
    resolution_text = f"{operation.note} {operation.customer_message}"
    evidence_quality = _coverage_score(gathered_facts, required_facts)
    workflow_quality = _coverage_score(action_history, good_actions)
    communication_quality = _term_score(resolution_text, customer_terms)
    safety_quality = 0.0 if operation.action_type in disallowed_actions else 1.0

    if operation.action_type not in TERMINAL_ACTIONS:
        return {
            "reward": 0.0,
            "case_score": 0.0,
            "reason": "resolution step must use a terminal action",
            "evidence_quality": 0.0,
            "resolution_quality": 0.0,
            "safety_quality": 0.0,
            "successful": False,
        }

    if operation.action_type != expected.get("action_type"):
        reward = 0.0 if operation.action_type in disallowed_actions else 0.15
        return {
            "reward": reward,
            "case_score": reward,
            "reason": f"wrong final action (expected {expected.get('action_type')})",
            "evidence_quality": evidence_quality,
            "resolution_quality": 0.0,
            "safety_quality": safety_quality,
            "successful": False,
        }

    resolution_quality = 0.55 + (0.2 * evidence_quality) + (0.15 * workflow_quality) + (0.1 * communication_quality)
    case_score = round(min(resolution_quality, 1.0), 2)
    reason = expected.get("reason", "correct resolution")
    return {
        "reward": case_score,
        "case_score": case_score,
        "reason": reason,
        "evidence_quality": round(evidence_quality, 2),
        "resolution_quality": round(case_score, 2),
        "safety_quality": safety_quality,
        "successful": True,
    }


def grade_task(task_name: str, operations: list[ResolutionOperation]) -> dict:
    from tasks import TASKS

    task = TASKS[task_name]
    max_steps = int(task.get("config", {}).get("max_steps_per_case", 5))
    grouped: dict[str, list[ResolutionOperation]] = {}
    for operation in operations:
        grouped.setdefault(operation.case_id, []).append(operation)

    trajectory = []
    case_scores: list[float] = []
    for case in task["cases"]:
        case_operations = grouped.get(case["id"], [])
        gathered_facts: list[str] = []
        action_history: list[str] = []
        case_score = 0.0
        successful = False
        reason = "no operations submitted for case"
        for index, operation in enumerate(case_operations[:max_steps], start=1):
            if operation.action_type in INVESTIGATION_ACTIONS:
                result = score_investigation(case, operation, gathered_facts, action_history)
                action_history.append(operation.action_type)
                for fact in result["new_facts"]:
                    if fact not in gathered_facts:
                        gathered_facts.append(fact)
                reason = result["reason"]
                continue

            result = score_resolution(case, operation, gathered_facts, action_history)
            action_history.append(operation.action_type)
            case_score = float(result["case_score"])
            successful = bool(result["successful"])
            reason = result["reason"]
            break

        case_scores.append(round(case_score, 2))
        trajectory.append(
            {
                "case_id": case["id"],
                "steps_used": min(len(case_operations), max_steps),
                "gathered_facts": gathered_facts,
                "action_history": action_history,
                "case_score": round(case_score, 2),
                "successful": successful,
                "reason": reason,
            }
        )

    cumulative_score = round(sum(case_scores) / len(case_scores), 2) if case_scores else 0.0
    return {
        "task_name": task_name,
        "done": True,
        "attempted_cases": len(task["cases"]),
        "total_cases": len(task["cases"]),
        "cumulative_score": cumulative_score,
        "resolution_accuracy": round(len([item for item in trajectory if item["successful"]]) / len(trajectory), 2) if trajectory else 0.0,
        "trajectory": trajectory,
    }
