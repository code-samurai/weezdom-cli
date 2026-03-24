"""Shared fixtures for weezdom-cli tests."""

import pytest
import respx
import httpx


API_URL = "https://test.weezdom.ai"


@pytest.fixture
def mock_api():
    """respx mock router for Weezdom API calls."""
    with respx.mock(base_url=API_URL) as rsps:
        yield rsps


@pytest.fixture
def mock_config(tmp_path, monkeypatch):
    """Redirect config to temp dir so tests don't touch ~/.weezdom."""
    config_dir = tmp_path / ".weezdom"
    config_dir.mkdir()
    monkeypatch.setattr("weezdom_cli.config.CONFIG_DIR", config_dir)
    monkeypatch.setattr("weezdom_cli.config.CONFIG_FILE", config_dir / "config.yaml")

    # Pre-populate with test values
    import yaml
    config = {
        "api_url": API_URL,
        "api_key": "wdm_testkey12345678",
        "active_graph_id": "graph-uuid-1",
        "output_format": "json",
    }
    with open(config_dir / "config.yaml", "w") as f:
        yaml.safe_dump(config, f)

    return config
