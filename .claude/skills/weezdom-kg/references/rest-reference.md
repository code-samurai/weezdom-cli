# REST Reference — Weezdom API

**Base URL:** `https://<your-instance>`
**Auth header:** `X-API-Key: wdm_<key>` (see §Auth below)
**Graph context:** `X-Graph-Id: <graph-uuid>` header (graph-scoped endpoints)

---

## Auth

### Critical: X-API-Key vs Authorization

```
CORRECT:   X-API-Key: wdm_<your-key>
WRONG:     Authorization: Bearer wdm_<your-key>   ← returns same 401 as no auth
```

The `Authorization: Bearer` slot is reserved for Supabase JWTs. A `wdm_` key in Bearer is treated as a malformed JWT.

### Create an API Key

Requires a one-time Supabase JWT (see §Getting a Supabase JWT below).

```bash
curl -X POST https://<instance>/settings/api-keys/personal \
  -H "Authorization: Bearer <supabase-jwt>" \
  -H "Content-Type: application/json" \
  -d '{"name":"agent-key"}'
```

Response:
```json
{
  "key": "wdm_<base62-body>",
  "id": "<uuid>",
  "key_prefix": "wdm_xxxx",
  "name": "agent-key",
  "created_at": "...",
  "last_used_at": null
}
```

**The full key is shown once.** Store it immediately. It is not retrievable afterward.

### Getting a Supabase JWT (one-time, for key creation)

```python
import requests

# Step 1: get anon key
config = requests.get(f"{BASE_URL}/auth/config").json()
anon_key = config["supabase_anon_key"]

# Step 2: exchange credentials for JWT
resp = requests.post(
    f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
    headers={"apikey": anon_key, "Content-Type": "application/json"},
    json={"email": EMAIL, "password": PASSWORD},
)
jwt = resp.json()["access_token"]

# Step 3: create API key
resp = requests.post(
    f"{BASE_URL}/settings/api-keys/personal",
    headers={"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"},
    json={"name": "agent-key"},
)
api_key = resp.json()["key"]  # store this — shown once only
```

Once you have `api_key`, use `X-API-Key: <api_key>` for all requests. API keys don't expire (unlike Supabase JWTs).

### Using an API Key

```python
headers = {
    "X-API-Key": "wdm_<your-key>",
    "X-Graph-Id": "<graph-uuid>",       # required for graph-scoped endpoints
    "Content-Type": "application/json",
}
```

### Error Shapes

| Status | Body | Cause |
|--------|------|-------|
| 401 | `{"detail":"Authentication required"}` | Missing header |
| 401 | `{"detail":"Invalid or expired token"}` | `wdm_` key in Bearer slot |
| 403 | `{"detail":"Tenant is pending approval"}` | Account not approved |
| 403 | `{"detail":"Graph is not an intelligence graph"}` | Writing to subject/reference graph |
| 403 | `{"detail":"Requires role: admin, editor. You have: viewer"}` | Insufficient role |
| 422 | (validation error) | Unknown `entity_type` |

---

## Search and Query

All search endpoints require `X-Graph-Id` header (except `/search/workspace`).

### POST /search
```json
request:  {"query": "...", "limit": 10, "format": "agent"}
response: {"query", "results": [{"content", "score", "source", "metadata"}], "context_tokens", "cursor"}
```
`format: "agent"` returns a simplified shape optimised for LLM consumption.

### POST /search/hybrid
```json
request:  {"query": "...", "limit": 10}
response: {"query_type", "sources_queried", "results": [...]}
```
Best general-purpose search — routes by query intent across KG + vectors.

### POST /search/workspace
No `X-Graph-Id` needed.
```json
request:  {"query": "...", "workspace_id": "<uuid>"}
response: {"query", "results": [...], "graphs_searched": [...]}
```

### POST /batch-query
Up to 20 queries, parallel execution.
```json
request:  {"queries": ["q1", "q2", ...]}
response: [{"query", "results": [...]}, ...]
```

### POST /retrieve
```json
request:  {"query": "...", "include_content": false}
response: {"results": [...]}  # KG + PageIndex segments; include_content=true fetches S3 blob
```

### POST /tools/search
```
X-Graph-Id required. Optional query param: ?format=agent
body: {"query": "..."}
```

### GET /tools/entity/{name}
Returns entity detail. 404 if not found.

### GET /tools/entity/{name}/related
```
query params: relationship_types=<comma-separated>
```

### GET /tools/entity/{name}/neighborhood
```
query params: depth=2  (1-3)
```

### GET /tools/paths
```
query params: source=<name>&target=<name>&max_depth=3
```

### POST /tools/sources
```json
request: {"query": "..."}
response: source document segments
```

