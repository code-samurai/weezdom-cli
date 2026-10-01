"""Outside-in ontology authoring — import, save, publish. HTTP is mocked."""

import json

import httpx
import respx
import yaml
from click.testing import CliRunner

from weezdom_cli.cli import main
from tests.conftest import API_URL

ONTOLOGY_ID = "ont-author-1"
VERSION_ID = "ver-author-1"

DOCUMENT = {
    "name": "Practice operations",
    "entity_types": [{"name": "Practice", "description": "A clinic site"}],
    "relationship_types": [{"name": "EMPLOYS"}],
    "domain": "healthcare",
    "published": True,
    "graph_id": "must-not-be-sent",
}

WRAPPED = {
    "name": "Outer label",
    "published": True,
    "config": {
        "name": "Inner document",
        "entity_types": [{"name": "Practice"}],
        "purpose": "operations",
    },
}

CREATED = {
    "ontology_id": ONTOLOGY_ID,
    "version_id": VERSION_ID,
    "quality": {"overall_score": 40},
    "gaps": [],
}

IMPORTED = {
    "ontology_id": ONTOLOGY_ID,
    "version_id": "ver-author-2",
    "version": 2,
    "quality": {"overall_score": 40},
    "gaps": [],
    "published": False,
}

PUBLISHED = {
    "ontology_id": ONTOLOGY_ID,
    "version_id": VERSION_ID,
    "status": "published",
    "published": True,
}


def _write(tmp_path, payload):
    path = tmp_path / "ontology.json"
    path.write_text(json.dumps(payload))
    return str(path)


def _json_output(result):
    start = result.output.find("{")
    assert start >= 0, result.output
    return json.loads(result.output[start:])


class TestOntologyImport:
    def test_create_via_import(self, mock_config, tmp_path):
        path = _write(tmp_path, DOCUMENT)
        with respx.mock(base_url=API_URL) as rsps:
            route = rsps.post("/ontologies").mock(
                return_value=httpx.Response(201, json=CREATED)
            )
            runner = CliRunner()
            result = runner.invoke(
                main,
                ["--format", "json", "ontology", "import", "--file", path],
            )
        assert result.exit_code == 0, result.output
        assert route.called
        req = route.calls[0].request
        assert req.headers["X-API-Key"] == "wdm_testkey12345678"
        assert "X-Graph-Id" not in req.headers
        body = json.loads(req.content.decode())
        assert body["name"] == "Practice operations"
        assert body["entity_types"][0]["name"] == "Practice"
        assert body["relationship_types"][0]["name"] == "EMPLOYS"
        assert body["domain"] == "healthcare"
        assert "published" not in body
        assert "graph_id" not in body
        assert "config" not in body
        data = _json_output(result)
        assert data["ontology_id"] == ONTOLOGY_ID
        assert data["version_id"] == VERSION_ID

    def test_create_uses_name_flag_over_file(self, mock_config, tmp_path):
        path = _write(tmp_path, DOCUMENT)
        with respx.mock(base_url=API_URL) as rsps:
            route = rsps.post("/ontologies").mock(
                return_value=httpx.Response(201, json=CREATED)
            )
            runner = CliRunner()
            result = runner.invoke(
                main,
                ["--format", "json", "ontology", "import", "--file", path, "--name", "Override"],
            )
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content.decode())
        assert body["name"] == "Override"

    def test_import_onto_existing_unwraps_config(self, mock_config, tmp_path):
        path = _write(tmp_path, WRAPPED)
        with respx.mock(base_url=API_URL) as rsps:
            route = rsps.post(f"/ontologies/{ONTOLOGY_ID}/import").mock(
                return_value=httpx.Response(200, json=IMPORTED)
            )
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "--format", "json", "ontology", "import",
                    "--file", path,
                    "--ontology-id", ONTOLOGY_ID,
                    "--name", "Ignored when targeting an existing ontology",
                ],
            )
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content.decode())
        assert body["entity_types"][0]["name"] == "Practice"
        assert body["purpose"] == "operations"
        assert "name" not in body
        assert "published" not in body
        assert "config" not in body
        assert _json_output(result)["published"] is False

    def test_import_without_entity_types_exits_2(self, mock_config, tmp_path):
        path = _write(tmp_path, {"name": "Empty"})
        runner = CliRunner()
        result = runner.invoke(
            main, ["--format", "json", "ontology", "import", "--file", path]
        )
        assert result.exit_code == 2
        payload = _json_output(result)
        assert payload["error"] == "validation"
        assert "entity type" in payload["message"]

    def test_create_without_name_exits_2(self, mock_config, tmp_path):
        path = _write(tmp_path, {"entity_types": [{"name": "Practice"}]})
        runner = CliRunner()
        result = runner.invoke(
            main, ["--format", "json", "ontology", "import", "--file", path]
        )
        assert result.exit_code == 2
        assert "name" in _json_output(result)["message"]


