"""Tests for content management CLI commands."""

import json
import pytest
import respx
import httpx

from click.testing import CliRunner
from weezdom_cli.cli import main

API_URL = "https://test.weezdom.ai"

CONTENT_LIST_RESPONSE = {
    "items": [
        {"id": "c-1111-2222-3333", "title": "Marketing Guide", "type": "url", "status": "completed"},
        {"id": "c-4444-5555-6666", "title": "Sales Deck", "type": "file", "status": "parsing"},
    ],
    "total": 2,
}

CONTENT_ADD_RESPONSE = {
    "job_ids": ["job-aaa", "job-bbb"],
    "message": "2 URLs queued",
}

CONTENT_VIEW_RESPONSE = {
    "content": "This is the full text content of the document.",
}

CONTENT_DELETE_RESPONSE = {"deleted": True}

CONTENT_EXTRACT_RESPONSE = {
    "job_ids": ["j-1", "j-2"],
    "message": "2 items queued for extraction",
}

CONTENT_UPLOAD_RESPONSE = {
    "job_ids": ["job-upload-1"],
    "message": "1 file uploaded",
}


class TestContentList:

    def test_content_list_json(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/content/library").mock(
                return_value=httpx.Response(200, json=CONTENT_LIST_RESPONSE)
            )
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "json", "content", "list"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert len(data) == 2
            assert data[0]["title"] == "Marketing Guide"

    def test_content_list_table(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/content/library").mock(
                return_value=httpx.Response(200, json=CONTENT_LIST_RESPONSE)
            )
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "content", "list"])
            assert result.exit_code == 0
            assert "Marketing Guide" in result.output
            assert "Sales Deck" in result.output

    def test_content_list_with_filters(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            route = rsps.get("/content/library").mock(
                return_value=httpx.Response(200, json=CONTENT_LIST_RESPONSE)
            )
            runner = CliRunner()
            result = runner.invoke(main, [
                "--format", "json", "content", "list",
                "--type", "url", "--status", "completed", "--tag", "marketing", "--limit", "5",
            ])
            assert result.exit_code == 0
            req = rsps.calls[0].request
            assert "type=url" in str(req.url)
            assert "status=completed" in str(req.url)
            assert "tag=marketing" in str(req.url)
            assert "limit=5" in str(req.url)

    def test_content_list_default_limit(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/content/library").mock(
                return_value=httpx.Response(200, json={"items": [], "total": 0})
            )
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "json", "content", "list"])
            assert result.exit_code == 0
            req = rsps.calls[0].request
            assert "limit=20" in str(req.url)

    def test_content_list_truncates_long_ids_table(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/content/library").mock(
                return_value=httpx.Response(200, json=CONTENT_LIST_RESPONSE)
            )
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "content", "list"])
            assert result.exit_code == 0
            # IDs longer than 12 chars should be truncated
            assert "c-1111-2222-..." in result.output


class TestContentAdd:

    def test_content_add_single_url(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/content/url").mock(
                return_value=httpx.Response(200, json=CONTENT_ADD_RESPONSE)
            )
            runner = CliRunner()
            result = runner.invoke(main, ["content", "add", "https://example.com"])
            assert result.exit_code == 0
            assert "Queued" in result.output
            body = json.loads(rsps.calls[0].request.content)
            assert body["urls"] == ["https://example.com"]

    def test_content_add_multiple_urls(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/content/url").mock(
                return_value=httpx.Response(200, json=CONTENT_ADD_RESPONSE)
            )
            runner = CliRunner()
            result = runner.invoke(main, [
                "content", "add", "https://a.com", "https://b.com",
            ])
            assert result.exit_code == 0
            body = json.loads(rsps.calls[0].request.content)
            assert body["urls"] == ["https://a.com", "https://b.com"]
            assert "job-aaa" in result.output
            assert "job-bbb" in result.output

    def test_content_add_with_tag(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/content/url").mock(
                return_value=httpx.Response(200, json=CONTENT_ADD_RESPONSE)
            )
            runner = CliRunner()
            result = runner.invoke(main, [
                "content", "add", "--tag", "marketing", "https://example.com",
            ])
            assert result.exit_code == 0
            body = json.loads(rsps.calls[0].request.content)
            assert body["tag"] == "marketing"


