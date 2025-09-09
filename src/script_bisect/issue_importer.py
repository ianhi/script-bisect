"""GitHub issue and comment importer for script-bisect."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

import mistune
import requests
from rich.console import Console

from .exceptions import ScriptBisectError

console = Console()


@dataclass
class CodeBlock:
    """Represents a code block found in GitHub content."""

    content: str
    language: str | None = None
    source_location: str = "unknown"
    is_python_script: bool = False
    confidence_score: float = 0.0


@dataclass
class GitHubContent:
    """Represents content from a GitHub issue or comment."""

    title: str
    body: str
    author: str
    url: str
    comments: list[str]
    target_comment_id: int | None = None  # ID of specific comment if targeting one


class GitHubIssueImporter:
    """Imports and processes GitHub issues and comments."""

    def __init__(self) -> None:
        """Initialize the GitHub issue importer."""
        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/vnd.github+json", "User-Agent": "script-bisect/1.0"}
        )

    def parse_github_url(self, url: str) -> tuple[str, str, int, int | None]:
        """Parse a GitHub URL to extract owner, repo, issue number, and optional comment ID.

        Args:
            url: GitHub issue or comment URL

        Returns:
            Tuple of (owner, repo, issue_number, comment_id)
            comment_id is None if URL points to issue, not specific comment

        Raises:
            ScriptBisectError: If URL format is invalid
        """
        parsed = urlparse(url)
        if parsed.hostname not in ("github.com", "www.github.com"):
            raise ScriptBisectError(f"URL must be from GitHub: {url}")

        # Parse path like: /owner/repo/issues/123 or /owner/repo/issues/123#issuecomment-456
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) < 4 or path_parts[2] not in ("issues", "pull"):
            raise ScriptBisectError(f"URL must point to a GitHub issue or PR: {url}")

        owner = path_parts[0]
        repo = path_parts[1]

        try:
            issue_number = int(path_parts[3])
        except ValueError as e:
            raise ScriptBisectError(f"Invalid issue number in URL: {url}") from e

        # Check for comment ID in fragment (e.g., #issuecomment-123456)
        comment_id = None
        if parsed.fragment and parsed.fragment.startswith("issuecomment-"):
            try:
                comment_id = int(parsed.fragment.replace("issuecomment-", ""))
            except ValueError:
                console.print(
                    f"[yellow]⚠️ Could not parse comment ID from: {parsed.fragment}[/yellow]"
                )

        return owner, repo, issue_number, comment_id

    def fetch_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        target_comment_id: int | None = None,
    ) -> GitHubContent:
        """Fetch issue content from GitHub API.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number
            target_comment_id: Optional specific comment ID to target

        Returns:
            GitHubContent object with issue data

        Raises:
            ScriptBisectError: If API request fails or issue not found
        """
        if target_comment_id:
            console.print(
                f"[dim]🔍 Fetching GitHub issue {owner}/{repo}#{issue_number} (comment {target_comment_id})...[/dim]"
            )
        else:
            console.print(
                f"[dim]🔍 Fetching GitHub issue {owner}/{repo}#{issue_number}...[/dim]"
            )

        # Fetch issue
        issue_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"

        try:
            issue_response = self.session.get(issue_url)
            issue_response.raise_for_status()
        except requests.RequestException as e:
            raise ScriptBisectError(f"Failed to fetch issue: {e}") from e

        issue_data = issue_response.json()

        # Fetch comments
        comments_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments"

        try:
            comments_response = self.session.get(comments_url)
            comments_response.raise_for_status()
        except requests.RequestException as e:
            console.print(f"[yellow]Warning: Failed to fetch comments: {e}[/yellow]")
            comments_data = []
        else:
            comments_data = comments_response.json()

        # Extract comment bodies
        comment_bodies = [
            comment["body"] for comment in comments_data if comment.get("body")
        ]

        return GitHubContent(
            title=issue_data.get("title", ""),
            body=issue_data.get("body", ""),
            author=issue_data.get("user", {}).get("login", "unknown"),
            url=issue_data.get("html_url", ""),
            comments=comment_bodies,
            target_comment_id=target_comment_id,
        )

    def extract_code_blocks(self, content: GitHubContent) -> list[CodeBlock]:
        """Extract code blocks from GitHub content.

        Args:
            content: GitHub content to process

        Returns:
            List of CodeBlock objects found in the content
        """
        console.print("[dim]🔍 Extracting code blocks...[/dim]")

        blocks = []

        # If targeting a specific comment, try to find it first
        if content.target_comment_id:
            console.print(
                f"[dim]🎯 Looking for target comment {content.target_comment_id}...[/dim]"
            )
            # Note: We would need to fetch individual comment details to match by ID
            # For now, we'll process all comments and rely on user selection

        # Process issue body (unless we're targeting a specific comment)
        if content.body and not content.target_comment_id:
            issue_blocks = self._extract_blocks_from_text(content.body, "issue body")
            blocks.extend(issue_blocks)

        # Process comments
        for i, comment in enumerate(content.comments):
            source_desc = f"comment {i+1}"
            if content.target_comment_id:
                source_desc += " (targeted)" if i == 0 else ""  # Simplified for now
            comment_blocks = self._extract_blocks_from_text(comment, source_desc)
            blocks.extend(comment_blocks)

        # Score blocks for likelihood of being test scripts
        for block in blocks:
            block.confidence_score = self._calculate_script_confidence(block)
            block.is_python_script = block.confidence_score > 0.5

        # Sort by confidence score
        blocks.sort(key=lambda x: x.confidence_score, reverse=True)

        console.print(f"[green]✅ Found {len(blocks)} code blocks[/green]")
        return blocks

    def _extract_blocks_from_text(self, text: str, source: str) -> list[CodeBlock]:
        """Extract code blocks from markdown text.

        Args:
            text: Markdown text to process
            source: Description of where the text came from

        Returns:
            List of CodeBlock objects
        """
        blocks = []

        # Create a custom renderer to capture code blocks
        class CodeBlockRenderer(mistune.HTMLRenderer):
            def __init__(self) -> None:
                super().__init__()
                self.code_blocks: list[tuple[str, str | None]] = []

            def block_code(self, code: str, info: str | None = None) -> str:
                self.code_blocks.append((code.strip(), info))
                return ""  # We don't need HTML output

        renderer = CodeBlockRenderer()
        markdown = mistune.Markdown(renderer=renderer)

        # Process the markdown to extract code blocks
        markdown(text)

        # Convert to CodeBlock objects
        for code, info in renderer.code_blocks:
            language = None
            if info:
                # Extract language from info string (e.g., "python" from "python copy")
                language = info.split()[0].lower() if info.strip() else None

            blocks.append(
                CodeBlock(content=code, language=language, source_location=source)
            )

        return blocks

    def _calculate_script_confidence(self, block: CodeBlock) -> float:
        """Calculate confidence score for whether a code block is a test script.

        Args:
            block: Code block to analyze

        Returns:
            Confidence score between 0.0 and 1.0
        """
        score = 0.0
        content = block.content.lower()

        # Language indicators
        if block.language == "python":
            score += 0.3
        elif block.language in ("py", "python3"):
            score += 0.25

        # Python-specific patterns
        python_patterns = [
            r"import \w+",
            r"from \w+ import",
            r"def \w+\(",
            r"if __name__ == ['\"]__main__['\"]:",
            r"print\s*\(",
            r"assert\s+",
        ]

        for pattern in python_patterns:
            if re.search(pattern, content):
                score += 0.1

        # Test/script indicators
        test_patterns = [
            r"test[_\s]",
            r"bug[_\s]",
            r"reproduce",
            r"example",
            r"script",
            r"run[_\s]",
            r"execute",
        ]

        for pattern in test_patterns:
            if re.search(pattern, content):
                score += 0.05

        # Package import patterns (common in bug reports)
        package_patterns = [
            r"import (pandas|numpy|matplotlib|sklearn|scipy|requests|flask|django)",
            r"from (pandas|numpy|matplotlib|sklearn|scipy|requests|flask|django) import",
        ]

        for pattern in package_patterns:
            if re.search(pattern, content):
                score += 0.15

        # Executable content indicators
        if "main(" in content or "__main__" in content:
            score += 0.2

        # Length indicators (too short or too long might not be executable scripts)
        lines = block.content.split("\n")
        line_count = len([line for line in lines if line.strip()])

        if 3 <= line_count <= 50:
            score += 0.1
        elif line_count > 50:
            score -= 0.1

        return min(score, 1.0)

    def import_from_url(self, url: str) -> list[CodeBlock]:
        """Import code blocks from a GitHub issue URL.

        Args:
            url: GitHub issue or comment URL

        Returns:
            List of CodeBlock objects found in the issue

        Raises:
            ScriptBisectError: If import fails
        """
        owner, repo, issue_number, comment_id = self.parse_github_url(url)
        content = self.fetch_issue(owner, repo, issue_number, comment_id)
        return self.extract_code_blocks(content)
