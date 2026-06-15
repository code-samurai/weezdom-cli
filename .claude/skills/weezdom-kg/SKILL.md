---
name: weezdom-kg
description: Use when working with Weezdom knowledge graphs — querying entities, writing facts, bootstrapping graphs, or managing ontologies. Covers CLI (weezdom commands), MCP workspace tools (ws_*), and REST API with wdm_ API keys.
compatibility:
  cli: pip install weezdom-cli
  mcp: workspace_mcp at /mcp/workspace/{id}/mcp
  rest: X-API-Key header required (NOT Authorization Bearer)
---

# weezdom-kg

Enable AI agents to use Weezdom as a knowledge layer — querying, writing, and bootstrapping graphs via three access paths: CLI, MCP workspace tools, and REST API.

## Choose Your Access Path

| Path | Best for | Write support |
|------|----------|---------------|
| **CLI** (`weezdom`) | Local dev, exploration, content management | Read + manage only (no entity writes) |
| **MCP** (`ws_*` tools) | Claude agents, Claude Desktop | Full — read, write, bootstrap, ontology |
| **REST** (HTTP) | Programmatic agents, non-Claude runtimes | Full — read, write, bootstrap, ontology |

Entity writes (adding facts to a graph) require MCP or REST. The CLI covers search, entity lookup, content ingestion, ontology management, and graph administration.

---

## Setup

### CLI

```bash
pip install weezdom-cli
weezdom auth login          # prompts for your wdm_ API key (get one from Settings → API Keys in the web app)
weezdom graph list          # find your graph-id
weezdom graph use <graph-id>
```

Key is stored at `~/.weezdom/config.yaml` (mode 0600). Run `weezdom auth status` to verify. Default output format is `table` — use `--format json` for agent/pipe use.

### MCP

Connect to the workspace endpoint — **not** the single-graph `/mcp` endpoint:
```
/mcp/workspace/<workspace_id>/mcp
```

The workspace ID is visible in the Weezdom dashboard URL and Settings → Workspace.

Claude Code `~/.claude/claude.json`:
```json
{
  "mcpServers": {
    "weezdom": {
      "url": "https://<your-instance>/mcp/workspace/<workspace_id>/mcp",
      "headers": { "X-API-Key": "wdm_<your-key>" }
    }
  }
}
```

Once connected, call `ws_get_workspace_info` first to confirm connectivity and discover available graphs.

### REST

```
Base URL: https://<your-instance>
Required headers:
  X-API-Key: wdm_<your-key>
  X-Graph-Id: <graph-uuid>        # for graph-scoped endpoints
  Content-Type: application/json
```

**Critical gotcha:** `wdm_` keys go in `X-API-Key`, NOT `Authorization: Bearer wdm_...`. The Bearer header is reserved for Supabase JWTs. A `wdm_` key in Bearer returns 401 — identical to missing auth.

Create a key (one-time setup — requires a Supabase JWT, see [REST Reference](references/rest-reference.md)):
```bash
curl -X POST https://<instance>/settings/api-keys/personal \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"name":"agent-key"}'
# Returns {"key":"wdm_..."} — shown ONCE, store immediately
```

---

## Reading the Graph

### CLI

```bash
weezdom search "query"                              # semantic + graph search
weezdom search "query" --limit 20 --format json     # agent-friendly output
weezdom entity "Entity Name"                        # entity detail
weezdom entity "Entity Name" --related              # entity + relationships
weezdom topics                                      # discover entity types
weezdom sources "query"                             # source document citations
weezdom neighborhood "Entity Name" --depth 2        # N-hop neighborhood
weezdom paths "Entity A" "Entity B"                 # graph paths between entities
weezdom workspace search "query"                    # search all graphs in workspace
weezdom workspace search "query" -w <workspace-id>  # target a specific workspace
# --format json on all query commands; default is table
```

### MCP

