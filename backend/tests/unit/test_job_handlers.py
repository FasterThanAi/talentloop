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
import pathlib

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


def test_scoring_handler_reads_the_key_the_endpoint_sends():
    """
    Regression: /requisitions/{id}/score enqueues "pipeline_entry_ids" but the handler read
    "pipeline_ids". The mismatch made every scoring run a silent no-op that still reported
    success. Assert the two sides agree, statically, so a rename cannot resurrect it.
    """
    app_dir = pathlib.Path(APP_DIR)
    endpoint_keys = set()
    tree = ast.parse((app_dir / "api" / "v1" / "requisitions.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and getattr(node.func, "id", None) == "enqueue_job"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == "score_candidates"
        ):
            payload = node.args[1]
            endpoint_keys = {k.value for k in payload.keys if isinstance(k, ast.Constant)}

    assert endpoint_keys, "could not find the score_candidates enqueue call"

    handler_src = (app_dir / "jobs" / "scoring.py").read_text(encoding="utf-8")
    ids_key = next(k for k in endpoint_keys if k.endswith("ids") and k != "org_id")
    assert f'payload.get("{ids_key}")' in handler_src, (
        f"endpoint sends '{ids_key}' but handle_scoring_job never reads it"
    )
