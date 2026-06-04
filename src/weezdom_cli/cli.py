"""Main CLI entry point — click command groups."""

import asyncio
import json
import sys
from urllib.parse import quote

import click

from weezdom_cli.client import ClickExit, WeezdomClient
from weezdom_cli.output import format_output


def run_async(coro):
    """Run an async coroutine from sync click context."""
    try:
        return asyncio.run(coro)
    except ClickExit as e:
        click.echo(f"Error: {e.message}", err=True)
        sys.exit(1)


def _get_format(ctx) -> str:
    """Resolve output format from context or config default."""
    fmt = ctx.obj.get("format") if ctx.obj else None
    if not fmt:
        from weezdom_cli import config
        fmt = config.get("output_format", "table")
    return fmt


@click.group()
@click.version_option()
@click.option("--format", "output_format", type=click.Choice(["table", "json", "text"]), default=None,
              help="Output format (default: table)")
@click.pass_context
def main(ctx, output_format):
    """Weezdom CLI — terminal access to knowledge graphs."""
    ctx.ensure_object(dict)
    if output_format:
        ctx.obj["format"] = output_format


# -- auth commands --

@main.group()
def auth():
    """Authenticate with Weezdom.ai."""
    pass


@auth.command()
def login():
    """Log in with a personal API key."""
    from weezdom_cli import config

    api_key = click.prompt("Enter your API key (wdm_...)", hide_input=True)
    if not api_key.startswith("wdm_"):
        click.echo("Error: API key must start with 'wdm_'", err=True)
        sys.exit(1)

    click.echo("Validating...")
    client = WeezdomClient(api_key=api_key)
    try:
        user = run_async(client.validate_auth())
        config.set_value("api_key", api_key)
        click.echo(f"Logged in as {user.get('email', 'unknown')}")
    except ClickExit as e:
        click.echo(f"Error: {e.message}", err=True)
        sys.exit(1)


@auth.command()
def logout():
    """Clear stored credentials."""
    from weezdom_cli import config
    config.clear_key("api_key")
    click.echo("Logged out.")


@auth.command()
def status():
    """Show current authentication status."""
    from weezdom_cli import config
    cfg = config.load()
    if cfg.get("api_key"):
        prefix = cfg["api_key"][:8] + "..."
        click.echo(f"Authenticated: {prefix}")
        click.echo(f"API URL: {cfg.get('api_url', 'not set')}")
        if cfg.get("active_graph_id"):
            click.echo(f"Active graph: {cfg['active_graph_id']}")
        else:
            click.echo("No active graph. Run: weezdom graph use <id>")
    else:
        click.echo("Not authenticated. Run: weezdom auth login")


# -- config commands --

@main.group("config")
def config_cmd():
    """View and modify configuration."""
    pass


@config_cmd.command("show")
def config_show():
    """Display current configuration."""
    from weezdom_cli import config
    cfg = config.load()
    for k, v in sorted(cfg.items()):
        if k == "api_key" and v:
            v = v[:8] + "..."
        click.echo(f"{k}: {v}")


@config_cmd.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key, value):
    """Set a configuration value."""
    from weezdom_cli import config
    if key == "api_url" and not value.startswith("https://"):
        raise click.ClickException("api_url must use https:// to protect your API key in transit.")
    config.set_value(key, value)
    # Mask credential values in output — never echo api_key to terminal
    display = value[:4] + "***" if key == "api_key" else value
    click.echo(f"Set {key} = {display}")


# -- query commands --

@main.command()
@click.argument("query")
@click.option("--limit", default=10, help="Max results")
@click.pass_context
def search(ctx, query, limit):
    """Search the knowledge graph for facts matching QUERY."""
    fmt = _get_format(ctx)
    client = WeezdomClient()
    result = run_async(client.post("/tools/search", json={"query": query, "num_results": limit}))

    if fmt == "json":
        format_output(result, fmt="json")
        return

    facts = result.get("facts", [])
    if not facts:
        click.echo("No results found.")
        return

    # Truncate long facts for table display
    for f in facts:
        fact_text = f.get("fact", "")
        if len(fact_text) > 60:
            f["fact"] = fact_text[:57] + "..."

    format_output(
        facts,
        fmt=fmt,
        columns=[("fact", "Fact"), ("entities", "Entities"), ("confidence", "Confidence")],
        title=f"Search: {query}",
    )


