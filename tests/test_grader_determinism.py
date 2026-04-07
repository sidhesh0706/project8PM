import unittest

from graders import grade_task, score_report
from tasks import TASKS


class TestGraderDeterminism(unittest.TestCase):
    def test_score_report_deterministic(self) -> None:
        correct = TASKS["easy"]["answers"][0]
        submission = correct.model_copy(deep=True)
        submission.explanation = "Determinism probe explanation for exact replay checks."
        submission.suggested_fix = correct.suggested_fix

        first = score_report(submission, correct)
        second = score_report(submission, correct)
        self.assertEqual(first, second)

    def test_grade_task_deterministic(self) -> None:
        submitted = [r.model_copy(deep=True) for r in TASKS["hard"]["answers"]]
        first = grade_task("hard", submitted)
        second = grade_task("hard", submitted)
        self.assertEqual(first["overall_score"], second["overall_score"])
        self.assertEqual(first["breakdown"], second["breakdown"])


if __name__ == "__main__":
    unittest.main()
