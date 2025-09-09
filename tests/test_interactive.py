"""Tests for interactive UI functionality."""

import pytest

from script_bisect.interactive import (
    _is_valid_git_ref,
    _is_valid_repo_url,
)


def test_valid_git_refs():
    """Test validation of git references."""
    valid_refs = [
        "main",
        "v1.0.0",
        "v2025.08.0",
        "release/v2.0",
        "feature/new-thing",
        "abc123def",
        "1a2b3c4d5e6f",
        "HEAD",
        "HEAD~1",
        "HEAD~2",
        "origin/main",
    ]

    for ref in valid_refs:
        assert _is_valid_git_ref(ref), f"Should be valid: {ref}"


def test_invalid_git_refs():
    """Test rejection of invalid git references."""
    invalid_refs = [
        "",
        " ",
        ".",
        "..",
        "ref with spaces",
        "ref\twith\ttabs",
        "ref\nwith\nnewlines",
        "-invalid-start",
        "ref^{commit}",
        "ref~~invalid",
        "ref:invalid",
        "ref?query",
        "ref*wildcard",
        "ref[bracket",
        "ref\\backslash",
    ]

    for ref in invalid_refs:
        assert not _is_valid_git_ref(ref), f"Should be invalid: {ref}"


def test_valid_repo_urls():
    """Test validation of repository URLs."""
    valid_urls = [
        "https://github.com/user/repo",
        "https://github.com/user/repo.git",
        "http://gitlab.com/user/repo",
        "git+https://github.com/user/repo.git",
        "git+http://example.com/user/repo",
        "git@github.com:user/repo.git",
        "git@gitlab.com:user/repo",
        "ssh://git@github.com/user/repo.git",
        "https://bitbucket.org/user/repo",
    ]

    for url in valid_urls:
        assert _is_valid_repo_url(url), f"Should be valid: {url}"


def test_invalid_repo_urls():
    """Test rejection of invalid repository URLs."""
    invalid_urls = [
        "",
        "invalid",
        "not a url",
        "ftp://example.com/repo",
        "https://",
        "github.com/user/repo",  # Missing protocol
        "https://github.com",  # Missing path
        "https://github.com/",  # Missing user/repo
        "git@github.com",  # Missing path
    ]

    for url in invalid_urls:
        assert not _is_valid_repo_url(url), f"Should be invalid: {url}"


def test_version_comparison():
    """Test version comparison logic."""
    from script_bisect.cli import _looks_like_newer_version

    # Test cases where first version is newer
    newer_cases = [
        ("v2.0.0", "v1.0.0"),
        ("v2025.09.0", "v2025.08.0"),
        ("2.1.0", "2.0.0"),
        ("v1.2.3", "v1.2.2"),
    ]

    for newer, older in newer_cases:
        assert _looks_like_newer_version(
            newer, older
        ), f"{newer} should be newer than {older}"
        assert not _looks_like_newer_version(
            older, newer
        ), f"{older} should not be newer than {newer}"

    # Test cases where comparison isn't clear
    unclear_cases = [
        ("main", "develop"),
        ("feature-branch", "v1.0.0"),
        ("abc123", "def456"),
        ("invalid", "also-invalid"),
    ]

    for ref1, ref2 in unclear_cases:
        result1 = _looks_like_newer_version(ref1, ref2)
        result2 = _looks_like_newer_version(ref2, ref1)
        # At least one should be False since we can't determine order
        assert not (
            result1 and result2
        ), f"Both {ref1} and {ref2} can't be newer than each other"


def test_fuzzy_completion():
    """Test that our fuzzy completion handles partial matches correctly."""
    try:
        from prompt_toolkit.completion import Completer, Completion
        from prompt_toolkit.document import Document
    except ImportError:
        pytest.skip("prompt-toolkit not available")

    # Test choices including the problematic case
    choices = ["v2025.09.0", "v2025.08.5", "v2024.12.0", "main", "develop"]

    # Create a simple version of our completer for testing
    class TestGitRefCompleter(Completer):
        def get_completions(
            self, document: Document, _complete_event: object
        ) -> list[Completion]:
            text_before_cursor = document.text_before_cursor
            matches = []
            for choice in choices:
                if text_before_cursor.lower() in choice.lower():
                    start_position = -len(text_before_cursor)
                    matches.append(
                        Completion(
                            text=choice, start_position=start_position, display=choice
                        )
                    )
            return matches

    completer = TestGitRefCompleter()

    # Test the specific problematic case that should work
    test_cases = [
        ("v2025.09.", ["v2025.09.0"]),  # This was the problematic case
        ("v2025", ["v2025.09.0", "v2025.08.5"]),  # Should match both
        ("main", ["main"]),  # Exact match
        ("develop", ["develop"]),  # Exact match
    ]

    for test_input, expected_matches in test_cases:
        doc = Document(text=test_input, cursor_position=len(test_input))
        completions = list(completer.get_completions(doc, None))
        actual_matches = [c.text for c in completions]

        # Check that all expected matches are found
        for expected in expected_matches:
            assert (
                expected in actual_matches
            ), f"Expected '{expected}' to be in completions for '{test_input}', got {actual_matches}"
