"""Tests for query commands — search, entity, topics, sources."""

import json
import pytest
import respx
import httpx
from click.testing import CliRunner

from weezdom_cli.cli import main

API_URL = "https://test.weezdom.ai"


SEARCH_RESPONSE = {
    "query": "progressive profiling",
    "facts": [
        {"fact": "Progressive profiling reduces form fatigue", "entities": ["Progressive Profiling"],
         "source_url": "Marketing Guide", "confidence": 0.95},
    ],
    "entities_found": ["Progressive Profiling"],
}

ENTITY_RESPONSE = {
    "name": "Progressive Profiling",
    "entity_type": "Technique",
    "summary": "A technique for gradually collecting user data",
    "facts": ["Fact one", "Fact two"],
    "relationships": {"SOLVES": ["Survey Fatigue"]},
    "sources": [{"title": "Guide", "url": "https://example.com"}],
}

RELATED_RESPONSE = {
    "entity": "Progressive Profiling",
    "related": [
        {"name": "Survey Fatigue", "entity_type": "Problem",
         "relationship": "SOLVES", "direction": "outgoing"},
    ],
}

TOPICS_RESPONSE = {
    "total_entities": 644,
    "by_type": {"Technique": 100, "Concept": 50},
    "sample_entities": [
        {"name": "Progressive Profiling", "type": "Technique", "mention_count": 15},
    ],
}

SOURCES_RESPONSE = {
    "query": "survey fatigue",
    "sources": [
        {"document_title": "Marketing Guide", "document_type": None,
         "source_url": "https://example.com",
         "segments": [{"content": "Quote from guide...", "context": None}]},
    ],
}


