from models import Observation, Action, StepResult
from graders import grade_task
from tasks import TASKS


class CodeReviewEnv:
    def __init__(self, task_name: str = "easy"):
        if task_name not in TASKS:
            raise ValueError(f"Unknown task: {task_name}. Choose from {list(TASKS.keys())}")
        self.task_name = task_name
        self.snippets = TASKS[task_name]["snippets"]
        self._step_number = 0
        self._done = False
        self._last_reports = []

    # ─── REQUIRED OPENENV METHODS ─────────────────────────────

    def reset(self) -> Observation:
        """Start a fresh episode. Always call this before step()."""
        self._step_number = 0
        self._done = False
        self._last_reports = []
        return self._make_observation()

    def step(self, action: Action) -> StepResult:
        """
        Agent submits its bug reports.
        Returns observation, reward, done, info.
        """
        if self._done:
            raise RuntimeError("Episode is finished. Call reset() to start again.")

        self._last_reports = action.reports
        self._step_number += 1
        self._done = True  # one step per episode — agent reviews all snippets at once

        result = grade_task(self.task_name, action.reports)
        reward = result["overall_score"]

        return StepResult(
            observation=self._make_observation(),
            reward=reward,
            done=self._done,
            info={
                "task": self.task_name,
                "overall_score": reward,
                "breakdown": result["breakdown"],
            },
        )

    def state(self) -> Observation:
        """Returns the current observation without advancing the episode."""
        return self._make_observation()

    # ─── INTERNAL ─────────────────────────────────────────────

    def _make_observation(self) -> Observation:
        return Observation(
            snippets=self.snippets,
            step_number=self._step_number,
            total_snippets=len(self.snippets),
            task_name=self.task_name,
        )


# ─── QUICK SMOKE TEST ─────────────────────────────────────────
# Run this file directly to verify everything works:
# python env.py

if __name__ == "__main__":
    from tasks import EASY_ANSWERS, MEDIUM_ANSWERS, HARD_ANSWERS

    for task_name, answers in [
        ("easy", EASY_ANSWERS),
        ("medium", MEDIUM_ANSWERS),
        ("hard", HARD_ANSWERS),
    ]:
        env = CodeReviewEnv(task_name=task_name)
        obs = env.reset()
        print(f"\n--- {task_name.upper()} TASK ---")
        print(f"Snippets: {len(obs.snippets)}")

        result = env.step(Action(reports=answers))
        print(f"Reward (perfect answers): {result.reward}")
        print(f"Done: {result.done}")
        print(f"Breakdown: {result.info['breakdown']}")