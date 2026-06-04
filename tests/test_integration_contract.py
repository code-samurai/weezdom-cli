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
        with pytest.raises(ClickExit, match="Entity not found: Nonexistent"):
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


# ---------------------------------------------------------------------------
# Paths contract (GET /tools/paths)
# ---------------------------------------------------------------------------

class TestPathsContract:
    """CLI paths must GET /tools/paths with source, target, max_depth params."""

    PATHS_RESPONSE = {
        "source": "A", "target": "B",
        "paths": [{"entities": [{"name": "A"}, {"name": "B"}],
                   "relationships": [{"type": "REL", "fact": None}]}],
    }

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_paths_sends_params(self, respx_mock):
        respx_mock.get("/tools/paths").mock(
            return_value=httpx.Response(200, json=self.PATHS_RESPONSE))
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key", graph_id="g-1")
        result = await client.get("/tools/paths", params={
            "source": "A", "target": "B", "max_depth": 3})
        assert result["source"] == "A"
        req = respx_mock.calls[0].request
        assert "source=A" in str(req.url)


# ---------------------------------------------------------------------------
# Neighborhood contract (GET /tools/entity/{name}/neighborhood)
# ---------------------------------------------------------------------------

class TestNeighborhoodContract:
    """CLI neighborhood must GET /tools/entity/{name}/neighborhood."""

    NEIGHBORHOOD_RESPONSE = {
        "center": "Entity A", "depth": 2,
        "nodes": [{"name": "Entity B", "entity_type": "Type", "summary": None, "distance": 1}],
    }

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_neighborhood_sends_params(self, respx_mock):
        respx_mock.get("/tools/entity/Entity%20A/neighborhood").mock(
            return_value=httpx.Response(200, json=self.NEIGHBORHOOD_RESPONSE))
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key", graph_id="g-1")
        result = await client.get("/tools/entity/Entity%20A/neighborhood",
                                  params={"depth": 2, "limit": 50})
        assert result["center"] == "Entity A"
        assert len(result["nodes"]) == 1


# ---------------------------------------------------------------------------
# Batch contract (POST /batch-query)
# ---------------------------------------------------------------------------

class TestBatchContract:
    """CLI batch must POST /batch-query with queries list."""

    BATCH_RESPONSE = {
        "results": [{"query": "test", "results": [], "context_tokens": 0,
                     "format": "agent", "cursor": None}],
        "total_queries": 1,
    }

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_batch_sends_queries(self, respx_mock):
        respx_mock.post("/batch-query").mock(
            return_value=httpx.Response(200, json=self.BATCH_RESPONSE))
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key", graph_id="g-1")
        result = await client.post("/batch-query", json={
            "queries": [{"query": "test", "num_results": 10}]})
        assert result["total_queries"] == 1
        body = json.loads(respx_mock.calls[0].request.content)
        assert body["queries"][0]["query"] == "test"


# ---------------------------------------------------------------------------
# Workspace search contract (POST /search/workspace)
# ---------------------------------------------------------------------------

class TestWorkspaceSearchContract:
    """CLI workspace search must POST /search/workspace."""

    WS_SEARCH_RESPONSE = {
        "query": "test", "workspace_id": "ws-1",
        "num_results": 0, "results": [],
    }

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_workspace_search_sends_body(self, respx_mock):
        respx_mock.post("/search/workspace").mock(
            return_value=httpx.Response(200, json=self.WS_SEARCH_RESPONSE))
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key")
        result = await client.post("/search/workspace", json={
            "query": "test", "workspace_id": "ws-1", "limit": 10})
        assert result["query"] == "test"
        body = json.loads(respx_mock.calls[0].request.content)
        assert body["workspace_id"] == "ws-1"


# ---------------------------------------------------------------------------
# Workspace info contract (GET /insights/workspaces)
# ---------------------------------------------------------------------------

class TestWorkspaceInfoContract:
    """CLI workspace info must GET /insights/workspaces (no X-Graph-Id required)."""

    WS_INFO_RESPONSE = {
        "workspaces": [{"id": "ws-1", "name": "WS", "graph_count": 1, "entity_count": 100}],
        "current_workspace_id": "ws-1",
    }

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_workspace_info_no_graph_required(self, respx_mock):
        respx_mock.get("/insights/workspaces").mock(
            return_value=httpx.Response(200, json=self.WS_INFO_RESPONSE))
        # Deliberately pass graph_id=None — workspace info doesn't need it
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key", graph_id=None)
        result = await client.get("/insights/workspaces")
        assert len(result["workspaces"]) == 1
        req = respx_mock.calls[0].request
        assert "x-graph-id" not in req.headers


