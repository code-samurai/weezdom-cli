"""Tests for ontology commands — ontology list."""

import json
import pytest
import respx
import httpx
from click.testing import CliRunner
from unittest.mock import patch

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


# ---------------------------------------------------------------------------
# Shared fixtures for async build tests
# ---------------------------------------------------------------------------

ENQUEUE_RESPONSE = {"job_id": "job-uuid-build", "status": "queued"}

COMPLETED_STATUS = {
    "job_id": "job-uuid-build",
    "status": "completed",
    "result": {
        "ontology_id": "ont-build-1",
        "version_id": "ver-build-1",
        "quality": {"overall_score": 78},
        "gaps": [],
        "iterations_used": 2,
        "reached_threshold": True,
    },
    "error": None,
}

FAILED_STATUS = {
    "job_id": "job-uuid-build",
    "status": "failed",
    "result": None,
    "error": "name_conflict",
}

QUEUED_STATUS = {
    "job_id": "job-uuid-build",
    "status": "queued",
    "result": None,
    "error": None,
}


class TestOntologyBuildCommand:
    def test_build_polls_until_complete_and_prints_result(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/ontologies/build").mock(
                return_value=httpx.Response(202, json=ENQUEUE_RESPONSE))
            rsps.get("/ontologies/build-status/job-uuid-build").mock(
                side_effect=[
                    httpx.Response(200, json=QUEUED_STATUS),
                    httpx.Response(200, json=COMPLETED_STATUS),
                ]
            )
            with patch("time.sleep"):
                runner = CliRunner()
                result = runner.invoke(
                    main, ["--format", "table", "ontology", "build",
                           "Revenue Brain", "Track SaaS pricing",
                           "--goal", "find patterns", "--iterations", "2"]
                )
        assert result.exit_code == 0, result.output
        assert "ont-build-1" in result.output
        assert "78/100" in result.output
        assert "threshold=yes" in result.output

    def test_build_exits_1_on_failed_status(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/ontologies/build").mock(
                return_value=httpx.Response(202, json=ENQUEUE_RESPONSE))
            rsps.get("/ontologies/build-status/job-uuid-build").mock(
                return_value=httpx.Response(200, json=FAILED_STATUS))
            with patch("time.sleep"):
                runner = CliRunner()
                result = runner.invoke(main, ["ontology", "build", "X", "Y"])
        assert result.exit_code == 1

    def test_build_exits_1_when_no_job_id_returned(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/ontologies/build").mock(
                return_value=httpx.Response(202, json={"status": "queued"}))  # missing job_id
            runner = CliRunner()
            result = runner.invoke(main, ["ontology", "build", "X", "Y"])
        assert result.exit_code == 1

    def test_build_json_output(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/ontologies/build").mock(
                return_value=httpx.Response(202, json=ENQUEUE_RESPONSE))
            rsps.get("/ontologies/build-status/job-uuid-build").mock(
                return_value=httpx.Response(200, json=COMPLETED_STATUS))
            with patch("time.sleep"):
                runner = CliRunner()
                result = runner.invoke(
                    main, ["--format", "json", "ontology", "build", "X", "Y"]
                )
        assert result.exit_code == 0, result.output
        # CliRunner mixes stderr (status line) into result.output; find the JSON object
        json_start = result.output.index("{")
        data = json.loads(result.output[json_start:])
        assert data["status"] == "completed"
        assert data["result"]["ontology_id"] == "ont-build-1"


class TestOntologyBuildStatusCommand:
    def test_build_status_completed(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/ontologies/build-status/job-uuid-build").mock(
                return_value=httpx.Response(200, json=COMPLETED_STATUS))
            runner = CliRunner()
            result = runner.invoke(main, ["ontology", "build-status", "job-uuid-build"])
        assert result.exit_code == 0, result.output
        assert "completed" in result.output
        assert "ont-build-1" in result.output

    def test_build_status_json(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/ontologies/build-status/job-uuid-build").mock(
                return_value=httpx.Response(200, json=COMPLETED_STATUS))
            runner = CliRunner()
            result = runner.invoke(
                main, ["--format", "json", "ontology", "build-status", "job-uuid-build"]
            )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["result"]["ontology_id"] == "ont-build-1"

    def test_build_status_queued(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/ontologies/build-status/job-uuid-build").mock(
                return_value=httpx.Response(200, json=QUEUED_STATUS))
            runner = CliRunner()
            result = runner.invoke(main, ["ontology", "build-status", "job-uuid-build"])
        assert result.exit_code == 0, result.output
        assert "queued" in result.output
