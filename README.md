---
title: IT Helpdesk Ops Env
emoji: "🛠️"
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# IT Helpdesk Operations Environment

An OpenEnv benchmark for real-world enterprise support and security workflows. Instead of solving a toy task, the agent works through IT helpdesk and security operations tickets: it investigates the situation, gathers facts, checks policy, and chooses a safe final action such as unlocking an account, reissuing a VPN profile, denying a risky request, revoking stale access, or escalating to Security.

This is meant to evaluate operational AI agents, not just classifiers. The environment rewards evidence gathering, policy awareness, safe escalation, and correct final resolution.

## Why This Benchmark Matters

Most agent benchmarks stop at extraction or classification. Real IT and security teams need something harder:
- understand a user ticket with incomplete context
- decide whether more evidence is needed
- distinguish routine support from real security risk
- avoid unsafe actions
- communicate the resolution clearly

Those are exactly the behaviors this environment measures.

## Benchmark Design

Each episode contains one tier of tickets. The agent sees one active ticket at a time and can:
- investigate with actions like `lookup_user`, `lookup_device`, `check_access_policy`, or `review_login_risk`
- gather ticket-specific facts revealed by those actions
- choose one final action such as `unlock_account`, `assign_license`, `deny_request`, `revoke_access`, `escalate_security`, or `close_as_no_issue`

The episode advances to the next case only after the current one is resolved, denied, escalated, or times out.

## Observation Space

| Field | Type | Description |
|------|------|-------------|
| `tickets` | `list[TicketItem]` | The currently active ticket |
| `step_number` | `int` | Global step count |
| `current_case_step` | `int` | Step count within the current ticket |
| `total_tickets` | `int` | Total tickets in the selected task |
| `task_name` | `str` | Active task tier |
| `session_id` | `str \| null` | Session identifier returned by `/reset` |

Each ticket includes:
- requester and department
- priority and category
- user message
- visible context
- available actions
- gathered facts
- action history

## Action Space

The agent submits one `ResolutionOperation` at a time:

| Field | Type | Description |
|------|------|-------------|
| `case_id` | `str` | Ticket identifier |
| `action_type` | `enum` | Investigation or final action |
| `target` | `str` | Resource, queue, or object affected |
| `note` | `str` | Internal reasoning note |
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

## Tasks

| Task | Cases | Focus |
|------|------:|-------|
| `easy` | 5 | Password resets, lockouts, VPN restoration, approved access, licensing |
| `medium` | 5 | Policy-aware access checks, travel false positives, contractor licensing, role-sync escalation |
| `hard` | 6 | Offboarding failures, probable compromise, unmanaged devices, production data access |
| `security` | 5 | MFA fatigue, leaked tokens, phishing, terminated access, unsafe data export |

## Reward Logic

Rewards stay in `[0.0, 1.0]` and provide partial credit:
- useful investigation steps receive credit when they reveal relevant facts
- repeated or irrelevant investigation steps receive low or zero reward
- the best scores require the correct final action plus good evidence coverage
- unsafe or policy-violating actions score poorly

The grader is deterministic and tracks:
- evidence quality
- resolution quality
- safety quality
- final case success

## API Endpoints

| Method | Endpoint | Purpose |
|------|----------|---------|
| `GET` | `/` | Service metadata |
| `GET` | `/health` | Health check |
| `POST` | `/reset` | Start a new episode |
| `POST` | `/step` | Submit an investigation or resolution step |
| `GET` | `/state` | Inspect current session state |
| `GET` | `/tasks` | Task catalog |
| `GET` | `/manifest` | Task counts and schema summary |
| `GET` | `/report` | Per-session case trajectory |
| `GET` | `/sessions/summary` | Aggregate session metrics |
| `GET` | `/web` | Browser-friendly overview |
| `POST` | `/grade` | Offline grading via replay |

## Baseline Inference

Run:

```bash
python inference.py
```

The baseline:
- uses the OpenAI client when `API_KEY` is present
- routes through `API_BASE_URL`
- emits strict `[START]`, `[STEP]`, and `[END]` logs
- writes `scores.json`

Environment variables:

| Variable | Description |
|----------|-------------|
| `API_BASE_URL` | LLM endpoint, default provided |
| `MODEL_NAME` | Model id, default provided |
| `API_KEY` | Primary proxy credential |
| `HF_TOKEN` | Local fallback accepted by the baseline |
| `LOCAL_IMAGE_NAME` | Optional docker-image runner variable |

## Local Setup

```bash
git clone https://github.com/sidhesh0706/project8PM
cd project8PM
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 7860
```

## Docker

```bash
docker build -t it-helpdesk-ops-env .
docker run -p 7860:7860 it-helpdesk-ops-env
```

## Validation And Tests

Run:

```bash
python -m unittest discover -s tests -v
python validate_submission.py
```

The local validator checks:
- task/config integrity
- `openenv.yaml` alignment
- API contract behavior
- manifest and report endpoints
- baseline reproducibility
- structured logging
- `scores.json` validity

## Live Demo

- Space: [https://huggingface.co/spaces/sid0706/code-review-env](https://huggingface.co/spaces/sid0706/code-review-env)
- Web UI: [https://sid0706-code-review-env.hf.space/web](https://sid0706-code-review-env.hf.space/web)
- Tasks: [https://sid0706-code-review-env.hf.space/tasks](https://sid0706-code-review-env.hf.space/tasks)
- Docs: [https://sid0706-code-review-env.hf.space/docs](https://sid0706-code-review-env.hf.space/docs)
