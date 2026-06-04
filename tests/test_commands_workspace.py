"""Tests for workspace commands — workspace search and workspace info."""

import json
import pytest
import respx
import httpx
from click.testing import CliRunner

from weezdom_cli.cli import main

API_URL = "https://test.weezdom.ai"


WORKSPACE_SEARCH_RESPONSE = {
    "query": "progressive profiling",
    "workspace_id": "ws-uuid-1",
    "num_results": 1,
    "results": [
        {
            "fact": "Progressive profiling reduces form fatigue",
            "source_graph_id": "g-uuid-1",
            "source_graph_name": "Marketing KG",
            "graph_role": "subject",
            "source": "Marketing Guide",
            "score": 0.95,
        }
    ],
}

WORKSPACE_INFO_RESPONSE = {
    "workspaces": [
        {"id": "ws-uuid-1", "name": "Marketing Workspace", "graph_count": 2, "entity_count": 500},
        {"id": "ws-uuid-2", "name": "Sales Workspace", "graph_count": 1, "entity_count": 200},
    ],
    "current_workspace_id": "ws-uuid-1",
}


class TestWorkspaceSearchCommand:
    def test_workspace_search_json_output(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/search/workspace").mock(
                return_value=httpx.Response(200, json=WORKSPACE_SEARCH_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "json", "workspace", "search",
                                          "progressive profiling", "-w", "ws-uuid-1"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["num_results"] == 1

    def test_workspace_search_table_output(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/search/workspace").mock(
                return_value=httpx.Response(200, json=WORKSPACE_SEARCH_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "workspace", "search",  # SC-3
                                          "progressive profiling", "-w", "ws-uuid-1"])
            assert result.exit_code == 0
            assert "Marketing KG" in result.output

    def test_workspace_search_no_results_tip(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/search/workspace").mock(return_value=httpx.Response(200, json={
                "query": "nothing", "workspace_id": None, "num_results": 0, "results": []
            }))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "workspace", "search", "nothing"])  # SC-3
            assert result.exit_code == 0
            assert "workspace info" in result.output.lower() or "no results" in result.output.lower()

    def test_workspace_search_sends_correct_body(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            route = rsps.post("/search/workspace").mock(
                return_value=httpx.Response(200, json=WORKSPACE_SEARCH_RESPONSE))
            runner = CliRunner()
            runner.invoke(main, ["workspace", "search", "my query",
                                  "-w", "ws-uuid-1", "--limit", "5"])
            body = json.loads(route.calls[0].request.content)
            assert body["query"] == "my query"
            assert body["workspace_id"] == "ws-uuid-1"
            assert body["limit"] == 5


class TestWorkspaceInfoCommand:
    def test_workspace_info_json_output(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/insights/workspaces").mock(
                return_value=httpx.Response(200, json=WORKSPACE_INFO_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "json", "workspace", "info"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["workspaces"][0]["name"] == "Marketing Workspace"

    def test_workspace_info_table_output(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/insights/workspaces").mock(
                return_value=httpx.Response(200, json=WORKSPACE_INFO_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "workspace", "info"])  # SC-3
            assert result.exit_code == 0
            assert "Marketing Workspace" in result.output
            assert "Sales Workspace" in result.output
