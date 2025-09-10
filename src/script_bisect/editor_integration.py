"""External editor integration for script refinement."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm

from .exceptions import ScriptBisectError

console = Console()


class EditorIntegration:
    """Handles external editor integration for script editing."""

    def __init__(self) -> None:
        """Initialize the editor integration."""
        pass  # No longer need preferred editors list

    def _get_git_editor(self) -> str | None:
        """Get git's configured editor."""
        try:
            result = subprocess.run(
                ["git", "config", "--global", "core.editor"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        return None

    def _find_terminal_editor(self) -> str | None:
        """Find a suitable terminal editor using git's approach."""
        # Try git's configured editor first
        git_editor = self._get_git_editor()
        if git_editor:
            return git_editor

        # Try environment variables
        for env_var in ["EDITOR", "VISUAL"]:
            editor = os.environ.get(env_var)
            if editor:
                return editor

        # Fallback to common terminal editors
        terminal_editors = ["vim", "vi", "nano", "emacs"]
        for editor in terminal_editors:
            if shutil.which(editor):
                return editor

        return None

    # Removed complex editor selection methods - now using git-based approach

    def launch_editor(self, file_path: Path, read_only: bool = False) -> bool:
        """Launch an external editor to edit a file using git's configured editor.

        Args:
            file_path: Path to the file to edit
            read_only: Whether to open in read-only mode (ignored for simplicity)

        Returns:
            True if editing completed successfully, False otherwise

        Raises:
            ScriptBisectError: If no suitable editor is found
        """
        editor = self._find_terminal_editor()
        if not editor:
            raise ScriptBisectError(
                "No terminal editor found. Please set git config core.editor, "
                "$EDITOR/$VISUAL environment variable, or install vim/nano."
            )

        console.print(f"[dim]🖊️ Opening {file_path.name} with {editor}...[/dim]")

        try:
            # Launch editor and wait for completion (all terminal editors are blocking)
            result = subprocess.run([editor, str(file_path)])
            # For terminal editors, any exit is considered success
            # (user may exit without saving, that's their choice)
            console.print("[green]✅ Editor session completed[/green]")
            return True

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            console.print(f"[red]❌ Failed to launch editor: {e}[/red]")
            return False

    def edit_script_interactively(
        self, script_path: Path, backup: bool = True, auto_skip: bool = False
    ) -> bool:
        """Launch an interactive editing session for a script.

        Args:
            script_path: Path to the script file to edit
            backup: Whether to create a backup before editing

        Returns:
            True if editing was successful and user wants to continue

        Raises:
            ScriptBisectError: If editor launch fails
        """
        if not script_path.exists():
            raise ScriptBisectError(f"Script file not found: {script_path}")

        # Create backup if requested
        backup_path = None
        if backup:
            backup_path = script_path.with_suffix(script_path.suffix + ".bak")
            try:
                backup_path.write_bytes(script_path.read_bytes())
                console.print(f"[dim]💾 Created backup: {backup_path.name}[/dim]")
            except OSError as e:
                console.print(f"[yellow]⚠️ Could not create backup: {e}[/yellow]")

        # Show initial content info
        try:
            content = script_path.read_text(encoding="utf-8")
            line_count = len(content.splitlines())
            console.print(f"[dim]📄 Script has {line_count} lines[/dim]")
        except (OSError, UnicodeDecodeError):
            console.print("[yellow]⚠️ Could not read script content[/yellow]")

        # Auto-skip if requested (e.g., with --yes flag)
        if auto_skip:
            console.print("[dim]🤖 Auto-skipping editor, using script as-is[/dim]")
            return True

        # Ask for confirmation
        if not Confirm.ask(
            f"[bold cyan]Edit {script_path.name} before running bisection?[/bold cyan]",
            default=True,
        ):
            console.print("[dim]Skipping editor, using script as-is[/dim]")
            return True

        # Launch editor
        success = self.launch_editor(script_path)

        if not success:
            if backup_path and backup_path.exists():
                console.print("[yellow]Restoring from backup...[/yellow]")
                try:
                    script_path.write_bytes(backup_path.read_bytes())
                    backup_path.unlink()  # Remove backup
                except OSError as e:
                    console.print(f"[red]Failed to restore backup: {e}[/red]")
            return False

        # Check if file was modified and clean up backup
        try:
            new_content = script_path.read_text(encoding="utf-8")
            new_line_count = len(new_content.splitlines())

            if backup_path and backup_path.exists():
                original_content = backup_path.read_text(encoding="utf-8")
                if new_content == original_content:
                    console.print("[dim]📄 Script unchanged[/dim]")
                else:
                    console.print(
                        f"[green]📄 Script modified ({new_line_count} lines)[/green]"
                    )

                # Clean up backup
                backup_path.unlink()

        except (OSError, UnicodeDecodeError):
            console.print("[yellow]⚠️ Could not verify script changes[/yellow]")

        # User already confirmed by completing editor session - no need for additional confirmation
        return True

    def show_script_preview(self, script_path: Path, max_lines: int = 20) -> None:
        """Show a preview of the script content.

        Args:
            script_path: Path to the script file
            max_lines: Maximum number of lines to show
        """
        if not script_path.exists():
            console.print("[red]❌ Script file not found[/red]")
            return

        console.print(f"\n[bold cyan]📄 Preview of {script_path.name}:[/bold cyan]")

        try:
            content = script_path.read_text(encoding="utf-8")
            lines = content.splitlines()

            # Show line numbers and content
            for i, line in enumerate(lines[:max_lines], 1):
                console.print(f"[dim]{i:3d}[/dim] {line}")

            if len(lines) > max_lines:
                console.print(f"[dim]... ({len(lines) - max_lines} more lines)[/dim]")

        except (OSError, UnicodeDecodeError) as e:
            console.print(f"[red]❌ Could not read file: {e}[/red]")

    def create_editable_script(
        self, content: str, filename: str = "script.py", temp_dir: Path | None = None
    ) -> Path:
        """Create a temporary script file that can be edited.

        Args:
            content: Initial script content
            filename: Preferred filename
            temp_dir: Directory to create the file in (uses temp if None)

        Returns:
            Path to the created script file
        """
        if temp_dir is None:
            temp_dir = Path(tempfile.gettempdir())

        # Ensure filename is safe
        safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        if not safe_filename:
            safe_filename = "script.py"

        # Create unique filename if file exists
        script_path = temp_dir / safe_filename
        counter = 1
        while script_path.exists():
            name, ext = (
                safe_filename.rsplit(".", 1)
                if "." in safe_filename
                else (safe_filename, "")
            )
            new_name = f"{name}_{counter}"
            script_path = temp_dir / (f"{new_name}.{ext}" if ext else new_name)
            counter += 1

        try:
            script_path.write_text(content, encoding="utf-8")
            console.print(f"[green]📄 Created editable script: {script_path}[/green]")
            return script_path
        except OSError as e:
            raise ScriptBisectError(f"Could not create script file: {e}") from e

    def validate_script_syntax(self, script_path: Path) -> tuple[bool, str]:
        """Validate Python syntax of a script file.

        Args:
            script_path: Path to the script file

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not script_path.exists():
            return False, "Script file not found"

        try:
            content = script_path.read_text(encoding="utf-8")
            compile(content, str(script_path), "exec")
            return True, ""
        except SyntaxError as e:
            error_msg = f"Syntax error at line {e.lineno}: {e.msg}"
            return False, error_msg
        except (OSError, UnicodeDecodeError) as e:
            return False, f"Could not read file: {e}"
