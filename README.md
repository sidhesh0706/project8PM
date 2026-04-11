---
title: IT Helpdesk Ops Env
emoji: "🔧"
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
base_path: /web
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

An OpenEnv benchmark for enterprise support and security workflows. The agent works through IT helpdesk and security operations tickets, gathers the right evidence, checks policy, and chooses a safe final action such as unlocking an account, reissuing a VPN profile, denying a risky request, revoking stale access, or escalating to Security.

The environment is designed to evaluate operational AI agents rather than simple labelers. It rewards evidence gathering, policy awareness, safe escalation, and correct final resolution.

## What The Agent Does

For each ticket, the agent must:
1. inspect the visible ticket context
2. choose an information-gathering action when evidence is incomplete
3. interpret policy, identity, device, or risk signals
4. decide whether to resolve, deny, revoke, or escalate
5. communicate the outcome clearly

## Why This Benchmark Matters

Most agent benchmarks stop at extraction or classification. Operational teams need something closer to real work:
- understand a user ticket with incomplete context
- decide whether more evidence is needed
- distinguish routine support from real security risk
- avoid unsafe actions
- communicate the resolution clearly

Those are the behaviors this environment measures.

## Benchmark Design

Each episode contains one tier of tickets. The agent sees one active ticket at a time and can:
- investigate with actions like `lookup_user`, `lookup_device`, `check_access_policy`, or `review_login_risk`
- consult knowledge-base style guidance with `search_kb`
- gather ticket-specific facts revealed by those actions
- choose one final action such as `unlock_account`, `assign_license`, `deny_request`, `revoke_access`, `escalate_security`, or `close_as_no_issue`

The episode advances only after the active case is resolved, denied, escalated, or times out.

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

## Why This Benchmark Is Hard

- Several cases are intentionally high-pressure and tempting, where the unsafe action is the fastest-looking action.
- Some tickets require one or two evidence-gathering steps before the correct resolution becomes obvious.
- The benchmark rewards restraint: agents lose points for granting risky access, missing policy checks, or escalating when the issue is routine.

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

That means the benchmark rewards not just the final answer, but also whether the agent used the right evidence path before acting.

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

Recent local baseline scores:
- `easy`: `0.99`
- `medium`: `0.93`
- `hard`: `0.91`
- `security`: `0.91`

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
