"""Reference validation and fixing logic.

This module handles validation of git references and provides logic
to detect and fix common issues like swapped good/bad refs.
"""

import re
import sys

from rich.console import Console
from rich.prompt import Confirm

console = Console()


def validate_and_fix_refs(
    good_ref: str, bad_ref: str, inverse: bool
) -> tuple[str, str]:
    """Validate git references and potentially swap them if needed."""
    # Check for same refs
    if good_ref == bad_ref:
        console.print("[red]❌ Good and bad references cannot be the same[/red]")
        console.print(f"Both refs are: {good_ref}")
        console.print("[yellow]Please provide different git references[/yellow]")
        sys.exit(1)

    # Check for obvious version tag patterns that might be swapped
    if _looks_like_newer_version(good_ref, bad_ref) and not inverse:
        console.print("[yellow]⚠️ Potential reference order issue detected[/yellow]")
        console.print(f"Good ref '{good_ref}' appears newer than bad ref '{bad_ref}'")
        console.print(
            "[dim]In normal mode, good ref should be older (working) version[/dim]"
        )

        if Confirm.ask("Swap the references?", default=True):
            good_ref, bad_ref = bad_ref, good_ref
            console.print(
                f"[green]✅ Swapped: good='{good_ref}', bad='{bad_ref}'[/green]"
            )

    return good_ref, bad_ref


def _looks_like_newer_version(ref1: str, ref2: str) -> bool:
    """Check if ref1 looks like a newer version than ref2."""

    def extract_version_parts(ref: str) -> list[int] | None:
        """Extract version number parts from a reference."""
        # Handle various version patterns: v1.2.3, 1.2.3, v2023.12.1, etc.
        version_pattern = r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?"
        match = re.search(version_pattern, ref)
        if not match:
            return None

        # Convert matched groups to integers, treating None as 0
        parts = []
        for group in match.groups():
            if group is not None:
                parts.append(int(group))
            else:
                parts.append(0)

        return parts

    ref1_parts = extract_version_parts(ref1)
    ref2_parts = extract_version_parts(ref2)

    # If either isn't a recognizable version, can't determine order
    if ref1_parts is None or ref2_parts is None:
        return False

    # Pad shorter list with zeros for comparison
    max_len = max(len(ref1_parts), len(ref2_parts))
    ref1_parts.extend([0] * (max_len - len(ref1_parts)))
    ref2_parts.extend([0] * (max_len - len(ref2_parts)))

    # Check if ref1 is newer (greater) than ref2
    return ref1_parts > ref2_parts
