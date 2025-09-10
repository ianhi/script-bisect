"""End state menu system for re-running bisections with different parameters.

This module provides interactive options after a bisection completes,
allowing users to re-run with different references, scripts, or parameters.
"""

import os
import subprocess
from pathlib import Path

from rich.console import Console

# Import moved inside functions to avoid circular import

console = Console()


def handle_end_state_options(
    script_path: Path,
    package: str,
    good_ref: str,
    bad_ref: str,
    repo_url: str | None,
    test_command: str | None,
    inverse: bool,
    keep_clone: bool,
    verify_endpoints: bool,
    dry_run: bool,
    full_traceback: bool,
    yes: bool,
) -> None:
    """Handle end state options for re-running bisection with different parameters."""
    if yes:
        # Auto-confirmed mode, skip end state options
        return

    console.print("\n[dim]─────────────────────────[/dim]")
    console.print("[bold]End State Options[/bold]")
    console.print("Would you like to:")
    console.print("  1. [green]Exit[/green] - Complete the bisection")
    console.print("  2. [yellow]Re-run with different refs[/yellow]")
    console.print("  3. [cyan]Re-run with different script[/cyan]")
    console.print("  4. [blue]Re-run with modified parameters[/blue]")

    while True:
        try:
            choice = console.input(
                "\nChoose an option [1-4] (or Enter for 1): "
            ).strip()
            if not choice:
                choice = "1"

            if choice == "1":
                return  # Exit normally
            elif choice == "2":
                _rerun_with_different_refs(
                    script_path,
                    package,
                    good_ref,
                    bad_ref,
                    repo_url,
                    test_command,
                    inverse,
                    keep_clone,
                    verify_endpoints,
                    dry_run,
                    full_traceback,
                )
                return
            elif choice == "3":
                _rerun_with_different_script(
                    script_path,
                    package,
                    good_ref,
                    bad_ref,
                    repo_url,
                    test_command,
                    inverse,
                    keep_clone,
                    verify_endpoints,
                    dry_run,
                    full_traceback,
                )
                return
            elif choice == "4":
                _rerun_with_modified_parameters(
                    script_path,
                    package,
                    good_ref,
                    bad_ref,
                    repo_url,
                    test_command,
                    inverse,
                    keep_clone,
                    verify_endpoints,
                    dry_run,
                    full_traceback,
                )
                return
            else:
                console.print(
                    f"[red]Invalid choice '{choice}'. Please enter 1, 2, 3, or 4.[/red]"
                )

        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Exiting...[/yellow]")
            return


def _rerun_with_different_refs(
    script_path: Path,
    package: str,
    good_ref: str,
    bad_ref: str,
    repo_url: str | None,
    test_command: str | None,
    inverse: bool,
    keep_clone: bool,
    verify_endpoints: bool,
    dry_run: bool,
    full_traceback: bool,
) -> None:
    """Re-run bisection with different good/bad refs."""
    console.print("\n[bold]Enter new references (press Enter to keep current):[/bold]")

    new_good_ref = console.input(f"Good ref [{good_ref}]: ").strip()
    if not new_good_ref:
        new_good_ref = good_ref

    new_bad_ref = console.input(f"Bad ref [{bad_ref}]: ").strip()
    if not new_bad_ref:
        new_bad_ref = bad_ref

    console.print(f"\n[dim]Re-running with refs: {new_good_ref} → {new_bad_ref}[/dim]")

    # Re-run the bisection with new refs
    from script_bisect.bisection_orchestrator import run_bisection_with_params

    # Only run if repo_url is not None
    if repo_url:
        run_bisection_with_params(
            script_path=script_path,
            package=package,
            good_ref=new_good_ref,
            bad_ref=new_bad_ref,
            repo_url=repo_url,
            test_command=test_command,
            inverse=inverse,
            keep_clone=keep_clone,
            verify_endpoints=verify_endpoints,
            dry_run=dry_run,
            full_traceback=full_traceback,
            yes=False,  # Allow interactive choices on re-run
        )

    # After bisection completes, re-offer end state options
    handle_end_state_options(
        script_path=script_path,
        package=package,
        good_ref=new_good_ref,
        bad_ref=new_bad_ref,
        repo_url=repo_url,
        test_command=test_command,
        inverse=inverse,
        keep_clone=keep_clone,
        verify_endpoints=verify_endpoints,
        dry_run=dry_run,
        full_traceback=full_traceback,
        yes=False,
    )


