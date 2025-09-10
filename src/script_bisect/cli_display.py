"""CLI display and formatting utilities.

This module contains functions for displaying information to the user,
including banners, summaries, tables, and confirmation dialogs.
"""

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

console = Console()


def print_banner() -> None:
    """Print the application banner."""
    console.print(
        Panel.fit(
            "🔍 [bold]script-bisect[/bold] v0.1.0\n"
            "Bisect package versions in PEP 723 Python scripts",
            border_style="bright_blue",
        )
    )


def print_summary_table(
    script_path: Path,
    package: str,
    repo_url: str,
    good_ref: str,
    bad_ref: str,
) -> None:
    """Print a summary table showing bisection parameters."""
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Parameter", style="dim")
    table.add_column("Value")

    table.add_row("📄 Script", str(script_path))
    table.add_row("📦 Package", package)
    table.add_row("🔗 Repository", repo_url)
    table.add_row("✅ Good ref", good_ref)
    table.add_row("❌ Bad ref", bad_ref)

    console.print()
    console.print(table)


def confirm_bisection_params(
    script_path: Path,
    package: str,
    good_ref: str,
    bad_ref: str,
    repo_url: str,
    test_command: str | None,
    inverse: bool,
    auto_confirm: bool = False,
) -> bool:
    """Display bisection parameters and get user confirmation."""
    console.print("\n🔄 [bold]Bisection Summary[/bold]")

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Parameter", style="dim", width=20)
    table.add_column("Value", width=40)

    table.add_row("📄 Script", str(script_path))
    table.add_row("📦 Package", package)
    table.add_row("🔗 Repository", repo_url)
    table.add_row("✅ Good ref", good_ref)
    table.add_row("❌ Bad ref", bad_ref)
    table.add_row("🧪 Test command", test_command or f"uv run {script_path.name}")
    table.add_row(
        "🔄 Mode",
        "Inverse (find when fixed)" if inverse else "Normal (find when broken)",
    )

    console.print(table)

    if auto_confirm:
        console.print("\nStart bisection? yes (auto-confirmed)")
        return True

    return Confirm.ask("\nStart bisection?", default=True)
