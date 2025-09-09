"""Interactive prompts for missing script-bisect parameters."""

from __future__ import annotations

import re
import subprocess
from typing import TYPE_CHECKING

from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

if TYPE_CHECKING:
    from pathlib import Path

    from prompt_toolkit.document import Document

console = Console()


def prompt_for_package(available_packages: list[str]) -> str:
    """Prompt user to select a package from available options.

    Args:
        available_packages: List of available package names

    Returns:
        Selected package name
    """
    if not available_packages:
        console.print("[red]❌ No packages found in script dependencies[/red]")
        raise SystemExit(1)

    if len(available_packages) == 1:
        package = available_packages[0]
        console.print(f"[green]📦 Using package: {package}[/green]")
        return package

    # Show available packages in a table
    table = Table(title="Available Packages", show_header=True)
    table.add_column("Index", style="cyan", width=8)
    table.add_column("Package Name", style="white")

    for i, pkg in enumerate(available_packages, 1):
        table.add_row(str(i), pkg)

    console.print(table)
    console.print()

    while True:
        try:
            choice = Prompt.ask(
                "[bold cyan]Select package to bisect[/bold cyan]",
                choices=[str(i) for i in range(1, len(available_packages) + 1)]
                + available_packages,
            )

            # Handle numeric choice
            if choice.isdigit():
                index = int(choice) - 1
                if 0 <= index < len(available_packages):
                    return available_packages[index]

            # Handle direct package name
            if choice in available_packages:
                return choice

            console.print("[red]Invalid choice. Please try again.[/red]")

        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️ Cancelled by user[/yellow]")
            raise SystemExit(130)


def prompt_for_refs(
    package: str,
    repo_url: str | None = None,
    good_ref: str | None = None,
    bad_ref: str | None = None,
) -> tuple[str, str]:
    """Prompt user for missing git references with autocompletion.

    Args:
        package: Package name being bisected
        repo_url: Repository URL (optional, for context)
        good_ref: Existing good reference (won't prompt if provided)
        bad_ref: Existing bad reference (won't prompt if provided)

    Returns:
        Tuple of (good_ref, bad_ref)
    """
    console.print(f"\n[bold blue]🔍 Bisecting package: {package}[/bold blue]")

    if repo_url:
        console.print(f"[dim]Repository: {repo_url}[/dim]")

    # Only fetch refs if we need to prompt for at least one
    available_refs = []
    if (not good_ref or not bad_ref) and repo_url:
        console.print("[dim]🔍 Fetching available git references...[/dim]")
        available_refs = _fetch_git_refs(repo_url)

        if available_refs:
            console.print(
                f"[dim]Found {len(available_refs)} references for autocompletion[/dim]"
            )

            # Show some recent refs as examples
            recent_refs = _get_recent_refs(available_refs)
            if recent_refs:
                console.print("\n[dim]Recent references:[/dim]")
                for ref in recent_refs[:10]:  # Show up to 10
                    console.print(f"  • {ref}")
                if len(recent_refs) > 10:
                    console.print(f"  ... and {len(recent_refs) - 10} more")
        else:
            console.print("[dim]Could not fetch refs - manual entry required[/dim]")

    # Only show instructions if we need to prompt for at least one ref
    if not good_ref or not bad_ref:
        console.print("\n[bold]Git References:[/bold]")
        console.print(
            "You need to specify a '[green]good[/green]' commit/tag where the package works correctly,"
        )
        console.print("and a '[red]bad[/red]' commit/tag where the issue is present.")
        console.print()

        if not available_refs:
            console.print("[dim]Examples:[/dim]")
            console.print("  • Tags: v1.2.0, v2025.08.0, 2.1.1")
            console.print("  • Branches: main, develop, release/v2.0")
            console.print("  • Commit SHAs: abc123, 1a2b3c4d")
            console.print()

    # Prompt for good_ref only if not provided
    if not good_ref:
        while True:
            try:
                if available_refs:
                    good_ref = _prompt_with_completion(
                        "[green]✅ Good reference (working version)[/green]",
                        available_refs,
                    )
                else:
                    good_ref = Prompt.ask(
                        "[green]✅ Good reference (working version)[/green]",
                        default="",
                    )

                if not good_ref:
                    console.print("[red]Good reference is required.[/red]")
                    continue

                if not _is_valid_git_ref(good_ref):
                    console.print("[red]Invalid git reference format.[/red]")
                    continue

                break

            except KeyboardInterrupt:
                console.print("\n[yellow]⚠️ Cancelled by user[/yellow]")
                raise SystemExit(130)
    else:
        # Show the already-entered good ref
        console.print(f"[green]✅ Good reference (working version)[/green]: {good_ref}")

    # Prompt for bad_ref only if not provided
    if not bad_ref:
        while True:
            try:
                if available_refs:
                    bad_ref = _prompt_with_completion(
                        "[red]❌ Bad reference (broken version)[/red]", available_refs
                    )
                else:
                    bad_ref = Prompt.ask(
                        "[red]❌ Bad reference (broken version)[/red]",
                        default="",
                    )

                if not bad_ref:
                    console.print("[red]Bad reference is required.[/red]")
                    continue

                if not _is_valid_git_ref(bad_ref):
                    console.print("[red]Invalid git reference format.[/red]")
                    continue

                if bad_ref == good_ref:
                    console.print(
                        "[red]Bad reference must be different from good reference.[/red]"
                    )
                    continue

                break

            except KeyboardInterrupt:
                console.print("\n[yellow]⚠️ Cancelled by user[/yellow]")
                raise SystemExit(130)
    else:
        # Show the already-entered bad ref
        console.print(f"[red]❌ Bad reference (broken version)[/red]: {bad_ref}")

    return good_ref, bad_ref


