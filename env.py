from models import Action, Observation, State, StepResult
from graders import grade_task
from graders import _score_single
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
        if report is None:
            reward = 0.0
            reason = "not attempted"
        else:
            reward = _score_single(report, correct_answer)
            reason = _get_reason(reward)

        self._rewards.append(reward)
        self._step_number += 1
        self._current_snippet_index += 1

        # Done when all snippets reviewed
        self._done = self._current_snippet_index >= len(self.snippets)

        return StepResult(
            observation=self._make_observation(),
            reward=reward,
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


def _get_reason(reward: float) -> str:
    if reward == 1.0:
        return "correct"
    elif reward == 0.8:
        return "correct bug and severity, fix missing or weak"
    elif reward == 0.7:
        return "correct bug type, wrong severity, good fix"
    elif reward == 0.5:
        return "correct bug type, wrong severity, weak fix"
    elif reward == 0.2:
        return "wrong bug type"
    else:
        return "incorrect"


# ─── SMOKE TEST ───────────────────────────────────────────────
if __name__ == "__main__":
    from tasks import EASY_ANSWERS, MEDIUM_ANSWERS, HARD_ANSWERS
    from models import Action

    for task_name, answers in [
        ("easy", EASY_ANSWERS),
        ("medium", MEDIUM_ANSWERS),
        ("hard", HARD_ANSWERS),
    ]:
        env = CodeReviewEnv(task_name=task_name)
        obs = env.reset()
        print(f"\n--- {task_name.upper()} TASK ---")
        print(f"Total snippets: {obs.total_snippets}")

        all_rewards = []
        step = 0
        while not env._done:
            current_id = obs.snippets[0].id if obs.snippets else None
            answer = next((a for a in answers if a.snippet_id == current_id), None)
            result = env.step(Action(reports=[answer] if answer else []))
            all_rewards.append(result.reward)
            obs = result.observation
            step += 1
            print(f"Step {step}: snippet={current_id} reward={result.reward} done={result.done}")

        final_score = round(sum(all_rewards) / len(all_rewards), 2)
        print(f"Final score: {final_score}")
