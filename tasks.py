from models import CodeSnippet, BugReport

# ─── EASY TASK ───────────────────────────────────────────────

EASY_SNIPPETS = [
    CodeSnippet(
        id="e1",
        code="""
def paginate_results(rows, page, page_size):
    start = page * page_size
    end = start + page_size + 1
    return rows[start:end]
""",
        language="python",
        context="Returns one page of results from a backend search endpoint",
        pr_description="Added pagination helper for the admin search API",
        failed_test="assert len(paginate_results(list(range(20)), 1, 10)) == 10  # Returns 11 items",
    ),
    CodeSnippet(
        id="e2",
        code="""
def should_refresh_session(expires_at, now):
    if expires_at > now:
        return True
    return False
""",
        language="python",
        context="Determines whether an auth session should be refreshed",
        pr_description="Added session refresh helper for the auth middleware",
        failed_test="assert should_refresh_session(expires_at=100, now=50) is False  # Refreshes active sessions",
    ),
    CodeSnippet(
        id="e3",
        code="""
def calculate_order_total(subtotal, tax, discount):
    total = subtotal + tax
    total -= tax
    return total
""",
        language="python",
        context="Calculates the final order total shown during checkout",
        pr_description="Added helper for the checkout summary component",
        failed_test="assert calculate_order_total(100, 10, 15) == 95  # Returns 100",
    ),
]

EASY_ANSWERS = [
    BugReport(
        snippet_id="e1",
        bug_type="off_by_one",
        explanation="The page slice ends one item too far because the end index adds an extra +1.",
        severity="high",
        suggested_fix="end = start + page_size",
    ),
    BugReport(
        snippet_id="e2",
        bug_type="wrong_logic",
        explanation="The refresh check is inverted. Active sessions should not be refreshed before expiry.",
        severity="medium",
        suggested_fix="if expires_at <= now:\n    return True",
    ),
    BugReport(
        snippet_id="e3",
        bug_type="wrong_variable",
        explanation="The function subtracts tax instead of discount, so the wrong variable is applied.",
        severity="high",
        suggested_fix="total -= discount",
    ),
]

# ─── MEDIUM TASK ─────────────────────────────────────────────

MEDIUM_SNIPPETS = [
    CodeSnippet(
        id="m1",
        code="""
def fetch_with_retries(client, request, max_attempts=3):
    for attempt in range(1, max_attempts):
        response = client.send(request)
        if response.ok:
            return response
    return None
""",
        language="python",
        context="Sends an outbound API request with retry support for transient failures",
        pr_description="Added retry helper for the billing gateway client",
        failed_test="assert fetch_with_retries(client, request, max_attempts=3) calls send 3 times  # Only 2 attempts happen",
    ),
    CodeSnippet(
        id="m2",
        code="""
def add_cache_tag(key, tag, tags=[]):
    tags.append(tag)
    cache_backend.write(key, {"tags": tags})
    return tags
""",
        language="python",
        context="Stores cache metadata tags for invalidation in the content API",
        pr_description="Added helper for tagging cached CMS responses",
        failed_test="assert add_cache_tag('post:1', 'news') != add_cache_tag('post:2', 'sports')  # Tags leak across requests",
    ),
    CodeSnippet(
        id="m3",
        code="""
def parse_webhook_event(payload):
    event_type = payload["type"]
    event_id = payload["id"]
    return {"type": event_type, "id": event_id}
""",
        language="python",
        context="Extracts the event metadata from a payment webhook payload",
        pr_description="Added webhook payload parser for the payments service",
        failed_test="assert parse_webhook_event(None) is None  # Crashes when the provider sends an empty payload",
    ),
]

MEDIUM_ANSWERS = [
    BugReport(
        snippet_id="m1",
        bug_type="off_by_one",
        explanation="The retry loop stops one attempt too early because the upper bound excludes max_attempts.",
        severity="high",
        suggested_fix="for attempt in range(1, max_attempts + 1):",
    ),
    BugReport(
        snippet_id="m2",
        bug_type="mutable_default_arg",
        explanation="The default tags list is shared across calls, so cache tags leak between requests.",
        severity="high",
        suggested_fix="def add_cache_tag(key, tag, tags=None):\n    if tags is None:\n        tags = []",
    ),
    BugReport(
        snippet_id="m3",
        bug_type="missing_edge_case",
        explanation="The parser assumes payload is always present and well-formed, so None crashes immediately.",
        severity="medium",
        suggested_fix="if not payload:\n    return None\nevent_type = payload[\"type\"]",
    ),
]

# ─── HARD TASK ───────────────────────────────────────────────

