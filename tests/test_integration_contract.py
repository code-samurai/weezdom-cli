"""Integration contract tests — verify CLI HTTP calls match server API.

These tests define the exact contract between the CLI and the Weezdom.ai
REST API. They use respx to mock HTTP and verify:
1. Correct HTTP method and path
2. Correct headers (X-API-Key, X-Graph-Id)
3. Correct request body shape
4. Correct parsing of response body

If these tests pass, the CLI correctly speaks the server's protocol.
If the server API changes, these tests catch the drift.
"""

import json
import pytest
import respx
import httpx

from weezdom_cli.client import WeezdomClient

API_URL = "https://test.weezdom.ai"


# ---------------------------------------------------------------------------
# Auth contract
# ---------------------------------------------------------------------------

class TestAuthContract:
    """CLI auth must call GET /auth/me with X-API-Key header."""

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_validate_auth_sends_api_key_header(self, respx_mock):
        respx_mock.get("/auth/me").mock(return_value=httpx.Response(200, json={
            "id": "user-1", "email": "test@example.com", "tenant_id": "t-1",
        }))
        client = WeezdomClient(api_url=API_URL, api_key="wdm_testkey123")
        result = await client.validate_auth()

        assert result["email"] == "test@example.com"
        req = respx_mock.calls[0].request
        assert req.headers["x-api-key"] == "wdm_testkey123"

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_invalid_key_raises(self, respx_mock):
        respx_mock.get("/auth/me").mock(return_value=httpx.Response(401, json={
            "detail": "Authentication required",
        }))
        client = WeezdomClient(api_url=API_URL, api_key="wdm_badkey")
        from weezdom_cli.client import ClickExit
        with pytest.raises(ClickExit, match="Not authenticated"):
            await client.validate_auth()


# ---------------------------------------------------------------------------
# Search contract (POST /tools/search)
# ---------------------------------------------------------------------------

class TestSearchContract:
    """CLI search must POST /tools/search with query + num_results."""

    SEARCH_RESPONSE = {
        "query": "progressive profiling",
        "facts": [
            {
                "fact": "Progressive profiling reduces form fatigue",
                "entities": ["Progressive Profiling"],
                "source_url": "Marketing Guide",
                "confidence": 0.95,
            },
        ],
        "entities_found": ["Progressive Profiling"],
    }

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_search_sends_correct_request(self, respx_mock):
        respx_mock.post("/tools/search").mock(
            return_value=httpx.Response(200, json=self.SEARCH_RESPONSE)
        )
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key", graph_id="g-1")
        result = await client.post("/tools/search", json={
            "query": "progressive profiling", "num_results": 10,
        })

        assert result["query"] == "progressive profiling"
        assert len(result["facts"]) == 1
        assert result["facts"][0]["confidence"] == 0.95

        req = respx_mock.calls[0].request
        assert req.headers["x-api-key"] == "wdm_key"
        assert req.headers["x-graph-id"] == "g-1"
        body = json.loads(req.content)
        assert body["query"] == "progressive profiling"
        assert body["num_results"] == 10


# ---------------------------------------------------------------------------
# Entity contract (GET /tools/entity/{name})
# ---------------------------------------------------------------------------

class TestEntityContract:
    """CLI entity must GET /tools/entity/{name} with URL-encoded name."""

    ENTITY_RESPONSE = {
        "name": "Progressive Profiling",
        "entity_type": "Technique",
        "summary": "A technique for gradually collecting user data",
        "facts": ["Fact one", "Fact two"],
        "relationships": {"SOLVES": ["Survey Fatigue"]},
        "sources": [{"title": "Guide", "url": "https://example.com"}],
    }

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_get_entity_url_encodes_name(self, respx_mock):
        respx_mock.get("/tools/entity/Progressive%20Profiling").mock(
            return_value=httpx.Response(200, json=self.ENTITY_RESPONSE)
        )
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key", graph_id="g-1")
        result = await client.get("/tools/entity/Progressive%20Profiling")

        assert result["name"] == "Progressive Profiling"
        assert result["entity_type"] == "Technique"
        assert "SOLVES" in result["relationships"]

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_entity_not_found_raises(self, respx_mock):
        respx_mock.get("/tools/entity/Nonexistent").mock(
            return_value=httpx.Response(404, json={"detail": "Entity not found: Nonexistent"})
        )
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key", graph_id="g-1")
        from weezdom_cli.client import ClickExit
        with pytest.raises(ClickExit, match="Not found"):
            await client.get("/tools/entity/Nonexistent")


