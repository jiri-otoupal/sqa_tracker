from rich.console import Console
from rich.tree import Tree
from rich.syntax import Syntax
from rich.panel import Panel

console = Console()


def build_tree_structure(rich_tree, node):
    for sub in set(node.substeps):
        # Color based on node type.
        if sub.call.startswith("Call: "):
            branch = rich_tree.add(f"[bold yellow]{sub.call}[/bold yellow]")
        elif any(sub.call.startswith(kw) for kw in ("if ", "elif ", "else", "case ", "switch ")):
            branch = rich_tree.add(f"[bold cyan]{sub.call}[/bold cyan]")
        else:
            branch = rich_tree.add(f"[bold green]{sub.call}[/bold green]")
        # For diff, add a panel with indentation according to branch depth.
        if sub.diff:
            diff_panel = Panel(
                Syntax(sub.diff, "sql", theme="monokai", line_numbers=True),
                title="🔄 SQL Diff",
                border_style="red"
            )
            branch.add(diff_panel)
        build_tree_structure(branch, sub)


def print_query_log(tracer_root):
    main_tree = Tree("[bold cyan]🔍 Query Execution Path[/bold cyan]")
    build_tree_structure(main_tree, tracer_root)
    console.print(main_tree)
