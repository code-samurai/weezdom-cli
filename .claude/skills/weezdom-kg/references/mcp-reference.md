# MCP Reference — workspace_mcp

**Endpoint:** `/mcp/workspace/{workspace_id}/mcp`
**Auth:** `X-API-Key: wdm_<key>` header
**Tool count:** 33 tools + 1 resource

Start every session with `ws_get_workspace_info` to discover workspace structure and graph roles.

---

## Read Tools

### ws_get_workspace_info
Returns workspace structure — **call this first**.
- Returns: `{workspace_id, workspace_name, graphs: [{graph_id, graph_name, graph_role, capabilities}], graph_count}`
- Scope: all graph roles

### ws_search
General semantic + graph search.
- Required: `query: str`
- Optional: `limit: int` (default 10)
- Returns: results tagged with `_graph_id, _graph_name, _graph_role`
- Scope: all graph roles

### ws_hybrid_search
Hybrid KG + vector search.
- Required: `query: str`
- Optional: `limit: int` (default 15)
- Returns: same shape as ws_search
- Scope: all graph roles

### ws_get_entity
Deep-dive on a specific entity.
- Required: `entity_name: str`
- Optional: `graph_id: str`
- Returns: `{name, entity_type, summary, definition, properties, facts, relationships, sources}` + `_graph_id, _graph_name`
- **Scope: subject graphs only** — use `ws_get_neighborhood(graph_id, name)` for intelligence/reference graphs

### ws_get_related_entities
Entities connected to a named entity.
- Required: `entity_name: str`
- Optional: `relationship_type: str` (single type, not a list)
- Returns: related entities with `{name, entity_type, relationship, direction}`
- Scope: subject graphs only

### ws_find_sources
Source document citations.
- Required: `query: str`
- Returns: document segments grouped by document, with timestamp context
- Scope: all graph roles

### ws_list_topics
Discover entity types.
- Returns: all entity types across graphs, deduped by name
- Scope: all graph roles

### ws_list_communities
Thematic clusters.
- Scope: **subject graphs only**

### ws_find_graph_paths
Graph paths between two entities.
- Required: `source: str`, `target: str`
- Scope: **first subject graph only** (may miss entities in other graphs)

### ws_get_entity_neighborhood
N-hop neighborhood traversal.
- Required: `entity_name: str`
- Optional: `depth: int` (default 1), `limit: int` (default 50)
- Scope: **subject graphs only**

### ws_get_neighborhood
N-hop neighborhood — any graph role.
- Required: `graph_id: str`, `entity_name: str`
- Optional: `depth: int` (default 2), `limit: int` (default 50)
- Scope: **any graph role** — use this for intelligence/reference graph traversal

### ws_search_by_property
Search by property value.
- Required: `property_name: str`, `property_value: str` (both required — unlike single-graph version)
- Scope: all graph roles

### ws_get_observations
Numeric property observations.
- Scope: **first subject graph only**, limit=100

---

## Write Tools (intelligence graphs only)

All write tools enforce `graph_role == "intelligence"`. Returns 403 for subject/reference graphs.

### ws_list_intelligence_graphs
Discover writable graphs.
- Returns: `{intelligence_graphs: [{graph_id, graph_name}], count}`
- Call before any write to confirm writable graphs exist

### ws_get_writable_types
Fetch valid types before writing.
- Required: `graph_id: str`
- Returns: `{entity_types: [...], relationship_types: [...]}`
- **Must call before ws_write_entity** — unknown type returns 422
- Guard: `graph_role == "intelligence"` required

### ws_write_entity
Add or update an entity.
- Required: `graph_id: str`, `name: str`, `entity_type: str`
- Optional: `description: str`, `properties: dict`
- Returns: `{status, entities_created, entities_updated}`
- Guard: `entity_type` must be in `ws_get_writable_types` result

### ws_write_relationship
Add a relationship between entities.
- Required: `graph_id: str`, `source_entity: str`, `target_entity: str`, `relationship_type: str`
- Optional: `fact: str`
- Returns: `{status, entities_created, entities_updated, relationships_written}`
- Creates entity stubs if source/target don't exist yet

