"""Live smoke tests — exercises each CLI command family against a real API.

Run with:
    RUN_LIVE=1 WEEZDOM_API_KEY=wdm_... pytest tests/test_live_smoke.py -v -s
Optional:
    WEEZDOM_BASE_URL=https://...  (default: production URL)

Prerequisites:
    - Tenant account must have at least one active knowledge graph
      (for /tools/search and /tools/topics — server falls back to
      tenant's default graph when X-Graph-Id is absent)
    - If WEEZDOM_API_KEY is unset, falls through to ~/.weezdom/config.yaml api_key
      (expected behaviour; documented to avoid surprise for devs with local config)

Failure modes:
    - Network unreachable or server offline: ClickExit("Connection error: …")
      propagated uncaught → pytest reports FAILED (not SKIPPED)
    - Invalid API key: ClickExit("Not authenticated.…") → pytest FAILED
    - In both cases the test RAN (it was not skipped) — distinguishable from
      a skip by the FAILED status in the output.
"""

import os
import pytest
from weezdom_cli.client import WeezdomClient

pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_LIVE"),
    reason="Live tests skipped. Set RUN_LIVE=1 and WEEZDOM_API_KEY to run.",
)

_BASE_URL = os.getenv("WEEZDOM_BASE_URL", "https://weezdomai-production.up.railway.app")
_API_KEY  = os.getenv("WEEZDOM_API_KEY", "")


@pytest.fixture(scope="module")
def live_client():
    # WeezdomClient.__init__(api_url, api_key, graph_id=_UNSET, timeout=30)
    # verified: weezdom-cli/src/weezdom_cli/client.py:14
    # graph_id=None → no X-Graph-Id header sent; server uses tenant's default graph
    return WeezdomClient(api_url=_BASE_URL, api_key=_API_KEY, graph_id=None)


class TestAuthLive:
    async def test_auth_me_returns_email(self, live_client):
        # GET /auth/me — routes/auth.py:151
        r = await live_client.validate_auth()
        assert isinstance(r.get("email"), str), r


class TestGraphLive:
    async def test_graph_list_returns_list(self, live_client):
        # GET /knowledge-graphs/data/list — routes/knowledge_graphs.py:377
        # Response may be a raw list OR {"graphs": [...]} — cli.py:330 dual-shape
        r = await live_client.get("/knowledge-graphs/data/list")
        assert not isinstance(r, dict) or "error" not in r, f"Server error: {r}"
        items = r if isinstance(r, list) else r.get("graphs", [])
        assert isinstance(items, list), r


class TestContentLive:
    async def test_content_library_shape(self, live_client):
        # GET /content/library — routes/content_library.py:443
        r = await live_client.get("/content/library")
        assert "items" in r and isinstance(r["items"], list), r


class TestOntologyLive:
    async def test_ontology_list_is_array(self, live_client):
        # GET /ontologies/list — routes/ontologies.py:119
        # SC-1: response is raw JSON array (not dict-wrapped)
        r = await live_client.get("/ontologies/list")
        assert isinstance(r, list), r


class TestWorkspaceLive:
    async def test_workspace_info_shape(self, live_client):
        # GET /insights/workspaces — routes/tenant.py:278
        r = await live_client.get("/insights/workspaces")
        assert "workspaces" in r and isinstance(r["workspaces"], list), r


class TestSearchLive:
    async def test_search_returns_facts_list(self, live_client):
        # POST /tools/search — routes/tools.py:91
        r = await live_client.post(
            "/tools/search",
            json={"query": "knowledge", "num_results": 3},
        )
        assert "facts" in r and isinstance(r["facts"], list), r

    async def test_topics_shape(self, live_client):
        # GET /tools/topics — routes/tools.py:254
        r = await live_client.get("/tools/topics", params={"limit": 5})
        assert "total_entities" in r, r
        assert isinstance(r["total_entities"], int), r
        assert "by_type" in r, r
        assert "sample_entities" in r, r
