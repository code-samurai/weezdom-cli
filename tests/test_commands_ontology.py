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


# ── v0.4 fixtures ───────────────────────────────────────────────────────────

SCORE_RESPONSE = {
    "ontology_id": "ont-1",
    "version_id": "ver-1",
    "version": 1,
    "quality": {
        "overall_score": 82,
        "grade": "B",
        "threshold": 70,
        "is_buildable": True,
        "axes": {},
        "weakest_entities": [],
        "weakest_relationships": [],
        "next_actions": [],
    },
    "gaps": [],
}


class TestOntologyScoreCommand:
    def test_score_json_output(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/ontologies/ont-1/score").mock(
                return_value=httpx.Response(200, json=SCORE_RESPONSE)
            )
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "json", "ontology", "score", "ont-1"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["quality"]["overall_score"] == 82

    def test_score_table_output_shows_score_and_grade(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/ontologies/ont-1/score").mock(
                return_value=httpx.Response(200, json=SCORE_RESPONSE)
            )
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "ontology", "score", "ont-1"])
        assert result.exit_code == 0, result.output
        assert "82" in result.output
        assert "B" in result.output

    def test_score_no_gaps_shows_no_gaps_message(self, mock_config):
        no_gap_response = {**SCORE_RESPONSE, "gaps": []}
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/ontologies/ont-1/score").mock(
                return_value=httpx.Response(200, json=no_gap_response)
            )
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "ontology", "score", "ont-1"])
        assert result.exit_code == 0
        assert "No gaps" in result.output

    def test_score_404_exits_1(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/ontologies/missing/score").mock(
                return_value=httpx.Response(404, json={"detail": "not found"})
            )
            runner = CliRunner()
            result = runner.invoke(main, ["ontology", "score", "missing"])
        assert result.exit_code == 1


IMPROVE_RESPONSE = {
    "ontology_id": "ont-1",
    "new_version_id": "ver-2",
    "new_version": 2,
    "quality": {"overall_score": 72, "grade": "B", "is_buildable": True},
}

UPDATES_DICT = {
    "entity_types": [
        {
            "name": "Revenue",
            "description": "Updated",
            "examples": [{"text": "Q2 deal", "why": "Revenue realized"}],
        }
    ]
}


class TestOntologyImproveCommand:
    def test_improve_with_updates_file_shows_new_version(self, mock_config, tmp_path):
        updates_file = tmp_path / "updates.json"
        updates_file.write_text(json.dumps(UPDATES_DICT))
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/ontologies/ont-1/improve").mock(
                return_value=httpx.Response(200, json=IMPROVE_RESPONSE)
            )
            runner = CliRunner()
            result = runner.invoke(
                main,
                ["--format", "table", "ontology", "improve", "ont-1",
                 "--updates-file", str(updates_file)],
            )
        assert result.exit_code == 0, result.output
        assert "version 2" in result.output
        assert "72" in result.output

    def test_improve_json_output(self, mock_config, tmp_path):
        updates_file = tmp_path / "updates.json"
        updates_file.write_text(json.dumps(UPDATES_DICT))
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/ontologies/ont-1/improve").mock(
                return_value=httpx.Response(200, json=IMPROVE_RESPONSE)
            )
            runner = CliRunner()
            result = runner.invoke(
                main,
                ["--format", "json", "ontology", "improve", "ont-1",
                 "--updates-file", str(updates_file)],
            )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["new_version_id"] == "ver-2"

    def test_improve_invalid_json_exits_1(self, mock_config, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json {")
        runner = CliRunner()
        result = runner.invoke(
            main, ["ontology", "improve", "ont-1", "--updates-file", str(bad_file)]
        )
        assert result.exit_code == 1
        assert "not valid JSON" in result.output

    def test_improve_stdin_reads_updates(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/ontologies/ont-1/improve").mock(
                return_value=httpx.Response(200, json=IMPROVE_RESPONSE)
            )
            runner = CliRunner()
            result = runner.invoke(
                main,
                ["ontology", "improve", "ont-1", "--updates-file", "-"],
                input=json.dumps(UPDATES_DICT),
            )
        assert result.exit_code == 0, result.output

    def test_improve_no_file_no_stdin_exits_1(self, mock_config):
        # CliRunner provides empty stdin (isatty=False) — json.loads("") raises JSONDecodeError
        runner = CliRunner()
        result = runner.invoke(main, ["ontology", "improve", "ont-1"])
        assert result.exit_code == 1


class TestOntologyDeleteCommand:
    def test_delete_with_force_skips_confirmation(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.delete("/ontologies/ont-del-1").mock(
                return_value=httpx.Response(200, json={"success": True})
            )
            runner = CliRunner()
            result = runner.invoke(
                main, ["ontology", "delete", "ont-del-1", "--force"]
            )
        assert result.exit_code == 0, result.output
        assert "Deleted" in result.output

    def test_delete_without_force_prompts_and_proceeds(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.delete("/ontologies/ont-del-2").mock(
                return_value=httpx.Response(200, json={"success": True})
            )
            runner = CliRunner()
            result = runner.invoke(
                main, ["ontology", "delete", "ont-del-2"], input="y\n"
            )
        assert result.exit_code == 0, result.output
        assert "Deleted" in result.output

    def test_delete_cancel_aborts(self, mock_config):
        runner = CliRunner()
        result = runner.invoke(
            main, ["ontology", "delete", "ont-3"], input="n\n"
        )
        assert result.exit_code == 0
        assert "Cancelled." in result.output

    def test_delete_409_exits_1(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.delete("/ontologies/ont-in-use").mock(
                return_value=httpx.Response(
                    409, json={"detail": "Cannot delete: ontology is in use"}
                )
            )
            runner = CliRunner()
            result = runner.invoke(
                main, ["ontology", "delete", "ont-in-use", "--force"]
            )
        assert result.exit_code == 1
        assert "Cannot delete" in result.output