class TestContentUpload:

    def test_content_upload(self, mock_config, tmp_path):
        test_file = tmp_path / "doc.txt"
        test_file.write_text("Hello world")

        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/content/upload").mock(
                return_value=httpx.Response(200, json=CONTENT_UPLOAD_RESPONSE)
            )
            runner = CliRunner()
            result = runner.invoke(main, ["content", "upload", str(test_file)])
            assert result.exit_code == 0
            assert "Uploaded: doc.txt" in result.output
            assert "job-upload-1" in result.output

    def test_content_upload_nonexistent_file(self, mock_config):
        runner = CliRunner()
        result = runner.invoke(main, ["content", "upload", "/nonexistent/file.txt"])
        assert result.exit_code != 0


class TestContentView:

    def test_content_view(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/content/library/c-1/content").mock(
                return_value=httpx.Response(200, json=CONTENT_VIEW_RESPONSE)
            )
            runner = CliRunner()
            result = runner.invoke(main, ["content", "view", "c-1"])
            assert result.exit_code == 0
            assert "full text content" in result.output

    def test_content_view_text_field(self, mock_config):
        """Some responses use 'text' instead of 'content'."""
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/content/library/c-2/content").mock(
                return_value=httpx.Response(200, json={"text": "Alt text field"})
            )
            runner = CliRunner()
            result = runner.invoke(main, ["content", "view", "c-2"])
            assert result.exit_code == 0
            assert "Alt text field" in result.output


class TestContentDelete:

    def test_content_delete_with_force(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.delete("/content/library/c-1").mock(
                return_value=httpx.Response(200, json=CONTENT_DELETE_RESPONSE)
            )
            runner = CliRunner()
            result = runner.invoke(main, ["content", "delete", "--force", "c-1"])
            assert result.exit_code == 0
            assert "Deleted: c-1" in result.output

    def test_content_delete_confirm_yes(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.delete("/content/library/c-1").mock(
                return_value=httpx.Response(200, json=CONTENT_DELETE_RESPONSE)
            )
            runner = CliRunner()
            result = runner.invoke(main, ["content", "delete", "c-1"], input="y\n")
            assert result.exit_code == 0
            assert "Deleted: c-1" in result.output

    def test_content_delete_confirm_no(self, mock_config):
        runner = CliRunner()
        result = runner.invoke(main, ["content", "delete", "c-1"], input="n\n")
        assert result.exit_code == 0
        assert "Cancelled" in result.output


class TestContentExtract:

    def test_content_extract_with_config_graph(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/content/bulk-extract").mock(
                return_value=httpx.Response(200, json=CONTENT_EXTRACT_RESPONSE)
            )
            runner = CliRunner()
            result = runner.invoke(main, ["content", "extract", "c-1", "c-2"])
            assert result.exit_code == 0
            body = json.loads(rsps.calls[0].request.content)
            assert body["content_item_ids"] == ["c-1", "c-2"]
            assert body["graph_id"] == "graph-uuid-1"  # from mock_config
            assert "Queued 2" in result.output

    def test_content_extract_with_graph_option(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/content/bulk-extract").mock(
                return_value=httpx.Response(200, json=CONTENT_EXTRACT_RESPONSE)
            )
            runner = CliRunner()
            result = runner.invoke(main, [
                "content", "extract", "--graph", "custom-graph", "c-1",
            ])
            assert result.exit_code == 0
            body = json.loads(rsps.calls[0].request.content)
            assert body["graph_id"] == "custom-graph"

    def test_content_extract_no_graph_errors(self, mock_config, tmp_path, monkeypatch):
        """Without active_graph_id and no --graph, should error."""
        # Override config to remove active_graph_id
        import yaml
        config_file = tmp_path / ".weezdom" / "config.yaml"
        cfg = yaml.safe_load(config_file.read_text())
        cfg.pop("active_graph_id", None)
        config_file.write_text(yaml.safe_dump(cfg))

        runner = CliRunner()
        result = runner.invoke(main, ["content", "extract", "c-1"])
        assert result.exit_code != 0
