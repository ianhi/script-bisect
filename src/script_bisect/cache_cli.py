"""Cache management CLI for script-bisect."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from .cache_system import get_cache

console = Console()


@click.group()
def cache_cli() -> None:
    """Manage script-bisect caches."""
    pass


@cache_cli.command()
@click.option(
    "--cache-type", "-t", help="Type of cache to clear (repos, refs, metadata, scripts)"
)
def clear(cache_type: str | None = None) -> None:
    """Clear cache entries."""
    cache = get_cache()

    if cache_type:
        cache.clear_cache(cache_type)
        console.print(f"[green]✅ Cleared {cache_type} cache[/green]")
    else:
        if click.confirm("Clear all caches?"):
            cache.clear_cache()
            console.print("[green]✅ Cleared all caches[/green]")
        else:
            console.print("[yellow]Cache clearing cancelled[/yellow]")


@cache_cli.command()
@click.option(
    "--max-age-days", "-a", default=30.0, help="Maximum age for cache entries in days"
)
def cleanup(max_age_days: float) -> None:
    """Clean up expired cache entries."""
    cache = get_cache()
    cache.cleanup_expired(max_age_days)
    console.print(
        f"[green]✅ Cleaned up cache entries older than {max_age_days} days[/green]"
    )


@cache_cli.command()
def stats() -> None:
    """Show cache statistics."""
    cache = get_cache()
    stats = cache.get_cache_stats()

    console.print("\n[bold]Cache Statistics[/bold]")
    console.print(f"[dim]Cache directory: {stats['cache_dir']}[/dim]")
    console.print(f"[cyan]Total size: {stats['total_size_mb']:.2f} MB[/cyan]")

    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Cache Type", style="cyan")
    table.add_column("Size (MB)", justify="right")
    table.add_column("Files", justify="right")

    for cache_type, data in stats["subdirs"].items():
        table.add_row(
            cache_type.title(), f"{data['size_mb']:.2f}", str(data["file_count"])
        )

    console.print(table)


if __name__ == "__main__":
    cache_cli()
