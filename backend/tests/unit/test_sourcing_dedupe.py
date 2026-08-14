"""
URL-sourced candidates must dedupe on the URL, not on position in the request.

The original implementation assigned `candidate_{idx+1}@profile.dev`, so the first URL of
every ingestion produced the same address as the first URL of every previous ingestion.
Sourcing dedupes on (org_id, email), so in production every profile after the very first
was silently dropped with "Candidate already present in requisition pipeline" — the user
saw an ingestion job succeed and nothing appear in the pipeline.
"""
from app.api.v1.sourcing import placeholder_email_for_url


def test_different_profiles_get_different_addresses():
    a = placeholder_email_for_url("https://github.com/FasterThanAi")
    b = placeholder_email_for_url("https://github.com/torvalds")
    assert a != b, "two different profiles collided — they would dedupe each other away"


def test_same_profile_is_idempotent():
    """Re-ingesting the same profile SHOULD dedupe. That behaviour is intentional."""
    a = placeholder_email_for_url("https://github.com/FasterThanAi")
    b = placeholder_email_for_url("https://github.com/FasterThanAi/")
    c = placeholder_email_for_url("  https://github.com/fasterthanai  ")
    assert a == b == c


def test_same_username_on_different_sites_does_not_collide():
    gh = placeholder_email_for_url("https://github.com/FasterThanAi")
    gl = placeholder_email_for_url("https://gitlab.com/FasterThanAi")
    assert gh != gl


def test_address_is_wellformed_and_readable():
    email = placeholder_email_for_url("https://github.com/FasterThanAi")
    local, _, domain = email.partition("@")
    assert domain == "sourced.talentloop.local"
    assert "fasterthanai" in local and "github" in local
    # No characters that would break an address or a CSV export.
    assert all(ch.isalnum() or ch in "._-" for ch in local)


def test_many_urls_in_one_batch_are_all_distinct():
    urls = [f"https://github.com/user{i}" for i in range(25)]
    addresses = {placeholder_email_for_url(u) for u in urls}
    assert len(addresses) == len(urls)
