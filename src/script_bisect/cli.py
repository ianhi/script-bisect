"""Command-line interface for script-bisect."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .bisector import GitBisector
from .exceptions import ScriptBisectError
from .parser import ScriptParser
from .utils import setup_logging


console = Console()


def print_banner() -> None:
    """Print the application banner."""
    banner = Panel.fit(
        f"[bold blue]🔍 script-bisect v{__version__}[/bold blue]\n"
        "[dim]Bisect package versions in PEP 723 Python scripts[/dim]",
        border_style="blue",
    )
    console.print(banner)


def print_summary_table(
    script_path: Path,
    package: str,
    repo_url: str,
    good_ref: str,
    bad_ref: str,
) -> None:
    """Print a summary table of the bisection parameters."""
    table = Table(title="Bisection Summary", show_header=True)
    table.add_column("Parameter", style="cyan", width=20)
    table.add_column("Value", style="white")
    
    table.add_row("📄 Script", str(script_path))
    table.add_row("📦 Package", package)
    table.add_row("🔗 Repository", repo_url)
    table.add_row("✅ Good ref", good_ref)
    table.add_row("❌ Bad ref", bad_ref)
    
    console.print(table)


@click.command()
@click.argument(
    "script",
    type=click.Path(exists=True, path_type=Path),
    metavar="SCRIPT",
)
@click.argument("package", metavar="PACKAGE")
@click.argument("good_ref", metavar="GOOD_REF")
@click.argument("bad_ref", metavar="BAD_REF")
@click.option(
    "--repo-url",
    help="Override the repository URL (auto-detected if not provided)",
    metavar="URL",
)
@click.option(
    "--test-command",
    help="Custom test command (default: uv run SCRIPT)",
    metavar="COMMAND",
)
@click.option(
    "--clone-dir",
    type=click.Path(path_type=Path),
    help="Directory for temporary clone (default: temp directory)",
    metavar="DIR",
)
@click.option(
    "--keep-clone",
    is_flag=True,
    help="Keep the cloned repository after bisecting",
)
@click.option(
    "--inverse",
    is_flag=True,
    help="Find when something was fixed (not broken)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be done without actually doing it",
)
@click.option(
    "--verify-endpoints",
    is_flag=True,
    help="Enable endpoint verification (slower but safer)",
)
@click.version_option(version=__version__)
def main(
    script: Path,
    package: str,
    good_ref: str,
    bad_ref: str,
    repo_url: str | None = None,
    test_command: str | None = None,
    clone_dir: Path | None = None,
    keep_clone: bool = False,
    inverse: bool = False,
    verbose: bool = False,
    dry_run: bool = False,
    verify_endpoints: bool = False,
) -> None:
    """Bisect package versions in PEP 723 Python scripts.
    
    This tool uses git bisect to find the commit that introduced a regression
    in a Python package dependency. It works by:
    
    1. Parsing the PEP 723 metadata in your script
    2. Cloning the package repository 
    3. Running git bisect with automatic testing
    4. Updating the package reference for each commit tested
    
    Examples:
    
        # Basic usage
        script-bisect script.py xarray v2024.01.0 v2024.03.0
        
        # With custom repository
        script-bisect script.py numpy 1.24.0 main --repo-url https://github.com/numpy/numpy
        
        # Find when something was fixed
        script-bisect script.py pandas v1.5.0 v2.0.0 --inverse
        
    The script must contain PEP 723 inline metadata with the target package
    as a dependency (either normal or git dependency).
    """
    setup_logging(verbose)
    
    try:
        print_banner()
        
        # Parse the script to validate and extract information
        console.print("[dim]📄 Parsing script metadata...[/dim]")
        parser = ScriptParser(script)
        
        if not parser.has_package(package):
            console.print(f"[red]❌ Package '{package}' not found in script dependencies[/red]")
            available = parser.get_available_packages()
            if available:
                console.print("[yellow]Available packages:[/yellow]")
                for pkg in available:
                    console.print(f"  • {pkg}")
            sys.exit(1)
        
        # Auto-detect repository URL if not provided
        if not repo_url:
            console.print("[dim]🔍 Auto-detecting repository URL...[/dim]")
            repo_url = parser.get_repository_url(package)
            if not repo_url:
                console.print(
                    f"[red]❌ Could not auto-detect repository URL for '{package}'[/red]"
                    "\n[yellow]Please specify --repo-url manually[/yellow]"
                )
                sys.exit(1)
        
        print_summary_table(script, package, repo_url, good_ref, bad_ref)
        
        if dry_run:
            console.print("[yellow]🏃 Dry run mode - no actual bisection will be performed[/yellow]")
            return
        
        # Create and run the bisector
        bisector = GitBisector(
            script_path=script,
            package=package,
            repo_url=repo_url,
            good_ref=good_ref,
            bad_ref=bad_ref,
            test_command=test_command,
            clone_dir=clone_dir,
            keep_clone=keep_clone,
            inverse=inverse,
            skip_verification=not verify_endpoints,
        )
        
        result = bisector.run()
        
        if result:
            console.print("\n[green]✨ Bisection completed successfully![/green]")
            # TODO: Display result details
        else:
            console.print("\n[yellow]⚠️ Bisection completed but no clear result found[/yellow]")
            
    except ScriptBisectError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()