### ws_delete_entity
- Required: `graph_id: str`, `entity_name: str`
- Returns: `{status: "deleted", deleted: bool}`

### ws_delete_relationship
- Required: `graph_id: str`, `source_entity: str`, `target_entity: str`, `relationship_type: str`
- Returns: `{status: "deleted", edges_removed: int}`

---

## Bootstrap Tools

### ws_list_ontologies
Available ontologies for graph creation.
- Returns: ontologies with `quality_score >= 70`
- **Quality gate:** ontologies scoring < 70 are excluded; use `ws_score_ontology` to check, `ws_improve_ontology` to raise score

### ws_create_graph
Create a new graph.
- Required: `ontology_id: str`, `name: str`
- Optional: `graph_role: str` (default "subject"), `workspace_id: str`
- Returns: `{graph_id, name, graph_role, ontology_version_id, status}`
- For intelligence graph: ready for writes immediately (no publish step)
- For subject graph: must link content then publish

### ws_publish_graph
Trigger extraction (subject graphs only).
- Required: `graph_id: str`
- Returns: `{status, jobs_queued, mode, warning?}`
- Guard: subject graphs only — returns error for intelligence graphs

### ws_get_build_status
Poll extraction progress.
- Required: `graph_id: str`
- Returns: `{ontology, content, extraction, incremental, ready: bool}`
- Poll until `ready == true`

---

## Ontology Authoring Tools

### ws_suggest_ontology
Generate a scored ontology template (nothing persisted).
- Required: `description: str`
- Optional: `goals: str`
- Returns: `{recommended_graph_role, config_template, scoring_rubric, graph_architecture, example_hunting_instructions}`

### ws_create_ontology
Persist an ontology.
- Required: `name: str`, `config: dict` (from ws_suggest_ontology output)
- Returns: `{ontology_id, version_id, quality, gaps}` or `{error: "name_conflict", existing_id}`

### ws_score_ontology
Score an existing ontology with actionable improvement gaps.
- Required: `ontology_id: str`
- Returns: `{quality: {overall_score, grade, is_buildable, axes}, gaps: [{criterion, specific_tip, seed_prompt, impact_points}]}`

### ws_improve_ontology
Apply improvements and create a new version.
- Required: `ontology_id: str`, `improvements: dict`
- Returns: `{new_version_id, quality, gaps}`

### ws_delete_ontology
Permanent delete if no graphs reference the ontology.
- Required: `ontology_id: str`

### ws_build_ontology
Autonomous ontology build (async, 1–4 min, 3 Opus LLM calls).
- Required: `name: str`, `description: str`
- Optional: `goals: str`
- Returns: `{job_id, status: "queued"}` immediately
- Poll `ws_get_ontology_build_status` every 5s

### ws_get_ontology_build_status
- Required: `job_id: str`
- Returns: `{job_id, status, result: {ontology_id, version_id, quality, gaps, iterations_used, reached_threshold}, error}`
- `status` values: `"queued"`, `"processing"`, `"completed"`, `"failed"`

---

## Resource

### kg://ontology
Full ontology config dict for the connected workspace.

---

## Tool Sequence Patterns

**Read an existing graph:**
```
ws_get_workspace_info → ws_list_topics → ws_search / ws_hybrid_search → ws_get_entity
```

**Write to an intelligence graph:**
```
ws_list_intelligence_graphs → ws_get_writable_types → ws_write_entity → ws_write_relationship
```

**Bootstrap a subject graph:**
```
ws_list_ontologies → ws_create_graph(role=subject) → [link content] → ws_publish_graph → poll ws_get_build_status
```

**Bootstrap an intelligence graph:**
```
ws_list_ontologies → ws_create_graph(role=intelligence) → ws_get_writable_types → ws_write_entity
```

**Create a new ontology:**
```
ws_suggest_ontology → ws_create_ontology → ws_score_ontology → (if < 70) ws_improve_ontology
```

**Build an ontology autonomously:**
```
ws_build_ontology → poll ws_get_ontology_build_status every 5s until completed
```