@main.command()
@click.argument("name")
@click.option("--related", is_flag=True, help="Show related entities")
@click.pass_context
def entity(ctx, name, related):
    """Look up an entity by NAME in the knowledge graph."""
    fmt = _get_format(ctx)
    client = WeezdomClient()
    encoded_name = quote(name, safe="")

    if related:
        result = run_async(client.get(f"/tools/entity/{encoded_name}/related"))

        if fmt == "json":
            format_output(result, fmt="json")
            return

        related_list = result.get("related", [])
        if not related_list:
            click.echo(f"No related entities found for '{name}'.")
            return

        format_output(
            related_list,
            fmt=fmt,
            columns=[
                ("name", "Name"),
                ("entity_type", "Type"),
                ("relationship", "Relationship"),
                ("direction", "Direction"),
            ],
            title=f"Related to: {name}",
        )
    else:
        result = run_async(client.get(f"/tools/entity/{encoded_name}"))

        if fmt == "json":
            format_output(result, fmt="json")
            return

        if fmt == "text":
            format_output(result, fmt="text")
            return

        # Rich table display for entity detail
        click.echo(f"\n  Name: {result.get('name', 'N/A')}")
        click.echo(f"  Type: {result.get('entity_type', 'N/A')}")
        click.echo(f"  Summary: {result.get('summary', 'N/A')}")

        facts = result.get("facts", [])
        if facts:
            click.echo(f"\n  Facts ({len(facts)}):")
            for f in facts:
                click.echo(f"    - {f}")

        rels = result.get("relationships", {})
        if rels:
            click.echo("\n  Relationships:")
            for rel_type, targets in rels.items():
                for t in targets:
                    click.echo(f"    {rel_type} -> {t}")

        sources = result.get("sources", [])
        if sources:
            click.echo(f"\n  Sources ({len(sources)}):")
            for s in sources:
                title = s.get("title", "Untitled")
                url = s.get("url", "")
                click.echo(f"    - {title} ({url})" if url else f"    - {title}")

        click.echo()


@main.command()
@click.option("--type", "entity_type", default=None, help="Filter by entity type")
@click.option("--limit", default=50, help="Max entities")
@click.pass_context
def topics(ctx, entity_type, limit):
    """List topics (entities) in the knowledge graph."""
    fmt = _get_format(ctx)
    client = WeezdomClient()

    params = {"limit": limit}
    if entity_type:
        params["entity_type"] = entity_type

    result = run_async(client.get("/tools/topics", params=params))

    if fmt == "json":
        format_output(result, fmt="json")
        return

    total = result.get("total_entities", 0)
    by_type = result.get("by_type", {})
    entities = result.get("sample_entities", [])

    click.echo(f"\nTotal entities: {total}")
    if by_type:
        click.echo("By type:")
        for t, count in sorted(by_type.items(), key=lambda x: -x[1]):
            click.echo(f"  {t}: {count}")
    click.echo()

    if entities:
        format_output(
            entities,
            fmt=fmt,
            columns=[("name", "Name"), ("type", "Type"), ("mention_count", "Mentions")],
            title="Entities",
        )
    else:
        click.echo("No entities found.")


@main.command()
@click.argument("query")
@click.option("--limit", default=5, help="Max source documents")
@click.pass_context
def sources(ctx, query, limit):
    """Find source documents matching QUERY."""
    fmt = _get_format(ctx)
    client = WeezdomClient()
    result = run_async(client.post("/tools/sources", json={"query": query, "limit": limit}))

    if fmt == "json":
        format_output(result, fmt="json")
        return

    source_list = result.get("sources", [])
    if not source_list:
        click.echo("No sources found.")
        return

    for src in source_list:
        title = src.get("document_title", "Untitled")
        url = src.get("source_url", "")
        click.echo(f"\n  {title}")
        if url:
            click.echo(f"  {url}")

        segments = src.get("segments", [])
        for seg in segments:
            content = seg.get("content", "")
            click.echo(f"    > {content}")

    click.echo()