class TestOntologySave:
    def test_save_draft_posts_import(self, mock_config, tmp_path):
        path = _write(tmp_path, DOCUMENT)
        with respx.mock(base_url=API_URL) as rsps:
            route = rsps.post(f"/ontologies/{ONTOLOGY_ID}/import").mock(
                return_value=httpx.Response(200, json=IMPORTED)
            )
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "--format", "json", "ontology", "save",
                    "--ontology-id", ONTOLOGY_ID,
                    "--file", path,
                ],
            )
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content.decode())
        assert body["entity_types"][0]["name"] == "Practice"
        assert "name" not in body
        assert "published" not in body
        assert "graph_id" not in body
        assert req_has_no_graph_header(route)
        data = _json_output(result)
        assert data["published"] is False
        assert data["version_id"] == "ver-author-2"


class TestOntologyPublish:
    def test_publish_without_version_sends_empty_object(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            route = rsps.post(f"/ontologies/{ONTOLOGY_ID}/publish").mock(
                return_value=httpx.Response(200, json=PUBLISHED)
            )
            runner = CliRunner()
            result = runner.invoke(
                main,
                ["--format", "json", "ontology", "publish", "--ontology-id", ONTOLOGY_ID],
            )
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content.decode())
        assert body == {}
        assert "graph_id" not in body
        data = _json_output(result)
        assert data["status"] == "published"
        assert data["published"] is True

    def test_publish_sends_version_id_only(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            route = rsps.post(f"/ontologies/{ONTOLOGY_ID}/publish").mock(
                return_value=httpx.Response(200, json=PUBLISHED)
            )
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "--format", "json", "ontology", "publish",
                    "--ontology-id", ONTOLOGY_ID,
                    "--version-id", VERSION_ID,
                ],
            )
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content.decode())
        assert body == {"version_id": VERSION_ID}


class TestOntologyAuthorAuth:
    def test_missing_key(self, tmp_path, monkeypatch):
        config_dir = tmp_path / ".weezdom"
        config_dir.mkdir()
        monkeypatch.setattr("weezdom_cli.config.CONFIG_DIR", config_dir)
        monkeypatch.setattr("weezdom_cli.config.CONFIG_FILE", config_dir / "config.yaml")
        with open(config_dir / "config.yaml", "w") as handle:
            yaml.safe_dump({"api_url": API_URL, "output_format": "json"}, handle)
        monkeypatch.delenv("WEEZDOM_API_KEY", raising=False)

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--format", "json", "ontology", "publish", "--ontology-id", ONTOLOGY_ID],
        )
        assert result.exit_code == 1
        payload = _json_output(result)
        assert payload["error"] == "config"
        assert "WEEZDOM_API_KEY" in payload["message"]
        assert "auth login" in payload["message"]

    def test_env_key_overrides_stored_key(self, mock_config, tmp_path, monkeypatch):
        monkeypatch.setenv("WEEZDOM_API_KEY", "wdm_env_author_key")
        monkeypatch.setenv("WEEZDOM_BASE_URL", API_URL)
        path = _write(tmp_path, DOCUMENT)
        with respx.mock(base_url=API_URL) as rsps:
            route = rsps.post(f"/ontologies/{ONTOLOGY_ID}/import").mock(
                return_value=httpx.Response(200, json=IMPORTED)
            )
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "--format", "json", "ontology", "save",
                    "--ontology-id", ONTOLOGY_ID,
                    "--file", path,
                ],
            )
        assert result.exit_code == 0, result.output
        assert route.calls[0].request.headers["X-API-Key"] == "wdm_env_author_key"

    def test_403_authoring_refusal(self, mock_config, tmp_path):
        path = _write(tmp_path, DOCUMENT)
        detail = "Requires role: admin, editor. You have: viewer"
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/ontologies").mock(
                return_value=httpx.Response(403, json={"detail": detail})
            )
            runner = CliRunner()
            result = runner.invoke(
                main,
                ["--format", "json", "ontology", "import", "--file", path, "--name", "Practice operations"],
            )
        assert result.exit_code == 1
        payload = _json_output(result)
        assert payload["error"] == "http_error"
        assert payload["status"] == 403
        assert payload["message"].startswith(
            "This key cannot author an ontology. Use an unscoped personal key for an admin or editor. "
        )
        assert detail in payload["message"]


def req_has_no_graph_header(route) -> bool:
    return "X-Graph-Id" not in route.calls[0].request.headers
