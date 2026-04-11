from copy import deepcopy

from graders import score_investigation, score_resolution
from models import (
    INVESTIGATION_ACTIONS,
    Action,
    Observation,
    Reward,
    State,
    StepResult,
    TicketItem,
)
from tasks import TASKS


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

    def reset(self) -> Observation:
        self._step_number = 0
        self._case_index = 0
        self._case_step = 0
        self._done = False
        self._current_facts = []
        self._current_actions = []
        self._completed_case_scores = []
        self._trajectory = []
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

        if operation.action_type in INVESTIGATION_ACTIONS:
            result = score_investigation(current_case, operation, self._current_facts, self._current_actions[:-1])
            for fact in result["new_facts"]:
                if fact not in self._current_facts:
                    self._current_facts.append(fact)

            timed_out = self._case_step >= self.max_steps_per_case
            case_score = None
            if timed_out:
                case_score = 0.0
                self._complete_case(
                    case_score=case_score,
                    final_action=operation.action_type,
                    reason="step limit reached without a final resolution",
                    successful=False,
                    evidence_quality=result["evidence_quality"],
                    resolution_quality=0.0,
                    safety_quality=result["safety_quality"],
                    note=operation.note,
                    customer_message=operation.customer_message,
                )

            reward_details = Reward(
                value=result["reward"],
                reason=result["reason"] if not timed_out else "step limit reached without a final resolution",
                evidence_quality=result["evidence_quality"],
                resolution_quality=result["resolution_quality"],
                safety_quality=result["safety_quality"],
            )
            observation = self._make_observation()
            cumulative_score = self._cumulative_score()
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
                    "cumulative_score": cumulative_score,
                    "tickets_remaining": self._tickets_remaining(),
                },
            )

        result = score_resolution(current_case, operation, self._current_facts, self._current_actions[:-1])
        self._complete_case(
            case_score=result["case_score"],
            final_action=operation.action_type,
            reason=result["reason"],
            successful=result["successful"],
            evidence_quality=result["evidence_quality"],
            resolution_quality=result["resolution_quality"],
            safety_quality=result["safety_quality"],
            note=operation.note,
            customer_message=operation.customer_message,
        )
        reward_details = Reward(
            value=result["reward"],
            reason=result["reason"],
            evidence_quality=result["evidence_quality"],
            resolution_quality=result["resolution_quality"],
            safety_quality=result["safety_quality"],
        )
        observation = self._make_observation()
        cumulative_score = self._cumulative_score()
        return StepResult(
            observation=observation,
            reward=result["reward"],
            reward_details=reward_details,
            done=self._done,
            info={
                "task": self.task_name,
                "step": self._step_number,
                "case_id": current_case["id"],
                "case_completed": True,
                "cumulative_score": cumulative_score,
                "tickets_remaining": self._tickets_remaining(),
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
        )

    def episode_report(self) -> dict:
        completed = len(self._trajectory)
        successful = len([item for item in self._trajectory if item["successful"]])
        average_score = self._cumulative_score()
        return {
            "session_id": self.session_id,
            "task_name": self.task_name,
            "done": self._done,
            "step_number": self._step_number,
            "total_cases": len(self.cases),
            "attempted_cases": completed,
            "tickets_remaining": self._tickets_remaining(),
            "cumulative_score": average_score,
            "resolution_accuracy": round(successful / completed, 2) if completed else 0.0,
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
            }
        )
        self._case_index += 1
        self._case_step = 0
        self._current_facts = []
        self._current_actions = []
        self._done = self._case_index >= len(self.cases)

    def _current_case(self) -> dict:
        return self.cases[self._case_index]

    def _tickets_remaining(self) -> int:
        return max(len(self.cases) - self._case_index, 0)

    def _cumulative_score(self) -> float:
        if not self._completed_case_scores:
            return 0.0
        return round(sum(self._completed_case_scores) / len(self._completed_case_scores), 2)

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
        )


CodeReviewEnv = HelpdeskOpsEnv
