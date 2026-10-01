"""Outside-in ontology authoring over HTTP.

Mirrors Weezdom.ai ``cli.ontology_http`` (milestone 13). Import and save
write a draft ``ontology_versions`` document. Publish makes that draft the
live ontology version. Neither command materialises a graph or writes
FalkorDB or Weaviate.

Credentials: ``WEEZDOM_API_KEY`` and ``WEEZDOM_BASE_URL`` when set, otherwise
the key and ``api_url`` stored by ``weezdom auth login``.
"""

from __future__ import annotations

import json
import os

import httpx

from weezdom_cli import config


_TIMEOUT = 60.0
_CREATE_KEYS = (
    "domain",
    "entity_types",
    "exclusion_rules",
    "extraction_model",
    "naming_rules",
    "purpose",
    "relationship_types",
)

_AUTHORING_403 = (
    "This key cannot author an ontology. Use an unscoped personal key "
    "for an admin or editor. "
)


class AuthoringError(Exception):
    """User-facing authoring failure with a stable JSON payload."""

    def __init__(self, code: str, message: str, exit_code: int = 1, extra: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_code = exit_code
        self.extra = extra or {}

    def payload(self) -> dict:
        return {"error": self.code, "message": self.message, **self.extra}


def resolve_credentials() -> tuple[str, str]:
    """Return ``(api_url, api_key)``.

    Environment wins when set so agents can override a stored login.
    An empty env value falls through to ``~/.weezdom/config.yaml``.
    """
    env_key = (os.environ.get("WEEZDOM_API_KEY") or "").strip()
    env_url = (os.environ.get("WEEZDOM_BASE_URL") or "").strip()
    cfg = config.load()
    stored_key = cfg.get("api_key") or ""
    if not isinstance(stored_key, str):
        stored_key = ""
    api_key = env_key or stored_key.strip()
    api_url = (env_url or cfg.get("api_url") or "").rstrip("/")
    return api_url, api_key


def load_document(path: str) -> dict:
    """Read an ontology JSON document. A ``config`` wrapper is unwrapped later."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthoringError(
            "validation", f"Could not read ontology JSON: {exc}", exit_code=2
        ) from exc
    if not isinstance(data, dict):
        raise AuthoringError(
            "validation", "Ontology file must contain a JSON object", exit_code=2
        )
    return data


def _source(document: dict) -> dict:
    wrapped = document.get("config")
    if isinstance(wrapped, dict):
        return wrapped
    return document


def document_body(document: dict) -> dict:
    """Structural document only. Publish and graph fields are not sent."""
    source = _source(document)
    body = {}
    for key in _CREATE_KEYS:
        if key in source:
            body[key] = source[key]
    if not body.get("entity_types"):
        raise AuthoringError(
            "validation", "Import needs at least one entity type.", exit_code=2
        )
    return body


def create_body(document: dict, name: str) -> dict:
    source = _source(document)
    resolved = (name or source.get("name") or document.get("name") or "").strip()
    if not resolved:
        raise AuthoringError(
            "validation",
            "Creating an ontology needs --name or a name in the JSON file.",
            exit_code=2,
        )
    body = {"name": resolved}
    for key in _CREATE_KEYS:
        if key in source:
            body[key] = source[key]
    if not body.get("entity_types"):
        raise AuthoringError(
            "validation", "Import needs at least one entity type.", exit_code=2
        )
    return body


def request(method: str, path: str, body: dict) -> dict:
    """POST an authoring call. No ``X-Graph-Id`` — authoring is not graph-scoped."""
    api_url, api_key = resolve_credentials()
    if not api_key:
        raise AuthoringError(
            "config",
            "WEEZDOM_API_KEY is required. Run: weezdom auth login",
        )
    if not api_url:
        raise AuthoringError(
            "config",
            "WEEZDOM_BASE_URL is required (or set api_url with weezdom config set)",
        )
    url = api_url + path
    headers = {
        "X-API-Key": api_key,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    content = json.dumps(body).encode("utf-8")
    try:
        status, raw = _open(method, url, headers, content)
    except httpx.RequestError as exc:
        raise AuthoringError("unavailable", "Could not reach the Weezdom API.") from exc
    return _decode(status, raw)


def _open(method: str, url: str, headers: dict, content: bytes) -> tuple[int, bytes]:
    with httpx.Client(timeout=_TIMEOUT, follow_redirects=False) as client:
        response = client.request(method, url, headers=headers, content=content)
        return response.status_code, response.content


def _decode(status: int, raw: bytes) -> dict:
    text = raw.decode("utf-8", errors="replace") if raw else ""
    if 200 <= status < 300:
        try:
            data = json.loads(text) if text else {}
        except json.JSONDecodeError as exc:
            raise AuthoringError(
                "invalid_response", "Weezdom API returned a non-JSON body."
            ) from exc
        if not isinstance(data, dict):
            raise AuthoringError(
                "invalid_response",
                "Weezdom API returned a JSON value that is not an object.",
            )
        return data
    message = _http_message(text)
    if status == 403:
        message = _AUTHORING_403 + message
    raise AuthoringError("http_error", message, extra={"status": status})


def _http_message(text: str) -> str:
    try:
        data = json.loads(text) if text else None
    except json.JSONDecodeError:
        data = None
    if isinstance(data, dict) and "detail" in data:
        detail = data["detail"]
        if isinstance(detail, str):
            return detail
        return json.dumps(detail)
    if text:
        return text[:500]
    return "Weezdom API request failed."


def import_document(path: str, name: str = "", ontology_id: str = "") -> dict:
    """Create a draft ontology, or import a draft onto an existing one.

    Omit ``ontology_id`` to ``POST /ontologies``. Pass it to
    ``POST /ontologies/{ontology_id}/import``. Neither call publishes.
    """
    document = load_document(path)
    ontology_id = (ontology_id or "").strip()
    if ontology_id:
        return request("POST", f"/ontologies/{ontology_id}/import", document_body(document))
    return request("POST", "/ontologies", create_body(document, name))


def save_document(path: str, ontology_id: str) -> dict:
    """Save the JSON document as a new draft version. Does not publish.

    Same HTTP call as import onto an existing ontology:
    ``POST /ontologies/{ontology_id}/import``.
    """
    document = load_document(path)
    ontology_id = (ontology_id or "").strip()
    if not ontology_id:
        raise AuthoringError("validation", "save requires --ontology-id", exit_code=2)
    return request("POST", f"/ontologies/{ontology_id}/import", document_body(document))


def publish_document(ontology_id: str, version_id: str = "") -> dict:
    """Publish the draft ontology version. Does not materialise a graph.

    ``POST /ontologies/{ontology_id}/publish``. ``graph_id`` is not sent.
    """
    ontology_id = (ontology_id or "").strip()
    if not ontology_id:
        raise AuthoringError("validation", "publish requires --ontology-id", exit_code=2)
    body: dict = {}
    version_id = (version_id or "").strip()
    if version_id:
        body["version_id"] = version_id
    return request("POST", f"/ontologies/{ontology_id}/publish", body)
