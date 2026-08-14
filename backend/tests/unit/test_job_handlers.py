"""
Every job name the API enqueues must have a registered handler.

This exists because `enqueue_job("score_requisition_candidates", ...)` shipped to production
against a handler registered as `score_candidates`. Nothing caught it: it imports fine, it
lints fine, and it only fails at runtime — as a 500 on the "Score All Candidates" button.
The test below reads the actual enqueue_job() call sites out of the source and asserts each
name resolves, so a typo fails in CI instead of in front of a user.
"""
import ast
import os

import app.main  # noqa: F401  — importing the app is what registers the handlers
from app.jobs.runner import registered_job_handlers, verify_job_handlers

APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "app")


def _enqueued_job_names() -> set[str]:
    """Every string literal passed as the first argument to enqueue_job(...)."""
    names: set[str] = set()
    for dirpath, _, files in os.walk(APP_DIR):
        if "__pycache__" in dirpath:
            continue
        for f in files:
            if not f.endswith(".py"):
                continue
            fp = os.path.join(dirpath, f)
            tree = ast.parse(open(fp, encoding="utf-8").read(), fp)
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and getattr(node.func, "id", getattr(node.func, "attr", None)) == "enqueue_job"
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)
                ):
                    names.add(node.args[0].value)
    return names


def test_every_enqueued_job_name_has_a_handler():
    enqueued = _enqueued_job_names()
    registered = set(registered_job_handlers())
    missing = enqueued - registered
    assert not missing, (
        f"enqueue_job() is called with {sorted(missing)}, but only {sorted(registered)} "
        "are registered. Either the name is misspelled or the registering module is not "
        "imported in app/main.py."
    )


def test_expected_handlers_are_all_registered():
    missing = verify_job_handlers()
    assert not missing, f"Expected job handlers not registered: {missing}"


def test_at_least_the_core_pipeline_handlers_exist():
    registered = set(registered_job_handlers())
    for required in ("source_candidates", "enrich_candidates", "score_candidates"):
        assert required in registered, f"core handler '{required}' is not registered"
