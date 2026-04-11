---
title: IT Helpdesk Ops Env
emoji: "🛡️"
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
base_path: /web
header: mini
fullWidth: true
suggested_hardware: cpu-basic
startup_duration_timeout: 30m
short_description: Multi-step IT helpdesk and security benchmark.
tags:
  - openenv
  - reinforcement-learning
  - agents
  - security
  - helpdesk
pinned: false
---

# IT Helpdesk Operations Environment

`it-helpdesk-ops-env` is an OpenEnv benchmark for operational AI agents. It simulates realistic internal IT helpdesk and security tickets where the agent must gather evidence, interpret policy, reason over shared organizational state, and choose a safe final action.

This environment is designed to test more than classification. Strong performance requires good investigation habits, policy awareness, cautious escalation, and clear user communication.

## Why This Benchmark Exists

Many agent benchmarks focus on extraction, labeling, or one-step tool use. Real operational work is messier. Internal IT and security teams routinely need to:

- understand incomplete ticket context
- collect the right evidence before acting
- distinguish routine support from real security risk
- avoid unsafe or policy-violating actions
- communicate the outcome clearly

That is the behavior this benchmark is built to measure.

## What The Agent Does

For each active ticket, the agent should:

1. inspect the visible context
2. decide whether more evidence is needed
3. use investigation actions to gather facts
4. interpret policy, identity, endpoint, or risk signals
5. choose a safe final action
6. explain the resolution clearly

Final actions may include resolving the issue directly, denying a request, revoking access, or escalating to the right team.

## Benchmark Design

Each episode runs through a task tier made of multiple tickets. The environment exposes one active ticket at a time and maintains persistent org-wide state across the episode.

The shared state includes:

- license inventory
- pending approvals
- active incidents
- compliance flags
- access-change history
- knowledge references
- audit logs

Because the state persists, early actions can influence later tickets through incident correlation, resource depletion, and dependency hints.

## Task Tiers

| Task | Cases | Focus |
|------|------:|-------|
| `easy` | 5 | Password resets, lockouts, VPN restoration, approved access, licensing |
| `medium` | 5 | Policy-aware access checks, travel false positives, contractor licensing, role-sync escalation |
| `hard` | 7 | Offboarding failures, probable compromise, unmanaged devices, production data access, privileged-access traps |
| `security` | 6 | MFA fatigue, leaked tokens, phishing, terminated access, unsafe data export |

## Operational Coverage

The scenarios cover:

- identity recovery and lockouts
- VPN and managed device issues
- SaaS access and license assignment
- policy-controlled access requests
- offboarding drift and entitlement cleanup
- compromise indicators such as phishing, MFA fatigue, and suspicious sign-ins
- regulated data-handling violations

## Why It Is Challenging

- Some tickets are intentionally high-pressure, where the fastest-looking action is unsafe.
- Several cases require one or two investigation steps before the correct resolution becomes obvious.
- The benchmark rewards restraint, not just speed.
- Later tickets can reflect the side effects of earlier actions.

## Observation Space

The environment returns one active ticket per step together with episode metadata.

| Field | Type | Description |
|------|------|-------------|
| `tickets` | `list[TicketItem]` | The current active ticket |
| `step_number` | `int` | Global step count in the episode |
| `current_case_step` | `int` | Step count within the current case |
| `total_tickets` | `int` | Total number of tickets in the selected task |
| `task_name` | `str` | Active task tier |
| `session_id` | `str \| null` | Session identifier returned by `/reset` |
| `org_state` | `OrgState` | Persistent simulated organization state |

Each ticket includes:

- requester and department
- priority and category
- user message
- visible context
- available actions
- gathered facts
- action history
- dependency hints
- related services

## Action Space

The agent submits one `ResolutionOperation` at a time.

| Field | Type | Description |
|------|------|-------------|
| `case_id` | `str` | Ticket identifier |
| `action_type` | `enum` | Investigation or terminal action |
| `target` | `str` | Resource, queue, or object affected |
| `note` | `str` | Internal analyst note |
| `customer_message` | `str` | User-facing response |

Supported `action_type` values:

- `lookup_user`
- `lookup_device`
- `search_kb`
- `check_access_policy`
- `review_login_risk`
- `reset_password`
- `unlock_account`
- `issue_vpn_profile`
- `grant_app_access`
- `assign_license`
- `revoke_access`
- `deny_request`
- `escalate_security`
- `escalate_it_ops`
- `close_as_no_issue`

## Reward Model

Rewards stay in `[0.0, 1.0]` and provide partial credit.

The grader evaluates:

- evidence quality
- resolution quality
- safety quality
- timeliness quality
- downstream state quality

In practice, that means the best scores come from following a good evidence path and taking the correct safe action, not just guessing the final label.

## API Overview