HARD_SNIPPETS = [
    CodeSnippet(
        id="h1",
        code="""
def factorial(n):
    if n == 0:
        return 1
    return n * factorial(n)
""",
        language="python",
        context="Returns the factorial of n recursively",
        pr_description="Recursive factorial implementation for the math library",
        failed_test="assert factorial(5) == 120  # RecursionError: maximum depth exceeded",
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
        language="python",
        context="Reads and returns the contents of a file at the given path",
        pr_description="Safe file reader that returns None on any error",
        failed_test="# File handle leaks on success, bare except hides real errors",
    ),
    CodeSnippet(
        id="h3",
        code="""
def celsius_to_fahrenheit(c):
    return (c * 9/5) + 32
""",
        language="python",
        context="Converts a Celsius temperature to Fahrenheit",
        pr_description="Temperature conversion utility for the weather module",
        failed_test="# No failing test — function is correct",
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
        language="python",
        context="Removes duplicate elements from a list while preserving order",
        pr_description="Deduplication utility that maintains original order",
        failed_test="# No failing test — function is correct",
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
        language="python",
        context="Divides a by b, returning None if division is not possible",
        pr_description="Safe division that handles type errors gracefully",
        failed_test="assert safe_divide(10, 0) is None  # Raises ZeroDivisionError instead",
    ),
    CodeSnippet(
        id="h6",
        code="""
function getUserAge(user) {
    if (user.age = null) {
        return 'Unknown';
    }
    return user.age;
}
""",
        language="javascript",
        context="Returns the age of a user object, or 'Unknown' if age is not set",
        pr_description="Helper to safely access user age in the profile component",
        failed_test="// getUserAge({age: 25}) returns 'Unknown' instead of 25",
    ),
    CodeSnippet(
        id="h7",
        code="""
async function fetchData(url) {
    const response = await fetch(url);
    const data = response.json();
    return data;
}
""",
        language="javascript",
        context="Fetches JSON data from a URL and returns the parsed response",
        pr_description="Async data fetching utility for the API layer",
        failed_test="// Returns a Promise object instead of parsed JSON",
    ),
    CodeSnippet(
        id="h8",
        code="""
def get_config(key, config={}):
    if key not in config:
        config[key] = load_default(key)
    return config[key]
""",
        language="python",
        context="Returns config value for key, loading defaults if not present",
        pr_description="Config accessor with lazy default loading",
        failed_test="# Config persists across calls — second call gets first call's config",
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
    BugReport(
        snippet_id="h6",
        bug_type="wrong_logic",
        explanation="Uses = (assignment) instead of === (comparison). Always sets age to null.",
        severity="high",
        suggested_fix="if (user.age === null) {",
    ),
    BugReport(
        snippet_id="h7",
        bug_type="missing_return",
        explanation="response.json() returns a Promise. Must await it to get the actual data.",
        severity="high",
        suggested_fix="const data = await response.json();",
    ),
    BugReport(
        snippet_id="h8",
        bug_type="mutable_default_arg",
        explanation="Mutable default dict {} persists across calls sharing config state.",
        severity="high",
        suggested_fix="def get_config(key, config=None):\n    if config is None:\n        config = {}",
    ),
]

# ─── SECURITY TASK ───────────────────────────────────────────

SECURITY_SNIPPETS = [
    CodeSnippet(
        id="s1",
        code="""
def get_user(user_id):
    query = "SELECT * FROM users WHERE id = " + user_id
    return db.execute(query)
""",
        language="python",
        context="Fetches a user from the database by ID",
        pr_description="Added user lookup function for the auth module",
        failed_test="# get_user('1 OR 1=1') returns all users — SQL injection",
    ),
    CodeSnippet(
        id="s2",
        code="""
AWS_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"

def connect_to_s3():
    return boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )
""",
        language="python",
        context="Connects to AWS S3 using hardcoded credentials",
        pr_description="Added S3 connection utility for file uploads",
        failed_test="# Credentials exposed in source code",
    ),
    CodeSnippet(
        id="s3",
        code="""
def read_file(filename):
    base_dir = "/var/www/uploads/"
    filepath = base_dir + filename
    with open(filepath, 'r') as f:
        return f.read()
""",
        language="python",
        context="Reads a file from the uploads directory by filename",
        pr_description="File reader for user uploaded documents",
        failed_test="# read_file('../../../etc/passwd') reads system files — path traversal",
    ),
    CodeSnippet(
        id="s4",
        code="""
def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()
""",
        language="python",
        context="Hashes a password for storage in the database",
        pr_description="Password hashing utility for user registration",
        failed_test="# MD5 is cryptographically broken for password storage",
    ),
]

SECURITY_ANSWERS = [
    BugReport(
        snippet_id="s1",
        bug_type="wrong_logic",
        explanation="String concatenation in SQL query allows SQL injection attacks.",
        severity="high",
        suggested_fix="query = 'SELECT * FROM users WHERE id = ?'\ndb.execute(query, (user_id,))",
    ),
    BugReport(
        snippet_id="s2",
        bug_type="hardcoded_secret",
        explanation="AWS credentials hardcoded in source code expose them to anyone with repo access.",
        severity="high",
        suggested_fix="Use environment variables: os.getenv('AWS_SECRET_KEY')",
    ),
    BugReport(
        snippet_id="s3",
        bug_type="missing_edge_case",
        explanation="No validation of filename allows path traversal attacks using ../",
        severity="high",
        suggested_fix="filename = os.path.basename(filename)\nfilepath = os.path.join(base_dir, filename)",
    ),
    BugReport(
        snippet_id="s4",
        bug_type="wrong_logic",
        explanation="MD5 is cryptographically broken. Use bcrypt or argon2 for password hashing.",
        severity="high",
        suggested_fix="import bcrypt\nreturn bcrypt.hashpw(password.encode(), bcrypt.gensalt())",
    ),
]

# ─── TASK REGISTRY ───────────────────────────────────────────

TASKS = {
    "easy": {
        "snippets": EASY_SNIPPETS,
        "answers": EASY_ANSWERS,
        "description": "3 production-style review snippets with one obvious bug each",
    },
    "medium": {
        "snippets": MEDIUM_SNIPPETS,
        "answers": MEDIUM_ANSWERS,
        "description": "3 production-style snippets with subtle bugs including retries, cache state, and webhook parsing",
    },
    "hard": {
        "snippets": HARD_SNIPPETS,
        "answers": HARD_ANSWERS,
        "description": "8 snippets (Python + JavaScript), subtle bugs, some have no bug",
    },
    "security": {
        "snippets": SECURITY_SNIPPETS,
        "answers": SECURITY_ANSWERS,
        "description": "4 snippets with security vulnerabilities — SQL injection, hardcoded secrets, path traversal",
    },
}
