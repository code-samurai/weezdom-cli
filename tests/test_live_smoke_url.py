"""The live smoke base URL must not default to production."""

import pytest

from tests.test_live_smoke import (
    _DEFAULT_SMOKE_BASE_URL,
    _is_production_host,
    resolve_live_base_url,
)


def test_smoke_url_default_is_not_production(monkeypatch):
    monkeypatch.delenv("WEEZDOM_BASE_URL", raising=False)
    monkeypatch.setenv("RUN_LIVE", "1")

    assert _DEFAULT_SMOKE_BASE_URL == "https://weezdomai-staging.up.railway.app"
    assert not _is_production_host(_DEFAULT_SMOKE_BASE_URL)

    url, reason = resolve_live_base_url()
    assert url is None
    assert reason
    assert "WEEZDOM_BASE_URL" in reason
    assert "weezdomai-production.up.railway.app" not in (url or "")
    assert "weezdomai-production.up.railway.app" not in reason


@pytest.mark.parametrize(
    "url",
    [
        "https://weezdomai-production.up.railway.app",
        "https://api.production.example.com",
        "weezdomai-production.up.railway.app",
    ],
)
def test_production_host_is_not_used(monkeypatch, url):
    monkeypatch.setenv("RUN_LIVE", "1")
    monkeypatch.setenv("WEEZDOM_BASE_URL", url)
    resolved, reason = resolve_live_base_url()
    assert resolved is None
    assert reason
    assert "production" in reason.lower()


def test_explicit_staging_url_is_used(monkeypatch):
    monkeypatch.setenv("RUN_LIVE", "1")
    monkeypatch.setenv("WEEZDOM_BASE_URL", _DEFAULT_SMOKE_BASE_URL)
    resolved, reason = resolve_live_base_url()
    assert reason is None
    assert resolved == _DEFAULT_SMOKE_BASE_URL
    assert not _is_production_host(resolved)