| Method | Endpoint | Purpose |
|------|----------|---------|
| `GET` | `/` | Service metadata |
| `GET` | `/health` | Health check |
| `POST` | `/reset` | Start a new episode |
| `POST` | `/step` | Submit one investigation or resolution step |
| `GET` | `/state` | Inspect the current session state |
| `GET` | `/tasks` | List task tiers and counts |
| `GET` | `/manifest` | Return schema and benchmark metadata |
| `GET` | `/report` | Return per-session trajectory details |
| `GET` | `/sessions/summary` | Aggregate session metrics |
| `GET` | `/web` | Browser-friendly overview |
| `POST` | `/grade` | Offline grading by replaying operations |

## Quick Start

### Local Setup

```bash
git clone https://github.com/sidhesh0706/project8PM
cd project8PM
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 7860
```

### Docker

```bash
docker build -t it-helpdesk-ops-env .
docker run -p 7860:7860 it-helpdesk-ops-env
```

## Hugging Face Spaces Deployment

This repository is configured for a Docker Space.

Recommended Space settings:

- SDK: `Docker`
- Hardware: `cpu-basic`
- Port: `7860`
- Visibility: `public` or `protected`, depending on whether you want the code to stay private

Recommended Space Variables:

- `API_BASE_URL`
- `MODEL_NAME`
- `SESSION_TTL_SECONDS`

Recommended Space Secrets:

- `API_KEY`

Notes:

- Do not hardcode API credentials in the repository or Dockerfile.
- The container now runs as user ID `1000`, which aligns with Hugging Face Docker Space guidance.
- `startup_duration_timeout: 30m` is included in the README frontmatter to give slower rebuilds more room.

### Basic Episode Flow

1. Start an episode with `POST /reset`.
2. Read the active ticket from the response.
3. Submit one operation at a time to `POST /step`.
4. Repeat until the environment reports `done=true`.

Example:

```bash
curl -X POST "http://localhost:7860/reset" \
  -H "Content-Type: application/json" \
  -d '{"task_name": "easy"}'
```

```bash
curl -X POST "http://localhost:7860/step" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "YOUR_SESSION_ID",
    "operations": [
      {
        "case_id": "e1",
        "action_type": "lookup_user",
        "target": "account",
        "note": "Check the account state before taking action.",
        "customer_message": "I am checking your account details now."
      }
    ]
  }'
```

## Offline Grading

`POST /grade` evaluates a replay payload without creating a live session. The response includes the usual report fields plus `fully_replayed`, which tells you whether the replay covered the entire task.

```bash
curl -X POST "http://localhost:7860/grade?task_name=easy" \
  -H "Content-Type: application/json" \
  -d '{
    "operations": [
      {
        "case_id": "e1",
        "action_type": "lookup_user",
        "target": "account",
        "note": "Check the account state first.",
        "customer_message": "I am checking your account now."
      },
      {
        "case_id": "e1",
        "action_type": "unlock_account",
        "target": "okta_account",
        "note": "Routine lockout after password reset attempts.",
        "customer_message": "I unlocked the account. Please try signing in again."
      }
    ]
  }'
```

If the replay runs out of operations before all tickets are handled, the response keeps `done=false` and sets `fully_replayed=false`.

## Baseline Inference

Run the baseline policy with:

```bash
python inference.py
```

The baseline:

- uses the OpenAI-compatible client when `API_KEY` is present
- falls back to a deterministic heuristic policy when no credentials are available
- emits strict `[START]`, `[STEP]`, and `[END]` logs
- writes `scores.json` in the repository root

### Environment Variables

| Variable | Description |
|----------|-------------|
| `API_BASE_URL` | OpenAI-compatible endpoint for inference |
| `MODEL_NAME` | Model identifier |
| `API_KEY` | Primary API credential |
| `HF_TOKEN` | Accepted fallback credential |
| `LOCAL_IMAGE_NAME` | Optional docker-image runner variable |
| `SESSION_TTL_SECONDS` | Optional session inactivity timeout for the API server |

### Recent Local Baseline Scores

- `easy`: `0.94`
- `medium`: `0.90`
- `hard`: `0.89`
- `security`: `0.90`

## Validation

Run the local checks with:

```bash
python -m unittest discover -s tests -v
python validate_submission.py
```

The validator checks:

- dataset and config integrity
- `openenv.yaml` alignment
- API contract behavior
- `/grade` replay behavior
- manifest and report endpoints
- baseline reproducibility
- structured logging
- `scores.json` validity

## Live Demo

- Space: [https://huggingface.co/spaces/sid0706/code-review-env](https://huggingface.co/spaces/sid0706/code-review-env)
- Web UI: [https://sid0706-code-review-env.hf.space/web](https://sid0706-code-review-env.hf.space/web)
- Tasks: [https://sid0706-code-review-env.hf.space/tasks](https://sid0706-code-review-env.hf.space/tasks)
- Docs: [https://sid0706-code-review-env.hf.space/docs](https://sid0706-code-review-env.hf.space/docs)
