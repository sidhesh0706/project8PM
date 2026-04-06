from pydantic import BaseModel
from typing import Literal, List, Optional


class CodeSnippet(BaseModel):
    id: str
    code: str
    language: str = "python"
    context: str = ""
    pr_description: str = ""
    failed_test: Optional[str] = None


class BugReport(BaseModel):
    snippet_id: str
    bug_type: Literal[
        "off_by_one",
        "wrong_variable",
        "missing_return",
        "mutable_default_arg",
        "wrong_logic",
        "missing_edge_case",
        "incorrect_exception_handling",
        "hardcoded_secret",
        "no_bug"
    ]
    explanation: str
    severity: Literal["low", "medium", "high"]
    suggested_fix: str


class Observation(BaseModel):
    snippets: List[CodeSnippet]
    step_number: int
    total_snippets: int
    task_name: str


class Action(BaseModel):
    reports: List[BugReport]


class StepResult(BaseModel):
    observation: Observation
    reward: float
    done: bool
    info: dict