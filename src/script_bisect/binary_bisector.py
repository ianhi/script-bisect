"""Pure Python binary search implementation for git bisection."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import git
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from .exceptions import GitError, RepositoryError
from .runner import TestRunner
from .utils import format_commit_info


logger = logging.getLogger(__name__)
console = Console()


class BinaryBisector:
    """Pure Python implementation of git bisect using binary search."""
    
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
    ) -> None:
        """Initialize the binary bisector."""
        self.script_path = script_path
        self.package = package
        self.repo_url = repo_url
        self.good_ref = good_ref
        self.bad_ref = bad_ref
        self.test_command = test_command
        self.clone_dir = clone_dir
        self.keep_clone = keep_clone
        self.inverse = inverse
        
        self.repo: git.Repo | None = None
        self.test_runner: TestRunner | None = None
    
    def get_commit_range(self) -> list[git.Commit]:
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
    
    def test_commit(self, commit: git.Commit) -> bool | None:
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
    
    def binary_search_commits(self, commits: list[git.Commit]) -> git.Commit | None:
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
                
                console.print(f"  🔍 Testing commit {commit.hexsha[:12]} ({commit.message.split()[0] if commit.message else 'No message'})")
                
                result = self.test_commit(commit)
                
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
    
    def run_bisection(self) -> dict[str, Any] | None:
        """Run the complete bisection process."""
        try:
            # Get the commit range
            commits = self.get_commit_range()
            
            if not commits:
                console.print("[yellow]⚠️ No commits found in range[/yellow]")
                return None
            
            console.print(f"[dim]Found {len(commits)} commits between {self.good_ref} and {self.bad_ref}[/dim]")
            
            # Verify the endpoints
            console.print("\\n[dim]🔍 Verifying endpoints...[/dim]")
            
            # Check that good_ref is actually good
            good_commit = self.repo.commit(self.good_ref)
            good_result = self.test_commit(good_commit)
            if good_result is False:
                console.print(f"[red]❌ Good ref '{self.good_ref}' is not actually good![/red]")
                return None
            console.print(f"    ✅ {self.good_ref} is good")
            
            # Check that bad_ref is actually bad  
            bad_commit = self.repo.commit(self.bad_ref)
            bad_result = self.test_commit(bad_commit)
            if bad_result is True:
                console.print(f"[red]❌ Bad ref '{self.bad_ref}' is not actually bad![/red]")
                return None
            console.print(f"    ❌ {self.bad_ref} is bad")
            
            # Run binary search
            console.print("\\n[bold blue]🔄 Starting binary search...[/bold blue]")
            first_bad_commit = self.binary_search_commits(commits)
            
            if first_bad_commit:
                commit_info = {
                    "commit_hash": first_bad_commit.hexsha,
                    "author": f"{first_bad_commit.author.name} <{first_bad_commit.author.email}>",
                    "date": first_bad_commit.committed_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                    "message": first_bad_commit.message.split('\\n')[0],
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