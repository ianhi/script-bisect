"""Tests for commit URL generation functionality."""

from script_bisect.utils import format_commit_info, get_commit_url


def test_github_commit_url():
    """Test GitHub commit URL generation."""
    repo_url = "git+https://github.com/pydata/xarray.git"
    commit_hash = "a13a2556a29b3c5ba342a402b2598bab42939b46"

    url = get_commit_url(repo_url, commit_hash)

    assert (
        url
        == "https://github.com/pydata/xarray/commit/a13a2556a29b3c5ba342a402b2598bab42939b46"
    )


def test_gitlab_commit_url():
    """Test GitLab commit URL generation."""
    repo_url = "https://gitlab.com/example/project"
    commit_hash = "abc123def456"

    url = get_commit_url(repo_url, commit_hash)

    assert url == "https://gitlab.com/example/project/-/commit/abc123def456"


def test_bitbucket_commit_url():
    """Test Bitbucket commit URL generation."""
    repo_url = "https://bitbucket.org/example/project"
    commit_hash = "abc123def456"

    url = get_commit_url(repo_url, commit_hash)

    assert url == "https://bitbucket.org/example/project/commits/abc123def456"


def test_ssh_url_conversion():
    """Test that SSH URLs are converted to HTTPS."""
    repo_url = "git@github.com:pydata/xarray.git"
    commit_hash = "abc123def456"

    url = get_commit_url(repo_url, commit_hash)

    assert url == "https://github.com/pydata/xarray/commit/abc123def456"


def test_unknown_hosting_service():
    """Test that unknown hosting services return None."""
    repo_url = "https://example.com/repo.git"
    commit_hash = "abc123def456"

    url = get_commit_url(repo_url, commit_hash)

    assert url is None


def test_format_commit_info_with_url():
    """Test that format_commit_info includes commit URL when provided."""
    commit_hash = "a13a2556a29b3c5ba342a402b2598bab42939b46"
    author = "John Doe <john@example.com>"
    date = "2025-01-15 10:30:00"
    message = "Fix dtype preservation in to_dataframe()"
    repo_url = "https://github.com/pydata/xarray"

    formatted = format_commit_info(commit_hash, author, date, message, repo_url)

    assert "Commit: a13a2556a29b..." in formatted
    assert "Author: John Doe <john@example.com>" in formatted
    assert "Date: 2025-01-15 10:30:00" in formatted
    assert "Message: Fix dtype preservation in to_dataframe()" in formatted
    assert (
        "View: https://github.com/pydata/xarray/commit/a13a2556a29b3c5ba342a402b2598bab42939b46"
        in formatted
    )


def test_format_commit_info_without_url():
    """Test that format_commit_info works without repository URL."""
    commit_hash = "abc123def456"
    author = "Jane Doe <jane@example.com>"
    date = "2025-01-15 10:30:00"
    message = "Some commit message"

    formatted = format_commit_info(commit_hash, author, date, message)

    assert "Commit: abc123def456..." in formatted
    assert "Author: Jane Doe <jane@example.com>" in formatted
    assert "Date: 2025-01-15 10:30:00" in formatted
    assert "Message: Some commit message" in formatted
    assert "View:" not in formatted  # No URL should be included