# ---------------------------------------------------------------------------
# Ontology list contract (GET /ontologies/list)
# ---------------------------------------------------------------------------

class TestOntologyListContract:
    """CLI ontology list must GET /ontologies/list; response is raw array."""

    ONTOLOGY_LIST_RESPONSE = [
        {"id": "ont-1", "name": "Test Ontology", "version_count": 1,
         "graph_count": 0, "published_graph_count": 0,
         "status": {"overall_score": 75, "status": "draft"}},
    ]

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_ontology_list_raw_array(self, respx_mock):
        respx_mock.get("/ontologies/list").mock(
            return_value=httpx.Response(200, json=self.ONTOLOGY_LIST_RESPONSE))
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key", graph_id="g-1")
        result = await client.get("/ontologies/list")
        # Must be a list (raw array)
        assert isinstance(result, list)
        assert result[0]["name"] == "Test Ontology"


# ---------------------------------------------------------------------------
# Property search contract (POST /tools/properties/search)
# ---------------------------------------------------------------------------

class TestPropertySearchContract:
    """CLI property-search must POST /tools/properties/search."""

    PROP_SEARCH_RESPONSE = {
        "property_name": "revenue", "property_value": None,
        "matches": [{"name": "Segment A", "entity_type": "Segment",
                     "properties": {"revenue": "high"}}],
    }

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_property_search_sends_body(self, respx_mock):
        respx_mock.post("/tools/properties/search").mock(
            return_value=httpx.Response(200, json=self.PROP_SEARCH_RESPONSE))
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key", graph_id="g-1")
        result = await client.post("/tools/properties/search", json={
            "property_name": "revenue", "limit": 50})
        assert result["property_name"] == "revenue"
        body = json.loads(respx_mock.calls[0].request.content)
        assert body["property_name"] == "revenue"
        assert body["limit"] == 50


# ---------------------------------------------------------------------------
# Ontology suggest contract (POST /ontologies/suggest)
# ---------------------------------------------------------------------------

class TestOntologySuggestContract:
    """CLI suggest must POST /ontologies/suggest with description and goals."""

    SUGGEST_RESPONSE = {
        "recommended_graph_role": "subject",
        "graph_role_reason": "reason",
        "graph_architecture": {"subject": "s", "intelligence": "i", "reference": "r"},
        "config_template": {
            "entity_types": [{"name": "ExampleEntity", "description": "..."}],
            "relationship_types": [],
        },
        "scoring_rubric": {},
        "example_hunting_instructions": "hunt",
    }

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_suggest_posts_description_and_goals(self, respx_mock):
        respx_mock.post("/ontologies/suggest").mock(
            return_value=httpx.Response(200, json=self.SUGGEST_RESPONSE))
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key", graph_id="g-1")
        result = await client.post(
            "/ontologies/suggest",
            json={"description": "Track sales", "goals": ["segment by stage"]},
        )
        assert "config_template" in result
        body = json.loads(respx_mock.calls[0].request.content)
        assert body["description"] == "Track sales"
        assert body["goals"] == ["segment by stage"]

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_suggest_sends_graph_header(self, respx_mock):
        respx_mock.post("/ontologies/suggest").mock(
            return_value=httpx.Response(200, json=self.SUGGEST_RESPONSE))
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key", graph_id="g-42")
        await client.post("/ontologies/suggest", json={"description": "test", "goals": []})
        req = respx_mock.calls[0].request
        assert req.headers.get("x-graph-id") == "g-42"


# ---------------------------------------------------------------------------
# Ontology create contract (POST /ontologies)
# ---------------------------------------------------------------------------

class TestOntologyCreateContract:
    """CLI create must POST /ontologies with name + entity_types."""

    CREATE_RESPONSE = {
        "ontology_id": "ont-1", "version_id": "ver-1",
        "quality": {"overall_score": 55, "grade": "C", "is_buildable": False,
                    "axes": {}, "weakest_entities": [], "weakest_relationships": [],
                    "next_actions": []},
        "gaps": [],
    }

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_create_posts_to_ontologies(self, respx_mock):
        respx_mock.post("/ontologies").mock(
            return_value=httpx.Response(201, json=self.CREATE_RESPONSE))
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key", graph_id="g-1")
        result = await client.post("/ontologies", json={
            "name": "Sales CRM",
            "entity_types": [{"name": "Deal", "description": "A sales deal."}],
        })
        assert result["ontology_id"] == "ont-1"
        body = json.loads(respx_mock.calls[0].request.content)
        assert body["name"] == "Sales CRM"
        assert len(body["entity_types"]) == 1

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_create_409_raises_click_exit(self, respx_mock):
        respx_mock.post("/ontologies").mock(
            return_value=httpx.Response(409, json={"detail": "already exists"}))
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key", graph_id="g-1")
        from weezdom_cli.client import ClickExit
        with pytest.raises(ClickExit, match="already exists"):
            await client.post("/ontologies", json={"name": "X", "entity_types": []})


