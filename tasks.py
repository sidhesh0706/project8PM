from models import CodeSnippet, BugReport

EASY_SNIPPETS = [
    CodeSnippet(
        id="e1",
        code="""
def get_last_element(lst):
    return lst[len(lst)]
""",
    ),
    CodeSnippet(
        id="e2",
        code="""
def is_even(number):
    if number % 2 == 1:
        return True
    return False
""",
    ),
    CodeSnippet(
        id="e3",
        code="""
def multiply(a, b):
    result = a + b
    return result
""",
    ),
]

EASY_ANSWERS = [
    BugReport(
        snippet_id="e1",
        bug_type="off_by_one",
        explanation="lst[len(lst)] is out of range. Should be lst[len(lst)-1] or lst[-1]",
        severity="high",
        suggested_fix="return lst[-1]",
    ),
    BugReport(
        snippet_id="e2",
        bug_type="wrong_logic",
        explanation="Returns True when number is odd, not even. Condition is inverted.",
        severity="medium",
        suggested_fix="if number % 2 == 0: return True",
    ),
    BugReport(
        snippet_id="e3",
        bug_type="wrong_variable",
        explanation="Uses + instead of *. The function is supposed to multiply.",
        severity="high",
        suggested_fix="result = a * b",
    ),
]

MEDIUM_SNIPPETS = [
    CodeSnippet(
        id="m1",
        code="""
def get_average(numbers):
    total = 0
    for i in range(1, len(numbers)):
        total += numbers[i]
    return total / len(numbers)
""",
    ),
    CodeSnippet(
        id="m2",
        code="""
def append_to_list(value, my_list=[]):
    my_list.append(value)
    return my_list
""",
    ),
    CodeSnippet(
        id="m3",
        code="""
def divide(a, b):
    return a / b
""",
    ),
]

MEDIUM_ANSWERS = [
    BugReport(
        snippet_id="m1",
        bug_type="off_by_one",
        explanation="range(1, len(numbers)) skips the first element at index 0.",
        severity="high",
        suggested_fix="for i in range(0, len(numbers)):",
    ),
    BugReport(
        snippet_id="m2",
        bug_type="mutable_default_arg",
        explanation="Using a mutable default argument [] means the list persists across calls.",
        severity="high",
        suggested_fix="def append_to_list(value, my_list=None):\n    if my_list is None:\n        my_list = []",
    ),
    BugReport(
        snippet_id="m3",
        bug_type="missing_edge_case",
        explanation="No check for b == 0. Will raise ZeroDivisionError at runtime.",
        severity="medium",
        suggested_fix="if b == 0: return None\nreturn a / b",
    ),
]

HARD_SNIPPETS = [
    CodeSnippet(
        id="h1",
        code="""
def factorial(n):
    if n == 0:
        return 1
    return n * factorial(n)
""",
    ),
    CodeSnippet(
        id="h2",
        code="""
def read_file(path):
    try:
        f = open(path, 'r')
        return f.read()
    except:
        return None
""",
    ),
    CodeSnippet(
        id="h3",
        code="""
def celsius_to_fahrenheit(c):
    return (c * 9/5) + 32
""",
    ),
    CodeSnippet(
        id="h4",
        code="""
def remove_duplicates(lst):
    seen = []
    result = []
    for item in lst:
        if item not in seen:
            seen.append(item)
            result.append(item)
    return result
""",
    ),
    CodeSnippet(
        id="h5",
        code="""
def safe_divide(a, b):
    try:
        return a / b
    except TypeError:
        return None
""",
    ),
]

HARD_ANSWERS = [
    BugReport(
        snippet_id="h1",
        bug_type="wrong_logic",
        explanation="factorial(n) calls factorial(n) not factorial(n-1). Infinite recursion.",
        severity="high",
        suggested_fix="return n * factorial(n-1)",
    ),
    BugReport(
        snippet_id="h2",
        bug_type="incorrect_exception_handling",
        explanation="Bare except swallows all errors and file is never closed.",
        severity="high",
        suggested_fix="with open(path, 'r') as f:\n    return f.read()",
    ),
    BugReport(
        snippet_id="h3",
        bug_type="no_bug",
        explanation="Formula is correct. No bug present.",
        severity="low",
        suggested_fix="No fix needed.",
    ),
    BugReport(
        snippet_id="h4",
        bug_type="no_bug",
        explanation="Logic is correct, just inefficient. No functional bug.",
        severity="low",
        suggested_fix="No fix needed.",
    ),
    BugReport(
        snippet_id="h5",
        bug_type="missing_edge_case",
        explanation="Catches TypeError but not ZeroDivisionError.",
        severity="high",
        suggested_fix="except (TypeError, ZeroDivisionError):\n    return None",
    ),
]

TASKS = {
    "easy": {
        "snippets": EASY_SNIPPETS,
        "answers": EASY_ANSWERS,
        "description": "3 snippets, one obvious bug each",
    },
    "medium": {
        "snippets": MEDIUM_SNIPPETS,
        "answers": MEDIUM_ANSWERS,
        "description": "3 snippets, subtle bugs including edge cases",
    },
    "hard": {
        "snippets": HARD_SNIPPETS,
        "answers": HARD_ANSWERS,
        "description": "5 snippets, subtle bugs — some snippets have no bug",
    },
}