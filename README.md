---
title: Code Review Env
emoji: 🔍
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# Code Review Environment

An OpenEnv environment where an AI agent reviews Python code snippets
and identifies bugs by type and severity, and suggests fixes.

## Environment Description

The agent receives Python code snippets and must identify:
- What type of bug exists (or if there is no bug)
- How severe the bug is
- A suggested fix for the bug

Partial credit is awarded at every level — finding the right bug type
but wrong severity still scores 0.7. Providing a good fix on top scores 1.0.

## Observation Space

| Field | Type | Description |
|-------|------|-------------|
| snippets | list[CodeSnippet] | Python code snippets to review |
| step_number | int | Current step in the episode |
| total_snippets | int | Total snippets in this task |
| task_name | str | Name of the current task |

## Action Space

| Field | Type | Values |
|-------|------|--------|
| reports | list[BugReport] | One report per snippet |
| bug_type | enum | off_by_one, wrong_variable, missing_return, mutable_default_arg, wrong_logic, missing_edge_case, incorrect_exception_handling, no_bug |
| severity | enum | low, medium, high |
| suggested_fix | str | Corrected line(s) of code |

## Tasks

| Task | Snippets | Languages | Description |
|------|----------|-----------|-------------|
| easy | 3 | Python | One obvious bug per snippet |
| medium | 3 | Python | Subtle bugs including edge cases |
| hard | 8 | Python + JavaScript | Subtle bugs, some snippets have no bug |
| security | 4 | Python | SQL injection, hardcoded secrets, path traversal, weak hashing |

## What makes this environment unique

- **Multi-language** — hard task includes JavaScript snippets alongside Python
- **PR context** — each snippet includes a pull request description and intent, mimicking real code review
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

## Setup & Run Locally
```bash
git clone https://github.com/sidhesh0706/project8PM
cd project8PM
pip install -r requirements.txt
python app.py
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

## Inference Output Format
[START] task=easy env=code-review-env model=llama-3.3-70b-versatile
[STEP] step=1 action=review(3_snippets) reward=0.73 done=true error=null
[END] success=true steps=1 score=0.730 rewards=0.73

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | / | Health check |
| POST | /reset | Start a new episode |
| POST | /step | Submit bug reports |
| GET | /state | Get current observation |
| GET | /tasks | List all tasks |

## Environment Variables

| Variable | Description |
|----------|-------------|
| API_BASE_URL | LLM API endpoint |
| MODEL_NAME | Model identifier |
| HF_TOKEN | Your API key |

## Live Demo

[https://huggingface.co/spaces/sid0706/code-review-env](https://huggingface.co/spaces/sid0706/code-review-env)
