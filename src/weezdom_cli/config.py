"""Configuration management — ~/.weezdom/config.yaml."""

import os
from pathlib import Path
from typing import Optional

import click
import yaml


CONFIG_DIR = Path.home() / ".weezdom"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

DEFAULTS = {
    "api_url": "https://weezdomai-production.up.railway.app",
    "api_key": None,
    "active_graph_id": None,
    "output_format": "table",
}


def _ensure_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load() -> dict:
    """Load config from disk, merging with defaults."""
    config = dict(DEFAULTS)
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            try:
                on_disk = yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                raise click.ClickException(
                    f"Config file is malformed: {e}. "
                    f"Delete {CONFIG_FILE} and run `weezdom auth login`."
                )
        config.update(on_disk)
    return config


def save(config: dict):
    """Save config to disk with user-only permissions."""
    _ensure_dir()
    with open(CONFIG_FILE, "w") as f:
        yaml.safe_dump(config, f, default_flow_style=False)
    os.chmod(CONFIG_FILE, 0o600)


def get(key: str, default=None):
    """Get a single config value."""
    return load().get(key, default)


def set_value(key: str, value):
    """Set a single config value."""
    config = load()
    config[key] = value
    save(config)


def clear_key(key: str):
    """Remove a config key (resets to default)."""
    config = load()
    config.pop(key, None)
    save(config)
