import re
from functools import lru_cache
from typing import List

from models import BugReport

STOPWORDS = {
    "added", "after", "against", "agent", "allows", "already", "always", "appears",
    "before", "being", "between", "calls", "case", "causing", "check", "clearly",
    "code", "correct", "crashes", "default", "described", "detected", "does", "edge",
    "errors", "from", "function", "helper", "implementation", "instead", "into",
    "item", "items", "logic", "missing", "must", "needed", "none", "note", "notes",
    "once", "only", "path", "present", "request", "requests", "returns", "review",
    "same", "shared", "should", "snippet", "still", "than", "that", "their", "there",
    "these", "this", "through", "uses", "using", "valid", "value", "when", "with",
    "without", "workflow", "wrong",
}

BUG_TYPE_HINTS = {
    "off_by_one": {"boundary", "index", "range", "slice"},
    "wrong_variable": {"field", "variable", "discount", "tax"},
    "missing_return": {"await", "return", "promise", "json"},
    "mutable_default_arg": {"default", "shared", "none", "list", "dict"},
    "wrong_logic": {"condition", "logic", "query", "comparison", "recursive"},
    "missing_edge_case": {"guard", "missing", "edge", "zero", "empty"},
    "incorrect_exception_handling": {"except", "error", "handle", "close"},
    "hardcoded_secret": {"secret", "credential", "environment", "bcrypt"},
    "no_bug": {"correct", "intended", "expected"},
}

SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}

SALIENT_PATTERNS = (
    "===", "0.0", "await", "basename", "bcrypt", "config", "discount",
    "environment", "exchange", "expires_at", "join", "max_attempts", "md5",
    "none", "null", "overrides", "page_size", "payload", "refresh_token",
    "response", "user_id", "zerodivisionerror",
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z_]{3,}", _normalize(text)))


def _extract_keywords(text: str) -> set[str]:
    normalized = _normalize(text)
    keywords = {
        token for token in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", normalized)
        if token not in STOPWORDS and (len(token) >= 4 or "_" in token or any(ch.isdigit() for ch in token))
    }
    for pattern in SALIENT_PATTERNS:
        if pattern in normalized:
            keywords.add(pattern)
    return keywords


