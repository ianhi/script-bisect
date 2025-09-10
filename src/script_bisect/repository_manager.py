"""Centralized repository management for efficient Git operations.

This module provides a centralized way to handle all Git repository interactions
with optimal performance by minimizing network requests and using efficient
Git operations.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import git
from rich.progress import Progress, SpinnerColumn, TextColumn

if TYPE_CHECKING:
    from git import Repo

logger = logging.getLogger(__name__)


class RepositoryManager:
    """Manages Git repository operations with optimized performance.

    This class centralizes all Git operations to minimize remote fetches
    and uses efficient blob-filtering to reduce bandwidth usage.
    """

    def __init__(self, repo_url: str) -> None:
        """Initialize the repository manager.

        Args:
            repo_url: The Git repository URL (with or without git+ prefix)
        """
        # Clean the URL for git operations
        self.repo_url = repo_url
        if repo_url.startswith("git+"):
            self.clone_url = repo_url[4:]  # Remove git+ prefix
        else:
            self.clone_url = repo_url

        self.repo: Repo | None = None
        self.clone_dir: Path | None = None

    def setup_repository(self, good_ref: str, bad_ref: str) -> Path:
        """Set up a local repository optimized for bisection.

        This method performs all necessary Git operations in the most efficient way:
        1. Creates a bare clone (no working directory initially)
        2. Fetches only the required refs with blob filtering
        3. Sets up sparse checkout to minimize disk usage
        4. Returns the repository path for bisection operations

        Args:
            good_ref: The known good reference (commit, tag, or branch)
            bad_ref: The known bad reference (commit, tag, or branch)

        Returns:
            Path to the optimized local repository

        Raises:
            git.GitCommandError: If any Git operation fails
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=None,  # Use default console
            transient=True,
        ) as progress:
            # Create temporary directory for the repository
            self.clone_dir = Path(tempfile.mkdtemp(prefix="script_bisect_repo_"))

            task = progress.add_task("Setting up optimized repository...", total=None)

            logger.info(f"Setting up repository from {self.clone_url}")

            try:
                # Step 1: Initialize empty repository (no initial clone)
                progress.update(task, description="Initializing repository...")
                self.repo = git.Repo.init(self.clone_dir)

                # Add the remote origin
                self.repo.create_remote("origin", self.clone_url)

                # Step 2: Configure for optimal performance
                progress.update(
                    task, description="Configuring for optimal performance..."
                )

                # Enable sparse-checkout for minimal working directory
                self.repo.git.config("core.sparseCheckout", "true")
                sparse_checkout_path = (
                    self.clone_dir / ".git" / "info" / "sparse-checkout"
                )
                sparse_checkout_path.parent.mkdir(parents=True, exist_ok=True)
                sparse_checkout_path.write_text("", encoding="utf-8")  # No files

                # Step 3: Fetch only what we need with blob filtering
                progress.update(task, description="Fetching required references...")

                # Fetch both refs in a single operation with blob filtering
                # This avoids downloading file contents, only getting commit metadata
                try:
                    self.repo.git.fetch(
                        "origin",
                        good_ref,
                        bad_ref,
                        "--filter=blob:none",
                        "--no-tags",  # Skip tags unless they're the refs we want
                    )
                except git.GitCommandError:
                    # If the combined fetch fails, try individual fetches
                    logger.debug("Combined fetch failed, trying individual fetches")
                    self.repo.git.fetch("origin", good_ref, "--filter=blob:none")
                    self.repo.git.fetch("origin", bad_ref, "--filter=blob:none")

                # Step 4: Fetch the commit range with blob filtering
                progress.update(task, description="Fetching commit history...")
                try:
                    # Fetch the full history between the refs efficiently
                    self.repo.git.fetch(
                        "origin", f"{good_ref}..{bad_ref}", "--filter=blob:none"
                    )
                except git.GitCommandError:
                    logger.debug(
                        "Range fetch failed, trying to fetch all refs with blob filtering"
                    )
                    # Fallback: fetch all refs (still with blob filtering)
                    try:
                        self.repo.git.fetch("origin", "--filter=blob:none")
                    except git.GitCommandError:
                        logger.debug("Blob filter not supported, fetching normally")
                        self.repo.git.fetch("origin")

                progress.update(task, description="✅ Repository ready for bisection")

            except Exception as e:
                # Clean up on failure
                if self.clone_dir and self.clone_dir.exists():
                    import shutil

                    shutil.rmtree(self.clone_dir, ignore_errors=True)
                raise git.GitCommandError(
                    f"Failed to set up repository: {e}", status=1
                ) from e

        return self.clone_dir

    def resolve_reference(self, ref: str) -> str:
        """Resolve a Git reference to its full commit hash.

        Args:
            ref: The reference to resolve (commit hash, tag, or branch)

        Returns:
            The full commit hash

        Raises:
            ValueError: If the reference cannot be resolved
        """
        if not self.repo:
            raise ValueError("Repository not set up. Call setup_repository() first.")

        try:
            commit = self.repo.commit(ref)
            return str(commit.hexsha)
        except git.BadName as e:
            raise ValueError(f"Cannot resolve reference '{ref}': {e}") from e

    def get_commit_range(self, good_ref: str, bad_ref: str) -> list[str]:
        """Get the list of commits between two references.

        Args:
            good_ref: The known good reference
            bad_ref: The known bad reference

        Returns:
            List of commit hashes in chronological order (oldest first)

        Raises:
            ValueError: If the repository is not set up or refs are invalid
        """
        if not self.repo:
            raise ValueError("Repository not set up. Call setup_repository() first.")

        try:
            # Get commits in reverse chronological order (newest first), then reverse
            commits = list(self.repo.iter_commits(f"{good_ref}..{bad_ref}"))
            # Return in chronological order (oldest first) for bisection
            return [str(commit.hexsha) for commit in reversed(commits)]
        except git.GitCommandError as e:
            raise ValueError(
                f"Cannot get commit range {good_ref}..{bad_ref}: {e}"
            ) from e

    def checkout_commit(self, commit_hash: str) -> None:
        """Check out a specific commit without affecting working directory.

        Args:
            commit_hash: The commit hash to check out

        Raises:
            ValueError: If the repository is not set up or commit is invalid
        """
        if not self.repo:
            raise ValueError("Repository not set up. Call setup_repository() first.")

        try:
            self.repo.git.checkout(commit_hash)
        except git.GitCommandError as e:
            raise ValueError(f"Cannot checkout commit {commit_hash}: {e}") from e

    def get_commit_info(self, commit_hash: str) -> dict[str, str]:
        """Get information about a specific commit.

        Args:
            commit_hash: The commit hash to get info for

        Returns:
            Dictionary with commit information (hash, author, date, message, etc.)

        Raises:
            ValueError: If the repository is not set up or commit is invalid
        """
        if not self.repo:
            raise ValueError("Repository not set up. Call setup_repository() first.")

        try:
            commit = self.repo.commit(commit_hash)
            return {
                "hash": str(commit.hexsha),
                "short_hash": str(commit.hexsha)[:12],
                "author": str(commit.author),
                "date": commit.committed_datetime.isoformat(),
                "message": str(commit.message).strip(),
                "summary": str(commit.summary),
            }
        except git.BadName as e:
            raise ValueError(f"Cannot get info for commit {commit_hash}: {e}") from e

    def cleanup(self) -> None:
        """Clean up the local repository and temporary files."""
        if self.clone_dir and self.clone_dir.exists():
            import shutil

            try:
                shutil.rmtree(self.clone_dir)
                logger.debug(f"Cleaned up repository: {self.clone_dir}")
            except OSError as e:
                logger.warning(f"Failed to clean up repository: {e}")
            finally:
                self.clone_dir = None
                self.repo = None

    def __enter__(self) -> RepositoryManager:
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Context manager exit with automatic cleanup."""
        self.cleanup()
