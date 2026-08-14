

def test_scoring_handler_reads_the_key_the_endpoint_sends():
    """
    Regression: /requisitions/{id}/score enqueues "pipeline_entry_ids" but the handler read
    "pipeline_ids". The mismatch made every scoring run a silent no-op that still reported
    success. Assert the two sides agree, statically, so a rename cannot resurrect it.
    """
    import ast
    import pathlib

    endpoint_keys = set()
    tree = ast.parse(pathlib.Path("app/api/v1/requisitions.py").read_text(encoding="utf-8"))
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

    handler_src = pathlib.Path("app/jobs/scoring.py").read_text(encoding="utf-8")
    ids_key = next(k for k in endpoint_keys if k.endswith("ids") and k != "org_id")
    assert f'payload.get("{ids_key}")' in handler_src, (
        f"endpoint sends '{ids_key}' but handle_scoring_job never reads it"
    )
