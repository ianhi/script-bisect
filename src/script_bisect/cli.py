"""Command-line interface for script-bisect."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from . import __version__
from .bisector import GitBisector
from .editor_integration import EditorIntegration
from .end_state_menu import handle_end_state_options
from .exceptions import ScriptBisectError
from .interactive import (
    confirm_bisection_params,
    prompt_for_code_block,
    prompt_for_package,
    prompt_for_refs,
    prompt_for_repo_url,
)
from .issue_importer import GitHubIssueImporter
from .parser import ScriptParser
from .script_generator import ScriptGenerator
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
@click.argument("source", metavar="SOURCE")
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
    "--dry-run",
    is_flag=True,
    help="Show what would be done without actually doing it",
)
@click.option(
    "--verify-endpoints",
    is_flag=True,
    help="Enable endpoint verification (slower but safer)",
)
@click.option(
    "--no-edit",
    is_flag=True,
    help="Skip script editing step (for GitHub URLs)",
)
@click.option(
    "--keep-script",
    is_flag=True,
    help="Keep the generated script file after bisection (for GitHub URLs)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Automatically confirm bisection without prompting",
)
@click.option(
    "--full-traceback",
    is_flag=True,
    help="Show complete error tracebacks instead of summary messages",
)
@click.version_option(version=__version__)
def main(
    source: str,
    package: str | None = None,
    good_ref: str | None = None,
    bad_ref: str | None = None,
    repo_url: str | None = None,
    test_command: str | None = None,
    clone_dir: Path | None = None,
    keep_clone: bool = False,
    inverse: bool = False,
    dry_run: bool = False,
    verify_endpoints: bool = False,
    no_edit: bool = False,
    keep_script: bool = False,
    verbose: bool = False,
    yes: bool = False,
    full_traceback: bool = False,
) -> None:
    """Bisect package versions in PEP 723 Python scripts.

    SOURCE can be either:
    - A GitHub issue/comment URL (e.g., https://github.com/user/repo/issues/123)
    - A local Python script file with PEP 723 metadata

    The tool automatically detects the input type and:

    For GitHub URLs:
    1. Fetches and extracts code blocks from the issue/comments
    2. Prompts you to select the correct script
    3. Auto-generates PEP 723 metadata with dependencies
    4. Optionally allows editing before bisection
    5. Runs the bisection process

    For local files:
    1. Parses the existing PEP 723 metadata
    2. Runs the bisection process directly

    Examples:

        # From GitHub issue
        script-bisect https://github.com/pandas/pandas/issues/12345 pandas

        # From local script
        script-bisect script.py xarray v2024.01.0 v2024.03.0

        # With custom repository and options
        script-bisect script.py numpy 1.24.0 main --repo-url https://github.com/numpy/numpy --inverse
    """
    setup_logging(verbose)

    try:
        print_banner()

        # Auto-detect source type
        if _is_github_url(source):
            console.print("[dim]🔍 Detected GitHub URL, extracting script...[/dim]")
            _handle_github_url(
                source,
                package,
                good_ref,
                bad_ref,
                repo_url,
                test_command,
                clone_dir,
                keep_clone,
                inverse,
                dry_run,
                verify_endpoints,
                no_edit,
                keep_script,
                yes,
                full_traceback,
            )
        elif Path(source).exists():
            console.print("[dim]📄 Detected script file, running bisection...[/dim]")
            _handle_script_file(
                Path(source),
                package,
                good_ref,
                bad_ref,
                repo_url,
                test_command,
                clone_dir,
                keep_clone,
                inverse,
                dry_run,
                verify_endpoints,
                yes,
                full_traceback,
            )
        else:
            console.print(f"[red]❌ Source not found or invalid: {source}[/red]")
            console.print(
                "[yellow]💡 SOURCE should be a GitHub URL or existing script file[/yellow]"
            )
            sys.exit(1)

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


def _is_github_url(url: str) -> bool:
    """Check if a string looks like a GitHub URL."""
    return url.startswith("https://github.com/") and (
        "/issues/" in url or "/pull/" in url
    )


def _handle_github_url(
    github_url: str,
    package: str | None = None,
    good_ref: str | None = None,
    bad_ref: str | None = None,
    repo_url: str | None = None,
    test_command: str | None = None,
    clone_dir: Path | None = None,
    keep_clone: bool = False,
    inverse: bool = False,
    dry_run: bool = False,
    verify_endpoints: bool = False,
    no_edit: bool = False,
    keep_script: bool = False,
    yes: bool = False,
    full_traceback: bool = False,
) -> None:
    """Handle GitHub URL workflow."""
    # Initialize components
    importer = GitHubIssueImporter()
    generator = ScriptGenerator()
    editor = EditorIntegration()

    # Step 1: Import code blocks from GitHub
    console.print(f"[dim]🔍 Importing from: {github_url}[/dim]")
    code_blocks = importer.import_from_url(github_url)

    if not code_blocks:
        console.print("[red]❌ No code blocks found in the GitHub issue/comments[/red]")
        sys.exit(1)

    # Step 2: Let user select the code block to use
    selected_block = prompt_for_code_block(code_blocks, auto_select=yes)

    # Step 3: Generate script with PEP 723 metadata
    console.print("[dim]🔧 Generating script with PEP 723 metadata...[/dim]")

    # Suggest additional dependencies based on common patterns
    suggested_deps = generator.suggest_common_dependencies(selected_block.content)

    # Include the package being bisected in dependencies
    if package and package not in suggested_deps:
        suggested_deps.append(package)
        console.print(
            f"[green]📦 Including target package in dependencies: {package}[/green]"
        )

    if suggested_deps:
        console.print(
            f"[yellow]💡 Suggested dependencies: {', '.join(suggested_deps)}[/yellow]"
        )

    # Create temporary script
    script_path = generator.create_temporary_script(
        selected_block, additional_dependencies=suggested_deps
    )

    try:
        # Step 4: Allow user to edit the script (unless --no-edit)
        if not no_edit:
            if not editor.edit_script_interactively(script_path, auto_skip=yes):
                console.print("[yellow]⚠️ Script editing cancelled[/yellow]")
                return

            # Validate syntax after editing
            is_valid, error_msg = editor.validate_script_syntax(script_path)
            if not is_valid:
                console.print(f"[red]❌ Script has syntax errors: {error_msg}[/red]")
                if not Confirm.ask("Continue anyway?", default=False):
                    return

        # Show preview of the final script
        editor.show_script_preview(script_path)

        # Step 5: Parse the generated script and proceed with bisection
        console.print("[dim]📄 Parsing generated script...[/dim]")
        parser = ScriptParser(script_path)

        # Step 6: Continue with common bisection logic
        _run_bisection(
            script_path,
            parser,
            package,
            good_ref,
            bad_ref,
            repo_url,
            test_command,
            clone_dir,
            keep_clone,
            inverse,
            dry_run,
            verify_endpoints,
            github_context=github_url,
            yes=yes,
            full_traceback=full_traceback,
        )

    finally:
        # Cleanup temporary script unless --keep-script
        if not keep_script and script_path.exists():
            try:
                script_path.unlink()
                console.print(
                    f"[dim]🗑️ Cleaned up temporary script: {script_path.name}[/dim]"
                )
            except OSError:
                console.print(
                    f"[yellow]⚠️ Could not remove temporary script: {script_path}[/yellow]"
                )


def _handle_script_file(
    script: Path,
    package: str | None = None,
    good_ref: str | None = None,
    bad_ref: str | None = None,
    repo_url: str | None = None,
    test_command: str | None = None,
    clone_dir: Path | None = None,
    keep_clone: bool = False,
    inverse: bool = False,
    dry_run: bool = False,
    verify_endpoints: bool = False,
    yes: bool = False,
    full_traceback: bool = False,
) -> None:
    """Handle local script file workflow."""
    # Parse the script to validate and extract information
    console.print("[dim]📄 Parsing script metadata...[/dim]")
    parser = ScriptParser(script)

    # Continue with common bisection logic
    _run_bisection(
        script,
        parser,
        package,
        good_ref,
        bad_ref,
        repo_url,
        test_command,
        clone_dir,
        keep_clone,
        inverse,
        dry_run,
        verify_endpoints,
        github_context=None,  # No GitHub context for local files
        yes=yes,
        full_traceback=full_traceback,
    )


def _run_bisection(
    script_path: Path,
    parser: ScriptParser,
    package: str | None = None,
    good_ref: str | None = None,
    bad_ref: str | None = None,
    repo_url: str | None = None,
    test_command: str | None = None,
    clone_dir: Path | None = None,
    keep_clone: bool = False,
    inverse: bool = False,
    dry_run: bool = False,
    verify_endpoints: bool = False,
    github_context: str | None = None,
    yes: bool = False,
    full_traceback: bool = False,
) -> None:
    """Run the common bisection logic."""
    # Interactive package selection if not provided
    if not package:
        available = parser.get_available_packages()
        if available:
            package = prompt_for_package(available)
        else:
            console.print("[red]❌ No packages found in script dependencies[/red]")
            sys.exit(1)
    elif not parser.has_package(package):
        console.print(
            f"[red]❌ Package '{package}' not found in script dependencies[/red]"
        )
        available = parser.get_available_packages()
        if available:
            console.print("[yellow]Available packages:[/yellow]")
            for pkg in available:
                console.print(f"  • {pkg}")
            # For GitHub URLs, we might be bisecting a package that's not in detected deps
            # but was added manually - show as option but don't force selection
            if package:
                console.print(f"  • [dim]{package} (target package)[/dim]")
                if yes or Confirm.ask(
                    f"Use target package '{package}' for bisection?", default=True
                ):
                    pass  # Keep the original package
                else:
                    package = prompt_for_package(available)
            else:
                package = prompt_for_package(available)
        else:
            sys.exit(1)

    # Auto-detect repository URL if not provided
    if not repo_url:
        console.print("[dim]🔍 Auto-detecting repository URL...[/dim]")
        repo_url = parser.get_repository_url(package, github_context)
        if not repo_url:
            console.print(
                f"\n[yellow]⚠️ Could not auto-detect repository URL for '{package}'[/yellow]"
            )
            repo_url = prompt_for_repo_url(package)

    # Interactive prompts for missing git refs
    if not good_ref or not bad_ref:
        good_ref, bad_ref = prompt_for_refs(package, repo_url, good_ref, bad_ref)

    # Validate and potentially swap refs
    good_ref, bad_ref = _validate_and_fix_refs(good_ref, bad_ref, inverse)

    # Show confirmation
    if not confirm_bisection_params(
        script_path,
        package,
        good_ref,
        bad_ref,
        repo_url,
        test_command,
        inverse,
        auto_confirm=yes,
    ):
        console.print("[yellow]⚠️ Bisection cancelled[/yellow]")
        return

    if dry_run:
        print_summary_table(script_path, package, repo_url, good_ref, bad_ref)
        console.print(
            "[yellow]🏃 Dry run mode - no actual bisection will be performed[/yellow]"
        )
        return

    # Create and run the bisector
    bisector = GitBisector(
        script_path=script_path,
        package=package,
        repo_url=repo_url,
        good_ref=good_ref,
        bad_ref=bad_ref,
        test_command=test_command,
        clone_dir=clone_dir,
        keep_clone=keep_clone,
        inverse=inverse,
        skip_verification=not verify_endpoints,
        full_traceback=full_traceback,
    )

    result = bisector.run()

    if result:
        console.print("\n[green]✨ Bisection completed successfully![/green]")
    else:
        console.print(
            "\n[yellow]⚠️ Bisection completed but no clear result found[/yellow]"
        )

    # Offer end state options for re-running
    handle_end_state_options(
        script_path=script_path,
        package=package,
        good_ref=good_ref,
        bad_ref=bad_ref,
        repo_url=repo_url,
        test_command=test_command,
        inverse=inverse,
        keep_clone=keep_clone,
        verify_endpoints=verify_endpoints,
        dry_run=dry_run,
        full_traceback=full_traceback,
        yes=yes,
    )


def _validate_and_fix_refs(
    good_ref: str, bad_ref: str, inverse: bool
) -> tuple[str, str]:
    """Validate git references and potentially swap them if needed."""
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

        try:
            if Confirm.ask("[bold]Swap the references?[/bold]", default=True):
                good_ref, bad_ref = bad_ref, good_ref
                console.print("[green]✅ References swapped[/green]")
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️ Keeping original order[/yellow]")

    return good_ref, bad_ref


def _looks_like_newer_version(ref1: str, ref2: str) -> bool:
    """Check if ref1 looks like a newer version than ref2."""
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
