"""Output formatters — table, json, text."""

import json
import sys

from rich.console import Console
from rich.table import Table

console = Console()


def format_output(data, fmt: str = "table", columns: list = None, title: str = None):
    """Format and print data based on output format.

    Args:
        data: list of dicts (table rows) or a single dict
        fmt: 'table', 'json', or 'text'
        columns: list of (key, header) tuples for table mode
        title: optional table title
    """
    if fmt == "json":
        print(json.dumps(data, indent=2, default=str))
        return

    if fmt == "text":
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    print(" | ".join(str(v) for v in item.values()))
                else:
                    print(item)
        elif isinstance(data, dict):
            for k, v in data.items():
                print(f"{k}: {v}")
        else:
            print(data)
        return

    # Table format (default)
    if isinstance(data, dict) and not columns:
        # Single dict — print as key/value pairs
        for k, v in data.items():
            if isinstance(v, (list, dict)):
                v = json.dumps(v, default=str)
            console.print(f"[bold]{k}[/bold]: {v}")
        return

    if isinstance(data, list) and columns:
        table = Table(title=title, show_lines=False)
        for _, header in columns:
            table.add_column(header)
        for item in data:
            row = []
            for key, _ in columns:
                val = item.get(key, "")
                if isinstance(val, list):
                    val = ", ".join(str(v) for v in val)
                row.append(str(val) if val is not None else "")
            table.add_row(*row)
        console.print(table)
        return

    # Fallback
    console.print(data)