class TestSearchCommand:
    def test_search_json_output(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/tools/search").mock(return_value=httpx.Response(200, json=SEARCH_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "json", "search", "profiling"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["query"] == "progressive profiling"
            assert len(data["facts"]) == 1

    def test_search_table_output(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/tools/search").mock(return_value=httpx.Response(200, json=SEARCH_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "search", "profiling"])
            assert result.exit_code == 0
            assert "Progressive profiling" in result.output

    def test_search_no_results(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/tools/search").mock(return_value=httpx.Response(200, json={
                "query": "nothing", "facts": [], "entities_found": [],
            }))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "search", "nothing"])
            assert result.exit_code == 0
            assert "No results" in result.output

    def test_search_sends_limit(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/tools/search").mock(return_value=httpx.Response(200, json=SEARCH_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "json", "search", "--limit", "5", "test"])
            assert result.exit_code == 0
            body = json.loads(rsps.calls[0].request.content)
            assert body["num_results"] == 5

    def test_search_truncates_long_facts(self, mock_config):
        long_fact = "A" * 100
        response = {
            "query": "test",
            "facts": [{"fact": long_fact, "entities": [], "confidence": 0.5}],
            "entities_found": [],
        }
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/tools/search").mock(return_value=httpx.Response(200, json=response))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "search", "test"])
            assert result.exit_code == 0
            assert long_fact not in result.output
            # Our code adds "..." but Rich may also use "…" (unicode ellipsis)
            assert "..." in result.output or "…" in result.output

    def test_search_sends_correct_headers(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/tools/search").mock(return_value=httpx.Response(200, json=SEARCH_RESPONSE))
            runner = CliRunner()
            runner.invoke(main, ["--format", "json", "search", "profiling"])
            req = rsps.calls[0].request
            body = json.loads(req.content)
            assert body["query"] == "profiling"
            assert body["num_results"] == 10  # default
            assert req.headers["x-api-key"] == "wdm_testkey12345678"
            assert req.headers["x-graph-id"] == "graph-uuid-1"


class TestEntityCommand:
    def test_entity_json(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get(url__regex=r"/tools/entity/.*").mock(
                return_value=httpx.Response(200, json=ENTITY_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "json", "entity", "Progressive Profiling"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["name"] == "Progressive Profiling"

    def test_entity_table(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get(url__regex=r"/tools/entity/[^/]+$").mock(
                return_value=httpx.Response(200, json=ENTITY_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["entity", "Progressive Profiling"])
            assert result.exit_code == 0
            assert "Progressive Profiling" in result.output
            assert "Technique" in result.output
            assert "SOLVES" in result.output

    def test_entity_related_json(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get(url__regex=r"/tools/entity/.+/related").mock(
                return_value=httpx.Response(200, json=RELATED_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "json", "entity", "--related", "Progressive Profiling"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert len(data["related"]) == 1
            assert data["related"][0]["relationship"] == "SOLVES"

    def test_entity_related_table(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get(url__regex=r"/tools/entity/.+/related").mock(
                return_value=httpx.Response(200, json=RELATED_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "entity", "--related", "Progressive Profiling"])
            assert result.exit_code == 0
            assert "Survey Fatigue" in result.output
            assert "SOLVES" in result.output
            assert "outgoing" in result.output

    def test_entity_url_encodes_name(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/tools/entity/A%26B%20Corp").mock(
                return_value=httpx.Response(200, json={
                    "name": "A&B Corp", "entity_type": "Company",
                    "summary": "", "facts": [], "relationships": {}, "sources": [],
                }))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "json", "entity", "A&B Corp"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["name"] == "A&B Corp"

    def test_entity_related_empty(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get(url__regex=r"/tools/entity/.+/related").mock(
                return_value=httpx.Response(200, json={"entity": "Orphan", "related": []}))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "entity", "--related", "Orphan"])
            assert result.exit_code == 0
            assert "No related entities" in result.output


class TestTopicsCommand:
    def test_topics_json(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/tools/topics").mock(return_value=httpx.Response(200, json=TOPICS_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "json", "topics"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["total_entities"] == 644

    def test_topics_table(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/tools/topics").mock(return_value=httpx.Response(200, json=TOPICS_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["topics"])
            assert result.exit_code == 0
            assert "644" in result.output
            assert "Technique" in result.output

    def test_topics_with_type_filter(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/tools/topics").mock(return_value=httpx.Response(200, json=TOPICS_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "json", "topics", "--type", "Technique"])
            assert result.exit_code == 0
            req = rsps.calls[0].request
            assert "entity_type=Technique" in str(req.url)

    def test_topics_with_limit(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/tools/topics").mock(return_value=httpx.Response(200, json=TOPICS_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "json", "topics", "--limit", "20"])
            assert result.exit_code == 0
            req = rsps.calls[0].request
            assert "limit=20" in str(req.url)

    def test_topics_empty(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/tools/topics").mock(return_value=httpx.Response(200, json={
                "total_entities": 0, "by_type": {}, "sample_entities": [],
            }))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "topics"])
            assert result.exit_code == 0
            assert "0" in result.output
            assert "No entities" in result.output


class TestSourcesCommand:
    def test_sources_json(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/tools/sources").mock(return_value=httpx.Response(200, json=SOURCES_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "json", "sources", "survey fatigue"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert len(data["sources"]) == 1

    def test_sources_table(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/tools/sources").mock(return_value=httpx.Response(200, json=SOURCES_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["sources", "survey fatigue"])
            assert result.exit_code == 0
            assert "Marketing Guide" in result.output
            assert "Quote from guide" in result.output

    def test_sources_no_results(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/tools/sources").mock(return_value=httpx.Response(200, json={
                "query": "nothing", "sources": [],
            }))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "sources", "nothing"])
            assert result.exit_code == 0
            assert "No sources" in result.output

    def test_sources_with_limit(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/tools/sources").mock(return_value=httpx.Response(200, json=SOURCES_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "json", "sources", "--limit", "3", "survey fatigue"])
            assert result.exit_code == 0
            body = json.loads(rsps.calls[0].request.content)
            assert body["limit"] == 3

    def test_sources_sends_correct_request(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/tools/sources").mock(return_value=httpx.Response(200, json=SOURCES_RESPONSE))
            runner = CliRunner()
            runner.invoke(main, ["--format", "json", "sources", "survey fatigue"])
            req = rsps.calls[0].request
            body = json.loads(req.content)
            assert body["query"] == "survey fatigue"
            assert body["limit"] == 5  # default
            assert req.headers["x-api-key"] == "wdm_testkey12345678"
            assert req.headers["x-graph-id"] == "graph-uuid-1"


PATHS_RESPONSE = {
    "source": "Progressive Profiling",
    "target": "Lead Scoring",
    "paths": [
        {
            "entities": [
                {"name": "Progressive Profiling", "entity_type": "Technique"},
                {"name": "Survey Fatigue", "entity_type": "Problem"},
                {"name": "Lead Scoring", "entity_type": "Metric"},
            ],
            "relationships": [
                {"type": "SOLVES", "fact": None},
                {"type": "IMPROVES", "fact": None},
            ],
        }
    ],
}

NEIGHBORHOOD_RESPONSE = {
    "center": "Progressive Profiling",
    "depth": 2,
    "nodes": [
        {"name": "Survey Fatigue", "entity_type": "Problem", "summary": "Fatigue from surveys", "distance": 1},
        {"name": "Lead Scoring", "entity_type": "Metric", "summary": "Score leads", "distance": 2},
    ],
}


class TestPathsCommand:
    def test_paths_json_output(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/tools/paths").mock(return_value=httpx.Response(200, json=PATHS_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "json", "paths",
                                          "Progressive Profiling", "Lead Scoring"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["source"] == "Progressive Profiling"
            assert len(data["paths"]) == 1

    def test_paths_table_output(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/tools/paths").mock(return_value=httpx.Response(200, json=PATHS_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "paths",
                                          "Progressive Profiling", "Lead Scoring"])
            assert result.exit_code == 0
            assert "Progressive Profiling" in result.output
            assert "SOLVES" in result.output

    def test_paths_no_paths_found(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get("/tools/paths").mock(return_value=httpx.Response(200, json={
                "source": "A", "target": "B", "paths": []
            }))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "paths", "A", "B"])
            assert result.exit_code == 0
            assert "No paths found" in result.output

    def test_paths_sends_correct_params(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            route = rsps.get("/tools/paths").mock(
                return_value=httpx.Response(200, json=PATHS_RESPONSE))
            runner = CliRunner()
            runner.invoke(main, ["paths", "Entity A", "Entity B", "--depth", "4"])
            assert route.called
            url_str = str(route.calls[0].request.url)
            assert "source=Entity" in url_str
            assert "max_depth=4" in url_str


class TestNeighborhoodCommand:
    def test_neighborhood_json_output(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get(url__regex=r'/tools/entity/.*/neighborhood').mock(
                return_value=httpx.Response(200, json=NEIGHBORHOOD_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "json", "neighborhood",
                                          "Progressive Profiling"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["center"] == "Progressive Profiling"
            assert len(data["nodes"]) == 2

    def test_neighborhood_table_output(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get(url__regex=r'/tools/entity/.*/neighborhood').mock(
                return_value=httpx.Response(200, json=NEIGHBORHOOD_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "neighborhood",
                                          "Progressive Profiling"])
            assert result.exit_code == 0
            assert "Survey Fatigue" in result.output
            assert "Lead Scoring" in result.output

    def test_neighborhood_no_nodes(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.get(url__regex=r'/tools/entity/.*/neighborhood').mock(
                return_value=httpx.Response(200, json={"center": "Unknown", "depth": 2, "nodes": []}))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "neighborhood", "Unknown"])
            assert result.exit_code == 0
            assert "No neighbors found" in result.output


BATCH_RESPONSE = {
    "results": [
        {
            "query": "profiling",
            "results": [
                {"content": "Progressive profiling reduces fatigue", "score": 0.95,
                 "source": "Marketing Guide", "entity_name": None, "entity_type": None},
            ],
            "context_tokens": 150,
            "format": "agent",
            "cursor": None,
        },
        {
            "query": "segmentation",
            "results": [
                {"content": "Segmentation improves targeting", "score": 0.88,
                 "source": "Sales Guide", "entity_name": None, "entity_type": None},
            ],
            "context_tokens": 120,
            "format": "agent",
            "cursor": None,
        },
    ],
    "total_queries": 2,
}


class TestBatchCommand:
    def test_batch_json_output(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/batch-query").mock(return_value=httpx.Response(200, json=BATCH_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "json", "batch",
                                          "profiling", "segmentation"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["total_queries"] == 2
            assert len(data["results"]) == 2

    def test_batch_table_output(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/batch-query").mock(return_value=httpx.Response(200, json=BATCH_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "batch",  # SC-3
                                          "profiling", "segmentation"])
            assert result.exit_code == 0
            assert "profiling" in result.output.lower()
            assert "segmentation" in result.output.lower()

    def test_batch_sends_correct_body(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            route = rsps.post("/batch-query").mock(
                return_value=httpx.Response(200, json=BATCH_RESPONSE))
            runner = CliRunner()
            runner.invoke(main, ["batch", "q1", "q2", "--limit", "5"])
            body = json.loads(route.calls[0].request.content)
            assert len(body["queries"]) == 2
            assert body["queries"][0]["query"] == "q1"
            assert body["queries"][0]["num_results"] == 5

    def test_batch_requires_at_least_one_query(self, mock_config):
        runner = CliRunner()
        result = runner.invoke(main, ["batch"])
        assert result.exit_code != 0


PROPERTY_SEARCH_RESPONSE = {
    "property_name": "revenue",
    "property_value": None,
    "matches": [
        {
            "name": "Enterprise Segment",
            "entity_type": "Segment",
            "properties": {"revenue": "high", "size": "large"},
        },
    ],
}


class TestPropertySearchCommand:
    def test_property_search_json_output(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/tools/properties/search").mock(
                return_value=httpx.Response(200, json=PROPERTY_SEARCH_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "json", "property-search", "revenue"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["property_name"] == "revenue"
            assert len(data["matches"]) == 1

    def test_property_search_table_output(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/tools/properties/search").mock(
                return_value=httpx.Response(200, json=PROPERTY_SEARCH_RESPONSE))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "property-search", "revenue"])  # SC-3
            assert result.exit_code == 0
            assert "Enterprise Segment" in result.output

    def test_property_search_with_value_and_type(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            route = rsps.post("/tools/properties/search").mock(
                return_value=httpx.Response(200, json=PROPERTY_SEARCH_RESPONSE))
            runner = CliRunner()
            runner.invoke(main, ["property-search", "revenue",
                                  "--value", "high", "--type", "Segment", "--limit", "20"])
            body = json.loads(route.calls[0].request.content)
            assert body["property_name"] == "revenue"
            assert body["property_value"] == "high"
            assert body["entity_type"] == "Segment"
            assert body["limit"] == 20

    def test_property_search_no_matches(self, mock_config):
        with respx.mock(base_url=API_URL) as rsps:
            rsps.post("/tools/properties/search").mock(return_value=httpx.Response(200, json={
                "property_name": "revenue", "property_value": None, "matches": []
            }))
            runner = CliRunner()
            result = runner.invoke(main, ["--format", "table", "property-search", "revenue"])  # SC-3
            assert result.exit_code == 0
            assert "No matches" in result.output
