"""
Regression test for the flush-before-audit rule.

The /pipeline/{id}/draft endpoint 500'd in production with:
    NotNullViolation: null value in column "entity_id" of relation "audit_events"
because write_audit() was handed msg.id right after db.add(msg) — before the flush that
actually applies the UUID default. These tests lock in both halves of the fix.
"""
import ast
import pathlib

import pytest

from app.core.audit import write_audit


def test_write_audit_rejects_empty_entity_id():
    with pytest.raises(ValueError) as exc:
        write_audit(
            db=None,
            org_id="org-1",
            actor_id="user-1",
            action="outreach_drafted",
            entity="outreach_message",
            entity_id=None,
        )
    assert "db.flush()" in str(exc.value)


def test_no_caller_audits_an_unflushed_row():
    """Static sweep: every db.add(x) whose .id is later audited must have a flush between."""
    offenders = []
    for path in pathlib.Path("app").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            added, flushed = {}, set()
            for node in ast.walk(fn):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if node.func.attr == "add" and node.args and isinstance(node.args[0], ast.Name):
                        added[node.args[0].id] = node.lineno
                    if node.func.attr in ("flush", "commit"):
                        flushed.add(node.lineno)
                if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "write_audit":
                    for kw in node.keywords:
                        if kw.arg != "entity_id":
                            continue
                        if not (isinstance(kw.value, ast.Attribute) and kw.value.attr == "id"):
                            continue
                        var = getattr(kw.value.value, "id", None)
                        if var in added and not any(added[var] < ln < node.lineno for ln in flushed):
                            offenders.append(f"{path}: db.add({var}) L{added[var]} -> write_audit L{node.lineno}")
    assert not offenders, "audit called on an unflushed row:\n" + "\n".join(offenders)
