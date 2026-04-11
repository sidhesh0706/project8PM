from copy import deepcopy

from graders import score_investigation, score_resolution
from models import (
    INVESTIGATION_ACTIONS,
    Action,
    Observation,
    OrgState,
    Reward,
    State,
    StepResult,
    TicketItem,
)
from tasks import TASKS


DEFAULT_ORG_STATE = {
    "license_inventory": {
        "figma_workspace": 8,
        "power_bi_pro": 6,
        "adobe_creative_cloud": 0,
    },
    "pending_approvals": ["AP-4431", "travel_itinerary_singapore", "weekend_support_roster"],
    "active_incidents": [],
    "compliance_flags": [],
    "access_changes": [],
    "resolved_tickets": [],
    "knowledge_refs": [],
    "audit_log": [],
}

SLA_BY_PRIORITY = {"low": 240, "medium": 120, "high": 60, "critical": 30}
DECISION_STEP_TARGET = {"low": 5, "medium": 4, "high": 3, "critical": 2}


class HelpdeskOpsEnv:
    def __init__(self, task_name: str = "easy", session_id: str | None = None):
        if task_name not in TASKS:
            raise ValueError(f"Unknown task: {task_name}. Choose from {list(TASKS.keys())}")
        self.task_name = task_name
        self.session_id = session_id
        self.task = TASKS[task_name]
        self.cases = deepcopy(self.task["cases"])
        self.max_steps_per_case = int(self.task.get("config", {}).get("max_steps_per_case", 5))

        self._step_number = 0
        self._case_index = 0
        self._case_step = 0
        self._done = False
        self._current_facts: list[str] = []
        self._current_actions: list[str] = []
        self._completed_case_scores: list[float] = []
        self._trajectory: list[dict] = []
        self._org_state = self._initial_org_state()

    def reset(self) -> Observation:
        self._step_number = 0
        self._case_index = 0
        self._case_step = 0
        self._done = False
        self._current_facts = []
        self._current_actions = []
        self._completed_case_scores = []
        self._trajectory = []
        self._org_state = self._initial_org_state()
        return self._make_observation()

    def step(self, action: Action) -> StepResult:
        if self._done:
            raise RuntimeError("Episode is finished. Call reset() to start again.")
        if not action.operations:
            raise RuntimeError("At least one operation is required.")

        current_case = self._current_case()
        operation = action.operations[0]
        if operation.case_id and operation.case_id != current_case["id"]:
            raise RuntimeError(
                f"Operation targets case_id={operation.case_id}, but the active case is {current_case['id']}."
            )

        self._step_number += 1
        self._case_step += 1
        self._current_actions.append(operation.action_type)
        self._append_audit(f"{current_case['id']}::{operation.action_type}")

        if operation.action_type in INVESTIGATION_ACTIONS:
            result = score_investigation(
                current_case,
                operation,
                self._current_facts,
                self._current_actions[:-1],
                active_incidents=self._org_state.active_incidents,
            )
            new_knowledge_refs = []
            for fact in result["new_facts"]:
                if fact not in self._current_facts:
                    self._current_facts.append(fact)
                if operation.action_type == "search_kb" and fact not in self._org_state.knowledge_refs:
                    new_knowledge_refs.append(fact)
                    self._org_state.knowledge_refs.append(fact)

            timed_out = self._case_step >= self.max_steps_per_case
            if timed_out:
                self._apply_follow_on_risk(current_case, operation.action_type, "timeout_without_resolution")
                self._complete_case(
                    case_score=0.0,
                    final_action=operation.action_type,
                    reason="step limit reached without a final resolution",
                    successful=False,
                    evidence_quality=result["evidence_quality"],
                    resolution_quality=0.0,
                    safety_quality=result["safety_quality"],
                    timeliness_quality=0.0,
                    state_quality=0.0,
                    state_delta={"knowledge_refs": new_knowledge_refs, "follow_on": "timeout_without_resolution"},
                    note=operation.note,
                    customer_message=operation.customer_message,
                )

            reward_details = Reward(
                value=result["reward"],
                reason=result["reason"] if not timed_out else "step limit reached without a final resolution",
                evidence_quality=result["evidence_quality"],
                resolution_quality=result["resolution_quality"],
                safety_quality=result["safety_quality"],
                timeliness_quality=0.0,
                state_quality=0.1 if new_knowledge_refs else 0.0,
            )
            observation = self._make_observation()
            return StepResult(
                observation=observation,
                reward=result["reward"],
                reward_details=reward_details,
                done=self._done,
                info={
                    "task": self.task_name,
                    "step": self._step_number,
                    "case_id": current_case["id"],
                    "case_completed": timed_out,
                    "cumulative_score": self._cumulative_score(),
                    "tickets_remaining": self._tickets_remaining(),
                    "org_state": self._org_state.model_dump(),
                },
            )

        resolution = score_resolution(
            current_case,
            operation,
            self._current_facts,
            self._current_actions[:-1],
            active_incidents=self._org_state.active_incidents,
        )
        timeliness_quality = self._timeliness_quality(current_case.get("priority", "medium"), self._case_step)
        state_delta = self._apply_terminal_action(current_case, operation, resolution["successful"])
        if resolution["successful"]:
            final_reward = round(
                min(
                    1.0,
                    (0.72 * resolution["case_score"])
                    + (0.16 * timeliness_quality)
                    + (0.12 * state_delta["state_quality"]),
                ),
                2,
            )
        else:
            final_reward = round(max(resolution["case_score"], 0.0), 2)

        self._complete_case(
            case_score=final_reward,
            final_action=operation.action_type,
            reason=resolution["reason"],
            successful=resolution["successful"],
            evidence_quality=resolution["evidence_quality"],
            resolution_quality=resolution["resolution_quality"],
            safety_quality=resolution["safety_quality"],
            timeliness_quality=timeliness_quality,
            state_quality=state_delta["state_quality"],
            state_delta=state_delta["state_delta"],
            note=operation.note,
            customer_message=operation.customer_message,
        )
        reward_details = Reward(
            value=final_reward,
            reason=resolution["reason"],
            evidence_quality=resolution["evidence_quality"],
            resolution_quality=resolution["resolution_quality"],
            safety_quality=resolution["safety_quality"],
            timeliness_quality=timeliness_quality,
            state_quality=state_delta["state_quality"],
        )
        observation = self._make_observation()
        return StepResult(
            observation=observation,
            reward=final_reward,
            reward_details=reward_details,
            done=self._done,
            info={
                "task": self.task_name,
                "step": self._step_number,
                "case_id": current_case["id"],
                "case_completed": True,
                "cumulative_score": self._cumulative_score(),
                "tickets_remaining": self._tickets_remaining(),
                "state_delta": state_delta["state_delta"],
                "org_state": self._org_state.model_dump(),
            },
        )

    def state(self) -> State:
        current_tickets = []
        if not self._done:
            current_tickets = [self._ticket_item(self._current_case())]

        return State(
            tickets=current_tickets,
            snippets=current_tickets,
            step_number=self._step_number,
            current_case_step=self._case_step,
            total_tickets=len(self.cases),
            total_snippets=len(self.cases),
            task_name=self.task_name,
            session_id=self.session_id,
            done=self._done,
            tickets_remaining=self._tickets_remaining(),
            snippets_remaining=self._tickets_remaining(),
            cumulative_score=self._cumulative_score(),
            org_state=self._org_state.model_copy(deep=True),
        )

    def episode_report(self) -> dict:
        completed = len(self._trajectory)
        successful = len([item for item in self._trajectory if item["successful"]])
        return {
            "session_id": self.session_id,
            "task_name": self.task_name,
            "done": self._done,
            "step_number": self._step_number,
            "total_cases": len(self.cases),
            "attempted_cases": completed,
            "tickets_remaining": self._tickets_remaining(),
            "cumulative_score": self._cumulative_score(),
            "resolution_accuracy": round(successful / completed, 2) if completed else 0.0,
            "org_state": self._org_state.model_dump(),
            "trajectory": self._trajectory,
        }

    def _complete_case(
        self,
        case_score: float,
        final_action: str,
        reason: str,
        successful: bool,
        evidence_quality: float,
        resolution_quality: float,
        safety_quality: float,
        timeliness_quality: float,
        state_quality: float,
        state_delta: dict,
        note: str,
        customer_message: str,
    ) -> None:
        current_case = self._current_case()
        self._completed_case_scores.append(round(case_score, 2))
        self._trajectory.append(
            {
                "case_id": current_case["id"],
                "title": current_case["title"],
                "priority": current_case["priority"],
                "category": current_case["category"],
                "step_count": self._case_step,
                "gathered_facts": list(self._current_facts),
                "action_history": list(self._current_actions),
                "final_action": final_action,
                "final_note": note,
                "customer_message": customer_message,
                "case_score": round(case_score, 2),
                "successful": successful,
                "reason": reason,
                "evidence_quality": round(evidence_quality, 2),
                "resolution_quality": round(resolution_quality, 2),
                "safety_quality": round(safety_quality, 2),
                "timeliness_quality": round(timeliness_quality, 2),
                "state_quality": round(state_quality, 2),
                "state_delta": state_delta,
                "org_state_after": self._org_state.model_dump(),
            }
        )
        self._case_index += 1
        self._case_step = 0
        self._current_facts = []
        self._current_actions = []
        self._done = self._case_index >= len(self.cases)

    def _initial_org_state(self) -> OrgState:
        state = deepcopy(DEFAULT_ORG_STATE)
        config_state = self.task.get("config", {}).get("initial_state", {})
        for key, value in config_state.items():
            if isinstance(value, dict):
                state.setdefault(key, {}).update(value)
            elif isinstance(value, list):
                state[key] = list(value)
            else:
                state[key] = value
        return OrgState(**state)

    def _current_case(self) -> dict:
        return self.cases[self._case_index]

    def _tickets_remaining(self) -> int:
        return max(len(self.cases) - self._case_index, 0)

    def _cumulative_score(self) -> float:
        if not self._completed_case_scores:
            return 0.0
        return round(sum(self._completed_case_scores) / len(self._completed_case_scores), 2)

    def _append_audit(self, message: str) -> None:
        self._org_state.audit_log.append(message)
        self._org_state.audit_log = self._org_state.audit_log[-20:]

    def _timeliness_quality(self, priority: str, case_step: int) -> float:
        target = DECISION_STEP_TARGET.get(priority, 4)
        if case_step <= target:
            return 1.0
        overflow = case_step - target
        return max(0.0, 1.0 - (0.35 * overflow))

    def _apply_follow_on_risk(self, case: dict, action_type: str, reason: str) -> None:
        tag = f"follow_on::{case['id']}::{reason}"
        if tag not in self._org_state.active_incidents:
            self._org_state.active_incidents.append(tag)
        flag = f"unsafe::{case['id']}::{action_type}"
        if flag not in self._org_state.compliance_flags:
            self._org_state.compliance_flags.append(flag)

    def _apply_terminal_action(self, case: dict, operation, successful: bool) -> dict:
        expected = case.get("expected_resolution", {})
        state_delta: dict[str, list[str] | str] = {"changes": []}
        state_quality = 1.0 if successful else 0.0
        target = expected.get("target") or operation.target or case["category"]
        tags = case.get("correlation_tags", [])

        if successful:
            if operation.action_type == "assign_license":
                current = self._org_state.license_inventory.get(target, 1)
                self._org_state.license_inventory[target] = max(current - 1, 0)
                state_delta["changes"].append(f"license_consumed:{target}")
            elif operation.action_type == "grant_app_access":
                self._org_state.access_changes.append(f"granted:{target}:{case['id']}")
                if "figma" in target or "workspace" in target:
                    self._org_state.license_inventory["figma_workspace"] = max(
                        self._org_state.license_inventory.get("figma_workspace", 1) - 1,
                        0,
                    )
                    state_delta["changes"].append("license_consumed:figma_workspace")
            elif operation.action_type == "revoke_access":
                self._org_state.access_changes.append(f"revoked:{target}:{case['id']}")
                state_delta["changes"].append(f"access_revoked:{target}")
            elif operation.action_type == "reset_password":
                state_delta["changes"].append("credential_rotated")
            elif operation.action_type == "unlock_account":
                state_delta["changes"].append("account_unlocked")
            elif operation.action_type == "issue_vpn_profile":
                state_delta["changes"].append("vpn_profile_reissued")
            elif operation.action_type == "deny_request":
                state_delta["changes"].append(f"request_denied:{target}")
            elif operation.action_type == "escalate_security":
                incident = f"security::{tags[0] if tags else case['category']}::{case['id']}"
                if incident not in self._org_state.active_incidents:
                    self._org_state.active_incidents.append(incident)
                state_delta["changes"].append(f"incident_opened:{incident}")
            elif operation.action_type == "escalate_it_ops":
                incident = f"it_ops::{case['category']}::{case['id']}"
                if incident not in self._org_state.active_incidents:
                    self._org_state.active_incidents.append(incident)
                state_delta["changes"].append(f"ops_queue_opened:{incident}")
            elif operation.action_type == "close_as_no_issue":
                state_delta["changes"].append(f"closed_no_issue:{case['id']}")

            for tag in tags:
                related = [item for item in self._org_state.active_incidents if tag in item]
                if related and operation.action_type in {"escalate_security", "revoke_access"}:
                    state_quality = min(1.0, state_quality + 0.1)
                    state_delta["changes"].append(f"correlated_with:{tag}")
        else:
            self._apply_follow_on_risk(case, operation.action_type, "wrong_terminal_action")
            state_delta["changes"].append(f"follow_on_incident:{case['id']}")
            state_quality = 0.0

        self._org_state.resolved_tickets.append(case["id"])
        self._org_state.resolved_tickets = self._org_state.resolved_tickets[-20:]
        return {"state_quality": round(min(state_quality, 1.0), 2), "state_delta": state_delta}

    def _dependency_hints(self, case: dict) -> list[str]:
        hints: list[str] = []
        for tag in case.get("correlation_tags", []):
            related = [item for item in self._org_state.active_incidents if tag in item]
            if related:
                hints.append(f"Related incident already active for {tag}.")
        if case.get("category") in {"licensing", "saas_access"}:
            if self._org_state.license_inventory:
                licenses = ", ".join(
                    f"{key}={value}" for key, value in sorted(self._org_state.license_inventory.items())
                )
                hints.append(f"Current license inventory: {licenses}.")
        if self._org_state.compliance_flags:
            hints.append(f"Open compliance flags: {len(self._org_state.compliance_flags)}.")
        return hints

    def _related_services(self, case: dict) -> list[str]:
        return case.get("related_services", [case.get("category", "general")])

    def _ticket_item(self, case: dict) -> TicketItem:
        return TicketItem(
            id=case["id"],
            title=case["title"],
            requester=case["requester"],
            department=case["department"],
            priority=case["priority"],
            category=case["category"],
            user_message=case["user_message"],
            visible_context=case.get("visible_context", []),
            available_actions=case.get("available_actions", []),
            gathered_facts=list(self._current_facts),
            action_history=list(self._current_actions),
            correlation_tags=case.get("correlation_tags", []),
            dependency_hints=self._dependency_hints(case),
            related_services=self._related_services(case),
            sla_minutes=int(case.get("sla_minutes", SLA_BY_PRIORITY.get(case.get("priority", "medium"), 120))),
        )

    def _make_observation(self) -> Observation:
        current_tickets = []
        if not self._done:
            current_tickets = [self._ticket_item(self._current_case())]

        return Observation(
            tickets=current_tickets,
            snippets=current_tickets,
            step_number=self._step_number,
            current_case_step=self._case_step,
            total_tickets=len(self.cases),
            total_snippets=len(self.cases),
            task_name=self.task_name,
            session_id=self.session_id,
            org_state=self._org_state.model_copy(deep=True),
        )


CodeReviewEnv = HelpdeskOpsEnv