def _extract_code_identifiers(text: str) -> set[str]:
    identifiers = set(re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", text or ""))
    return {
        identifier.lower()
        for identifier in identifiers
        if identifier.lower() not in STOPWORDS and len(identifier) >= 4
    }


def _select_expected_terms(terms: set[str], limit: int = 5) -> set[str]:
    ranked = sorted(
        terms,
        key=lambda term: (
            "_" not in term and not any(ch.isdigit() for ch in term),
            len(term) < 6,
            term,
        ),
    )
    return set(ranked[:limit])


@lru_cache(maxsize=None)
def _load_reference_entry(snippet_id: str) -> dict:
    from tasks import TASKS

    for task_name, task in TASKS.items():
        for snippet in task["snippets"]:
            if snippet.id == snippet_id:
                return {
                    "task_name": task_name,
                    "context": snippet.context or "",
                    "pr_description": snippet.pr_description or "",
                    "failed_test": snippet.failed_test or "",
                    "code": snippet.code or "",
                    "rubric": task.get("rubrics", {}).get(snippet_id, {}),
                    "config": task.get("config", {}),
                }
    return {
        "task_name": "",
        "context": "",
        "pr_description": "",
        "failed_test": "",
        "code": "",
        "rubric": {},
        "config": {},
    }


def _grader_defaults(reference_entry: dict) -> dict:
    return reference_entry.get("config", {}).get("grader_defaults", {})


@lru_cache(maxsize=None)
def _build_snippet_expectations(
    snippet_id: str,
    bug_type: str,
    explanation: str,
    suggested_fix: str,
) -> dict[str, set[str]]:
    metadata = _load_reference_entry(snippet_id)
    bug_hints = BUG_TYPE_HINTS.get(bug_type, set())
    rubric = metadata.get("rubric", {})
    defaults = _grader_defaults(metadata)
    limit = rubric.get("expected_term_limit", defaults.get("expected_term_limit", 5))
    shared_terms = (
        _extract_keywords(metadata["context"])
        | _extract_keywords(metadata["pr_description"])
        | _extract_keywords(metadata["failed_test"])
        | _extract_code_identifiers(metadata["code"])
    )
    rubric_explanation_terms = {term.lower() for term in rubric.get("explanation_terms", [])}
    rubric_fix_terms = {term.lower() for term in rubric.get("fix_terms", [])}
    explanation_terms = _select_expected_terms(
        rubric_explanation_terms | _extract_keywords(explanation) | bug_hints | shared_terms,
        limit=limit,
    )
    fix_terms = _select_expected_terms(
        rubric_fix_terms | _extract_keywords(suggested_fix) | bug_hints | shared_terms,
        limit=limit,
    )
    return {"explanation": explanation_terms, "fix": fix_terms}


def _semantic_match_score(submitted_text: str, reference_text: str) -> float:
    submitted_tokens = _tokenize(submitted_text)
    reference_tokens = _tokenize(reference_text)
    if not submitted_tokens or not reference_tokens:
        return 0.0
    overlap = submitted_tokens & reference_tokens
    return len(overlap) / len(reference_tokens)


def _coverage_score(text: str, expected_terms: set[str]) -> float:
    if not expected_terms:
        return 0.0
    normalized = _normalize(text)
    matches = sum(1 for term in expected_terms if term in normalized)
    return matches / len(expected_terms)


def _explanation_quality_score(submitted: BugReport, correct: BugReport) -> float:
    explanation = submitted.explanation or ""
    if len(explanation.strip()) < 8:
        return 0.0

    snippet_expectations = _build_snippet_expectations(
        correct.snippet_id, correct.bug_type, correct.explanation, correct.suggested_fix
    )
    expected_explanation_terms = snippet_expectations["explanation"]
    coverage = _coverage_score(explanation, expected_explanation_terms)
    similarity = _semantic_match_score(explanation, correct.explanation)
    return max(coverage, similarity)


def _fix_quality_score(submitted: BugReport, correct: BugReport) -> float:
    suggested_fix = submitted.suggested_fix or ""
    if _normalize(suggested_fix) == "no fix needed.":
        return 1.0 if correct.bug_type == "no_bug" else 0.0
    if len(suggested_fix.strip()) <= 5:
        return 0.0

    snippet_expectations = _build_snippet_expectations(
        correct.snippet_id, correct.bug_type, correct.explanation, correct.suggested_fix
    )
    expected_fix_terms = snippet_expectations["fix"]
    coverage = _coverage_score(suggested_fix, expected_fix_terms)
    similarity = _semantic_match_score(suggested_fix, correct.suggested_fix)
    return max(coverage, similarity)


def _severity_alignment(submitted: BugReport, correct: BugReport) -> dict[str, float | bool]:
    if submitted.severity == correct.severity:
        return {"exact": True, "distance": 0, "score": 1.0}

    distance = abs(SEVERITY_ORDER[submitted.severity] - SEVERITY_ORDER[correct.severity])
    if distance == 1:
        return {"exact": False, "distance": distance, "score": 0.5}
    return {"exact": False, "distance": distance, "score": 0.0}


def _quality_thresholds(correct: BugReport) -> dict[str, float]:
    reference_entry = _load_reference_entry(correct.snippet_id)
    defaults = _grader_defaults(reference_entry)
    rubric = reference_entry.get("rubric", {})

    fix_threshold = rubric.get("fix_threshold", defaults.get("fix_threshold", 0.35))
    pair_fix_threshold = rubric.get("pair_fix_threshold", defaults.get("pair_fix_threshold", 0.2))
    pair_explanation_threshold = rubric.get(
        "pair_explanation_threshold",
        defaults.get("pair_explanation_threshold", 0.2),
    )
    return {
        "fix_threshold": float(fix_threshold),
        "pair_fix_threshold": float(pair_fix_threshold),
        "pair_explanation_threshold": float(pair_explanation_threshold),
    }


def _is_high_quality_report(submitted: BugReport, correct: BugReport) -> tuple[bool, float, float]:
    explanation_quality = _explanation_quality_score(submitted, correct)
    fix_quality = _fix_quality_score(submitted, correct)
    thresholds = _quality_thresholds(correct)

    # High-quality answers usually explain the bug clearly and provide a concrete fix.
    is_high_quality = (
        fix_quality >= thresholds["fix_threshold"]
        or (
            fix_quality >= thresholds["pair_fix_threshold"]
            and explanation_quality >= thresholds["pair_explanation_threshold"]
        )
    )

    return is_high_quality, round(explanation_quality, 2), round(fix_quality, 2)


def score_report(submitted: BugReport | None, correct: BugReport) -> dict:
    if submitted is None:
        return {
            "score": 0.0,
            "reason": "not attempted",
            "explanation_quality": 0.0,
            "fix_quality": 0.0,
            "severity_alignment": 0.0,
        }

    if correct.bug_type == "no_bug":
        score = 1.0 if submitted.bug_type == "no_bug" else 0.0
        reason = "correct restraint" if score == 1.0 else "false positive - no bug existed"
        return {
            "score": score,
            "reason": reason,
            "explanation_quality": 1.0 if score == 1.0 else 0.0,
            "fix_quality": 1.0 if score == 1.0 else 0.0,
            "severity_alignment": 1.0 if submitted.severity == correct.severity else 0.0,
        }

    if submitted.bug_type != correct.bug_type:
        severity = _severity_alignment(submitted, correct)
        return {
            "score": 0.2,
            "reason": f"wrong bug type (got {submitted.bug_type}, expected {correct.bug_type})",
            "explanation_quality": 0.0,
            "fix_quality": 0.0,
            "severity_alignment": severity["score"],
        }

    high_quality, explanation_quality, fix_quality = _is_high_quality_report(submitted, correct)
    severity = _severity_alignment(submitted, correct)

    if severity["exact"]:
        score = 1.0 if high_quality else 0.8
        reason = "correct" if high_quality else "correct bug and severity, fix missing or weak"
    else:
        score = 0.7 if high_quality else 0.5
        if severity["score"] == 0.5:
            reason = "correct bug type, adjacent severity, review quality varies"
        else:
            reason = "correct bug type, severity far from expected"

    return {
        "score": score,
        "reason": reason,
        "explanation_quality": explanation_quality,
        "fix_quality": fix_quality,
        "severity_alignment": severity["score"],
    }


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
    return score_report(submitted, correct)["score"]


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
        total_score += score_report(submitted_report, correct_report)["score"]

    return round(total_score / len(correct), 2)


def grade_task(task_name: str, submitted: List[BugReport]) -> dict:
    from tasks import TASKS

    if task_name not in TASKS:
        raise ValueError(f"Unknown task: {task_name}")

    correct = TASKS[task_name]["answers"]
    submitted_lookup = {r.snippet_id: r for r in submitted}
    valid_ids = {r.snippet_id for r in correct}
    extra_reports = sorted(r.snippet_id for r in submitted if r.snippet_id not in valid_ids)

    breakdown = {}
    for correct_report in correct:
        sid = correct_report.snippet_id
        submitted_report = submitted_lookup.get(sid)
        result = score_report(submitted_report, correct_report)
        breakdown[sid] = {
            "score": result["score"],
            "reason": result["reason"],
            "explanation_quality": result["explanation_quality"],
            "fix_quality": result["fix_quality"],
            "severity_alignment": result["severity_alignment"],
        }

    overall = round(
        sum(v["score"] for v in breakdown.values()) / len(breakdown), 2
    )

    return {
        "task": task_name,
        "overall_score": overall,
        "attempted_reports": len([r for r in correct if r.snippet_id in submitted_lookup]),
        "extra_reports": extra_reports,
        "breakdown": breakdown,
    }
