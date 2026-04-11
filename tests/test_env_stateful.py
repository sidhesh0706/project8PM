import unittest

from env import HelpdeskOpsEnv
from models import Action, ResolutionOperation


def operation(case_id: str, action_type: str, target: str, note: str) -> Action:
    return Action(
        operations=[
            ResolutionOperation(
                case_id=case_id,
                action_type=action_type,
                target=target,
                note=note,
                customer_message=note,
            )
        ]
    )


class TestEnvStatefulBehavior(unittest.TestCase):
    def test_wrong_terminal_action_creates_follow_on_risk(self) -> None:
        env = HelpdeskOpsEnv(task_name="easy")
        obs = env.reset()
        case_id = obs.tickets[0].id

        result = env.step(operation(case_id, "escalate_security", "security_incident", "Unsafe escalation."))

        org_state = result.info["org_state"]
        self.assertIn(f"unsafe::{case_id}::escalate_security", org_state["compliance_flags"])
        self.assertIn(f"follow_on::{case_id}::wrong_terminal_action", org_state["active_incidents"])
        self.assertIn(case_id, org_state["resolved_tickets"])

    def test_license_inventory_changes_flow_into_dependency_hints(self) -> None:
        env = HelpdeskOpsEnv(task_name="easy")
        obs = env.reset()

        env.step(operation(obs.tickets[0].id, "lookup_user", "account", "Check user lockout state."))
        obs = env.step(operation("e1", "unlock_account", "okta_account", "Unlock routine lockout.")).observation

        env.step(operation(obs.tickets[0].id, "lookup_user", "account", "Check onboarding password state."))
        obs = env.step(operation("e2", "reset_password", "directory_password", "Reset expired onboarding password.")).observation

        env.step(operation(obs.tickets[0].id, "lookup_device", "device", "Check VPN profile assignment."))
        obs = env.step(operation("e3", "issue_vpn_profile", "corporate_vpn_profile", "Reissue missing VPN profile.")).observation

        env.step(operation(obs.tickets[0].id, "check_access_policy", "figma_workspace", "Verify design approval token."))
        obs = env.step(operation("e4", "grant_app_access", "figma_workspace", "Provision approved Figma access.")).observation

        self.assertEqual(obs.org_state.license_inventory["figma_workspace"], 7)
        self.assertIn("Current license inventory: adobe_creative_cloud=0, figma_workspace=7, power_bi_pro=6.", obs.tickets[0].dependency_hints)

    def test_active_incident_creates_cross_case_dependency_hint(self) -> None:
        env = HelpdeskOpsEnv(task_name="security")
        obs = env.reset()

        env.step(operation(obs.tickets[0].id, "review_login_risk", "sign_in_risk", "Review MFA fatigue indicators."))
        obs = env.step(operation("s1", "escalate_security", "incident_response", "Escalate active compromise signal.")).observation

        env.step(operation(obs.tickets[0].id, "lookup_user", "github_pat", "Identify the leaked token owner."))
        obs = env.step(operation("s2", "revoke_access", "github_pat", "Revoke the exposed token.")).observation

        env.step(operation(obs.tickets[0].id, "lookup_user", "vendor_vpn_access", "Verify contractor status."))
        env.step(operation("s3", "check_access_policy", "vendor_vpn_access", "Confirm offboarding policy."))
        obs = env.step(operation("s3", "revoke_access", "vendor_vpn_access", "Remove stale vendor VPN access.")).observation

        self.assertIn("Related incident already active for identity_takeover.", obs.tickets[0].dependency_hints)


if __name__ == "__main__":
    unittest.main()