### GET /tools/topics
Returns entity types defined in the graph ontology.

### POST /tools/properties/search
```json
request: {"property_name": "...", "property_value": "..."}
```

### GET /tools/observations
Numeric property observations.

---

## Writing to Intelligence Graphs

All write endpoints enforce `_assert_writable_graph()`. 403 if `graph_role != "intelligence"`.

`graph_id` is in the URL path — no `X-Graph-Id` header needed.

### GET /knowledge-graphs/data/{graph_id}/entity-types
Discover valid entity types before writing. 422 if you submit an unknown type.

### POST /knowledge-graphs/data/{graph_id}/entities
```json
request: {"name": "Entity Name", "entity_type": "ValidType", "description": "..."}
```
Returns created entity. Guards: intelligence graph only, entity_type must be in ontology.

### DELETE /knowledge-graphs/data/{graph_id}/entities/{name}

### POST /knowledge-graphs/data/{graph_id}/relationships
```json
request: {"source": "Entity A", "target": "Entity B", "relationship_type": "RELATES_TO", "fact": "..."}
```
Creates entity stubs if source/target don't exist.

### DELETE /knowledge-graphs/data/{graph_id}/relationships/{src}/{tgt}/{rel}

### POST /knowledge-graphs/data/{graph_id}/synthesize
Async LLM synthesis from a subject graph into this intelligence graph.
```json
request:  {"subject_graph_id": "<uuid>"}
response: {"job_id": "..."}  # poll build-status
```

---

## Bootstrapping Graphs

### POST /knowledge-graphs/data
Create a graph.
```json
request:  {"ontology_id": "...", "name": "My Graph", "workspace_id": "...", "graph_role": "subject"}
response: {"graph_id": "...", "name", "graph_role", "status"}
```
`graph_role`: `"subject"` | `"intelligence"` | `"reference"`

### POST /knowledge-graphs/data/{id}/content
Link content items to a graph (subject graphs).
```json
request: {"content_item_ids": ["...", "..."]}
```

### GET /knowledge-graphs/data/{id}/publish-estimate
Cost + time estimate before publishing.

### POST /knowledge-graphs/data/{id}/publish
Trigger extraction (subject graphs only).
```json
request: {"incremental": false}  # optional
```

### POST /knowledge-graphs/data/{id}/rebuild
Wipe and re-queue all content for extraction.

### POST /knowledge-graphs/data/{id}/cancel-publish
Cancel queued extraction jobs.

---

## Graph Status Endpoints

### GET /knowledge-graphs/data/list
```
optional header: X-Workspace-Id to filter by workspace
response: list of graphs with status, entity counts
```

### GET /knowledge-graphs/data/{id}
Graph detail including `stale` flag.

### GET /knowledge-graphs/data/{id}/build-status
```json
response: {"ready": bool, "ontology": {...}, "content": {...}, "extraction": {...}}
```
Poll until `ready == true`.

### GET /knowledge-graphs/data/{id}/pipeline
Job counts + last 500 jobs.

### GET /knowledge-graphs/data/{id}/health
Entity/relationship coverage vs ontology definition.

### GET /knowledge-graphs/data/{id}/summary
Type breakdown + top entities.

---

## Bootstrap Flows

### Subject graph (content → extraction)
```python
# 1. create
resp = requests.post(f"{BASE}/knowledge-graphs/data", headers=headers,
    json={"ontology_id": oid, "name": "My Graph", "workspace_id": wid, "graph_role": "subject"})
graph_id = resp.json()["graph_id"]

# 2. link content
requests.post(f"{BASE}/knowledge-graphs/data/{graph_id}/content", headers=headers,
    json={"content_item_ids": ["..."]})

# 3. publish
requests.post(f"{BASE}/knowledge-graphs/data/{graph_id}/publish", headers=headers)

# 4. poll
while True:
    status = requests.get(f"{BASE}/knowledge-graphs/data/{graph_id}/build-status",
        headers=headers).json()
    if status["ready"]:
        break
    time.sleep(10)
```

### Intelligence graph (direct write)
```python
# 1. create
resp = requests.post(f"{BASE}/knowledge-graphs/data", headers=headers,
    json={"ontology_id": oid, "name": "My Intel Graph", "workspace_id": wid, "graph_role": "intelligence"})
graph_id = resp.json()["graph_id"]

# 2. discover valid types (no X-Graph-Id needed — graph_id in path)
key_headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
types = requests.get(f"{BASE}/knowledge-graphs/data/{graph_id}/entity-types",
    headers=key_headers).json()

# 3. write
requests.post(f"{BASE}/knowledge-graphs/data/{graph_id}/entities", headers=key_headers,
    json={"name": "My Entity", "entity_type": types[0], "description": "..."})
```
