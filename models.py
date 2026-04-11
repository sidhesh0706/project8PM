from typing import List, Literal, Optional

from pydantic import BaseModel, Field

ACTION_TYPES = (
    "lookup_user",
    "lookup_device",
    "search_kb",
    "check_access_policy",
    "review_login_risk",
    "reset_password",
    "unlock_account",
    "issue_vpn_profile",
    "grant_app_access",
    "assign_license",
    "revoke_access",
    "deny_request",
    "escalate_security",
    "escalate_it_ops",
    "close_as_no_issue",
)

PRIORITIES = ("low", "medium", "high", "critical")
INVESTIGATION_ACTIONS = (
    "lookup_user",
    "lookup_device",
    "search_kb",
    "check_access_policy",
    "review_login_risk",
)
TERMINAL_ACTIONS = tuple(action for action in ACTION_TYPES if action not in INVESTIGATION_ACTIONS)

ActionType = Literal[
    "lookup_user",
    "lookup_device",
    "search_kb",
    "check_access_policy",
    "review_login_risk",
    "reset_password",
    "unlock_account",
    "issue_vpn_profile",
    "grant_app_access",
    "assign_license",
    "revoke_access",
    "deny_request",
    "escalate_security",
    "escalate_it_ops",
    "close_as_no_issue",
]

Priority = Literal["low", "medium", "high", "critical"]


class TicketItem(BaseModel):
    id: str
    title: str
    requester: str
    department: str
    priority: Priority
    category: str
    user_message: str
    visible_context: List[str] = Field(default_factory=list)
    available_actions: List[ActionType] = Field(default_factory=list)
    gathered_facts: List[str] = Field(default_factory=list)
    action_history: List[str] = Field(default_factory=list)


class ResolutionOperation(BaseModel):
    case_id: str
    action_type: ActionType
    target: str = ""
    note: str = ""
    customer_message: str = ""


class Action(BaseModel):
    operations: List[ResolutionOperation] = Field(default_factory=list)


class ResetRequest(BaseModel):
    task_name: str = "easy"


class StepRequest(BaseModel):
    session_id: Optional[str] = None
    operations: Optional[List[ResolutionOperation]] = None
    action: Optional[Action] = None


class Observation(BaseModel):
    tickets: List[TicketItem]
    snippets: List[TicketItem] = Field(default_factory=list)
    step_number: int
    current_case_step: int
    total_tickets: int
    total_snippets: int
    task_name: str
    session_id: Optional[str] = None


class State(BaseModel):
    tickets: List[TicketItem]
    snippets: List[TicketItem] = Field(default_factory=list)
    step_number: int
    current_case_step: int
    total_tickets: int
    total_snippets: int
    task_name: str
    session_id: Optional[str] = None
    done: bool
    tickets_remaining: int
    snippets_remaining: int
    cumulative_score: float


class Reward(BaseModel):
    value: float
    reason: str
    evidence_quality: float = 0.0
    resolution_quality: float = 0.0
    safety_quality: float = 0.0


class StepResult(BaseModel):
    observation: Observation
    reward: float
    reward_details: Optional[Reward] = None
    done: bool
    info: dict
