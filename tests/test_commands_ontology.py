"""Tests for ontology commands — ontology list."""

import json
import pytest
import respx
import httpx
from click.testing import CliRunner

from weezdom_cli.cli import main

API_URL = "https://test.weezdom.ai"


# Response is a raw JSON array (SC-1: NOT {"ontologies": [...]})
ONTOLOGY_LIST_RESPONSE = [
    {
        "id": "ont-uuid-1",
        "name": "Marketing Ontology",
        "version_count": 3,
        "graph_count": 2,
        "published_graph_count": 1,
        "status": {"overall_score": 85, "status": "published"},
    },
    {
        "id": "ont-uuid-2",
        "name": "Sales Ontology",
        "version_count": 1,
        "graph_count": 0,
        "published_graph_count": 0,
        "status": {"overall_score": None, "status": "draft"},
    },
]


class TestOntologyListCommand:
    def test_ontology_list_json_output(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/ontologies/list").mock(
                return_value=httpx.Response(200, json=ONTOLOGY_LIST_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "json", "ontology", "list"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert isinstance(data, list)
            assert data[0]["name"] == "Marketing Ontology"

    def test_ontology_list_table_output(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/ontologies/list").mock(
                return_value=httpx.Response(200, json=ONTOLOGY_LIST_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "ontology", "list"])  # SC-3
            assert result.exit_code == 0
            assert "Marketing Ontology" in result.output
            assert "Sales Ontology" in result.output

    def test_ontology_list_shows_score(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/ontologies/list").mock(
                return_value=httpx.Response(200, json=ONTOLOGY_LIST_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "ontology", "list"])  # SC-3
            assert result.exit_code == 0
            assert "85" in result.output

    def test_ontology_list_empty(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/ontologies/list").mock(
                return_value=httpx.Response(200, json=[]))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "ontology", "list"])  # SC-3
            assert result.exit_code == 0
            assert "No ontologies" in result.output
