# Cache Management in script-bisect

This document explains how the intelligent caching system works and how to manage it.

## Cache Location

The cache follows XDG Base Directory standards:

- **Default**: `~/.cache/script-bisect/`
- **Custom**: `$XDG_CACHE_HOME/script-bisect/` (if XDG_CACHE_HOME is set)

## Cache Structure

```
~/.cache/script-bisect/
├── repositories/        # Git repository clones (TTL: 1 week)
├── references/         # Git refs (tags/branches) (TTL: 6 hours) 
├── metadata/           # PyPI package metadata (TTL: 24 hours)
└── scripts/            # Script parsing info (TTL: 1 hour)
```

## Automatic Cache Management

### Auto-Cleanup on Startup
- When `script-bisect` starts, it automatically removes cache entries older than 30 days
- This prevents the cache from growing indefinitely
- Cleanup happens in the background and doesn't slow down startup

### Repository Updates
- **Cached repositories**: When using a cached repo, script-bisect automatically fetches the latest commits for the specified refs
- **New commits**: The system pulls new commits between good_ref and bad_ref to ensure bisection includes recent changes
- **Graceful fallback**: If fetch fails, continues with cached version

### TTL-Based Invalidation
Different cache types have different lifetimes:
- **Repositories**: 1 week (long-lived, expensive to clone)
- **Git references**: 6 hours (moderate, good balance for new tags)
- **Package metadata**: 24 hours (changes infrequently)
- **Script info**: 1 hour (based on file modification time)

## Manual Cache Management

### CLI Commands

```bash
# View cache statistics
python -m script_bisect.cache_cli stats

# Clear all caches
python -m script_bisect.cache_cli clear

# Clear specific cache type
python -m script_bisect.cache_cli clear --cache-type repos
python -m script_bisect.cache_cli clear --cache-type refs
python -m script_bisect.cache_cli clear --cache-type metadata
python -m script_bisect.cache_cli clear --cache-type scripts

# Clean up expired entries
python -m script_bisect.cache_cli cleanup --max-age-days 7
```

### Force Refresh During Bisection

```bash
# Force refresh all cached data
script-bisect script.py pandas v1.0.0 v2.0.0 --refresh-cache
```

This clears all caches before starting the bisection, ensuring:
- Fresh repository clone
- Latest git references
- Updated package metadata

## Cache Performance Benefits

### Before Caching
- Repository clone: ~30-60 seconds
- Git reference fetch: ~2-5 seconds  
- Package metadata lookup: ~1-3 seconds
- **Total cold start**: ~35-70 seconds

### After Caching (Warm)
- Repository reuse: ~2-3 seconds (copy from cache)
- Git reference reuse: <1 second
- Package metadata reuse: <1 second
- **Total warm start**: ~3-5 seconds

### Cache Hit Scenarios
- **Repository cache hit**: 90%+ speedup for same repo+refs
- **Reference cache hit**: 80%+ speedup for autocompletion
- **Metadata cache hit**: 70%+ speedup for package discovery

## When to Clear Cache

### Repository Issues
If you encounter repository-related errors:
```bash
python -m script_bisect.cache_cli clear --cache-type repos
```

### Outdated References
If git references seem outdated:
```bash
python -m script_bisect.cache_cli clear --cache-type refs
# or use --refresh-cache flag
```

### Package Metadata Issues
If package detection fails:
```bash
python -m script_bisect.cache_cli clear --cache-type metadata
```

### Full Reset
For any persistent issues:
```bash
python -m script_bisect.cache_cli clear
```

## Cache Monitoring

### Check Cache Size
```bash
python -m script_bisect.cache_cli stats
```

Output example:
```
Cache Statistics
Cache directory: /Users/user/.cache/script-bisect
Total size: 12.30 MB
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━┓
┃ Cache Type   ┃ Size (MB) ┃ Files ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━┩
│ Repositories │     12.30 │   147 │
│ References   │      0.02 │     5 │
│ Metadata     │      0.01 │    12 │
│ Scripts      │      0.00 │     3 │
└──────────────┴───────────┴───────┘
```

### Monitor Growth
Run `stats` periodically to ensure cache isn't growing too large. A reasonable cache size is:
- **Small projects**: 50-200 MB
- **Large projects**: 200-500 MB  
- **Many repositories**: 500-1000 MB

If cache exceeds 1GB, consider running cleanup or clearing specific cache types.

## Advanced Configuration

The caching system is designed to work automatically, but advanced users can:

1. **Set custom cache directory**: Set `XDG_CACHE_HOME` environment variable
2. **Adjust auto-cleanup frequency**: Modify the 30-day default in `cache_system.py`
3. **Change TTL values**: Modify the TTL constants in cache method calls

## Security Considerations

- **Cache isolation**: Each user has their own cache directory
- **No sensitive data**: Cache contains only public git data and metadata
- **Automatic cleanup**: Old entries are automatically removed
- **Safe deletion**: Cache can be safely deleted at any time without affecting functionality

## Troubleshooting

### Cache Directory Permissions
If you get permission errors:
```bash
ls -la ~/.cache/
chmod -R u+rw ~/.cache/script-bisect/
```

### Corrupted Cache
If cache files are corrupted:
```bash
python -m script_bisect.cache_cli clear
```

### High Memory Usage
If script-bisect uses too much memory:
```bash
python -m script_bisect.cache_cli cleanup --max-age-days 1
```

### Network Issues
If you have network connectivity issues, caching might mask problems. Use:
```bash
script-bisect script.py package good bad --refresh-cache
```

This ensures fresh data is fetched despite any cached entries.