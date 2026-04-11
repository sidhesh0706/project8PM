import unittest

from fastapi.testclient import TestClient

from app import app


class TestAPIContract(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_root_and_tasks(self) -> None:
        root = self.client.get("/")
        self.assertEqual(root.status_code, 200)
        payload = root.json()
        self.assertEqual(payload["status"], "running")
        self.assertIn("tasks", payload)

        tasks = self.client.get("/tasks")
        self.assertEqual(tasks.status_code, 200)
        self.assertGreaterEqual(len(tasks.json()), 3)

    def test_episode_flow_and_reports(self) -> None:
        reset = self.client.post("/reset", json={"task_name": "easy"})
        self.assertEqual(reset.status_code, 200)
        obs = reset.json()
        session_id = obs["session_id"]
        ticket = obs["tickets"][0]

        step = self.client.post(
            "/step",
            json={
                "session_id": session_id,
                "operations": [
                    {
                        "case_id": ticket["id"],
                        "action_type": "lookup_user",
                        "target": "account",
                        "note": "contract test submission",
                        "customer_message": "Checking the account details now.",
                    }
                ],
            },
        )
        self.assertEqual(step.status_code, 200)
        self.assertIn("reward", step.json())

        state = self.client.get("/state", params={"session_id": session_id})
        self.assertEqual(state.status_code, 200)
        self.assertIn("done", state.json())

        report = self.client.get("/report", params={"session_id": session_id})
        self.assertEqual(report.status_code, 200)
        report_payload = report.json()
        self.assertIn("trajectory", report_payload)
        self.assertIn("resolution_accuracy", report_payload)

        summary = self.client.get("/sessions/summary")
        self.assertEqual(summary.status_code, 200)
        self.assertIn("total_sessions", summary.json())

        manifest = self.client.get("/manifest")
        self.assertEqual(manifest.status_code, 200)
        self.assertIn("task_counts", manifest.json())

    def test_step_validation_errors(self) -> None:
        invalid_action = self.client.post(
            "/step",
            json={
                "session_id": "missing",
                "operations": [
                    {
                        "case_id": "e1",
                        "action_type": "not_real",
                        "target": "account",
                        "note": "bad action",
                        "customer_message": "bad action",
                    }
                ],
            },
        )
        self.assertEqual(invalid_action.status_code, 422)

        invalid_operations = self.client.post("/step", json={"operations": "bad"})
        self.assertEqual(invalid_operations.status_code, 422)

        missing_operations = self.client.post("/step", json={"session_id": "missing"})
        self.assertEqual(missing_operations.status_code, 422)

    def test_step_rejects_wrong_case_id(self) -> None:
        reset = self.client.post("/reset", json={"task_name": "easy"})
        session_id = reset.json()["session_id"]

        step = self.client.post(
            "/step",
            json={
                "session_id": session_id,
                "operations": [
                    {
                        "case_id": "wrong-case",
                        "action_type": "lookup_user",
                        "target": "account",
                        "note": "wrong case",
                        "customer_message": "wrong case",
                    }
                ],
            },
        )
        self.assertEqual(step.status_code, 400)
        self.assertIn("active case", step.json()["detail"])

    def test_grade_reports_incomplete_replay(self) -> None:
        response = self.client.post(
            "/grade?task_name=easy",
            json={
                "operations": [
                    {
                        "case_id": "e1",
                        "action_type": "lookup_user",
                        "target": "account",
                        "note": "Initial account lookup.",
                        "customer_message": "Checking the account details first.",
                    }
                ]
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["done"])
        self.assertFalse(payload["fully_replayed"])
        self.assertGreater(payload["tickets_remaining"], 0)


if __name__ == "__main__":
    unittest.main()
