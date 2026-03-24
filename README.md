# weezdom-cli

Terminal access to [Weezdom.ai](https://weezdomai-production.up.railway.app) knowledge graphs. Search, explore entities, manage content, and integrate with AI coding assistants.

## Install

```bash
pip install weezdom-cli
```

## Quick Start

```bash
# 1. Authenticate (generate a personal API key at Settings > CLI Access)
weezdom auth login

# 2. Select a knowledge graph
weezdom graph list
weezdom graph use <graph-id>

# 3. Search
weezdom search "progressive profiling"

# 4. Explore an entity
weezdom entity "Progressive Profiling"
weezdom entity "Progressive Profiling" --related
```

## Commands

### Authentication

```bash
weezdom auth login       # Enter your personal API key
weezdom auth logout      # Clear stored credentials
weezdom auth status      # Show current auth state
```

### Search & Query

```bash
weezdom search <query> [--limit N]              # Search for facts
weezdom entity <name> [--related]               # Entity details or related entities
weezdom topics [--type TYPE] [--limit N]        # List entities/topics
weezdom sources <query> [--limit N]             # Find source documents
```

### Content Management

```bash
weezdom content list [--type TYPE] [--status STATUS] [--tag TAG]
weezdom content add <url> [<url>...] [--tag TAG]    # Ingest URLs
weezdom content upload <file> [--tag TAG]            # Upload file
weezdom content view <id>                            # View content text
weezdom content delete <id> [--force]                # Delete (with confirmation)
weezdom content extract <id> [--graph ID]            # Trigger extraction
```

### Graph Management

```bash
weezdom graph list                   # List available graphs
weezdom graph use <graph-id>         # Set active graph
weezdom graph info [graph-id]        # Graph details
weezdom graph pipeline [graph-id]    # Pipeline/job status
```

### Configuration

```bash
weezdom config show              # Display current config
weezdom config set <key> <value> # Set a value
```

## Output Formats

All commands support `--format`:

```bash
weezdom search "query" --format json    # JSON (pipe to jq)
weezdom search "query" --format table   # Rich table (default)
weezdom search "query" --format text    # Plain text
```

## Claude Code Integration

Add Weezdom as a tool source for Claude Code by adding to your project's configuration:

```bash
# Search your knowledge graph from Claude Code
weezdom search "your query" --format json

# Look up specific entities
weezdom entity "Entity Name" --format json

# List available topics
weezdom topics --format json
```

The `--format json` flag outputs structured JSON suitable for AI agent consumption.

## Configuration

Config stored at `~/.weezdom/config.yaml`:

```yaml
api_url: https://weezdomai-production.up.railway.app
api_key: wdm_...
active_graph_id: <graph-uuid>
output_format: table
```

## Development

```bash
git clone https://github.com/code-samurai/weezdom-cli.git
cd weezdom-cli
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT
