import pytest

from app.jobs.enrichment import is_safe_url


def test_ssrf_guard_blocks_private_ips():
    blocked_urls = [
        "http://127.0.0.1:8000/internal",
        "http://localhost:3000/admin",
        "http://10.0.0.1/secrets",
        "http://192.168.1.1/router",
        "http://172.16.0.5/api",
        "http://169.254.169.254/latest/meta-data/",
        "ftp://example.com/file",
        "http://metadata.google.internal/computeMetadata/v1/"
    ]
    for url in blocked_urls:
        safe, reason = is_safe_url(url)
        assert not safe, f"Expected {url} to be blocked by SSRF guard, but passed ({reason})"


def test_ssrf_guard_allows_public_domains():
    safe_urls = [
        "https://github.com/torvalds",
        "https://fastapi.tiangolo.com",
        "https://python.org"
    ]
    for url in safe_urls:
        safe, reason = is_safe_url(url)
        assert safe, f"Expected {url} to be safe, but got blocked: {reason}"
