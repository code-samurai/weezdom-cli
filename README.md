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
```

### Content Management

```bash
weezdom content list [--type TYPE] [--status STATUS] [--tag TAG]
weezdom content add <url> [<url>...] [--tag TAG]    # Ingest URLs into knowledge base
weezdom content upload <file> [--tag TAG]            # Upload a file (PDF, DOCX, etc.)
weezdom content view <id>                            # View the text of a content item
weezdom content delete <id> [--force]                # Delete (prompts for confirmation)
weezdom content extract <id> [--graph ID]            # Trigger extraction to a graph
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

## License

MIT
