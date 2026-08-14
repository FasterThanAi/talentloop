"""
Gemini -> Groq failover.

The Gemini free tier allows ~20 generate_content requests per day on gemini-3.5-flash.
That is enough to exhaust mid-demo, at which point every AI feature returns 429 and the
product looks broken. These tests pin the behaviour that keeps it working:

  * a quota error fails over IMMEDIATELY (no retry — a daily quota won't clear in seconds)
  * a transient error retries on the same provider first
  * ordering is configurable, and unconfigured providers are skipped entirely
"""
import asyncio

import pytest

from app.ai import client as ai
from app.core.config import settings


@pytest.fixture(autouse=True)
def restore_settings():
    original = (
        settings.GEMINI_API_KEY, settings.GROQ_API_KEY, settings.AI_PROVIDER_ORDER,
    )
    yield
    (settings.GEMINI_API_KEY, settings.GROQ_API_KEY, settings.AI_PROVIDER_ORDER) = original


# ─────────────────────────────────────────────────────────── quota detection

@pytest.mark.parametrize("message", [
    "429 You exceeded your current quota, please check your plan and billing details.",
    "Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests",
    "RESOURCE_EXHAUSTED",
    "Rate limit reached for model",
    "HTTP 429: Too Many Requests",
])
def test_quota_errors_are_recognised(message):
    assert ai.is_quota_error(RuntimeError(message)), f"should be treated as quota: {message}"


@pytest.mark.parametrize("message", [
    "Connection reset by peer",
    "500 Internal Server Error",
    "invalid JSON in response",
])
def test_non_quota_errors_are_not_misread(message):
    assert not ai.is_quota_error(RuntimeError(message))


# ─────────────────────────────────────────────────────────── provider selection

def test_unconfigured_providers_are_skipped():
    settings.GEMINI_API_KEY = None
    settings.GROQ_API_KEY = "gsk_test"
    settings.AI_PROVIDER_ORDER = "gemini,groq"
    assert ai.active_providers() == ["groq"]


def test_order_is_configurable():
    settings.GEMINI_API_KEY = "gem_test"
    settings.GROQ_API_KEY = "gsk_test"
    settings.AI_PROVIDER_ORDER = "groq,gemini"
    assert ai.active_providers() == ["groq", "gemini"]


def test_no_keys_means_mock_mode():
    settings.GEMINI_API_KEY = None
    settings.GROQ_API_KEY = None
    assert ai.active_providers() == []
    assert ai.ai_is_mocked() is True


def test_groq_alone_is_not_mock_mode():
    """A Groq-only deployment must run for real, not silently serve canned output."""
    settings.GEMINI_API_KEY = None
    settings.GROQ_API_KEY = "gsk_test"
    settings.AI_PROVIDER_ORDER = "gemini,groq"
    assert ai.ai_is_mocked() is False


# ─────────────────────────────────────────────────────────── failover behaviour

def _client_with(monkeypatch, gemini_effect, groq_effect):
    c = ai.AIClient.__new__(ai.AIClient)  # skip __init__ (it configures the real SDK)
    calls = {"gemini": 0, "groq": 0}

    async def fake_gemini(prompt_text, temperature, want_json):
        calls["gemini"] += 1
        if isinstance(gemini_effect, Exception):
            raise gemini_effect
        return gemini_effect, 10, 20

    async def fake_groq(prompt_text, temperature, want_json):
        calls["groq"] += 1
        if isinstance(groq_effect, Exception):
            raise groq_effect
        return groq_effect, 11, 21

    monkeypatch.setattr(c, "_generate_gemini", fake_gemini)
    monkeypatch.setattr(c, "_generate_groq", fake_groq)
    return c, calls


def test_quota_error_fails_over_without_retrying(monkeypatch):
    settings.GEMINI_API_KEY = "gem_test"
    settings.GROQ_API_KEY = "gsk_test"
    settings.AI_PROVIDER_ORDER = "gemini,groq"
    c, calls = _client_with(
        monkeypatch,
        RuntimeError("429 You exceeded your current quota"),
        '{"ok": true}',
    )
    monkeypatch.setattr(ai, "load_prompt_template", lambda name: "Return JSON only.")

    result = asyncio.run(c.generate("score.v1", {}, temperature=0.0))

    assert result.provider == "groq"
    assert result.raw_text == '{"ok": true}'
    assert calls["gemini"] == 1, "a quota error must not be retried — it will not clear"
    assert calls["groq"] == 1


def test_transient_error_retries_before_failing_over(monkeypatch):
    settings.GEMINI_API_KEY = "gem_test"
    settings.GROQ_API_KEY = "gsk_test"
    settings.AI_PROVIDER_ORDER = "gemini,groq"
    c, calls = _client_with(monkeypatch, RuntimeError("Connection reset"), '{"ok": true}')
    monkeypatch.setattr(ai, "load_prompt_template", lambda name: "Return JSON only.")

    result = asyncio.run(c.generate("score.v1", {}, temperature=0.0))

    assert result.provider == "groq"
    assert calls["gemini"] == ai.MAX_ATTEMPTS_PER_PROVIDER


def test_primary_success_never_touches_the_fallback(monkeypatch):
    settings.GEMINI_API_KEY = "gem_test"
    settings.GROQ_API_KEY = "gsk_test"
    settings.AI_PROVIDER_ORDER = "gemini,groq"
    c, calls = _client_with(monkeypatch, '{"ok": true}', '{"never": true}')
    monkeypatch.setattr(ai, "load_prompt_template", lambda name: "Return JSON only.")

    result = asyncio.run(c.generate("score.v1", {}, temperature=0.0))

    assert result.provider == "gemini"
    assert calls["groq"] == 0


def test_both_providers_failing_raises_with_both_reasons(monkeypatch):
    settings.GEMINI_API_KEY = "gem_test"
    settings.GROQ_API_KEY = "gsk_test"
    settings.AI_PROVIDER_ORDER = "gemini,groq"
    c, _ = _client_with(
        monkeypatch,
        RuntimeError("429 quota"),
        RuntimeError("HTTP 503: service unavailable"),
    )
    monkeypatch.setattr(ai, "load_prompt_template", lambda name: "Return JSON only.")

    with pytest.raises(RuntimeError) as exc:
        asyncio.run(c.generate("score.v1", {}, temperature=0.0))

    message = str(exc.value)
    assert "gemini" in message and "groq" in message, "the error must name every provider tried"
