"""High-level bisection orchestration and coordination.

This module provides the main orchestration logic for running bisections,
coordinating between different components like parser, bisector, and user interface.
"""

import sys
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm

from script_bisect.bisector import GitBisector
from script_bisect.cli_display import (
    confirm_bisection_params,
    print_summary_table,
)
from script_bisect.interactive import (
    prompt_for_package,
    prompt_for_refs,
    prompt_for_repo_url,
)
from script_bisect.parser import ScriptParser
from script_bisect.validation import validate_and_fix_refs

console = Console()


def run_bisection_workflow(
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
    """Run the full bisection workflow with interactive prompting for missing parameters."""
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

    # Delegate to the simplified implementation
    run_bisection_with_params(
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
        clone_dir=clone_dir,
    )


def run_bisection_with_params(
    script_path: Path,
    package: str,
    good_ref: str,
    bad_ref: str,
    repo_url: str,
    test_command: str | None,
    inverse: bool,
    keep_clone: bool,
    verify_endpoints: bool,
    dry_run: bool,
    full_traceback: bool,
    yes: bool,
    clone_dir: Path | None = None,
) -> None:
    """Run bisection with all parameters specified - supports re-runs."""
    if dry_run:
        print_summary_table(script_path, package, repo_url, good_ref, bad_ref)
        console.print(
            "[yellow]🏃 Dry run mode - no actual bisection will be performed[/yellow]"
        )
        return

    # Validate and potentially swap refs
    good_ref, bad_ref = validate_and_fix_refs(good_ref, bad_ref, inverse)

    # Show confirmation and allow parameter editing
    should_start, updated_params = confirm_bisection_params(
        script_path,
        package,
        good_ref,
        bad_ref,
        repo_url,
        test_command,
        inverse,
        auto_confirm=yes,
    )

    if not should_start:
        console.print("[yellow]⚠️ Bisection cancelled[/yellow]")
        return

    # Apply any parameter changes from user editing
    package = str(updated_params["package"])
    good_ref = str(updated_params["good_ref"])
    bad_ref = str(updated_params["bad_ref"])
    repo_url = str(updated_params["repo_url"])
    test_command = (
        updated_params["test_command"]
        if updated_params["test_command"] is None
        else str(updated_params["test_command"])
    )
    inverse = bool(updated_params["inverse"])

    # Re-validate refs if they were changed
    good_ref, bad_ref = validate_and_fix_refs(good_ref, bad_ref, inverse)

    # Run the bisection
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

    # Let the caller handle end state options to avoid circular imports
    # The CLI will call the end state menu after this function returns
