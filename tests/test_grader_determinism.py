import unittest

from graders import grade_task, score_investigation, score_resolution
from models import ResolutionOperation
from tasks import TASKS


class TestGraderDeterminism(unittest.TestCase):
    def test_investigation_deterministic(self) -> None:
        case = TASKS["easy"]["cases"][0]
        operation = ResolutionOperation(
            case_id=case["id"],
            action_type="lookup_user",
            target="account",
            note="Check account status.",
            customer_message="I'm checking the account details now.",
        )
        first = score_investigation(case, operation, [], [])
        second = score_investigation(case, operation, [], [])
        self.assertEqual(first, second)

    def test_resolution_deterministic(self) -> None:
        case = TASKS["security"]["cases"][0]
        operation = ResolutionOperation(
            case_id=case["id"],
            action_type=case["expected_resolution"]["action_type"],
            target=case["expected_resolution"]["target"],
            note="Escalating due to confirmed compromise indicators.",
            customer_message="I escalated this to the security team immediately.",
        )
        facts = case["expected_resolution"]["required_facts"]
        history = case["expected_resolution"]["good_actions"]
        first = score_resolution(case, operation, facts, history)
        second = score_resolution(case, operation, facts, history)
        self.assertEqual(first, second)

    def test_grade_task_deterministic(self) -> None:
        operations = [
            ResolutionOperation(
                case_id=case["id"],
                action_type="lookup_user",
                target=case["category"],
                note="Initial account lookup.",
                customer_message="Checking the account details first.",
            )
            for case in TASKS["hard"]["cases"]
        ]
        first = grade_task("hard", operations)
        second = grade_task("hard", operations)
        self.assertEqual(first["cumulative_score"], second["cumulative_score"])
        self.assertEqual(first["trajectory"], second["trajectory"])

    def test_grade_task_marks_incomplete_replay(self) -> None:
        case = TASKS["easy"]["cases"][0]
        report = grade_task(
            "easy",
            [
                ResolutionOperation(
                    case_id=case["id"],
                    action_type="lookup_user",
                    target="account",
                    note="Initial account lookup.",
                    customer_message="Checking the account details first.",
                )
            ],
        )
        self.assertFalse(report["done"])
        self.assertFalse(report["fully_replayed"])
        self.assertEqual(report["attempted_cases"], 0)
        self.assertGreater(report["tickets_remaining"], 0)


if __name__ == "__main__":
    unittest.main()