# ---------------------------------------------------------------------------
# Related entities contract (GET /tools/entity/{name}/related)
# ---------------------------------------------------------------------------

class TestRelatedContract:
    """CLI related must GET /tools/entity/{name}/related."""

    RELATED_RESPONSE = {
        "entity": "Progressive Profiling",
        "related": [
            {"name": "Survey Fatigue", "entity_type": "Problem",
             "relationship": "SOLVES", "direction": "outgoing"},
        ],
    }

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_get_related(self, respx_mock):
        respx_mock.get("/tools/entity/Progressive%20Profiling/related").mock(
            return_value=httpx.Response(200, json=self.RELATED_RESPONSE)
        )
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key", graph_id="g-1")
        result = await client.get("/tools/entity/Progressive%20Profiling/related")

        assert result["entity"] == "Progressive Profiling"
        assert len(result["related"]) == 1
        assert result["related"][0]["relationship"] == "SOLVES"


# ---------------------------------------------------------------------------
# Sources contract (POST /tools/sources)
# ---------------------------------------------------------------------------

class TestSourcesContract:
    """CLI sources must POST /tools/sources with query + limit."""

    SOURCES_RESPONSE = {
        "query": "survey fatigue",
        "sources": [
            {
                "document_title": "Marketing Guide",
                "document_type": None,
                "source_url": "https://example.com",
                "segments": [
                    {"content": "Quote from guide...", "context": None},
                ],
            },
        ],
    }

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_find_sources_sends_correct_body(self, respx_mock):
        respx_mock.post("/tools/sources").mock(
            return_value=httpx.Response(200, json=self.SOURCES_RESPONSE)
        )
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key", graph_id="g-1")
        result = await client.post("/tools/sources", json={
            "query": "survey fatigue", "limit": 5,
        })

        assert len(result["sources"]) == 1
        assert result["sources"][0]["document_title"] == "Marketing Guide"

        body = json.loads(respx_mock.calls[0].request.content)
        assert body["query"] == "survey fatigue"
        assert body["limit"] == 5


# ---------------------------------------------------------------------------
# Topics contract (GET /tools/topics)
# ---------------------------------------------------------------------------

class TestTopicsContract:
    """CLI topics must GET /tools/topics with optional entity_type and limit."""

    TOPICS_RESPONSE = {
        "total_entities": 644,
        "by_type": {"Technique": 100, "Concept": 50},
        "sample_entities": [
            {"name": "Progressive Profiling", "type": "Technique", "mention_count": 15},
        ],
    }

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_list_topics(self, respx_mock):
        respx_mock.get("/tools/topics").mock(
            return_value=httpx.Response(200, json=self.TOPICS_RESPONSE)
        )
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key", graph_id="g-1")
        result = await client.get("/tools/topics", params={"limit": 50})

        assert result["total_entities"] == 644
        assert len(result["sample_entities"]) == 1

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_list_topics_with_type_filter(self, respx_mock):
        respx_mock.get("/tools/topics").mock(
            return_value=httpx.Response(200, json=self.TOPICS_RESPONSE)
        )
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key", graph_id="g-1")
        await client.get("/tools/topics", params={"entity_type": "Technique", "limit": 20})

        req = respx_mock.calls[0].request
        assert "entity_type=Technique" in str(req.url)


# ---------------------------------------------------------------------------
# Content library contract
# ---------------------------------------------------------------------------

