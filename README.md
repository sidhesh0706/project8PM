---
title: Code Review Env
emoji: "🔍"
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# Code Review Environment

A real-world OpenEnv benchmark where an agent performs pull-request style code review on Python and JavaScript snippets. For each snippet, the agent must identify the bug type, assign severity, and suggest a fix.

This environment is designed to evaluate whether an agent can behave like a practical software reviewer rather than solve a toy task. It rewards accurate diagnosis, good reviewer restraint on no-bug snippets, and concrete fixes that address the real root cause.

## Why This Benchmark Matters

Most coding benchmarks focus on generation. This one focuses on **review**:
- understanding intent from PR-style context
- spotting subtle logic, async, state, and security bugs
- avoiding false positives on correct code
- proposing fixes, not just naming the issue

That makes it useful for evaluating real-world engineering agents that assist with pull requests, CI review, or code-quality workflows.

## Environment Design

Each episode reveals **one snippet at a time**.
The agent submits a `BugReport` for the current snippet and receives immediate reward and feedback.

### Observation Space

| Field | Type | Description |
|------|------|-------------|
| `snippets` | `list[CodeSnippet]` | Current snippet only |
| `step_number` | `int` | Current step in the episode |
| `total_snippets` | `int` | Total snippets in the selected task |
| `task_name` | `str` | Active task |
| `session_id` | `str \| null` | Session identifier returned by `/reset` |

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
| `medium` | 6 | Python | Subtler retries, cache-state, and webhook issues |
| `hard` | 14 | Python + JavaScript | Advanced regressions, async issues, and no-bug traps |
| `security` | 5 | Python | SQL injection, secrets, traversal, hashing, and secure no-bug validation |

## What Makes It Strong

- **PR context** - each snippet includes intent, PR description, and failing-test context
- **Real-world bug types** - pagination, auth refresh, cache leakage, async parsing, feature flags, retry loops, and security flaws
- **No-bug cases** - the agent must avoid over-reporting
- **Partial-credit grading** - scoring reflects bug type, severity, explanation quality, and fix quality
- **Multi-language coverage** - benchmark includes both Python and JavaScript
- **Session-based API** - episodes are isolated with `session_id`

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
- bug and severity correctness
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
| `GET` | `/manifest` | Project/task schema summary |
| `GET` | `/report` | Detailed per-session analytics |
| `GET` | `/sessions/summary` | Aggregate session summary |
| `GET` | `/web` | Browser-friendly benchmark overview |
| `POST` | `/grade` | Offline grading for full-task submission |

`/reset` and `/step` support both query-style and JSON-body usage for evaluator compatibility.

## Baseline Inference

Run:

```bash
python inference.py
```

Environment variables:

| Variable | Description |
|----------|-------------|
| `API_BASE_URL` | LLM endpoint, default provided |
| `MODEL_NAME` | Model id, default provided |
| `API_KEY` | Primary credential used by the injected LiteLLM/OpenAI-compatible proxy |
| `HF_TOKEN` | Local fallback accepted by the baseline |
| `LOCAL_IMAGE_NAME` | Optional docker-image runner variable |

When `API_KEY` is present, `inference.py` initializes the OpenAI client with `base_url=API_BASE_URL` and sends proxy traffic through the injected LiteLLM-compatible endpoint.

Expected logs include:
- `[START] ...`
- `[STEP] ...`
- `[END] ...`

The baseline writes `scores.json` with per-task scores in `[0.0, 1.0]`.

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

## Validation And Tests

Run the tests:

```bash
python -m unittest discover -s tests -v
```

Run the local submission validator:

```bash
python validate_submission.py
```

This checks:
- dataset/task integrity
- `openenv.yaml` alignment with task counts
- API contract behavior via `TestClient`
- manifest and analytics endpoints
- baseline reproducibility and log format
- `scores.json` validity

## Reproducibility

Full runbook is documented in `REPRODUCIBILITY.md`.

## Live Demo

- Space: [https://huggingface.co/spaces/sid0706/code-review-env](https://huggingface.co/spaces/sid0706/code-review-env)
- Web UI: [https://sid0706-code-review-env.hf.space/web](https://sid0706-code-review-env.hf.space/web)
- Tasks: [https://sid0706-code-review-env.hf.space/tasks](https://sid0706-code-review-env.hf.space/tasks)
- Docs: [https://sid0706-code-review-env.hf.space/docs](https://sid0706-code-review-env.hf.space/docs)