def prompt_for_repo_url(package: str) -> str:
    """Prompt user for repository URL when auto-detection fails.

    Args:
        package: Package name being bisected

    Returns:
        Repository URL
    """
    console.print(
        f"\n[yellow]⚠️ Could not auto-detect repository URL for '{package}'[/yellow]"
    )
    console.print("\n[bold]Repository URL needed:[/bold]")
    console.print("Please provide the Git repository URL for bisection.")
    console.print()
    console.print("[dim]Examples:[/dim]")
    console.print("  • https://github.com/user/repo")
    console.print("  • git+https://github.com/user/repo.git")
    console.print("  • git@github.com:user/repo.git")
    console.print()

    while True:
        try:
            repo_url = Prompt.ask(
                "[cyan]🔗 Repository URL[/cyan]",
                default="",
            ).strip()

            if not repo_url:
                console.print("[red]Repository URL is required.[/red]")
                continue

            if not _is_valid_repo_url(repo_url):
                console.print("[red]Invalid repository URL format.[/red]")
                continue

            return repo_url

        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️ Cancelled by user[/yellow]")
            raise SystemExit(130)


def confirm_bisection_params(
    script_path: Path,
    package: str,
    good_ref: str,
    bad_ref: str,
    repo_url: str,
    test_command: str | None = None,
    inverse: bool = False,
) -> bool:
    """Show bisection parameters and ask for confirmation.

    Args:
        script_path: Path to the script
        package: Package name
        good_ref: Good git reference
        bad_ref: Bad git reference
        repo_url: Repository URL
        test_command: Custom test command (optional)
        inverse: Whether this is inverse bisection

    Returns:
        True if user confirms, False otherwise
    """
    console.print("\n[bold blue]🔄 Bisection Summary[/bold blue]")

    table = Table(show_header=False)
    table.add_column("Parameter", style="cyan", width=20)
    table.add_column("Value", style="white")

    table.add_row("📄 Script", str(script_path))
    table.add_row("📦 Package", package)
    table.add_row("🔗 Repository", repo_url)
    table.add_row("✅ Good ref", good_ref)
    table.add_row("❌ Bad ref", bad_ref)

    if test_command:
        table.add_row("🧪 Test command", test_command)
    else:
        table.add_row("🧪 Test command", f"uv run {script_path.name}")

    if inverse:
        table.add_row("🔄 Mode", "Inverse (find when fixed)")
    else:
        table.add_row("🔄 Mode", "Normal (find when broken)")

    console.print(table)
    console.print()

    try:
        return Confirm.ask("[bold cyan]Start bisection?[/bold cyan]", default=True)
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Cancelled by user[/yellow]")
        raise SystemExit(130)


def _is_valid_git_ref(ref: str) -> bool:
    """Check if a string looks like a valid git reference.

    Args:
        ref: Git reference to validate

    Returns:
        True if valid-looking reference
    """
    if not ref or len(ref.strip()) < 1:
        return False

    ref = ref.strip()

    # Check for obviously invalid characters (but allow ~ for HEAD~1, etc.)
    invalid_chars = [" ", "\t", "\n", "\r", "..", "^{", "?", "*", "[", "\\", "~~"]
    if any(char in ref for char in invalid_chars):
        return False

    # Special handling for valid patterns with colons (like origin/main)
    if ":" in ref and not ref.startswith("git@"):
        return False

    # Must not start with - or be just dots
    return not (ref.startswith("-") or ref in [".", ".."])


def _is_valid_repo_url(url: str) -> bool:
    """Check if a string looks like a valid repository URL.

    Args:
        url: Repository URL to validate

    Returns:
        True if valid-looking URL
    """
    if not url or len(url.strip()) < 5:
        return False

    url = url.strip()

    # Common valid patterns
    patterns = [
        r"^https?://[^/\s]+/[^/\s]+/[^/\s]+",  # HTTP(S) URLs
        r"^git\+https?://[^/\s]+/[^/\s]+/[^/\s]+",  # git+http(s) URLs
        r"^git@[^:\s]+:[^/\s]+/[^/\s]+",  # SSH URLs
        r"^ssh://git@[^/\s]+/[^/\s]+/[^/\s]+",  # SSH URLs with protocol
    ]

    return any(re.match(pattern, url) for pattern in patterns)


