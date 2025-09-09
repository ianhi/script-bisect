"""Git bisection orchestration for script-bisect using binary search."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

import git
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from .exceptions import GitError, RepositoryError
from .parser import ScriptParser
from .runner import TestRunner
from .utils import create_temp_dir, format_commit_info


logger = logging.getLogger(__name__)
console = Console()


class BisectResult:
    """Result of a git bisect operation."""
    
    def __init__(
        self,
        found_commit: str | None = None,
        commit_info: dict[str, Any] | None = None,
        is_regression: bool = True,
        steps_taken: int = 0,
    ) -> None:
        self.found_commit = found_commit
        self.commit_info = commit_info or {}
        self.is_regression = is_regression
        self.steps_taken = steps_taken
    
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
        try:
            # Step 1: Clone the repository  
            self._clone_repository()
            
            # Step 2: Validate refs
            self._validate_refs()
            
            # Step 3: Set up test runner
            self._setup_test_runner()
            
            # Step 4: Run binary search bisection
            commit_info = self._run_binary_search()
            
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
    
    def _clone_repository(self) -> None:
        """Clone the repository for bisection with optimized history fetching."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Cloning repository (shallow)...", total=None)
            
            try:
                # Clean the URL for git clone
                clone_url = self.repo_url
                if clone_url.startswith("git+"):
                    clone_url = clone_url[4:]  # Remove git+ prefix
                
                logger.info(f"Shallow cloning {clone_url} to {self.clone_dir}")
                
                # First do a shallow clone to minimize initial download
                self.repo = git.Repo.clone_from(
                    clone_url, 
                    self.clone_dir,
                    depth=1
                )
                
                progress.update(task, description="Fetching history for bisection...")
                
                # Now fetch the specific refs we need for bisection
                # This fetches only the commits between good and bad refs
                try:
                    self.repo.git.fetch("origin", f"{self.good_ref}:{self.good_ref}", "--depth=50")
                except git.GitCommandError:
                    # Ref might already exist or be a commit hash, try fetching more broadly
                    self.repo.git.fetch("origin", self.good_ref, "--depth=50")
                
                try:
                    self.repo.git.fetch("origin", f"{self.bad_ref}:{self.bad_ref}", "--depth=50")
                except git.GitCommandError:
                    self.repo.git.fetch("origin", self.bad_ref, "--depth=50")
                
                # Unshallow the repository to allow bisection
                progress.update(task, description="Preparing for bisection...")
                self.repo.git.fetch("--unshallow")
                
                progress.update(task, description="✅ Repository ready for bisection")
                
            except Exception as e:
                raise RepositoryError(f"Failed to clone repository: {e}") from e
    
    def _validate_refs(self) -> None:
        """Validate that the good and bad refs exist in the repository."""
        if not self.repo:
            raise RepositoryError("Repository not initialized")
        
        try:
            # Check if refs exist
            good_commit = self.repo.commit(self.good_ref)
            bad_commit = self.repo.commit(self.bad_ref)
            
            console.print(f"✅ Good ref '{self.good_ref}' → {good_commit.hexsha[:12]}")
            console.print(f"❌ Bad ref '{self.bad_ref}' → {bad_commit.hexsha[:12]}")
            
        except git.BadName as e:
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
            # Get the commit range using git rev-list
            # This gives us commits from good_ref to bad_ref in reverse chronological order
            commit_shas = self.repo.git.rev_list(
                f"{self.good_ref}..{self.bad_ref}",
                "--reverse"  # Get them in chronological order (oldest first)
            ).strip().split('\n')
            
            if not commit_shas or commit_shas == ['']:
                raise GitError(f"No commits found between {self.good_ref} and {self.bad_ref}")
            
            # Convert SHAs to commit objects
            commits = [self.repo.commit(sha) for sha in commit_shas]
            
            logger.info(f"Found {len(commits)} commits to bisect")
            return commits
            
        except git.GitCommandError as e:
            raise GitError(f"Failed to get commit range: {e}") from e
    
    def _test_commit(self, commit: git.Commit) -> bool | None:
        """Test a specific commit.
        
        Returns:
            True if test passes (good), False if test fails (bad), None if untestable
        """
        if not self.test_runner:
            raise RepositoryError("Test runner not initialized")
        
        try:
            success = self.test_runner.test_commit(commit.hexsha)
            
            # Handle inverse mode
            if self.inverse:
                return not success
            return success
            
        except Exception as e:
            logger.warning(f"Error testing commit {commit.hexsha[:12]}: {e}")
            return None  # Untestable
    
    def _run_binary_search(self) -> dict[str, Any] | None:
        """Run binary search bisection to find the first bad commit."""
        try:
            # Get the commit range
            commits = self._get_commit_range()
            
            if not commits:
                console.print("[yellow]⚠️ No commits found in range[/yellow]")
                return None
            
            console.print(f"[dim]Found {len(commits)} commits between {self.good_ref} and {self.bad_ref}[/dim]")
            
            # Verify the endpoints (unless skipped)
            if not self.skip_verification:
                console.print("\\n[dim]🔍 Verifying endpoints...[/dim]")
                
                # Check that good_ref is actually good
                console.print(f"    Testing {self.good_ref}...")
                good_commit = self.repo.commit(self.good_ref)
                good_result = self._test_commit(good_commit)
                if good_result is False:
                    console.print(f"[red]❌ Good ref '{self.good_ref}' is not actually good![/red]")
                    return None
                elif good_result is None:
                    console.print(f"[yellow]⚠️ Could not test good ref '{self.good_ref}' - continuing anyway[/yellow]")
                else:
                    console.print(f"    ✅ {self.good_ref} is good")
                
                # Check that bad_ref is actually bad  
                console.print(f"    Testing {self.bad_ref}...")
                bad_commit = self.repo.commit(self.bad_ref)
                bad_result = self._test_commit(bad_commit)
                if bad_result is True:
                    console.print(f"[red]❌ Bad ref '{self.bad_ref}' is not actually bad![/red]")
                    return None
                elif bad_result is None:
                    console.print(f"[yellow]⚠️ Could not test bad ref '{self.bad_ref}' - continuing anyway[/yellow]") 
                else:
                    console.print(f"    ❌ {self.bad_ref} is bad")
            else:
                console.print("\\n[dim]⏩ Skipping endpoint verification[/dim]")
            
            # Run binary search
            console.print("\\n[bold blue]🔄 Starting binary search...[/bold blue]")
            first_bad_commit = self._binary_search_commits(commits)
            
            if first_bad_commit:
                commit_info = {
                    "commit_hash": first_bad_commit.hexsha,
                    "author": f"{first_bad_commit.author.name} <{first_bad_commit.author.email}>",
                    "date": first_bad_commit.committed_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                    "message": first_bad_commit.message.strip().split('\\n')[0].strip() if first_bad_commit.message else "No message",
                }
                
                console.print(f"\\n[green]✨ Found first bad commit: {first_bad_commit.hexsha[:12]}[/green]")
                console.print(format_commit_info(**commit_info))
                
                return commit_info
            else:
                console.print("\\n[yellow]⚠️ Could not find a clear first bad commit[/yellow]")
                return None
                
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
                f"Bisecting {len(commits)} commits...", 
                total=total_steps
            )
            
            while left <= right:
                steps += 1
                mid = (left + right) // 2
                commit = commits[mid]
                
                progress.update(
                    task, 
                    description=f"Step {steps}/{total_steps}: Testing commit {commit.hexsha[:12]}",
                    advance=1
                )
                
                # Get just the first line of the commit message, truncate if too long
                if commit.message:
                    first_line = commit.message.strip().split('\\n')[0].strip()
                    subject = first_line[:80] + '...' if len(first_line) > 80 else first_line
                else:
                    subject = 'No message'
                console.print(f"  🔍 Testing commit {commit.hexsha[:12]} ({subject})")
                
                result = self._test_commit(commit)
                
                if result is None:
                    # Untestable commit, skip it
                    console.print(f"    ⚠️  Skipping untestable commit")
                    # Remove this commit and continue
                    commits.pop(mid)
                    if mid <= (left + right) // 2:
                        right -= 1
                    continue
                
                if result:  # Good commit
                    console.print(f"    ✅ Good")
                    left = mid + 1
                else:  # Bad commit
                    console.print(f"    ❌ Bad")
                    first_bad = commit
                    right = mid - 1
            
            progress.update(task, description="✨ Bisection complete!", completed=total_steps)
        
        return first_bad
    
    def _cleanup(self) -> None:
        """Clean up resources after bisection."""
        if not self.keep_clone and self.clone_dir.exists():
            try:
                shutil.rmtree(self.clone_dir)
                logger.debug(f"Cleaned up clone directory: {self.clone_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up clone directory: {e}")
        elif self.keep_clone:
            console.print(f"[dim]📁 Repository kept at: {self.clone_dir}[/dim]")
