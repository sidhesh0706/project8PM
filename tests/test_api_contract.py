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
        snippet = obs["snippets"][0]

        step = self.client.post(
            "/step",
            json={
                "session_id": session_id,
                "reports": [
                    {
                        "snippet_id": snippet["id"],
                        "bug_type": "wrong_logic",
                        "explanation": "contract test submission",
                        "severity": "medium",
                        "suggested_fix": "return value",
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
        self.assertIn("accuracy", report_payload)

        summary = self.client.get("/sessions/summary")
        self.assertEqual(summary.status_code, 200)
        self.assertIn("total_sessions", summary.json())

        manifest = self.client.get("/manifest")
        self.assertEqual(manifest.status_code, 200)
        self.assertIn("task_counts", manifest.json())


if __name__ == "__main__":
    unittest.main()