def _rerun_with_different_script(
    script_path: Path,
    package: str,
    good_ref: str,
    bad_ref: str,
    repo_url: str | None,
    test_command: str | None,
    inverse: bool,
    keep_clone: bool,
    verify_endpoints: bool,
    dry_run: bool,
    full_traceback: bool,
) -> None:
    """Re-run bisection with a modified script."""
    console.print("\n[bold]Script modification options:[/bold]")
    console.print("  1. [green]Edit current script[/green]")
    console.print("  2. [yellow]Use different script file[/yellow]")

    while True:
        try:
            choice = console.input("Choose [1-2]: ").strip()

            if choice == "1":
                console.print(f"\n[dim]Opening {script_path} for editing...[/dim]")
                console.print(
                    "[yellow]Please edit the script and save it, then press Enter to continue.[/yellow]"
                )

                # Use the consolidated editor integration
                from .editor_integration import EditorIntegration
                editor = EditorIntegration()
                
                try:
                    opened = editor.launch_editor(script_path)
                except Exception:
                    opened = False

                if not opened:
                    console.print(
                        f"[yellow]Could not auto-open editor. Please manually edit: {script_path}[/yellow]"
                    )

                console.input("Press Enter when done editing...")
                break

            elif choice == "2":
                new_script_path = console.input("Enter path to new script: ").strip()
                if new_script_path and Path(new_script_path).exists():
                    script_path = Path(new_script_path)
                    break
                else:
                    console.print("[red]Script file not found![/red]")
                    continue

            else:
                console.print(
                    f"[red]Invalid choice '{choice}'. Please enter 1 or 2.[/red]"
                )

        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Cancelled script modification.[/yellow]")
            return

    # Re-run the bisection with the (potentially modified) script
    from script_bisect.bisection_orchestrator import run_bisection_with_params

    # Only run if repo_url is not None
    if repo_url:
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
            yes=False,  # Allow interactive choices on re-run
        )

    # After bisection completes, re-offer end state options
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
        yes=False,
    )


def _rerun_with_modified_parameters(
    script_path: Path,
    package: str,
    good_ref: str,
    bad_ref: str,
    repo_url: str | None,
    test_command: str | None,
    inverse: bool,
    keep_clone: bool,
    verify_endpoints: bool,
    dry_run: bool,
    full_traceback: bool,
) -> None:
    """Re-run bisection with modified parameters."""
    console.print("\n[bold]Current parameters:[/bold]")
    console.print(f"  Package: {package}")
    console.print(f"  Repository URL: {repo_url or 'auto-detected'}")
    console.print(f"  Test command: {test_command or f'uv run {script_path.name}'}")
    console.print(f"  Inverse mode: {inverse}")
    console.print(f"  Verify endpoints: {verify_endpoints}")

    console.print("\n[bold]Modify parameters (press Enter to keep current):[/bold]")

    new_package = console.input(f"Package [{package}]: ").strip()
    if not new_package:
        new_package = package

    new_repo_url_input = console.input(
        f"Repository URL [{repo_url or 'auto-detect'}]: "
    ).strip()
    if not new_repo_url_input:
        new_repo_url: str | None = repo_url
    elif new_repo_url_input.lower() in ("auto", "auto-detect", "none"):
        new_repo_url = None
    else:
        new_repo_url = new_repo_url_input

    new_test_command_input = console.input(
        f"Test command [{test_command or f'uv run {script_path.name}'}]: "
    ).strip()
    if not new_test_command_input:
        new_test_command: str | None = test_command
    elif new_test_command_input.lower() in ("default", "auto", "none"):
        new_test_command = None
    else:
        new_test_command = new_test_command_input

    inverse_input = (
        console.input(f"Inverse mode [{'yes' if inverse else 'no'}]: ").strip().lower()
    )
    if inverse_input in ("y", "yes", "true", "1"):
        new_inverse = True
    elif inverse_input in ("n", "no", "false", "0"):
        new_inverse = False
    else:
        new_inverse = inverse  # Keep current value

    verify_input = (
        console.input(f"Verify endpoints [{'yes' if verify_endpoints else 'no'}]: ")
        .strip()
        .lower()
    )
    if verify_input in ("y", "yes", "true", "1"):
        new_verify_endpoints = True
    elif verify_input in ("n", "no", "false", "0"):
        new_verify_endpoints = False
    else:
        new_verify_endpoints = verify_endpoints  # Keep current value

    # Re-run the bisection with new parameters
    from script_bisect.bisection_orchestrator import run_bisection_with_params

    # Only run if new_repo_url is not None
    if new_repo_url:
        run_bisection_with_params(
            script_path=script_path,
            package=new_package,
            good_ref=good_ref,
            bad_ref=bad_ref,
            repo_url=new_repo_url,
            test_command=new_test_command,
            inverse=new_inverse,
            keep_clone=keep_clone,
            verify_endpoints=new_verify_endpoints,
            dry_run=dry_run,
            full_traceback=full_traceback,
            yes=False,  # Allow interactive choices on re-run
        )

    # After bisection completes, re-offer end state options
    handle_end_state_options(
        script_path=script_path,
        package=new_package,
        good_ref=good_ref,
        bad_ref=bad_ref,
        repo_url=new_repo_url,
        test_command=new_test_command,
        inverse=new_inverse,
        keep_clone=keep_clone,
        verify_endpoints=new_verify_endpoints,
        dry_run=dry_run,
        full_traceback=full_traceback,
        yes=False,
    )


# Removed _open_editor_safely function - now using consolidated EditorIntegration
