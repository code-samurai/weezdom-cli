"""Tests for graph management CLI commands."""

import json
import pytest
import respx
import httpx

from click.testing import CliRunner
from weezdom_cli.cli import main

API_URL = "https://test.weezdom.ai"

GRAPH_LIST_RESPONSE = {
    "graphs": [
        {"id": "g-1111-2222-3333", "name": "Marketing KG", "status": "ready",
         "entity_count": 644, "content_count": 112},
        {"id": "g-4444-5555-6666", "name": "Sales KG", "status": "empty",
         "entity_count": 0, "content_count": 0},
    ],
}

GRAPH_DETAIL_RESPONSE = {
    "id": "g-1111-2222-3333",
    "name": "Marketing KG",
    "status": "ready",
    "entity_count": 644,
    "content_count": 112,
    "ontology_name": "Marketing Ontology",
    "extraction_model": "claude-3-5-haiku-20241022",
}

GRAPH_PIPELINE_RESPONSE = {
    "jobs": [
        {"id": "j-aaaa-bbbb-cccc", "content_title": "Guide", "status": "completed", "progress": "100%"},
        {"id": "j-dddd-eeee-ffff", "content_title": "Deck", "status": "extracting", "progress": "40%"},
    ],
    "total": 2,
}


class TestGraphList:

    def test_graph_list_json(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/knowledge-graphs/data/list").mock(
                return_value=httpx.Response(200, json=GRAPH_LIST_RESPONSE)
            )
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "json", "graph", "list"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert len(data) == 2
            assert data[0]["name"] == "Marketing KG"

    def test_graph_list_table(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/knowledge-graphs/data/list").mock(
                return_value=httpx.Response(200, json=GRAPH_LIST_RESPONSE)
            )
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "graph", "list"])
            assert result.exit_code == 0
            assert "Marketing KG" in result.output
            assert "Sales KG" in result.output

    def test_graph_list_truncates_long_ids(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/knowledge-graphs/data/list").mock(
                return_value=httpx.Response(200, json=GRAPH_LIST_RESPONSE)
            )
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "graph", "list"])
            assert result.exit_code == 0
            assert "g-1111-2222-..." in result.output

    def test_graph_list_empty(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/knowledge-graphs/data/list").mock(
                return_value=httpx.Response(200, json={"graphs": []})
            )
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "json", "graph", "list"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data == []


class TestGraphUse:

    def test_graph_use_sets_config(self, mock_config, tmp_path):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/knowledge-graphs/data/g-new").mock(
                return_value=httpx.Response(200, json={
                    "id": "g-new", "name": "New Graph",
                })
            )
            runner = CliRunner()
            result = runner.invoke(main, ["graph", "use", "g-new"])
            assert result.exit_code == 0
            assert "Active graph: New Graph (g-new)" in result.output

            # Verify config was updated
            import yaml
            config_file = tmp_path / ".weezdom" / "config.yaml"
            cfg = yaml.safe_load(config_file.read_text())
            assert cfg["active_graph_id"] == "g-new"

    def test_graph_use_validates_existence(self, mock_config):
        """Using a non-existent graph should fail (404 from API)."""
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/knowledge-graphs/data/bad-id").mock(
                return_value=httpx.Response(404, json={"detail": "Not found"})
            )
            runner = CliRunner()
            result = runner.invoke(main, ["graph", "use", "bad-id"])
            assert result.exit_code != 0


class TestGraphInfo:

    def test_graph_info_with_argument(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/knowledge-graphs/data/g-1111-2222-3333").mock(
                return_value=httpx.Response(200, json=GRAPH_DETAIL_RESPONSE)
            )
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "json", "graph", "info", "g-1111-2222-3333"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["name"] == "Marketing KG"
            assert data["entity_count"] == 644

    def test_graph_info_uses_active_graph(self, mock_config):
        """Without argument, uses active_graph_id from config."""
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/knowledge-graphs/data/graph-uuid-1").mock(
                return_value=httpx.Response(200, json=GRAPH_DETAIL_RESPONSE)
            )
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "json", "graph", "info"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["name"] == "Marketing KG"

    def test_graph_info_no_graph_errors(self, mock_config, tmp_path):
        """Without argument and no active graph, should error."""
        import yaml
        config_file = tmp_path / ".weezdom" / "config.yaml"
        cfg = yaml.safe_load(config_file.read_text())
        cfg.pop("active_graph_id", None)
        config_file.write_text(yaml.safe_dump(cfg))

        runner = CliRunner()
        result = runner.invoke(main, ["graph", "info"])
        assert result.exit_code != 0

    def test_graph_info_table_format(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/knowledge-graphs/data/graph-uuid-1").mock(
                return_value=httpx.Response(200, json=GRAPH_DETAIL_RESPONSE)
            )
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "graph", "info"])
            assert result.exit_code == 0
            assert "Marketing KG" in result.output
            assert "644" in result.output


class TestGraphPipeline:

    def test_graph_pipeline_json(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/knowledge-graphs/data/graph-uuid-1/pipeline").mock(
                return_value=httpx.Response(200, json=GRAPH_PIPELINE_RESPONSE)
            )
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "json", "graph", "pipeline"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert len(data) == 2
            assert data[0]["content_title"] == "Guide"

    def test_graph_pipeline_with_argument(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/knowledge-graphs/data/g-custom/pipeline").mock(
                return_value=httpx.Response(200, json=GRAPH_PIPELINE_RESPONSE)
            )
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "json", "graph", "pipeline", "g-custom"])
            assert result.exit_code == 0

    def test_graph_pipeline_table(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/knowledge-graphs/data/graph-uuid-1/pipeline").mock(
                return_value=httpx.Response(200, json=GRAPH_PIPELINE_RESPONSE)
            )
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "graph", "pipeline"])
            assert result.exit_code == 0
            assert "Guide" in result.output
            assert "completed" in result.output
            assert "extracting" in result.output

    def test_graph_pipeline_truncates_ids(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/knowledge-graphs/data/graph-uuid-1/pipeline").mock(
                return_value=httpx.Response(200, json=GRAPH_PIPELINE_RESPONSE)
            )
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "graph", "pipeline"])
            assert result.exit_code == 0
            assert "j-aaaa-bbbb-..." in result.output

    def test_graph_pipeline_no_graph_errors(self, mock_config, tmp_path):
        import yaml
        config_file = tmp_path / ".weezdom" / "config.yaml"
        cfg = yaml.safe_load(config_file.read_text())
        cfg.pop("active_graph_id", None)
        config_file.write_text(yaml.safe_dump(cfg))

        runner = CliRunner()
        result = runner.invoke(main, ["graph", "pipeline"])
        assert result.exit_code != 0