def _fetch_git_refs(repo_url: str) -> list[str]:
    """Fetch available git references from a repository.

    Args:
        repo_url: Repository URL to fetch refs from

    Returns:
        List of available git references (tags, branches)
    """
    refs = []

    # Clean up repo URL
    clean_url = repo_url
    if clean_url.startswith("git+"):
        clean_url = clean_url[4:]

    try:
        # Fetch remote refs without cloning
        result = subprocess.run(
            ["git", "ls-remote", "--heads", "--tags", clean_url],
            capture_output=True,
            text=True,
            timeout=30,  # 30 second timeout
        )

        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if "\t" in line:
                    sha, ref = line.split("\t", 1)

                    # Extract branch names
                    if ref.startswith("refs/heads/"):
                        branch_name = ref[len("refs/heads/") :]
                        refs.append(branch_name)

                    # Extract tag names
                    elif ref.startswith("refs/tags/"):
                        tag_name = ref[len("refs/tags/") :]
                        # Skip annotated tag objects (ending with ^{})
                        if not tag_name.endswith("^{}"):
                            refs.append(tag_name)

    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        # git command failed or not available
        pass

    return sorted(set(refs))  # Remove duplicates and sort


def _get_recent_refs(refs: list[str]) -> list[str]:
    """Get recent git references from the list.

    Prioritizes version tags (newest first), then main branches.

    Args:
        refs: List of all available references

    Returns:
        List of recent references in priority order
    """
    recent = []

    # Priority 1: Version tags (sorted by apparent version, newest first)
    version_refs = []
    for ref in refs:
        if re.match(r"^v?\d+(\.\d+)*", ref):
            version_refs.append(ref)

    # Sort version tags by version number (newest first)
    version_refs.sort(key=_version_sort_key, reverse=True)
    recent.extend(version_refs)  # All version tags, newest first

    # Priority 2: Main branches
    main_branches = ["main", "master", "develop", "dev", "trunk"]
    for branch in main_branches:
        if branch in refs and branch not in recent:
            recent.append(branch)

    # Priority 3: Other branches (limit to avoid clutter)
    other_branches = [
        ref
        for ref in refs
        if not re.match(r"^v?\d+(\.\d+)*", ref)
        and ref not in main_branches
        and ref not in recent
    ]
    recent.extend(other_branches[:5])  # Add up to 5 other refs

    return recent


def _version_sort_key(version_ref: str) -> tuple[int, ...]:
    """Create a sort key for version references.

    Args:
        version_ref: Version reference like 'v1.2.0' or '2025.08.0'

    Returns:
        Tuple of integers for sorting
    """
    # Extract numeric version parts
    match = re.search(r"v?(\d+(?:\.\d+)*)", version_ref)
    if match:
        try:
            return tuple(int(x) for x in match.group(1).split("."))
        except ValueError:
            pass

    return (0,)  # Default for non-parseable versions


def _prompt_with_completion(prompt_text: str, choices: list[str]) -> str:
    """Prompt with tab autocompletion support using prompt-toolkit.

    Args:
        prompt_text: Text to display for the prompt
        choices: List of choices for autocompletion

    Returns:
        User's selected/entered value
    """
    try:
        from prompt_toolkit import prompt
        from prompt_toolkit.completion import Completer, Completion
        from prompt_toolkit.shortcuts import CompleteStyle
    except ImportError:
        # Fallback to Rich prompt if prompt-toolkit not available
        from rich.prompt import Prompt

        return Prompt.ask(f"{prompt_text} (no tab completion available)", default="")

    # Strip rich formatting for the prompt
    import re

    clean_prompt = re.sub(r"\[.*?\]", "", prompt_text)
    clean_prompt += ": "

    # Sort choices to put newer versions first (reverse the recent_refs ordering)
    # For autocomplete, we want the most recent/relevant options at the top
    def sort_key(x: str) -> tuple:
        is_version = re.match(r"^v?\d+(\.\d+)*", x) is not None
        if is_version:
            # Version tags first, newest first (negate each component for reverse order)
            version_tuple = _version_sort_key(x)
            negated_version = tuple(-v for v in version_tuple)  # Negate each number
            return (0, negated_version)  # 0 = highest priority
        else:
            # Non-version refs second, alphabetical
            return (1, x.lower())

    sorted_choices = sorted(choices, key=sort_key)

    # Create custom completer that handles partial matches correctly
    class GitRefCompleter(Completer):
        def get_completions(
            self, document: Document, _complete_event: object
        ) -> list[Completion]:
            text_before_cursor = document.text_before_cursor

            matches = []
            for choice in sorted_choices:
                # Case-insensitive substring matching
                if text_before_cursor.lower() in choice.lower():
                    start_position = -len(text_before_cursor)
                    matches.append(
                        Completion(
                            text=choice, start_position=start_position, display=choice
                        )
                    )

            return matches

    completer = GitRefCompleter()

    try:
        while True:
            user_input = prompt(
                clean_prompt,
                completer=completer,
                complete_style=CompleteStyle.MULTI_COLUMN,
                mouse_support=True,
            )

            if user_input:
                return str(user_input).strip()
            console.print("[yellow]Please enter a git reference[/yellow]")

    except (EOFError, KeyboardInterrupt):
        console.print("\n[yellow]⚠️ Cancelled by user[/yellow]")
        raise SystemExit(130)
