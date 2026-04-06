---
title: Code Review Env
emoji: 🔍
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# Code Review Environment

An OpenEnv-style environment where an AI agent reviews code snippets,
identifies bugs by type and severity, and suggests fixes.

## Environment Description

The agent receives Python and JavaScript code snippets and must identify:
- What type of bug exists (or if there is no bug)
- How severe the bug is
- A suggested fix for the bug

Partial credit is awarded at every level — finding the right bug type
but wrong severity still scores 0.7. Providing a good fix on top scores 1.0.

## Observation Space

| Field | Type | Description |
|-------|------|-------------|
| snippets | list[CodeSnippet] | Python and JavaScript code snippets to review |
| step_number | int | Current step in the episode |
| total_snippets | int | Total snippets in this task |
| task_name | str | Name of the current task |
| session_id | str \| null | Session identifier returned by `/reset` |

## Action Space

| Field | Type | Values |
|-------|------|--------|
| reports | list[BugReport] | One report per snippet |
| bug_type | enum | off_by_one, wrong_variable, missing_return, mutable_default_arg, wrong_logic, missing_edge_case, incorrect_exception_handling, hardcoded_secret, no_bug |
| severity | enum | low, medium, high |
| suggested_fix | str | Corrected line(s) of code |

## Tasks

| Task | Snippets | Languages | Description |
|------|----------|-----------|-------------|
| easy | 3 | Python | Production-style snippets with one obvious bug per snippet |
| medium | 3 | Python | Production-style snippets with retries, cache state, and webhook edge cases |
| hard | 8 | Python + JavaScript | Subtle bugs, some snippets have no bug |
| security | 4 | Python | SQL injection, hardcoded secrets, path traversal, weak hashing |

## What makes this environment unique

- **Multi-language** — supports both Python and JavaScript snippets
- **PR context** — each snippet includes a pull request description and intent, mimicking real code review
- **Real-world review flow** — tasks cover pagination, auth refresh, checkout totals, retry logic, cache invalidation, webhooks, and security bugs
- **Fix suggestion scoring** — agent must not only identify the bug but suggest a correct fix
- **Security vulnerability detection** — dedicated task for real-world security bugs
- **No-bug detection** — some snippets have no bug, agent must avoid false positives
- **Partial credit grading** — 6 score levels rewarding nuanced understanding

## Scoring

| Condition | Score |
|-----------|-------|
| Correct bug type + correct severity + good fix | **1.0** |
| Correct bug type + correct severity + weak fix | **0.8** |
| Correct bug type + wrong severity + good fix | **0.7** |
| Correct bug type + wrong severity + weak fix | **0.5** |
| Wrong bug type | **0.2** |
| False positive on no-bug snippet | **0.0** |
| Missed snippet | **0.0** |

Partial credit is awarded at every level — the reward function provides signal across the full trajectory, not just at episode end.

Each episode reveals one snippet at a time. The agent must submit a report for the current snippet, receive a reward, and continue until the task is complete.

The grader is deterministic and combines exact bug-type matching with semantic checks on the explanation and suggested fix so partially correct reviews receive partial credit.

## Setup & Run Locally
```bash
git clone https://github.com/sidhesh0706/project8PM
cd project8PM
pip install -r requirements.txt
python app.py
```

You can also run with:

```bash
uvicorn app:app --host 0.0.0.0 --port 7860
```

## Run with Docker
```bash
docker build -t code-review-env .
docker run -p 7860:7860 \
  -e API_BASE_URL=https://api.groq.com/openai/v1 \
  -e MODEL_NAME=llama-3.3-70b-versatile \
  -e HF_TOKEN=your_key_here \
  code-review-env
```

## Run Inference
```bash
export API_BASE_URL=https://api.groq.com/openai/v1
export MODEL_NAME=llama-3.3-70b-versatile
export HF_TOKEN=your_key_here
python inference.py
```

The default baseline is deterministic and offline-friendly for validator reproducibility. To force live LLM calls, set `USE_LLM_BASELINE=1` in addition to the variables above.

## Inference Output Format
```text
[START] task=easy env=code-review-env model=llama-3.3-70b-versatile
[STEP] step=1 action=review(snippet=e1) reward=1.00 done=false error=null
[STEP] step=2 action=review(snippet=e2) reward=0.70 done=false error=null
[STEP] step=3 action=review(snippet=e3) reward=1.00 done=true error=null
[END] success=true steps=3 score=0.900 rewards=1.00,0.70,1.00
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | / | Health check |
| POST | /reset | Start a new episode and return a `session_id` |
| POST | /step | Submit bug reports for a `session_id` |
| GET | /state | Get current observation for a `session_id` |
| GET | /tasks | List all tasks |

All four tasks currently supported by the API are `easy`, `medium`, `hard`, and `security`.

Call `/reset` first, then pass the returned `session_id` to `/step` and `/state`.

## Environment Variables

| Variable | Description |
|----------|-------------|
| API_BASE_URL | LLM API endpoint |
| MODEL_NAME | Model identifier |
| HF_TOKEN | Your API key |
| USE_LLM_BASELINE | Optional flag to enable live model calls in `inference.py` |

## Live Demo

[https://huggingface.co/spaces/sid0706/code-review-env](https://huggingface.co/spaces/sid0706/code-review-env)
