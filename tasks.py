import json
from pathlib import Path
from pydantic import ValidationError
from models import CodeSnippet, BugReport

DATASET_DIR = Path("dataset")
TASKS = {}

def build_tasks():
    if not DATASET_DIR.exists():
        print(f"[WARNING] Dataset directory not found at {DATASET_DIR.absolute()}")
        return

    for tier_dir in DATASET_DIR.iterdir():
        if not tier_dir.is_dir():
            continue

        tier_name = tier_dir.name
        answers_file = tier_dir / "answers.json"
        config_file = tier_dir / "config.json"

        if not answers_file.exists():
            continue

        task_config = {}
        description = f"{tier_name.capitalize()} tier: dynamically loaded."
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    task_config = json.load(f)
                    description = task_config.get("description", description)
            except json.JSONDecodeError:
                pass

        try:
            with open(answers_file, "r", encoding="utf-8") as f:
                answers_data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[CRITICAL] Malformed answers.json in {tier_dir}: {e}")
            continue

        snippets = []
        answers = []
        rubrics = {}

        for item in answers_data:
            snippet_id = item.get("snippet_id")
            if not snippet_id:
                continue

            code_file = tier_dir / f"{snippet_id}.py"
            if not code_file.exists():
                code_file = tier_dir / f"{snippet_id}.js"

            if not code_file.exists():
                print(f"[WARNING] Missing code file for {snippet_id}.")
                continue

            with open(code_file, "r", encoding="utf-8") as f:
                raw_code = f.read().strip()

            try:
                validated_snippet = CodeSnippet(
                    id=snippet_id,
                    code=raw_code,
                    language=item.get("language", "python"),
                    context=item.get("context", ""),
                    pr_description=item.get("pr_description", ""),
                    failed_test=item.get("failed_test", "")
                )
                validated_answer = BugReport(**item)

                snippets.append(validated_snippet)
                answers.append(validated_answer)
                rubrics[snippet_id] = item.get("grading_hints", {})

            except ValidationError as e:
                print(f"[WARNING] Validation failed for '{snippet_id}': {e}")
                continue

        if snippets:
            TASKS[tier_name] = {
                "snippets": snippets,
                "answers": answers,
                "rubrics": rubrics,
                "config": task_config,
                "description": description,
            }

build_tasks()