Start with workspace discovery on every session:
```
ws_get_workspace_info             → workspace structure + graph roles
ws_list_topics                    → entity types across all graphs
ws_search(query)                  → semantic + graph search
ws_hybrid_search(query)           → hybrid KG + vector search
ws_get_entity(entity_name)        → entity detail [subject graphs only]
ws_get_related_entities(entity_name, relationship_type)
ws_find_sources(query)            → source citations (all graph roles)
ws_get_entity_neighborhood(entity_name, depth, limit)   [subject graphs only]
ws_get_neighborhood(graph_id, entity_name, depth)       [any graph role]
ws_search_by_property(property_name, property_value)    [all graph roles]
ws_find_graph_paths(source, target)    [first subject graph only]
ws_get_observations()                  [first subject graph only]
```

For entities in intelligence or reference graphs, use `ws_get_neighborhood(graph_id, name)` — `ws_get_entity` searches subject graphs only.

### REST

```
POST /search/hybrid           {query, limit}   X-Graph-Id header required
POST /search                  {query, format:"agent"}
POST /batch-query             {queries:[...]}   up to 20 queries
GET  /tools/entity/{name}
GET  /tools/entity/{name}/related
GET  /tools/entity/{name}/neighborhood?depth=2
GET  /tools/topics
GET  /tools/observations
POST /tools/sources           {query}
GET  /tools/paths?source=X&target=Y
POST /search/workspace        {query, workspace_id}   (no X-Graph-Id needed)
```

---

## Writing to Intelligence Graphs

Only **intelligence-role graphs** accept direct entity writes. Subject and reference graphs return 403.

> **CLI users:** The CLI has no entity-write commands. Switch to MCP (`ws_write_entity`, `ws_write_relationship`) or REST (`POST /knowledge-graphs/data/{id}/entities`) for this operation.

### MCP

Required sequence:
1. `ws_list_intelligence_graphs` — confirms writable graphs exist and returns `graph_id`
2. `ws_get_writable_types(graph_id)` — get valid entity + relationship types (422 if you skip this)
3. `ws_write_entity(graph_id, name, entity_type, description?, properties?)`
4. `ws_write_relationship(graph_id, source_entity, target_entity, relationship_type, fact?)`

```
ws_delete_entity(graph_id, entity_name)
ws_delete_relationship(graph_id, source, target, relationship_type)
```

`ws_write_relationship` creates entity stubs if source/target don't exist yet.

### REST

```
GET  /knowledge-graphs/data/{id}/entity-types    → valid entity types
POST /knowledge-graphs/data/{id}/entities        {name, entity_type, description}
POST /knowledge-graphs/data/{id}/relationships   {source, target, relationship_type, fact}
DELETE /knowledge-graphs/data/{id}/entities/{name}
DELETE /knowledge-graphs/data/{id}/relationships/{src}/{tgt}/{rel}
```

`graph_id` is in the URL path — no `X-Graph-Id` header needed for these endpoints.

---

## Bootstrapping a New Graph

> **CLI users:** The CLI has no graph-create command. Use MCP (`ws_create_graph`) or REST (`POST /knowledge-graphs/data`) to create a graph, then use the CLI for content ingestion (`weezdom content add`, `weezdom content extract`) and ontology management.

Two flows depending on intended graph role:

### Subject graph (content → LLM extraction)

```
MCP:
  ws_list_ontologies                        # quality ≥ 70 required to appear
  ws_create_graph(ontology_id, name, graph_role="subject")
  # link content via Content Library or REST
  ws_publish_graph(graph_id)                # queues extraction jobs
  while not ready:
    ws_get_build_status(graph_id)           # poll until ready=true

REST equivalent:
  POST /knowledge-graphs/data              {ontology_id, name, workspace_id, graph_role:"subject"}
  POST /knowledge-graphs/data/{id}/content {content_item_ids:[...]}
  POST /knowledge-graphs/data/{id}/publish
  GET  /knowledge-graphs/data/{id}/build-status   → poll until ready=true
```

### Intelligence graph (direct write — no publish step)

```
MCP:
  ws_list_ontologies
  ws_create_graph(ontology_id, name, graph_role="intelligence")
  ws_get_writable_types(graph_id)
  ws_write_entity(...)    # ready immediately

REST equivalent:
  POST /knowledge-graphs/data              {ontology_id, name, workspace_id, graph_role:"intelligence"}
  GET  /knowledge-graphs/data/{id}/entity-types
  POST /knowledge-graphs/data/{id}/entities    # ready immediately
```

---

## Ontology Management

