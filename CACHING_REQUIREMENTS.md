# Caching System Requirements

## Overview

Script-bisect performs expensive operations that could benefit significantly from intelligent caching:
- Repository cloning and git operations
- Commit list generation
- Script generation from GitHub URLs
- uv dependency resolution and installation

A well-designed caching system could provide 10x+ performance improvements for repeated bisections.

## 1. Repository Caching

### What to Cache
- Shallow clones of repositories with commit metadata
- Remote tracking information
- Commit objects and refs

### Storage
- **Location**: `~/.cache/script-bisect/repos/{repo_url_hash}/`
- **Structure**: Standard git repository format
- **Metadata**: `.cache-info.json` with last update time, original URL

### Update Strategy
- Check remote for new commits before each bisection
- Fetch only new commits incrementally (`git fetch --shallow-since=<last_update>`)
- Update cache metadata after successful fetch
- Fallback to full clone if incremental update fails

### Benefits
- Avoid repeated full clones of large repositories
- Faster bisection startup time
- Reduced network bandwidth usage

## 2. Commit List Caching

### What to Cache
- Commit SHAs and metadata for specific ref ranges
- Author, date, message for each commit
- Parent relationships for bisection ordering

### Storage
- **Location**: `~/.cache/script-bisect/commits/`
- **Format**: JSON files with structure:
  ```json
  {
    "repo_url": "https://github.com/org/repo",
    "good_ref": "v1.0.0",
    "bad_ref": "v2.0.0",
    "generated_at": "2025-01-15T10:30:00Z",
    "commits": [
      {
        "sha": "abc123...",
        "author": "Author Name <email>",
        "date": "2025-01-10T15:00:00Z",
        "message": "Fix bug in feature X"
      }
    ]
  }
  ```
- **Key**: `{repo_url_hash}_{good_ref}_{bad_ref}.json`

### Update Strategy
- Regenerate if good_ref or bad_ref changes
- Regenerate if cache is older than repository cache
- Validate cached commits still exist in repository

### Benefits
- Avoid expensive `git log` operations
- Faster bisection range calculation
- Consistent commit ordering across runs

## 3. Script Caching

### What to Cache
- Generated scripts from GitHub URLs/issues
- Original GitHub content and metadata
- Generated script content hash

### Storage
- **Location**: `~/.cache/script-bisect/scripts/`
- **Key**: SHA256 of GitHub URL + content
- **Files**:
  - `{hash}.py` - Generated script
  - `{hash}.meta.json` - Metadata (URL, generation time, etc.)

### Update Strategy
- Cache scripts generated from GitHub URLs/issues
- Reuse if GitHub content hasn't changed (ETag/Last-Modified)
- Allow manual cache invalidation via CLI

### Benefits
- Skip GitHub API calls for repeated URLs
- Avoid script regeneration overhead
- Preserve working scripts for reference

## 4. uv Cache Integration

### Strategy
- Keep managed scripts in persistent locations
- Use predictable paths so uv can reuse virtual environments
- Share dependency caches across similar scripts

### Storage
- **Location**: `~/.cache/script-bisect/uv-environments/`
- **Structure**: One environment per unique dependency set
- **Key**: Hash of requirements specification

### Implementation
- Create managed scripts in cache directory instead of temp files
- Use consistent virtual environment names
- Let uv handle dependency caching naturally

### Benefits
- Faster test execution on repeated bisections
- Reduced dependency download/compilation time
- More efficient disk usage through sharing

## 5. Cache Management

### CLI Commands

```bash
# Show cache status
script-bisect cache info
script-bisect cache info --detailed

# Clean expired entries
script-bisect cache clean
script-bisect cache clean --older-than=7d
script-bisect cache clean --repos
script-bisect cache clean --scripts

# Clear all cache
script-bisect cache clear
script-bisect cache clear --confirm

# Validate cache integrity
script-bisect cache validate
script-bisect cache validate --fix
```

### Auto-cleanup
- Run cleanup on startup if last cleanup > 24 hours ago
- Remove entries older than configured TTL
- Implement LRU eviction when cache size exceeds limits
- Clean up orphaned/corrupted entries

### Size Management
- Track cache size efficiently (avoid full directory scans)
- Configurable size limits with sensible defaults
- Warn user when approaching size limits
- Provide size breakdown by cache type

## 6. Configuration

### File Location
- `~/.config/script-bisect/config.toml`
- Environment variables with `SCRIPT_BISECT_` prefix
- CLI flags override config file

### Configuration Schema
```toml
[cache]
enabled = true
max_size = "1GB"  # Total cache size limit
location = "~/.cache/script-bisect"  # Override default location

[cache.repos]
ttl = "7d"  # How long to keep repository data
max_count = 50  # Maximum number of repositories to cache

[cache.commits]
ttl = "1d"  # How long commit lists stay fresh
max_count = 1000  # Maximum commit list files

[cache.scripts]
ttl = "3d"  # How long to keep generated scripts
max_count = 100  # Maximum cached scripts

[cache.uv_environments]
ttl = "7d"  # How long to keep uv environments
max_count = 20  # Maximum uv environments
```

### Environment Variables
```bash
SCRIPT_BISECT_CACHE_ENABLED=true
SCRIPT_BISECT_CACHE_LOCATION=/custom/cache/path
SCRIPT_BISECT_CACHE_MAX_SIZE=2GB
```

## 7. Implementation Phases

### Phase 1: Basic Repository Caching
- Implement repository caching with TTL
- Add basic cache info/clean commands
- Integrate with existing RepositoryManager

### Phase 2: Commit List Caching
- Cache commit ranges and metadata
- Integrate with GitBisector commit range logic
- Add cache validation

### Phase 3: Script and uv Caching
- Implement script caching for GitHub URLs
- Integrate uv environment persistence
- Add advanced cache management

### Phase 4: Configuration and Polish
- Add comprehensive configuration system
- Implement size limits and LRU eviction
- Add cache analytics and optimization

## 8. Performance Expectations

### Current Performance (No Cache)
- Repository clone: 5-30 seconds
- Commit list generation: 1-5 seconds
- Script generation: 2-3 seconds
- uv dependency resolution: 10-60 seconds per test

### With Caching (Estimated)
- Repository operations: 0.5-2 seconds (10x improvement)
- Commit list generation: 0.1-0.5 seconds (5x improvement)
- Script generation: 0.1 seconds (20x improvement)
- uv operations: 1-5 seconds (10x improvement)

### Overall Impact
- First run: Similar performance (cache population)
- Subsequent runs: 5-15x faster bisection startup
- Repeated testing: 10x faster due to uv cache reuse
