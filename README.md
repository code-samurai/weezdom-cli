# weezdom-cli

Terminal access to [Weezdom.ai](https://weezdomai-production.up.railway.app) knowledge graphs. Search facts, explore entities, manage content, and integrate with AI coding assistants.

## Install

```bash
pip install weezdom-cli
```

Requires Python 3.10+.

## Quick Start

```bash
# 1. Get a personal API key from Settings > API Keys in the Weezdom web app
weezdom auth login

# 2. Select a knowledge graph
weezdom graph list
weezdom graph use <graph-id>

# 3. Start querying
weezdom search "revenue strategy"
weezdom entity "Revenue Brain"
weezdom topics
```

## Commands

### Authentication

```bash
weezdom auth login       # Authenticate with your personal API key (wdm_...)
weezdom auth logout      # Revoke key and clear stored credentials
weezdom auth status      # Show current auth state and active graph
```

### Search & Query

```bash
weezdom search <query> [--limit N]              # Search for facts across the graph
weezdom entity <name> [--related]               # Entity details or related entities
weezdom topics [--type TYPE] [--limit N]        # List entity types and top entities
weezdom sources <query> [--limit N]             # Find source documents for a query
weezdom batch <query>... [--limit N]            # Run multiple queries in parallel
weezdom property-search <prop> [--value V] [--type T] [--limit N]  # Filter entities by property
```

### Graph Traversal

```bash
weezdom paths <source> <target> [--depth N]            # Shortest paths between two entities
weezdom neighborhood <name> [--depth N] [--limit N]    # N-hop subgraph around an entity
```

### Workspaces

```bash
weezdom workspace info                              # List all workspaces with graph/entity counts
weezdom workspace search <query> [-w WORKSPACE_ID] [--limit N]  # Search across all graphs in a workspace
```

### Ontologies

Two authoring paths share the `ontology` group:

- **Deep JSON document** (`import` / `save` / `publish`) — the same `ontology_versions` document Wizard, Chat, MCP, and Import write. Import and save write **drafts**. Publish makes that draft the live ontology version and does **not** materialise (no FalkorDB, Weaviate, or `graph_publish`). Materialise stays a separate server path and is not a command here.
- **Autonomous build** (`suggest` / `create` / `build` / `score` / `improve`) — template, spec, and server-side AI build. Use this when you do not already have a JSON document.

Authoring needs an **unscoped personal admin or editor** key (`weezdom auth login`, or `WEEZDOM_API_KEY`). A viewer key, a Hermes key, or a workspace reader key cannot author. `WEEZDOM_BASE_URL` overrides the stored `api_url` when set.

```bash
weezdom ontology import --file spec.json [--name NAME]              # Create a draft ontology from JSON
weezdom ontology import --file spec.json --ontology-id <id>         # New draft on an existing ontology
weezdom ontology save --ontology-id <id> --file spec.json           # Same draft write as import onto an existing id
weezdom ontology publish --ontology-id <id> [--version-id <id>]     # Live version only; does not materialise

weezdom ontology list                                               # List ontologies with version count and quality score
weezdom ontology suggest "<description>" [--goal TEXT]...           # Generate a scored ontology template (no DB write)
weezdom ontology create <name> [--spec FILE|-]                      # Create ontology from a suggest spec (file or stdin)
weezdom ontology build <name> "<description>" [--goal TEXT]... [--iterations N]  # Autonomous AI build (~1–4 min, polls until done)
weezdom ontology build-status <job_id>                              # Check status of a build job (use after timeout/interruption)
weezdom ontology score <id>                                         # Show quality score and gaps
weezdom ontology improve <id> --updates-file F                      # Apply updates from JSON file (- for stdin)
weezdom ontology delete <id> [--force]                              # Delete ontology (must not be referenced by graphs)
```

Pipe `suggest` into `create` for a two-step workflow:
```bash
weezdom ontology suggest "Track SaaS pricing metrics" --goal "find patterns" > spec.json
weezdom ontology create "Revenue Brain" --spec spec.json
```

Or let the AI do everything in one command:
```bash
weezdom ontology build "Revenue Brain" "Track SaaS pricing" --goal "find patterns" --iterations 3
```

Deep JSON import (draft, then publish the document — not the graph):
```bash
weezdom ontology import --file spec.json --name "Practice operations"
weezdom ontology save --ontology-id <ontology-id> --file spec.json
weezdom ontology publish --ontology-id <ontology-id>
```

`--format json` prints the API object. Validation errors exit 2. A 403 from a viewer, Hermes, or workspace reader key exits 1 and says an unscoped personal admin or editor key is required.

### Content Management

```bash
weezdom content list [--type TYPE] [--status STATUS] [--tag TAG] [--limit N]
weezdom content add <url> [<url>...] [--tag TAG]     # Ingest URLs into knowledge base
weezdom content upload <file> [--tag TAG]             # Upload a file (PDF, DOCX, etc.)
weezdom content view <id>                             # View the text of a content item
weezdom content delete <id> [--force]                 # Delete (prompts for confirmation)
weezdom content extract <id> [<id>...] [--graph ID]  # Trigger extraction to a graph
```

### Graph Management

```bash
weezdom graph list                   # List all available graphs
weezdom graph use <graph-id>         # Set the active graph
weezdom graph info [graph-id]        # Graph details, entity count, ontology
weezdom graph pipeline [graph-id]    # Pipeline and job status
```

### Configuration

```bash
weezdom config show                    # Display current config (API key masked)
weezdom config set <key> <value>       # Set a config value
```

Available keys: `api_url`, `active_graph_id`, `output_format`.
> Note: set `api_key` via `weezdom auth login` — never via `config set` (shell history risk).

## Output Formats

All query commands support `--format`:

```bash
weezdom search "query" --format json    # JSON — pipe to jq, feed to AI agents
weezdom search "query" --format table   # Rich table (default)
weezdom search "query" --format text    # Plain text
```

## Claude Code / AI Agent Integration

weezdom-cli is designed as a data source for AI coding assistants. Use `--format json` for structured output:

```bash
# In Claude Code, Cursor, or any MCP-aware tool:
weezdom search "progressive profiling" --format json
weezdom entity "Revenue Brain" --format json
weezdom topics --format json
```

Alternatively, the Weezdom MCP server provides the same data directly via the Model Context Protocol — see the web app's MCP Integration settings.

## Configuration File

Stored at `~/.weezdom/config.yaml` with `0600` permissions (owner read/write only):

```yaml
api_url: https://weezdomai-production.up.railway.app
api_key: wdm_...
active_graph_id: <graph-uuid>
output_format: table
```

See [SECURITY.md](SECURITY.md) for credential storage details.

## Development

```bash
git clone https://github.com/code-samurai/weezdom-cli.git
cd weezdom-cli
pip install -e ".[dev]"
pytest tests/ -v
```

### Live Smoke Tests

To verify response-shape contracts against the real API:

```bash
RUN_LIVE=1 WEEZDOM_API_KEY=wdm_<your-key> pytest tests/test_live_smoke.py -v -s
```

Optional — override the default production URL:

```bash
WEEZDOM_BASE_URL=https://... RUN_LIVE=1 WEEZDOM_API_KEY=wdm_<your-key> pytest tests/test_live_smoke.py -v -s
```

Prerequisites: tenant account must have at least one active knowledge graph. All 7 tests skip automatically in standard CI (`RUN_LIVE` is not set).

## License

MIT
