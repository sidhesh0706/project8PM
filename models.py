from typing import List, Literal, Optional

from pydantic import BaseModel


BUG_TYPES = (
    "off_by_one",
    "wrong_variable",
    "missing_return",
    "mutable_default_arg",
    "wrong_logic",
    "missing_edge_case",
    "incorrect_exception_handling",
    "hardcoded_secret",
    "no_bug",
)

SEVERITIES = ("low", "medium", "high")

BugType = Literal[
    "off_by_one",
    "wrong_variable",
    "missing_return",
    "mutable_default_arg",
    "wrong_logic",
    "missing_edge_case",
    "incorrect_exception_handling",
    "hardcoded_secret",
    "no_bug",
]

Severity = Literal["low", "medium", "high"]


class CodeSnippet(BaseModel):
    id: str
    code: str
    language: str = "python"
    context: str = ""
    pr_description: str = ""
    failed_test: Optional[str] = None


class BugReport(BaseModel):
    snippet_id: str
    bug_type: BugType
    explanation: str
    severity: Severity
    suggested_fix: str


class Observation(BaseModel):
    snippets: List[CodeSnippet]
    step_number: int
    total_snippets: int
    task_name: str
    session_id: Optional[str] = None


class State(BaseModel):
    snippets: List[CodeSnippet]
    step_number: int
    total_snippets: int
    task_name: str
    session_id: Optional[str] = None
    done: bool
    snippets_remaining: int
    cumulative_score: float


class Reward(BaseModel):
    value: float
    reason: str


class Action(BaseModel):
    reports: List[BugReport]


class StepResult(BaseModel):
    observation: Observation
    reward: float
    done: bool
    info: dict
