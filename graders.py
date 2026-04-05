from models import BugReport
from typing import List


def _score_single(submitted: BugReport, correct: BugReport) -> float:
    """
    Score one submitted report against the correct answer.
    - Correct bug_type + correct severity + good fix = 1.0
    - Correct bug_type + correct severity + weak fix = 0.8
    - Correct bug_type + wrong severity + good fix   = 0.7
    - Correct bug_type + wrong severity + weak fix   = 0.5
    - Wrong bug_type                                 = 0.2
    - Correct is no_bug but agent flagged something  = 0.0
    """
    if correct.bug_type == "no_bug":
        return 1.0 if submitted.bug_type == "no_bug" else 0.0

    if submitted.bug_type != correct.bug_type:
        return 0.2

    fix_is_good = (
        submitted.suggested_fix is not None
        and len(submitted.suggested_fix.strip()) > 5
        and submitted.suggested_fix.strip().lower() != "no fix needed."
    )

    if submitted.severity == correct.severity:
        return 1.0 if fix_is_good else 0.8
    else:
        return 0.7 if fix_is_good else 0.5


def grade_reports(
    submitted: List[BugReport],
    correct: List[BugReport]
) -> float:
    if not correct:
        return 0.0

    submitted_lookup = {r.snippet_id: r for r in submitted}
    total_score = 0.0

    for correct_report in correct:
        sid = correct_report.snippet_id
        submitted_report = submitted_lookup.get(sid)
        if submitted_report is None:
            score = 0.0
        else:
            score = _score_single(submitted_report, correct_report)
        total_score += score

    return round(total_score / len(correct), 2)


def grade_task(task_name: str, submitted: List[BugReport]) -> dict:
    from tasks import TASKS

    if task_name not in TASKS:
        raise ValueError(f"Unknown task: {task_name}")

    correct = TASKS[task_name]["answers"]
    submitted_lookup = {r.snippet_id: r for r in submitted}

    breakdown = {}
    for correct_report in correct:
        sid = correct_report.snippet_id
        submitted_report = submitted_lookup.get(sid)

        if submitted_report is None:
            snippet_score = 0.0
            reason = "not attempted"
        else:
            snippet_score = _score_single(submitted_report, correct_report)
            if snippet_score == 1.0:
                reason = "correct"
            elif snippet_score == 0.8:
                reason = "correct bug and severity, fix missing or weak"
            elif snippet_score == 0.7:
                reason = "correct bug type, wrong severity, good fix"
            elif snippet_score == 0.5:
                reason = "correct bug type, wrong severity, weak fix"
            elif snippet_score == 0.2:
                reason = f"wrong bug type (got {submitted_report.bug_type}, expected {correct_report.bug_type})"
            else:
                reason = "false positive — no bug existed"

        breakdown[sid] = {
            "score": snippet_score,
            "reason": reason,
        }

    overall = round(
        sum(v["score"] for v in breakdown.values()) / len(breakdown), 2
    )

    return {
        "task": task_name,
        "overall_score": overall,
        "breakdown": breakdown,
    }