# ---------------------------------------------------------------------------
# Ontology build contract (POST /ontologies/build)
# ---------------------------------------------------------------------------

class TestOntologyBuildContract:
    """POST /ontologies/build now returns 202 + {job_id, status: 'queued'}."""

    ENQUEUE_RESPONSE = {"job_id": "job-uuid-42", "status": "queued"}

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_build_returns_job_id(self, respx_mock):
        respx_mock.post("/ontologies/build").mock(
            return_value=httpx.Response(202, json=self.ENQUEUE_RESPONSE))
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key", graph_id="g-1")
        result = await client.post("/ontologies/build", json={
            "name": "Sales AI", "description": "Track sales",
            "goals": ["find patterns"], "max_iterations": 3,
        })
        assert result["job_id"] == "job-uuid-42"
        assert result["status"] == "queued"
        body = json.loads(respx_mock.calls[0].request.content)
        assert body["name"] == "Sales AI"
        assert body["max_iterations"] == 3

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_build_status_contract(self, respx_mock):
        """GET /ontologies/build-status/{job_id} returns status shape."""
        status_response = {
            "job_id": "job-uuid-42",
            "status": "completed",
            "result": {
                "ontology_id": "ont-2", "version_id": "ver-2",
                "quality": {"overall_score": 75},
                "gaps": [], "iterations_used": 2, "reached_threshold": True,
            },
            "error": None,
        }
        respx_mock.get("/ontologies/build-status/job-uuid-42").mock(
            return_value=httpx.Response(200, json=status_response))
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key", graph_id="g-1")
        result = await client.get("/ontologies/build-status/job-uuid-42")
        assert result["job_id"] == "job-uuid-42"
        assert result["status"] == "completed"
        assert result["result"]["ontology_id"] == "ont-2"
        assert result["error"] is None

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_build_502_raises_click_exit(self, respx_mock):
        respx_mock.post("/ontologies/build").mock(
            return_value=httpx.Response(502, json={"detail": "job_store unavailable"}))
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key", graph_id="g-1")
        from weezdom_cli.client import ClickExit
        with pytest.raises(ClickExit, match="API error"):
            await client.post("/ontologies/build",
                              json={"name": "x", "description": "y", "goals": []})


class TestOntologyScoreContract:
    """CLI score must GET /ontologies/{id}/score with X-API-Key header."""

    SCORE_RESPONSE = {
        "ontology_id": "ont-1",
        "version_id": "ver-1",
        "version": 1,
        "quality": {"overall_score": 78, "grade": "B", "is_buildable": True},
        "gaps": [],
    }

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_score_sends_get_to_correct_path(self, respx_mock):
        respx_mock.get("/ontologies/ont-1/score").mock(
            return_value=httpx.Response(200, json=self.SCORE_RESPONSE)
        )
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key", graph_id="g-1")
        result = await client.get("/ontologies/ont-1/score")
        assert result["quality"]["overall_score"] == 78
        req = respx_mock.calls[0].request
        assert req.headers["x-api-key"] == "wdm_key"
        assert req.method == "GET"


class TestOntologyImproveContract:
    """CLI improve must POST /ontologies/{id}/improve with body {"updates": {...}}."""

    IMPROVE_RESPONSE = {
        "ontology_id": "ont-1",
        "new_version_id": "ver-2",
        "new_version": 2,
        "quality": {"overall_score": 72, "grade": "B"},
    }

    @respx.mock(base_url=API_URL)
    @pytest.mark.asyncio
    async def test_improve_sends_post_with_updates_key(self, respx_mock):
        respx_mock.post("/ontologies/ont-1/improve").mock(
            return_value=httpx.Response(200, json=self.IMPROVE_RESPONSE)
        )
        client = WeezdomClient(api_url=API_URL, api_key="wdm_key", graph_id="g-1")
        updates = {"entity_types": [{"name": "Deal", "description": "Updated"}]}
        result = await client.post(
            "/ontologies/ont-1/improve", json={"updates": updates}
        )
        assert result["new_version_id"] == "ver-2"
        req = respx_mock.calls[0].request
        import json as _json
        body = _json.loads(req.content)
        assert "updates" in body
        assert req.method == "POST"
