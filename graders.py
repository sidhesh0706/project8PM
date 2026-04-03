from models import BugReport
from typing import List


def grade_reports(
    submitted: List[BugReport],
    correct: List[BugReport]
) -> float:
    """
    Grades a list of submitted BugReports against the correct answers.
    Returns a float between 0.0 and 1.0.

    Scoring per snippet:
      - Correct bug_type + correct severity = 1.0
      - Correct bug_type + wrong severity   = 0.7
      - Wrong bug_type but not no_bug       = 0.2
      - Completely missing the snippet      = 0.0
    """
    if not correct:
        return 0.0

    # Build a lookup of submitted reports by snippet_id
    submitted_lookup = {r.snippet_id: r for r in submitted}

    total_score = 0.0

    for correct_report in correct:
        sid = correct_report.snippet_id
        submitted_report = submitted_lookup.get(sid)

        if submitted_report is None:
            # Agent didn't report anything for this snippet
            score = 0.0

        elif submitted_report.bug_type == correct_report.bug_type:
            # Correct bug type — now check severity
            if submitted_report.severity == correct_report.severity:
                score = 1.0
            else:
                score = 0.7  # right bug, wrong severity

        elif correct_report.bug_type == "no_bug":
            # Correct answer was no_bug but agent flagged something
            score = 0.0

        else:
            # Wrong bug type identified
            score = 0.2

        total_score += score

    return round(total_score / len(correct), 2)


def grade_task(task_name: str, submitted: List[BugReport]) -> dict:
    """
    Grades a full task by name.
    Returns a dict with score and per-snippet breakdown.
    """
    from tasks import TASKS

    if task_name not in TASKS:
        raise ValueError(f"Unknown task: {task_name}")

    correct = TASKS[task_name]["answers"]
    submitted_lookup = {r.snippet_id: r for r in submitted}
    correct_lookup = {r.snippet_id: r for r in correct}

    breakdown = {}
    for sid, correct_report in correct_lookup.items():
        submitted_report = submitted_lookup.get(sid)

        if submitted_report is None:
            snippet_score = 0.0
            reason = "not attempted"
        elif submitted_report.bug_type == correct_report.bug_type:
            if submitted_report.severity == correct_report.severity:
                snippet_score = 1.0
                reason = "correct"
            else:
                snippet_score = 0.7
                reason = "right bug type, wrong severity"
        elif correct_report.bug_type == "no_bug":
            snippet_score = 0.0
            reason = "false positive — no bug existed"
        else:
            snippet_score = 0.2
            reason = f"wrong bug type (got {submitted_report.bug_type}, expected {correct_report.bug_type})"

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