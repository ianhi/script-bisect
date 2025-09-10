"""CLI display and formatting utilities.

This module contains functions for displaying information to the user,
including banners, summaries, tables, and confirmation dialogs.
"""

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
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
) -> tuple[bool, dict[str, str | bool | None]]:
    """Display bisection parameters and get user confirmation with optional editing.

    Returns:
        A tuple of (should_start, updated_params) where updated_params contains
        any modified parameters.
    """
    # Track any changes made by the user
    current_params = {
        "package": package,
        "good_ref": good_ref,
        "bad_ref": bad_ref,
        "repo_url": repo_url,
        "test_command": test_command,
        "inverse": inverse,
    }

    while True:
        console.print("\n🔄 [bold]Bisection Summary[/bold]")

        # Manual formatting for complete control over spacing
        # Escape square brackets to prevent Rich markup conflicts
        console.print(f"[cyan]\\[s][/cyan] [dim]📄 Script[/dim]     {script_path}")
        console.print(
            f"[cyan]\\[p][/cyan] [dim]📦 Package[/dim]    {current_params['package']}"
        )
        console.print(
            f"[cyan]\\[r][/cyan] [dim]🔗 Repository[/dim] {current_params['repo_url']}"
        )
        console.print(
            f"[cyan]\\[g][/cyan] [dim]✅ Good ref[/dim]   {current_params['good_ref']}"
        )
        console.print(
            f"[cyan]\\[b][/cyan] [dim]❌ Bad ref[/dim]    {current_params['bad_ref']}"
        )
        test_cmd = current_params["test_command"] or f"uv run {script_path.name}"
        console.print(f"[cyan]\\[t][/cyan] [dim]🧪 Test command[/dim] {test_cmd}")
        mode_text = (
            "Inverse (find when fixed)"
            if current_params["inverse"]
            else "Normal (find when broken)"
        )
        console.print(f"[cyan]\\[i][/cyan] [dim]🔄 Mode[/dim]       {mode_text}")

        if auto_confirm:
            console.print("\nStart bisection? yes (auto-confirmed)")
            return True, current_params

        console.print("\n[dim]Press the highlighted key to edit that parameter, or:[/dim]")
        console.print("  [green]Enter/y[/green] - Start bisection")
        console.print("  [red]n/q[/red] - Cancel")

        try:
            choice = console.input("\nChoice: ").strip().lower()

            if choice in ("", "y", "yes"):
                return True, current_params
            elif choice in ("n", "no", "q", "quit"):
                return False, current_params
            elif choice == "s":
                console.print(
                    "[yellow]Script editing opens the file in your default editor[/yellow]"
                )
                console.print(f"[dim]Script path: {script_path}[/dim]")

                # Use the consolidated editor integration
                from .editor_integration import EditorIntegration
                editor = EditorIntegration()
                
                try:
                    if editor.launch_editor(script_path):
                        console.print("[green]✓[/green] Script editor opened")
                    else:
                        console.print("[yellow]Could not open editor automatically[/yellow]")
                        console.print(f"[dim]Please manually edit: {script_path}[/dim]")
                except Exception as e:
                    console.print(f"[yellow]Could not open editor: {e}[/yellow]")
                    console.print(f"[dim]Please manually edit: {script_path}[/dim]")

            elif choice == "p":
                new_package = Prompt.ask(
                    "Package name", default=current_params["package"]
                )
                current_params["package"] = new_package
            elif choice == "r":
                new_repo = Prompt.ask(
                    "Repository URL", default=current_params["repo_url"]
                )
                current_params["repo_url"] = new_repo
            elif choice == "g":
                new_good = Prompt.ask(
                    "Good reference", default=current_params["good_ref"]
                )
                current_params["good_ref"] = new_good
            elif choice == "b":
                new_bad = Prompt.ask("Bad reference", default=current_params["bad_ref"])
                current_params["bad_ref"] = new_bad
            elif choice == "t":
                current_cmd = (
                    current_params["test_command"] or f"uv run {script_path.name}"
                )
                new_cmd = Prompt.ask("Test command", default=current_cmd)
                current_params["test_command"] = (
                    new_cmd if new_cmd != f"uv run {script_path.name}" else None
                )
            elif choice == "i":
                current_params["inverse"] = not current_params["inverse"]
                mode = "inverse" if current_params["inverse"] else "normal"
                console.print(f"[green]✓[/green] Switched to {mode} mode")
            else:
                console.print(f"[red]Unknown option: {choice}[/red]")

        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Cancelled[/yellow]")
            return False, current_params