# -- graph commands --

@main.group()
@click.pass_context
def graph(ctx):
    """Manage knowledge graphs."""
    ctx.ensure_object(dict)


@graph.command("list")
@click.pass_context
def graph_list(ctx):
    """List all knowledge graphs."""
    fmt = _get_format(ctx)
    client = WeezdomClient()
    result = run_async(client.get("/knowledge-graphs/data/list"))
    graphs = result if isinstance(result, list) else result.get("graphs", [])

    for g in graphs:
        if g.get("id") and len(str(g["id"])) > 12:
            g["id"] = str(g["id"])[:12] + "..."
        if isinstance(g.get("status"), dict):
            g["status"] = g["status"].get("label", "")

    format_output(graphs, fmt=fmt, columns=[
        ("id", "ID"),
        ("name", "Name"),
        ("status", "Status"),
        ("entity_count", "Entities"),
        ("content_count", "Content"),
    ], title="Knowledge Graphs")


@graph.command("use")
@click.argument("graph_id")
@click.pass_context
def graph_use(ctx, graph_id):
    """Set the active graph for subsequent commands."""
    from weezdom_cli import config

    client = WeezdomClient()
    result = run_async(client.get(f"/knowledge-graphs/data/{graph_id}"))
    config.set_value("active_graph_id", graph_id)
    name = result.get("name", graph_id)
    click.echo(f"Active graph: {name} ({graph_id})")


@graph.command("info")
@click.argument("graph_id", required=False)
@click.pass_context
def graph_info(ctx, graph_id):
    """Show details for a knowledge graph."""
    from weezdom_cli import config

    if not graph_id:
        graph_id = config.get("active_graph_id")
    if not graph_id:
        click.echo("Error: No graph specified. Pass a graph_id or run: weezdom graph use <id>", err=True)
        sys.exit(1)

    fmt = _get_format(ctx)
    client = WeezdomClient()
    result = run_async(client.get(f"/knowledge-graphs/data/{graph_id}"))
    format_output(result, fmt=fmt)


@graph.command("pipeline")
@click.argument("graph_id", required=False)
@click.pass_context
def graph_pipeline(ctx, graph_id):
    """Show pipeline jobs for a knowledge graph."""
    from weezdom_cli import config

    if not graph_id:
        graph_id = config.get("active_graph_id")
    if not graph_id:
        click.echo("Error: No graph specified. Pass a graph_id or run: weezdom graph use <id>", err=True)
        sys.exit(1)

    fmt = _get_format(ctx)
    client = WeezdomClient()
    result = run_async(client.get(f"/knowledge-graphs/data/{graph_id}/pipeline"))
    jobs = result.get("jobs", [])

    for j in jobs:
        if j.get("id") and len(str(j["id"])) > 12:
            j["id"] = str(j["id"])[:12] + "..."

    format_output(jobs, fmt=fmt, columns=[
        ("id", "ID"),
        ("content_title", "Content"),
        ("status", "Status"),
        ("progress", "Progress"),
    ], title="Pipeline Jobs")


# -- content commands --

@main.group()
@click.pass_context
def content(ctx):
    """Manage content library."""
    ctx.ensure_object(dict)


