"""Command-line interface for script-bisect."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .bisector import GitBisector
from .exceptions import ScriptBisectError
from .interactive import (
    confirm_bisection_params,
    prompt_for_package,
    prompt_for_refs,
    prompt_for_repo_url,
)
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
@click.argument("package", metavar="PACKAGE", required=False)
@click.argument("good_ref", metavar="GOOD_REF", required=False)
@click.argument("bad_ref", metavar="BAD_REF", required=False)
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
    package: str | None = None,
    good_ref: str | None = None,
    bad_ref: str | None = None,
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

        # Interactive package selection if not provided
        if not package:
            available = parser.get_available_packages()
            package = prompt_for_package(available)
        elif not parser.has_package(package):
            console.print(
                f"[red]❌ Package '{package}' not found in script dependencies[/red]"
            )
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
                repo_url = prompt_for_repo_url(package)

        # Interactive prompts for missing git refs
        if not good_ref or not bad_ref:
            good_ref, bad_ref = prompt_for_refs(package, repo_url, good_ref, bad_ref)

        # Validate and potentially swap refs if they're in wrong order
        good_ref, bad_ref = _validate_and_fix_refs(good_ref, bad_ref, inverse)

        # Show confirmation unless all parameters were provided via command line
        if not all([package, good_ref, bad_ref]) and not confirm_bisection_params(
            script, package, good_ref, bad_ref, repo_url, test_command, inverse
        ):
            console.print("[yellow]⚠️ Bisection cancelled[/yellow]")
            return

        if dry_run:
            print_summary_table(script, package, repo_url, good_ref, bad_ref)
            console.print(
                "[yellow]🏃 Dry run mode - no actual bisection will be performed[/yellow]"
            )
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
            console.print(
                "\n[yellow]⚠️ Bisection completed but no clear result found[/yellow]"
            )

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


def _validate_and_fix_refs(
    good_ref: str, bad_ref: str, inverse: bool
) -> tuple[str, str]:
    """Validate git references and potentially swap them if needed.

    This function helps handle edge cases where users accidentally:
    - Swap good/bad refs
    - Provide the same ref for both
    - Use obviously wrong chronological order

    Args:
        good_ref: The "good" reference provided by user
        bad_ref: The "bad" reference provided by user
        inverse: Whether this is inverse mode (finding when something was fixed)

    Returns:
        Tuple of (validated_good_ref, validated_bad_ref)
    """
    # Check for same refs
    if good_ref == bad_ref:
        console.print("[red]❌ Good and bad references cannot be the same[/red]")
        console.print(f"Both refs are: {good_ref}")
        console.print("[yellow]Please provide different git references[/yellow]")
        sys.exit(1)

    # Check for obvious version tag patterns that might be swapped
    if _looks_like_newer_version(good_ref, bad_ref) and not inverse:
        console.print("[yellow]⚠️ Potential reference order issue detected[/yellow]")
        console.print(f"[green]Good ref: {good_ref}[/green] (appears newer)")
        console.print(f"[red]Bad ref: {bad_ref}[/red] (appears older)")
        console.print()
        console.print(
            "Typically, the '[green]good[/green]' ref should be an older working version,"
        )
        console.print("and the '[red]bad[/red]' ref should be a newer broken version.")
        console.print()

        from rich.prompt import Confirm

        try:
            if Confirm.ask("[bold]Swap the references?[/bold]", default=True):
                good_ref, bad_ref = bad_ref, good_ref
                console.print("[green]✅ References swapped[/green]")
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️ Keeping original order[/yellow]")

    return good_ref, bad_ref


def _looks_like_newer_version(ref1: str, ref2: str) -> bool:
    """Check if ref1 looks like a newer version than ref2.

    This is a heuristic for common version patterns like:
    - v1.2.0 vs v2.0.0
    - 2024.01.0 vs 2024.12.0
    - 1.0 vs 2.0

    Args:
        ref1: First reference
        ref2: Second reference

    Returns:
        True if ref1 appears to be a newer version than ref2
    """
    import re

    # Extract version-like patterns
    version_pattern = r"v?(\d+(?:\.\d+)*(?:\.\d+)*)"

    match1 = re.search(version_pattern, ref1)
    match2 = re.search(version_pattern, ref2)

    if not (match1 and match2):
        return False

    def version_tuple(version_str: str) -> tuple[int, ...]:
        """Convert version string to tuple for comparison."""
        return tuple(map(int, version_str.split(".")))

    try:
        v1 = version_tuple(match1.group(1))
        v2 = version_tuple(match2.group(1))
        return v1 > v2
    except (ValueError, AttributeError):
        return False


if __name__ == "__main__":
    main()
