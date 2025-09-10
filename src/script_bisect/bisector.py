"""Git bisection orchestration for script-bisect using binary search."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from .exceptions import GitError, RepositoryError
from .parser import ScriptParser
from .repository_manager import RepositoryManager
from .runner import TestRunner
from .utils import create_temp_dir, format_commit_info

if TYPE_CHECKING:
    from pathlib import Path

    import git

logger = logging.getLogger(__name__)
console = Console()


class BisectResult:
    """Result of a git bisect operation."""

    def __init__(
        self,
        found_commit: str | None = None,
        commit_info: dict[str, Any] | None = None,
        is_regression: bool = True,
    ) -> None:
        self.found_commit = found_commit
        self.commit_info = commit_info or {}
        self.is_regression = is_regression

    @property
    def success(self) -> bool:
        """Whether bisection found a clear result."""
        return self.found_commit is not None


class GitBisector:
    """Orchestrates git bisection using binary search for PEP 723 scripts."""

    def __init__(
        self,
        script_path: Path,
        package: str,
        repo_url: str,
        good_ref: str,
        bad_ref: str,
        test_command: str | None = None,
        clone_dir: Path | None = None,
        keep_clone: bool = False,
        inverse: bool = False,
        skip_verification: bool = False,
    ) -> None:
        """Initialize the git bisector.

        Args:
            script_path: Path to the PEP 723 script
            package: Name of the package to bisect
            repo_url: Git repository URL
            good_ref: Git reference for the good commit
            bad_ref: Git reference for the bad commit
            test_command: Custom test command (default: uv run script)
            clone_dir: Directory for repository clone (default: temp)
            keep_clone: Whether to keep the cloned repository
            inverse: Whether to find when something was fixed (not broken)
            skip_verification: Skip endpoint verification for faster startup
        """
        self.script_path = script_path
        self.package = package
        self.repo_url = repo_url
        self.good_ref = good_ref
        self.bad_ref = bad_ref
        self.test_command = test_command
        self.clone_dir = clone_dir or create_temp_dir("script_bisect_repo_")
        self.keep_clone = keep_clone
        self.inverse = inverse
        self.skip_verification = skip_verification

        # Initialize components
        self.parser = ScriptParser(script_path)
        self.repo_manager = RepositoryManager(repo_url)
        self.repo: git.Repo | None = None
        self.test_runner: TestRunner | None = None

    def run(self) -> BisectResult:
        """Run the complete bisection process using binary search.

        Returns:
            BisectResult containing the outcome

        Raises:
            GitError: If there's an error with git operations
            RepositoryError: If there's an error with the repository
        """
        start_time = time.time()

        try:
            # Step 1: Set up optimized repository
            self.clone_dir = self.repo_manager.setup_repository(
                self.good_ref, self.bad_ref
            )
            self.repo = self.repo_manager.repo

            # Step 2: Validate refs
            self._validate_refs()

            # Step 3: Set up test runner
            self._setup_test_runner()

            # Step 4: Run binary search bisection
            commit_info, commits_tested = self._run_binary_search()

            # Step 5: Show performance report
            self._show_performance_report(start_time, commits_tested)

            if commit_info:
                return BisectResult(
                    found_commit=commit_info["commit_hash"],
                    commit_info=commit_info,
                    is_regression=not self.inverse,
                )
            else:
                return BisectResult()

        finally:
            self._cleanup()

    def _validate_refs(self) -> None:
        """Validate that the good and bad refs exist in the repository."""
        try:
            # Use repository manager to resolve references
            good_hash = self.repo_manager.resolve_reference(self.good_ref)
            bad_hash = self.repo_manager.resolve_reference(self.bad_ref)

            console.print(f"✅ Good ref '{self.good_ref}' → {good_hash[:12]}")
            console.print(f"❌ Bad ref '{self.bad_ref}' → {bad_hash[:12]}")

        except ValueError as e:
            raise GitError(f"Invalid git reference: {e}") from e

    def _setup_test_runner(self) -> None:
        """Set up the test runner for bisection."""
        self.test_runner = TestRunner(
            script_path=self.script_path,
            package=self.package,
            repo_url=self.repo_url,
            test_command=self.test_command,
        )

    def _get_commit_range(self) -> list[git.Commit]:
        """Get the list of commits between good and bad refs in chronological order."""
        if not self.repo:
            raise RepositoryError("Repository not initialized")

        try:
            # Use repository manager to get commit range efficiently
            commit_shas = self.repo_manager.get_commit_range(
                self.good_ref, self.bad_ref
            )

            if not commit_shas:
                raise GitError(
                    f"No commits found between {self.good_ref} and {self.bad_ref}"
                )

            # Convert SHAs to commit objects
            commits = [self.repo.commit(sha) for sha in commit_shas]

            # Commit count shown in user-friendly format below
            return commits

        except ValueError as e:
            raise GitError(f"Failed to get commit range: {e}") from e

    def _test_commit(self, commit: git.Commit) -> tuple[bool | None, str | None]:
        """Test a specific commit.

        Returns:
            Tuple of (result, error_message) where:
            - result: True if test passes (good), False if test fails (bad), None if untestable
            - error_message: Error description if test failed, None if passed or untestable
        """
        if not self.test_runner:
            raise RepositoryError("Test runner not initialized")

        try:
            result = self.test_runner.test_commit(commit.hexsha, return_error=True)
            if isinstance(result, tuple):
                success, error_msg = result
            else:
                # This shouldn't happen when return_error=True, but handle it
                success, error_msg = result, None

            # Handle inverse mode
            if self.inverse:
                return (not success if success is not None else None), error_msg
            return success, error_msg

        except Exception as e:
            logger.warning(f"Error testing commit {commit.hexsha[:12]}: {e}")
            return None, f"Test execution error: {e}"

    def _run_binary_search(self) -> tuple[dict[str, Any] | None, int]:
        """Run binary search bisection to find the first bad commit."""
        try:
            # Get the commit range
            commits = self._get_commit_range()

            if not commits:
                console.print("[yellow]⚠️ No commits found in range[/yellow]")
                return None, 0

            console.print(
                f"[dim]Found {len(commits)} commits between {self.good_ref} and {self.bad_ref}[/dim]"
            )

            # Verify the endpoints (unless skipped)
            if not self.skip_verification:
                console.print("\n[dim]🔍 Verifying endpoints...[/dim]")

                # Check that good_ref is actually good
                console.print(f"    Testing {self.good_ref}...")
                assert self.repo  # For mypy
                good_commit = self.repo.commit(self.good_ref)
                good_result, good_error = self._test_commit(good_commit)
                if good_result is False:
                    console.print(
                        f"[red]❌ Good ref '{self.good_ref}' is not actually good![/red]"
                    )
                    return None, 0
                elif good_result is None:
                    if good_error:
                        console.print(
                            f"[yellow]⚠️ Could not test good ref '{self.good_ref}': {good_error}[/yellow]"
                        )
                    else:
                        console.print(
                            f"[yellow]⚠️ Could not test good ref '{self.good_ref}' - continuing anyway[/yellow]"
                        )
                else:
                    console.print(f"    ✅ {self.good_ref} is good")

                # Check that bad_ref is actually bad
                console.print(f"    Testing {self.bad_ref}...")
                bad_commit = self.repo.commit(self.bad_ref)
                bad_result, bad_error = self._test_commit(bad_commit)
                if bad_result is True:
                    console.print(
                        f"[red]❌ Bad ref '{self.bad_ref}' is not actually bad![/red]"
                    )
                    return None, 0
                elif bad_result is None:
                    if bad_error:
                        console.print(
                            f"[yellow]⚠️ Could not test bad ref '{self.bad_ref}': {bad_error}[/yellow]"
                        )
                    else:
                        console.print(
                            f"[yellow]⚠️ Could not test bad ref '{self.bad_ref}' - continuing anyway[/yellow]"
                        )
                else:
                    if bad_error:
                        console.print(f"    ❌ {self.bad_ref} is bad - {bad_error}")
                    else:
                        console.print(f"    ❌ {self.bad_ref} is bad")
            else:
                console.print("\n[dim]⏩ Skipping endpoint verification[/dim]")

            # Run binary search
            console.print("\n[bold blue]🔄 Starting binary search...[/bold blue]")
            first_bad_commit = self._binary_search_commits(commits)
            commits_tested = len(commits)  # Placeholder - will be improved later

            if first_bad_commit:
                commit_info = {
                    "commit_hash": first_bad_commit.hexsha,
                    "author": f"{first_bad_commit.author.name} <{first_bad_commit.author.email}>",
                    "date": first_bad_commit.committed_datetime.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "message": str(first_bad_commit.message)
                    .strip()
                    .split("\n")[0]
                    .strip()
                    if first_bad_commit.message
                    else "No message",
                }

                console.print(
                    f"\n[green]✨ Found first bad commit: {first_bad_commit.hexsha[:12]}[/green]"
                )
                console.print(
                    format_commit_info(
                        commit_info["commit_hash"],
                        commit_info["author"],
                        commit_info["date"],
                        commit_info["message"],
                        self.repo_url,
                    )
                )

                return commit_info, commits_tested
            else:
                console.print(
                    "\n[yellow]⚠️ Could not find a clear first bad commit[/yellow]"
                )
                return None, commits_tested

        except Exception as e:
            logger.error(f"Bisection failed: {e}")
            raise GitError(f"Bisection failed: {e}") from e

    def _binary_search_commits(self, commits: list[git.Commit]) -> git.Commit | None:
        """Perform binary search on commits to find the first bad commit."""
        left = 0
        right = len(commits) - 1
        first_bad = None

        steps = 0
        total_steps = len(commits).bit_length()  # Approximate number of steps needed

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"Bisecting {len(commits)} commits...", total=total_steps
            )

            while left <= right:
                steps += 1
                mid = (left + right) // 2
                commit = commits[mid]

                progress.update(
                    task,
                    description=f"Step {steps}/{total_steps}: Testing commit {commit.hexsha[:12]}",
                    advance=1,
                )

                # Get just the first line of the commit message and clean it
                if commit.message:
                    # Get first line and replace any remaining newlines with spaces
                    subject = str(commit.message).strip().split("\n")[0].strip()
                    # Replace any remaining newline chars that might be embedded
                    subject = subject.replace("\n", " ").replace("\r", " ")
                    # Clean up multiple spaces
                    subject = " ".join(subject.split())
                else:
                    subject = "No message"

                console.print(f"  🔍 Testing commit {commit.hexsha[:12]} ({subject})")

                result, error_msg = self._test_commit(commit)

                if result is None:
                    # Untestable commit, skip it
                    if error_msg:
                        console.print(f"    ⚠️  Skipping untestable commit: {error_msg}")
                    else:
                        console.print("    ⚠️  Skipping untestable commit")
                    # Remove this commit and continue
                    commits.pop(mid)
                    if mid <= (left + right) // 2:
                        right -= 1
                    continue

                if result:  # Good commit
                    console.print("    ✅ Good")
                    left = mid + 1
                else:  # Bad commit
                    if error_msg:
                        console.print(f"    ❌ Bad - {error_msg}")
                    else:
                        console.print("    ❌ Bad")
                    first_bad = commit
                    right = mid - 1

            progress.update(
                task, description="✨ Bisection complete!", completed=total_steps
            )

        return first_bad

    def _show_performance_report(self, start_time: float, commits_tested: int) -> None:
        """Show performance report with commits tested and time taken."""
        elapsed_time = time.time() - start_time

        # Format time display
        if elapsed_time < 60:
            time_str = f"{elapsed_time:.1f} seconds"
        elif elapsed_time < 3600:
            minutes = elapsed_time / 60
            time_str = f"{minutes:.1f} minutes"
        else:
            hours = elapsed_time / 3600
            time_str = f"{hours:.1f} hours"

        console.print(f"\n[dim]⏱️ Tested {commits_tested} commits in {time_str}[/dim]")

    def _cleanup(self) -> None:
        """Clean up resources after bisection."""
        if self.test_runner:
            self.test_runner.cleanup()

        if not self.keep_clone:
            self.repo_manager.cleanup()
        elif self.keep_clone:
            console.print(f"[dim]📁 Repository kept at: {self.clone_dir}[/dim]")