@content.command("list")
@click.option("--type", "content_type", default=None, help="Filter by content type")
@click.option("--status", default=None, help="Filter by status")
@click.option("--tag", default=None, help="Filter by tag")
@click.option("--limit", default=20, help="Max items to return")
@click.pass_context
def content_list(ctx, content_type, status, tag, limit):
    """List content items."""
    fmt = _get_format(ctx)
    client = WeezdomClient()

    params = {"limit": limit}
    if content_type:
        params["type"] = content_type
    if status:
        params["status"] = status
    if tag:
        params["tag"] = tag

    result = run_async(client.get("/content/library", params=params))
    items = result.get("items", [])

    for item in items:
        if item.get("id") and len(str(item["id"])) > 12:
            item["id"] = str(item["id"])[:12] + "..."

    format_output(items, fmt=fmt, columns=[
        ("id", "ID"),
        ("title", "Title"),
        ("type", "Type"),
        ("status", "Status"),
    ], title="Content Library")


@content.command("add")
@click.argument("urls", nargs=-1, required=True)
@click.option("--tag", default=None, help="Tag to apply")
@click.pass_context
def content_add(ctx, urls, tag):
    """Add content by URL."""
    client = WeezdomClient()

    body = {"urls": list(urls)}
    if tag:
        body["tag"] = tag

    result = run_async(client.post("/content/url", json=body))
    job_ids = result.get("job_ids", [])
    click.echo(f"Queued {len(job_ids)} URL(s):")
    for jid in job_ids:
        click.echo(f"  Job: {jid}")


@content.command("upload")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--tag", default=None, help="Tag to apply")
@click.pass_context
def content_upload(ctx, file_path, tag):
    """Upload a file as content."""
    import mimetypes
    import os

    client = WeezdomClient()
    filename = os.path.basename(file_path)
    mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

    with open(file_path, "rb") as f:
        files = {"file": (filename, f, mime_type)}
        data = {}
        if tag:
            data["tag"] = tag
        result = run_async(client.post("/content/upload", files=files, data=data if data else None))

    click.echo(f"Uploaded: {filename}")
    if result.get("job_ids"):
        for jid in result["job_ids"]:
            click.echo(f"  Job: {jid}")
    elif result.get("id"):
        click.echo(f"  Item ID: {result['id']}")


@content.command("view")
@click.argument("item_id")
@click.pass_context
def content_view(ctx, item_id):
    """View content of an item."""
    client = WeezdomClient()
    result = run_async(client.get(f"/content/library/{item_id}/content"))
    text = result.get("content", result.get("text", ""))
    click.echo(text)


@content.command("delete")
@click.argument("item_id")
@click.option("--force", is_flag=True, help="Skip confirmation")
@click.pass_context
def content_delete(ctx, item_id, force):
    """Delete a content item."""
    client = WeezdomClient()

    if not force:
        if not click.confirm(f"Delete content item {item_id}?"):
            click.echo("Cancelled.")
            return

    run_async(client.delete(f"/content/library/{item_id}"))
    click.echo(f"Deleted: {item_id}")


@content.command("extract")
@click.argument("ids", nargs=-1, required=True)
@click.option("--graph", "graph_id", default=None, help="Target graph ID")
@click.pass_context
def content_extract(ctx, ids, graph_id):
    """Extract content items into a knowledge graph."""
    from weezdom_cli import config

    if not graph_id:
        graph_id = config.get("active_graph_id")
    if not graph_id:
        click.echo("Error: No graph specified. Use --graph or run: weezdom graph use <id>", err=True)
        sys.exit(1)

    client = WeezdomClient()
    result = run_async(client.post("/content/bulk-extract", json={
        "content_item_ids": list(ids),
        "graph_id": graph_id,
    }))
    job_ids = result.get("job_ids", [])
    click.echo(f"Queued {len(job_ids)} item(s) for extraction:")
    for jid in job_ids:
        click.echo(f"  Job: {jid}")


# -- traversal commands --