class TestContentContract:
    """CLI content commands must match /content/* endpoints."""

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_content_list(self, respx_mock):
        respx_mock.get("/content/library").mock(return_value=httpx.Response(200, json={
            "items": [{"id": "c-1", "title": "Guide", "type": "url", "status": "completed"}],
            "total": 1,
        }))
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key", graph_id="g-1")
        result = await client.get("/content/library")
        assert result["total"] == 1

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_content_add_url(self, respx_mock):
        respx_mock.post("/content/url").mock(return_value=httpx.Response(200, json={
            "job_ids": ["job-1"], "message": "1 URL queued",
        }))
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key", graph_id="g-1")
        result = await client.post("/content/url", json={
            "urls": ["https://example.com/article"],
        })
        assert len(result["job_ids"]) == 1

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_content_delete(self, respx_mock):
        respx_mock.delete("/content/library/c-1").mock(
            return_value=httpx.Response(200, json={"deleted": True})
        )
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key", graph_id="g-1")
        result = await client.delete("/content/library/c-1")
        assert result["deleted"] is True

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_content_extract(self, respx_mock):
        respx_mock.post("/content/bulk-extract").mock(return_value=httpx.Response(200, json={
            "job_ids": ["j-1", "j-2"], "message": "2 items queued for extraction",
        }))
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key", graph_id="g-1")
        result = await client.post("/content/bulk-extract", json={
            "content_item_ids": ["c-1", "c-2"], "graph_id": "g-1",
        })
        assert len(result["job_ids"]) == 2


# ---------------------------------------------------------------------------
# Graph management contract
# ---------------------------------------------------------------------------

class TestGraphContract:
    """CLI graph commands must match /knowledge-graphs/* endpoints."""

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_graph_list(self, respx_mock):
        respx_mock.get("/knowledge-graphs/data/list").mock(return_value=httpx.Response(200, json={
            "graphs": [
                {"id": "g-1", "name": "Marketing KG", "status": "ready",
                 "entity_count": 644, "content_count": 112},
            ],
        }))
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key")
        result = await client.get("/knowledge-graphs/data/list")
        assert len(result["graphs"]) == 1
        assert result["graphs"][0]["name"] == "Marketing KG"

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_graph_detail(self, respx_mock):
        respx_mock.get("/knowledge-graphs/data/g-1").mock(return_value=httpx.Response(200, json={
            "id": "g-1", "name": "Marketing KG", "status": "ready",
            "entity_count": 644, "content_count": 112,
            "ontology_name": "Marketing Ontology",
        }))
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key")
        result = await client.get("/knowledge-graphs/data/g-1")
        assert result["name"] == "Marketing KG"

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_graph_pipeline(self, respx_mock):
        respx_mock.get("/knowledge-graphs/data/g-1/pipeline").mock(return_value=httpx.Response(200, json={
            "jobs": [{"id": "j-1", "status": "completed", "content_title": "Guide"}],
            "total": 1,
        }))
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key", graph_id="g-1")
        result = await client.get("/knowledge-graphs/data/g-1/pipeline")
        assert result["total"] == 1


# ---------------------------------------------------------------------------
# Header contract — every request must include auth and graph headers
# ---------------------------------------------------------------------------

class TestHeaderContract:
    """All API calls must include X-API-Key and X-Graph-Id headers."""

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_all_requests_include_auth_header(self, respx_mock):
        respx_mock.get("/tools/topics").mock(
            return_value=httpx.Response(200, json={"total_entities": 0, "by_type": {}, "sample_entities": []})
        )
        client = WeezdomClient(api_url=API_URL, api_key="wdm_mykey", graph_id="g-42")
        await client.get("/tools/topics")

        req = respx_mock.calls[0].request
        assert req.headers["x-api-key"] == "wdm_mykey"
        assert req.headers["x-graph-id"] == "g-42"

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_no_graph_header_when_not_set(self, respx_mock):
        respx_mock.get("/knowledge-graphs/data/list").mock(
            return_value=httpx.Response(200, json={"graphs": []})
        )
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key", graph_id=None)
        await client.get("/knowledge-graphs/data/list")

        req = respx_mock.calls[0].request
        assert "x-graph-id" not in req.headers
