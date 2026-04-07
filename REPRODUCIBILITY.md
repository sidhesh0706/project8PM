# Reproducibility Guide

This document gives a deterministic local validation flow for the project.

## 1) Install

```bash
pip install -r requirements.txt
```

## 2) Run API

```bash
uvicorn app:app --host 0.0.0.0 --port 7860
```

## 3) Run Tests

```bash
python -m unittest discover -s tests -v
```

## 4) Run Baseline

```bash
python inference.py
```

Expected output includes machine-readable markers:

- `[START] ...`
- `[STEP] ...`
- `[END] ...`

Baseline writes `scores.json` with one score per task.

## 5) Run Preflight Validator

```bash
python validate_submission.py
```

Expected summary:

```text
Validation status: PASSED
```

## Notes

- Baseline uses `API_KEY` or `HF_TOKEN` when provided.
- Without credentials, baseline falls back to deterministic heuristic action selection.