An ontology defines the entity and relationship types for a graph. Ontologies scoring below 70/100 are excluded from `ws_list_ontologies` — use `ws_score_ontology` to check and `ws_improve_ontology` to raise the score.

### MCP

```
ws_suggest_ontology(description, goals?)    → config_template + scoring_rubric (nothing persisted)
ws_create_ontology(name, config)            → {ontology_id, quality, gaps}
ws_score_ontology(ontology_id)              → {overall_score, grade, is_buildable, gaps}
ws_improve_ontology(ontology_id, improvements) → {new_version_id, quality}
ws_delete_ontology(ontology_id)

# Autonomous build (1–4 min, async):
ws_build_ontology(name, description, goals?) → {job_id}
poll ws_get_ontology_build_status(job_id) every 5s until status=="completed"
```

### CLI

```bash
weezdom ontology list
weezdom ontology suggest "my domain" [--goal "find patterns"]
weezdom ontology create "Name" --spec spec.json   # pipe from suggest: suggest "..." > spec.json
weezdom ontology build "Name" "description" [--goal "..."] [--iterations N]
weezdom ontology build-status <job-id>
weezdom ontology score <ontology-id>
weezdom ontology improve <ontology-id> --updates-file updates.json
weezdom ontology delete <ontology-id> [--force]

# Two-step workflow:
weezdom ontology suggest "Track SaaS metrics" --goal "find patterns" > spec.json
weezdom ontology create "Revenue Brain" --spec spec.json
```

### REST

```
GET    /ontologies                          → list (quality ≥ 70 only)
POST   /ontologies                          {name, config}  → {ontology_id, quality, gaps}
POST   /ontologies/suggest                  {description, goals?}
GET    /ontologies/{id}/score               → {overall_score, grade, gaps}
POST   /ontologies/{id}/improve             {improvements}  → {new_version_id, quality}
POST   /ontologies/build                    {name, description, goals?}  → {job_id}
GET    /ontologies/build-status/{job_id}    → {status, ontology_id?}
DELETE /ontologies/{id}
```

> **MCP users:** if you need to manage ontologies from a non-CLI runtime, use these REST endpoints or the MCP `ws_*` ontology tools above.

---

## Error Reference

| Status | Message | Cause | Fix |
|--------|---------|-------|-----|
| 401 | Authentication required | Missing header | Add `X-API-Key: wdm_<key>` |
| 401 | Invalid or expired token | `wdm_` key in Bearer slot | Move key to `X-API-Key` header |
| 403 | Tenant is pending approval | Account not approved | Contact workspace admin |
| 403 | Graph is not an intelligence graph | Writing to subject/reference graph | Use `ws_list_intelligence_graphs` first |
| 403 | Requires role: admin, editor | User role is viewer | Grant admin/editor role in workspace settings |
| 422 | (validation error) | Unknown `entity_type` | Call `ws_get_writable_types` first |
| 409 | (on ontology create) | Name conflict | Use returned `existing_id` |

---

## Gotchas

1. **X-API-Key vs Authorization** — `wdm_` keys go in `X-API-Key`, never `Authorization: Bearer`. Both failure modes return the same 401.
2. **Intelligence graphs only for writes** — `ws_write_entity` and REST entity endpoints return 403 for subject/reference graphs. Confirm graph role with `ws_get_workspace_info` or `ws_list_intelligence_graphs`.
3. **Fetch writable types before every write session** — submitting an unknown `entity_type` returns 422. Always call `ws_get_writable_types(graph_id)` first.
4. **`ws_get_entity` is subject-graph-only** — for intelligence or reference graph entities, use `ws_get_neighborhood(graph_id, entity_name)` instead.
5. **Ontology quality gate** — `ws_list_ontologies` hides ontologies scoring below 70. Check with `ws_score_ontology`; raise with `ws_improve_ontology`.
6. **API key shown once** — the full `wdm_` key is returned only at creation time (`POST /settings/api-keys/personal`). Store it immediately.

---

## Reference Files

- [CLI Reference](references/cli-reference.md) — full command table with all flags and output shapes
- [MCP Reference](references/mcp-reference.md) — all 33 ws_* tools with parameters, return shapes, and graph-role restrictions
- [REST Reference](references/rest-reference.md) — full REST endpoint list with request/response shapes and API key creation flow
