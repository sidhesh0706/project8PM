---
title: Code Review Env
emoji: "🔍"
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# Code Review Environment

A real-world OpenEnv benchmark where an agent performs pull-request style code review on Python and JavaScript snippets, identifies bug type/severity, and proposes fixes.

## Current Status

- Round 2 qualified submission
- OpenEnv API implemented: `reset` / `step` / `state`
- 4 tasks with clear progression: `easy -> medium -> hard -> security`
- Deterministic grader with partial-credit reward in `[0.0, 1.0]`
- Baseline inference script with machine-readable logs
- Added run analytics endpoints plus `/manifest` for evaluator visibility
- Added automated tests and CI validation

## Environment Design

Each episode shows one snippet at a time.
The agent submits one `BugReport` for the current snippet and receives immediate reward + feedback.

### Observation Space

| Field | Type | Description |
|------|------|-------------|
| `snippets` | `list[CodeSnippet]` | Current snippet only (single-step reveal) |
| `step_number` | `int` | Current step in episode |
| `total_snippets` | `int` | Total snippets in selected task |
| `task_name` | `str` | Active task |
| `session_id` | `str \| null` | Session identifier from `/reset` |

### Action Space

| Field | Type | Description |
|------|------|-------------|
| `reports` | `list[BugReport]` | Submitted bug reports |
| `bug_type` | `enum` | `off_by_one`, `wrong_variable`, `missing_return`, `mutable_default_arg`, `wrong_logic`, `missing_edge_case`, `incorrect_exception_handling`, `hardcoded_secret`, `no_bug` |
| `severity` | `enum` | `low`, `medium`, `high` |
| `suggested_fix` | `str` | Proposed correction |

## Tasks

| Task | Snippets | Languages | Description |
|------|----------|-----------|-------------|
| `easy` | 5 | Python | Obvious but realistic production bugs |
| `medium` | 6 | Python | Subtle retries/cache/webhook issues |
| `hard` | 14 | Python + JavaScript | Advanced regressions + no-bug traps (extra hard negatives) |
| `security` | 5 | Python | SQL injection, secrets, traversal, hashing, and secure no-bug validation |

## What makes this environment unique

- **Multi-language** — supports both Python and JavaScript snippets
- **PR context** — each snippet includes a pull request description and intent, mimicking real code review
- **Real-world review flow** — tasks cover pagination, auth refresh, checkout totals, retry logic, cache invalidation, webhooks, and security bugs
- **Hard-mode ambiguity** — advanced tasks include realistic no-bug snippets and subtle regressions that reward reviewer restraint
- **Fix suggestion scoring** — agent must not only identify the bug but suggest a correct fix
- **Security vulnerability detection** — dedicated task for real-world security bugs
- **No-bug detection** — some snippets have no bug, agent must avoid false positives
- **Partial credit grading** — 6 score levels rewarding nuanced understanding

## Reward Logic

| Condition | Score |
|----------|-------|
| Correct bug type + correct severity + high-quality fix | `1.0` |
| Correct bug type + correct severity + weak fix | `0.8` |
| Correct bug type + non-exact severity + high-quality fix | `0.7` |
| Correct bug type + non-exact severity + weak fix | `0.5` |
| Wrong bug type | `0.2` |
| Missed snippet / false positive on no-bug case | `0.0` |

The grader is deterministic and checks:
- bug/severity correctness
- explanation quality
- fix quality
- context grounding and specificity

## API Endpoints

| Method | Endpoint | Purpose |
|------|----------|---------|
| `GET` | `/` | Service metadata / running status |
| `GET` | `/health` | Health check |
| `POST` | `/reset` | Start episode |
| `POST` | `/step` | Submit action |
| `GET` | `/state` | Current session state |
| `GET` | `/tasks` | Task catalog |
| `GET` | `/manifest` | Project/task schema summary for evaluators |
| `GET` | `/report` | Detailed per-session analytics |
| `GET` | `/sessions/summary` | Aggregate session summary |
| `POST` | `/grade` | Offline grading for full-task submission |

`/reset` and `/step` support both query-style and JSON-body usage for evaluator compatibility.

## Setup

### Local

```bash
git clone https://github.com/sidhesh0706/project8PM
cd project8PM
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 7860
```

### Docker

```bash
docker build -t code-review-env .
docker run -p 7860:7860 code-review-env
```

## Baseline Inference

```bash
python inference.py
```

Environment variables:

| Variable | Description |
|----------|-------------|
| `API_BASE_URL` | LLM endpoint (default present) |
| `MODEL_NAME` | Model id (default present) |
| `API_KEY` | Primary credential |
| `HF_TOKEN` | Credential fallback accepted by baseline |
| `LOCAL_IMAGE_NAME` | Optional docker-image runner variable |

Expected logs include:
- `[START] ...`
- `[STEP] ...`
- `[END] ...`

Baseline writes `scores.json` with per-task scores in `[0.0, 1.0]`.

## Tests

```bash
python -m unittest discover -s tests -v
```

Included:
- `tests/test_api_contract.py`
- `tests/test_grader_determinism.py`

## Submission Validation

Run preflight validator before submitting:

```bash
python validate_submission.py
```

It checks:
- task + dataset integrity
- `openenv.yaml` alignment with real task counts
- API contract behavior via `TestClient`
- manifest endpoint availability and schema keys
- baseline reproducibility/log format (`[START]`, `[STEP]`, `[END]`)
- `scores.json` validity

## CI

GitHub Actions workflow: `.github/workflows/ci.yml`

It runs on push/pull request and executes:
1. dependency install
2. unit tests
3. `python validate_submission.py`

## Reproducibility

Full runbook is documented in `REPRODUCIBILITY.md`.

## Judge Quick Run

```bash
# 1) Start server
uvicorn app:app --host 0.0.0.0 --port 7860

# 2) Run tests
python -m unittest discover -s tests -v

# 3) Run preflight
python validate_submission.py
```

## Live Demo

https://huggingface.co/spaces/sid0706/code-review-env