@main.command()
@click.argument("source")
@click.argument("target")
@click.option("--depth", default=3, help="Maximum path length (default 3)")
@click.pass_context
def paths(ctx, source, target, depth):
    """Find shortest paths between SOURCE and TARGET entities."""
    fmt = _get_format(ctx)
    client = WeezdomClient()
    result = run_async(client.get("/tools/paths", params={
        "source": source, "target": target, "max_depth": depth,
    }))

    if fmt == "json":
        format_output(result, fmt="json")
        return

    path_list = result.get("paths", [])
    if not path_list:
        click.echo("No paths found.")
        return

    click.echo(f"\nPaths from '{result.get('source')}' to '{result.get('target')}':\n")
    for i, p in enumerate(path_list, 1):
        entities = p.get("entities", [])
        rels = p.get("relationships", [])
        parts = []
        for j, ent in enumerate(entities):
            parts.append(ent.get("name", "?"))
            if j < len(rels):
                parts.append(f" -[{rels[j].get('type', '?')}]-> ")
        click.echo(f"  {i}. {''.join(parts)}")
    click.echo()


@main.command()
@click.argument("queries", nargs=-1, required=True)
@click.option("--limit", default=10, help="Max results per query (default 10)")
@click.pass_context
def batch(ctx, queries, limit):
    """Run multiple QUERIES in parallel. Pass each query as a separate argument."""
    fmt = _get_format(ctx)
    client = WeezdomClient()
    result = run_async(client.post("/batch-query", json={
        "queries": [{"query": q, "num_results": limit} for q in queries],
    }))

    if fmt == "json":
        format_output(result, fmt="json")
        return

    for item in result.get("results", []):
        q = item.get("query", "")
        hits = item.get("results", [])
        click.echo(f"\n  Query: {q} ({len(hits)} result(s))")
        for h in hits:
            content = h.get("content", "")
            if len(content) > 70:
                content = content[:67] + "..."
            score = h.get("score", 0)
            click.echo(f"    [{score:.2f}] {content}")
    click.echo()


@main.command()
@click.argument("name")
@click.option("--depth", default=2, help="Number of hops (default 2)")
@click.option("--limit", default=50, help="Max nodes to return (default 50)")
@click.pass_context
def neighborhood(ctx, name, depth, limit):
    """Explore the neighborhood around entity NAME up to N hops away."""
    fmt = _get_format(ctx)
    client = WeezdomClient()
    encoded_name = quote(name, safe="")
    result = run_async(client.get(
        f"/tools/entity/{encoded_name}/neighborhood",
        params={"depth": depth, "limit": limit},
    ))

    if fmt == "json":
        format_output(result, fmt="json")
        return

    nodes = result.get("nodes", [])
    if not nodes:
        click.echo(f"No neighbors found for '{name}'.")
        return

    for n in nodes:
        summary = n.get("summary") or ""
        if len(summary) > 50:
            summary = summary[:47] + "..."
        n["summary_short"] = summary

    format_output(
        nodes,
        fmt=fmt,
        columns=[
            ("name", "Name"),
            ("entity_type", "Type"),
            ("distance", "Distance"),
            ("summary_short", "Summary"),
        ],
        title=f"Neighborhood: {name} (depth={depth})",
    )


# -- workspace commands --

@main.group()
@click.pass_context
def workspace(ctx):
    """Explore workspaces and search across graphs."""
    ctx.ensure_object(dict)


@workspace.command("search")
@click.argument("query")
@click.option("--workspace-id", "-w", default=None, help="Workspace ID to search within")
@click.option("--limit", default=10, help="Max results (default 10)")
@click.pass_context
def workspace_search(ctx, query, workspace_id, limit):
    """Search across graphs in a workspace for QUERY."""
    fmt = _get_format(ctx)
    client = WeezdomClient()
    body = {"query": query, "limit": limit}
    if workspace_id:
        body["workspace_id"] = workspace_id
    result = run_async(client.post("/search/workspace", json=body))

    if fmt == "json":
        format_output(result, fmt="json")
        return

    items = result.get("results", [])
    if not items:
        click.echo("No results found.")
        if not workspace_id:
            click.echo("Tip: use -w WORKSPACE_ID to search a specific workspace.")
            click.echo("Run 'weezdom workspace info' to list available workspaces.")
        return

    for item in items:
        fact = item.get("fact", "")
        if len(fact) > 60:
            fact = fact[:57] + "..."
        item["fact_short"] = fact

    format_output(
        items,
        fmt=fmt,
        columns=[
            ("fact_short", "Fact"),
            ("source_graph_name", "Graph"),
            ("graph_role", "Role"),
            ("score", "Score"),
        ],
        title=f"Workspace search: {query}",
    )


