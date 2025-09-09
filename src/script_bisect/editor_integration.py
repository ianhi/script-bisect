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
        self.preferred_editors = [
            "vim",
            "nvim",
            "nano",
            "emacs",
            "code",  # VS Code
            "subl",  # Sublime Text
            "atom",
        ]

    def find_available_editors(self) -> list[tuple[str, str]]:
        """Find all available editors on the system.

        Returns:
            List of tuples (name, path) for available editors
        """
        available = []

        # Check EDITOR environment variable first
        env_editor = os.environ.get("EDITOR")
        if env_editor and shutil.which(env_editor):
            available.append(("$EDITOR", env_editor))

        # Check VISUAL environment variable
        visual_editor = os.environ.get("VISUAL")
        if (
            visual_editor
            and shutil.which(visual_editor)
            and visual_editor != env_editor
        ):
            available.append(("$VISUAL", visual_editor))

        # Check preferred editors
        for editor in self.preferred_editors:
            editor_path = shutil.which(editor)
            if editor_path and editor_path not in [e[1] for e in available]:
                available.append((editor, editor_path))

        return available

    def find_available_editor(self) -> str | None:
        """Find an available editor on the system (legacy method).

        Returns:
            Path to an available editor, or None if none found
        """
        editors = self.find_available_editors()
        return editors[0][1] if editors else None

    def prompt_for_editor(self) -> str | None:
        """Prompt user to select an editor from available options.

        Returns:
            Path to selected editor, or None if cancelled
        """
        available_editors = self.find_available_editors()

        if not available_editors:
            console.print("[red]❌ No editors found on system[/red]")
            console.print(
                "[yellow]💡 Please install one of:[/yellow] "
                + ", ".join(self.preferred_editors)
            )
            return None

        if len(available_editors) == 1:
            name, path = available_editors[0]
            console.print(f"[green]📝 Using {name}: {Path(path).name}[/green]")
            return path

        # Show editor selection table
        from rich.prompt import Prompt
        from rich.table import Table

        console.print("\n[bold blue]📝 Available Editors[/bold blue]")
        table = Table(show_header=True)
        table.add_column("Index", style="cyan", width=6)
        table.add_column("Name", style="yellow", width=15)
        table.add_column("Command", style="white", width=30)
        table.add_column("Path", style="dim", width=50)

        for i, (name, path) in enumerate(available_editors, 1):
            command = Path(path).name
            table.add_row(str(i), name, command, str(path))

        console.print(table)
        console.print()

        while True:
            try:
                choice = Prompt.ask(
                    "[bold cyan]Select editor[/bold cyan]",
                    choices=[str(i) for i in range(1, len(available_editors) + 1)],
                    default="1",
                )

                index = int(choice) - 1
                if 0 <= index < len(available_editors):
                    name, path = available_editors[index]
                    console.print(
                        f"[green]✅ Selected {name}: {Path(path).name}[/green]"
                    )
                    return path

            except (ValueError, KeyboardInterrupt):
                console.print("\n[yellow]⚠️ Editor selection cancelled[/yellow]")
                return None

    def launch_editor(self, file_path: Path, read_only: bool = False) -> bool:
        """Launch an external editor to edit a file.

        Args:
            file_path: Path to the file to edit
            read_only: Whether to open in read-only mode (if supported)

        Returns:
            True if editing completed successfully, False otherwise

        Raises:
            ScriptBisectError: If no suitable editor is found
        """
        editor = self.prompt_for_editor()
        if not editor:
            raise ScriptBisectError(
                "No editor selected or available. Please install one of: "
                + ", ".join(self.preferred_editors)
            )

        console.print(
            f"[dim]🖊️ Opening {file_path.name} in {Path(editor).name}...[/dim]"
        )

        # Build editor command
        cmd = [editor]

        # Add read-only flags for supported editors
        if read_only:
            editor_name = Path(editor).name.lower()
            if editor_name in ("vim", "nvim"):
                cmd.extend(["-R"])  # Read-only mode
            elif editor_name == "nano":
                cmd.extend(["-v"])  # View mode
            elif editor_name == "emacs":
                cmd.extend(["--eval", "(setq buffer-read-only t)"])

        cmd.append(str(file_path))

        try:
            # Launch editor and wait for completion
            result = subprocess.run(
                cmd,
                check=False,  # Don't raise on non-zero exit codes
                env=dict(os.environ, TERM=os.environ.get("TERM", "xterm-256color")),
            )

            if result.returncode != 0:
                console.print(
                    f"[yellow]⚠️ Editor exited with code {result.returncode}[/yellow]"
                )
                return False

            console.print("[green]✅ Editor session completed[/green]")
            return True

        except (subprocess.SubprocessError, FileNotFoundError) as e:
            console.print(f"[red]❌ Failed to launch editor: {e}[/red]")
            return False

    def edit_script_interactively(self, script_path: Path, backup: bool = True) -> bool:
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

        # Check if file was modified
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

        # Confirm continuation
        return Confirm.ask(
            "[bold cyan]Continue with bisection using the edited script?[/bold cyan]",
            default=True,
        )

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
