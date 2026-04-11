import re
from difflib import SequenceMatcher
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
    scores = []
    for term in term_list:
        normalized_term = _normalize(term)
        if normalized_term in normalized:
            scores.append(1.0)
            continue
        token_overlap = _coverage_score(re.findall(r"[a-z0-9_]+", normalized), re.findall(r"[a-z0-9_]+", normalized_term))
        fuzzy_ratio = SequenceMatcher(None, normalized, normalized_term).ratio()
        scores.append(max(token_overlap, fuzzy_ratio))
    return sum(scores) / len(term_list)


def _incident_correlation_score(case: dict, active_incidents: list[str]) -> float:
    tags = case.get("correlation_tags", [])
    if not tags:
        return 0.0
    for tag in tags:
        if any(tag in incident for incident in active_incidents):
            return 1.0
    return 0.0


def score_investigation(
    case: dict,
    operation: ResolutionOperation,
    gathered_facts: list[str],
    action_history: list[str],
    active_incidents: list[str] | None = None,
) -> dict:
    active_incidents = active_incidents or []
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
        correlation_bonus = 0.05 * _incident_correlation_score(case, active_incidents)
        return {
            "reward": round(min(reward + correlation_bonus, 0.4), 2),
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
    active_incidents: list[str] | None = None,
) -> dict:
    active_incidents = active_incidents or []
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
    incident_awareness = _incident_correlation_score(case, active_incidents)

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

    resolution_quality = (
        0.5
        + (0.2 * evidence_quality)
        + (0.12 * workflow_quality)
        + (0.1 * communication_quality)
        + (0.08 * incident_awareness)
    )
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
    from env import HelpdeskOpsEnv
    from models import Action

    env = HelpdeskOpsEnv(task_name=task_name)
    env.reset()
    grouped: dict[str, list[ResolutionOperation]] = {}
    for operation in operations:
        grouped.setdefault(operation.case_id, []).append(operation)

    replay_exhausted = False
    while not env.state().done:
        current_ticket = env.state().tickets[0]
        case_operations = grouped.get(current_ticket.id, [])
        if case_operations:
            operation = case_operations.pop(0)
        else:
            replay_exhausted = True
            break
        env.step(Action(operations=[operation]))

    report = env.episode_report()
    report["done"] = report["done"] and not replay_exhausted
    report["fully_replayed"] = not replay_exhausted and report["tickets_remaining"] == 0
    return report