@workspace.command("info")
@click.pass_context
def workspace_info(ctx):
    """List all workspaces for this tenant."""
    fmt = _get_format(ctx)
    client = WeezdomClient()
    result = run_async(client.get("/insights/workspaces"))

    if fmt == "json":
        format_output(result, fmt="json")
        return

    workspaces = result.get("workspaces", [])
    if not workspaces:
        click.echo("No workspaces found.")
        return

    for ws in workspaces:
        if ws.get("id") and len(str(ws["id"])) > 12:
            ws["id_short"] = str(ws["id"])[:12] + "..."
        else:
            ws["id_short"] = ws.get("id", "")

    format_output(
        workspaces,
        fmt=fmt,
        columns=[
            ("id_short", "ID"),
            ("name", "Name"),
            ("graph_count", "Graphs"),
            ("entity_count", "Entities"),
        ],
        title="Workspaces",
    )


# -- ontology commands --

@main.group()
@click.pass_context
def ontology(ctx):
    """Manage ontologies."""
    ctx.ensure_object(dict)


@ontology.command("list")
@click.pass_context
def ontology_list(ctx):
    """List all ontologies for this tenant."""
    fmt = _get_format(ctx)
    client = WeezdomClient()
    # GET /ontologies/list returns a raw JSON array (SC-1: not dict-wrapped)
    result = run_async(client.get("/ontologies/list"))
    rows = result if isinstance(result, list) else []

    if fmt == "json":
        format_output(rows, fmt="json")
        return

    if not rows:
        click.echo("No ontologies found.")
        return

    for row in rows:
        if row.get("id") and len(str(row["id"])) > 12:
            row["id_short"] = str(row["id"])[:12] + "..."
        else:
            row["id_short"] = row.get("id", "")
        score = (row.get("status") or {}).get("overall_score")
        row["score_str"] = str(score) if score is not None else "—"

    format_output(
        rows,
        fmt=fmt,
        columns=[
            ("id_short", "ID"),
            ("name", "Name"),
            ("version_count", "Versions"),
            ("graph_count", "Graphs"),
            ("score_str", "Score"),
        ],
        title="Ontologies",
    )


@ontology.command("suggest")
@click.argument("description")
@click.option("--goal", multiple=True, help="Goal for the ontology (repeatable)")
@click.pass_context
def ontology_suggest(ctx, description, goal):
    """Generate a scored ontology template for DESCRIPTION.

    Outputs a JSON config_template you can edit and pass to 'ontology create'.
    Example: weezdom ontology suggest "Track SaaS pricing" --goal "find patterns" > spec.json
    """
    client = WeezdomClient()
    result = run_async(client.post(
        "/ontologies/suggest",
        json={"description": description, "goals": list(goal)},
    ))
    format_output(result, fmt="json")


@ontology.command("create")
@click.argument("name")
@click.option("--spec", "spec_file", type=click.File("r"), default="-",
              help="JSON spec file or stdin (default: stdin). Use output of 'ontology suggest'.")
