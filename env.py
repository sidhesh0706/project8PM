from models import Action, Observation, Reward, State, StepResult
from graders import score_report
from tasks import TASKS


class CodeReviewEnv:
    def __init__(self, task_name: str = "easy", session_id: str | None = None):
        if task_name not in TASKS:
            raise ValueError(f"Unknown task: {task_name}. Choose from {list(TASKS.keys())}")
        self.task_name = task_name
        self.session_id = session_id
        self.snippets = TASKS[task_name]["snippets"]
        self.correct_answers = TASKS[task_name]["answers"]
        self._step_number = 0
        self._done = False
        self._rewards = []
        self._current_snippet_index = 0

    # ─── REQUIRED OPENENV METHODS ─────────────────────────────

    def reset(self) -> Observation:
        """Start a fresh episode."""
        self._step_number = 0
        self._done = False
        self._rewards = []
        self._current_snippet_index = 0
        return self._make_observation()

    def step(self, action: Action) -> StepResult:
        """
        Agent submits a bug report for the CURRENT snippet only.
        One step = one snippet reviewed.
        """
        if self._done:
            raise RuntimeError("Episode is finished. Call reset() to start again.")

        # Get the current snippet and its correct answer
        current_snippet = self.snippets[self._current_snippet_index]
        correct_answer = self.correct_answers[self._current_snippet_index]

        # Find the report for this snippet
        report = next(
            (r for r in action.reports if r.snippet_id == current_snippet.id),
            None
        )

        # Score this single snippet
        result = score_report(report, correct_answer)
        reward = result["score"]
        reason = result["reason"]

        self._rewards.append(reward)
        self._step_number += 1
        self._current_snippet_index += 1

        # Done when all snippets reviewed
        self._done = self._current_snippet_index >= len(self.snippets)

        return StepResult(
            observation=self._make_observation(),
            reward=reward,
            reward_details=Reward(
                value=reward,
                reason=reason,
                explanation_quality=result["explanation_quality"],
                fix_quality=result["fix_quality"],
            ),
            done=self._done,
            info={
                "task": self.task_name,
                "step": self._step_number,
                "snippet_id": current_snippet.id,
                "reward": reward,
                "reason": reason,
                "cumulative_score": round(sum(self._rewards) / len(self._rewards), 2),
                "snippets_remaining": len(self.snippets) - self._current_snippet_index,
            },
        )

    def state(self) -> State:
        """Returns the current episode state without advancing."""
        if self._done or self._current_snippet_index >= len(self.snippets):
            current_snippets = []
        else:
            current_snippets = [self.snippets[self._current_snippet_index]]

        cumulative_score = 0.0
        if self._rewards:
            cumulative_score = round(sum(self._rewards) / len(self._rewards), 2)

        return State(
            snippets=current_snippets,
            step_number=self._step_number,
            total_snippets=len(self.snippets),
            task_name=self.task_name,
            session_id=self.session_id,
            done=self._done,
            snippets_remaining=len(self.snippets) - self._current_snippet_index,
            cumulative_score=cumulative_score,
        )

    # ─── INTERNAL ─────────────────────────────────────────────

    def _make_observation(self) -> Observation:
        # Only show the current snippet to the agent
        if self._done or self._current_snippet_index >= len(self.snippets):
            current_snippets = []
        else:
            current_snippets = [self.snippets[self._current_snippet_index]]

        return Observation(
            snippets=current_snippets,
            step_number=self._step_number,
            total_snippets=len(self.snippets),
            task_name=self.task_name,
            session_id=self.session_id,
        )
