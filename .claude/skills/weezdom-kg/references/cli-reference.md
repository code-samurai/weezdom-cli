# CLI Reference — weezdom

**Install:** `pip install weezdom-cli` (Python 3.10+)
**Config:** `~/.weezdom/config.yaml` (mode 0600)
**Output formats:** `table` (default), `json`, `text` — use `--format json` for agent/pipe use

---

## Auth Commands

```bash
weezdom auth login              # prompts for wdm_ API key, stores in config
weezdom auth logout             # revoke key and clear stored credentials
weezdom auth status             # show current auth state and active graph
```

---

## Config Commands

```bash
weezdom config show                           # print current config (API key masked)
weezdom config set api_url <url>              # set base URL
weezdom config set active_graph_id <uuid>     # set default graph for graph-scoped commands
weezdom config set output_format <format>     # table | json | text
```

> Set `api_key` via `weezdom auth login` — never via `config set` (shell history risk).

---

## Search Commands

```bash
weezdom search <query>
weezdom search <query> --limit <n>
weezdom search <query> --format json
```

Returns: semantic + graph search results. Uses `active_graph_id` from config.

---

## Entity Commands

```bash
weezdom entity "<name>"
weezdom entity "<name>" --related
weezdom entity "<name>" --format json
```

Returns: entity detail (definition, summary, properties). `--related` includes relationships.

---

## Topics Command

```bash
weezdom topics
weezdom topics --type <entity-type>
weezdom topics --limit <n>
weezdom topics --format json
```

Returns: entity types defined in the active graph's ontology.

---

## Sources Command

```bash
weezdom sources "<query>"
weezdom sources "<query>" --limit <n>
weezdom sources "<query>" --format json
```

Returns: source document citations backing entities matching the query.

---

## Batch Command

```bash
weezdom batch "<query1>" "<query2>" ...
weezdom batch "<query1>" "<query2>" --limit <n>
weezdom batch "<query1>" "<query2>" --format json
```

Returns: parallel results for multiple queries.

---

## Property Search

```bash
weezdom property-search <property-name>
weezdom property-search <property-name> --value <value>
weezdom property-search <property-name> --value <value> --type <entity-type>
weezdom property-search <property-name> --value <value> --limit <n> --format json
```

Returns: entities whose named property matches the given value. `--type` filters to a specific entity type.

---

## Paths Command

```bash
weezdom paths "<source>" "<target>"
weezdom paths "<source>" "<target>" --depth <n>
weezdom paths "<source>" "<target>" --format json
```

Returns: graph paths between two named entities.

---

## Neighborhood Command

```bash
weezdom neighborhood "<entity>"
weezdom neighborhood "<entity>" --depth <n>
weezdom neighborhood "<entity>" --depth <n> --limit <n>
weezdom neighborhood "<entity>" --format json
```

Returns: N-hop neighborhood around the entity.

---

## Workspace Commands

```bash
weezdom workspace info                                   # list all workspaces with graph/entity counts
weezdom workspace search "<query>"                       # search across all graphs in workspace
weezdom workspace search "<query>" -w <workspace-id>    # target a specific workspace
weezdom workspace search "<query>" --limit <n> --format json
```

---

## Graph Commands

```bash
weezdom graph list                    # list all available graphs
weezdom graph use <graph-id>          # set the active graph
weezdom graph info [graph-id]         # graph details, entity count, ontology
weezdom graph pipeline [graph-id]     # pipeline and job status
```

---

## Content Commands

```bash
weezdom content list [--type TYPE] [--status STATUS] [--tag TAG]
weezdom content add <url> [<url>...] [--tag TAG]    # ingest one or more URLs
weezdom content upload <file> [--tag TAG]            # upload a file (PDF, DOCX, etc.)
weezdom content view <content-id>
weezdom content delete <content-id> [--force]              # prompts for confirmation unless --force
weezdom content extract <id> [<id>...] [--graph ID]    # extract one or more items; uses active_graph_id if --graph omitted
weezdom content list [--limit N]                         # default 20
```

---

## Ontology Commands

```bash
weezdom ontology list
weezdom ontology suggest "<description>" [--goal TEXT]...      # generate scored template (nothing persisted)
weezdom ontology create <name> [--spec FILE|-]                 # create from spec file or stdin
weezdom ontology build <name> "<description>" [--goal TEXT]... [--iterations N]   # autonomous AI build
weezdom ontology build-status <job-id>                         # check async build progress
weezdom ontology score <ontology-id>                           # quality score + improvement gaps
weezdom ontology improve <ontology-id> --updates-file FILE     # apply updates (- for stdin)
weezdom ontology delete <ontology-id> [--force]
```

Pipe `suggest` into `create` for a two-step workflow:
```bash
weezdom ontology suggest "Track SaaS metrics" --goal "find patterns" > spec.json
weezdom ontology create "Revenue Brain" --spec spec.json
```

Or let the AI do everything autonomously (1–4 min, async):
```bash
weezdom ontology build "Revenue Brain" "Track SaaS pricing" --goal "find patterns" --iterations 3
weezdom ontology build-status <job-id>    # poll until status == "completed"
```

`weezdom ontology list` shows only ontologies with quality ≥ 70.

---

## Global Flags

```bash
--format json       JSON output — pipe to jq or feed to AI agents
--format table      rich table (default)
--format text       plain text
--help              command help
--version           print version
```

---

## Notes

- **No entity write commands** — `weezdom` has no equivalent of `ws_write_entity`. Direct entity writes require MCP tools or REST API.
- CLI auth is transparent — no manual header management needed. `weezdom auth login` stores the key; all commands use it automatically.
- `active_graph_id` must be set for graph-scoped commands (search, entity, topics, sources, etc.). Set it with `weezdom config set active_graph_id <uuid>` or `weezdom graph use <uuid>`.