@click.pass_context
def ontology_create(ctx, name, spec_file):
    """Create a new ontology from NAME and a JSON spec.

    Reads spec from --spec FILE or stdin (pipe from 'ontology suggest').
    Example: weezdom ontology suggest "..." | weezdom ontology create "My Ontology"
    """
    fmt = _get_format(ctx)
    if spec_file.name == "<stdin>" and sys.stdin.isatty():
        click.echo(
            "Error: provide --spec FILE or pipe JSON from 'weezdom ontology suggest'.\n"
            "Example: weezdom ontology suggest \"my domain\" | weezdom ontology create \"Name\"",
            err=True,
        )
        sys.exit(1)
    try:
        raw = spec_file.read()
        spec = json.loads(raw)
    except json.JSONDecodeError as e:
        click.echo(f"Error: invalid JSON in spec: {e}", err=True)
        sys.exit(1)

    if "config_template" in spec:
        spec = spec["config_template"]

    body = {"name": name, **spec}
    client = WeezdomClient()
    result = run_async(client.post("/ontologies", json=body))

    if fmt == "json":
        format_output(result, fmt="json")
        return

    ont_id = result.get("ontology_id", "?")
    score = (result.get("quality") or {}).get("overall_score", "?")
    reached = (result.get("quality") or {}).get("is_buildable", False)
    click.echo(f"Created: ontology_id={ont_id}  score={score}/100  buildable={reached}")
    if score != "?" and score < 70:
        click.echo(
            "Tip: score below 70 — run 'ontology build' for auto-improvement, "
            "or edit the spec and re-create."
        )


@ontology.command("build")
@click.argument("name")
@click.argument("description")
@click.option("--goal", multiple=True, help="Goal for the knowledge graph (repeatable)")
@click.option("--iterations", default=3, show_default=True,
              help="Max improvement cycles (each ~15-60s)")
@click.option("--timeout", default=300, show_default=True,
              help="HTTP timeout in seconds (build takes 1–4 min)")
@click.pass_context
def ontology_build(ctx, name, description, goal, iterations, timeout):
    """Build a production-quality ontology using server-side AI.

    One call: AI generates spec, scores it, iterates until score >= 70.
    Takes 1-4 minutes. If interrupted, run 'weezdom ontology list' to check completion.
    Example: weezdom ontology build "Revenue Brain" "Track SaaS pricing" --goal "find patterns"
    """
    fmt = _get_format(ctx)
    click.echo(
        f"Building '{name}'... (this may take up to {timeout}s depending on --iterations)",
        err=True,
    )
    body = {
        "name": name,
        "description": description,
        "goals": list(goal),
        "max_iterations": iterations,
    }
    client = WeezdomClient(timeout=timeout)
    result = run_async(client.post("/ontologies/build", json=body))

    if fmt == "json":
        format_output(result, fmt="json")
        return

    ont_id = result.get("ontology_id", "?")
    score = (result.get("quality") or {}).get("overall_score", "?")
    iters = result.get("iterations_used", "?")
    reached = result.get("reached_threshold", False)
    click.echo(
        f"Built: ontology_id={ont_id}  score={score}/100  "
        f"iterations={iters}  threshold={'yes' if reached else 'no'}"
    )
    if not reached:
        click.echo(
            f"Tip: threshold not reached — try --iterations {iterations + 2}"
        )


@main.command("property-search")
@click.argument("property")
@click.option("--value", default=None, help="Filter by property value")
@click.option("--type", "entity_type", default=None, help="Filter by entity type")
@click.option("--limit", default=50, help="Max results (default 50)")
@click.pass_context
def property_search(ctx, property, value, entity_type, limit):
    """Search entities by PROPERTY name, optionally filtering by value or type."""
    fmt = _get_format(ctx)
    client = WeezdomClient()
    body = {"property_name": property, "limit": limit}
    if value:
        body["property_value"] = value
    if entity_type:
        body["entity_type"] = entity_type
    result = run_async(client.post("/tools/properties/search", json=body))

    if fmt == "json":
        format_output(result, fmt="json")
        return

    matches = result.get("matches", [])
    if not matches:
        click.echo(f"No matches found for property '{property}'.")
        return

    for m in matches:
        props = json.dumps(m.get("properties", {}), default=str)
        if len(props) > 60:
            props = props[:57] + "..."
        m["props_str"] = props

    format_output(
        matches,
        fmt=fmt,
        columns=[
            ("name", "Name"),
            ("entity_type", "Type"),
            ("props_str", "Properties"),
        ],
        title=f"Property search: {property}",
    )
