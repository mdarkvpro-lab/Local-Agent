from __future__ import annotations

import ctypes
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


# ============================================================
# Console
# ============================================================

console = Console(
    highlight=False,
    soft_wrap=True,
)


# ============================================================
# Theme
# ============================================================

THEME = {
    "primary": "rgb(167,139,250)",       # Purple
    "secondary": "rgb(96,165,250)",      # Blue
    "success": "rgb(74,222,128)",        # Green
    "warning": "rgb(250,204,21)",        # Amber
    "error": "rgb(248,113,113)",         # Red
    "muted": "rgb(148,163,184)",         # Slate
    "text": "rgb(226,232,240)",          # Light slate
    "border": "rgb(71,85,105)",          # Graphite
}


# ============================================================
# Windows clipboard API
# ============================================================

if sys.platform == "win32":
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    CF_UNICODETEXT = 13

    user32.OpenClipboard.argtypes = [ctypes.c_void_p]
    user32.OpenClipboard.restype = ctypes.c_bool

    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = ctypes.c_bool

    user32.IsClipboardFormatAvailable.argtypes = [ctypes.c_uint]
    user32.IsClipboardFormatAvailable.restype = ctypes.c_bool

    user32.GetClipboardData.argtypes = [ctypes.c_uint]
    user32.GetClipboardData.restype = ctypes.c_void_p

    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p

    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.restype = ctypes.c_bool


def get_clipboard_text() -> str | None:
    """
    Read Unicode text from the Windows clipboard.
    """

    if sys.platform != "win32":
        return None

    if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
        return None

    if not user32.OpenClipboard(None):
        return None

    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)

        if not handle:
            return None

        pointer = kernel32.GlobalLock(handle)

        if not pointer:
            return None

        try:
            return ctypes.wstring_at(pointer)
        finally:
            kernel32.GlobalUnlock(handle)

    finally:
        user32.CloseClipboard()


# ============================================================
# Banner
# ============================================================

def show_banner(model: str, workspace: Path):
    console.clear()

    logo = Text()
    logo.append("LOCAL ", style=f"bold {THEME['text']}")
    logo.append("AGENT", style=f"bold {THEME['primary']}")

    version = Text("V2", style=f"bold {THEME['secondary']}")

    subtitle = Text(
        "Autonomous local software engineering",
        style=f"{THEME['muted']}",
    )

    info = Table.grid(
        padding=(0, 2),
        expand=False,
    )

    info.add_row(
        Text("MODEL", style=f"bold {THEME['muted']}"),
        Text(model, style=THEME["text"]),
    )

    info.add_row(
        Text("RUNTIME", style=f"bold {THEME['muted']}"),
        Text("Ollama", style=THEME["text"]),
    )

    info.add_row(
        Text("WORKSPACE", style=f"bold {THEME['muted']}"),
        Text(str(workspace), style=THEME["text"]),
    )

    info.add_row(
        Text("GIT", style=f"bold {THEME['muted']}"),
        Text("Git-aware", style=THEME["text"]),
    )

    info.add_row(
        Text("SECURITY", style=f"bold {THEME['muted']}"),
        Text(
            "Sandbox + approval gates",
            style=THEME["text"],
        ),
    )

    info.add_row(
        Text("PLATFORM", style=f"bold {THEME['muted']}"),
        Text("Windows", style=THEME["text"]),
    )

    header = Table.grid(expand=True)
    header.add_column()
    header.add_column(justify="right")

    header.add_row(
        logo,
        version,
    )

    content = Group(
        header,
        Text(""),
        info,
    )

    console.print(
        Panel(
            content,
            border_style=THEME["primary"],
            padding=(1, 2),
            title=Text(
                " SYSTEM ",
                style=f"bold {THEME['primary']}",
            ),
            subtitle=subtitle,
        )
    )

    console.print()


# ============================================================
# Input
# ============================================================

def prompt_user() -> str:
    """
    Rich terminal input.

    Enter:
        Submit the message.

    Ctrl+V:
        Insert the complete clipboard contents,
        including multiple lines.

    Backspace:
        Delete the previous character.

    Ctrl+C:
        Interrupt safely.
    """

    if sys.platform != "win32":
        return console.input(
            f"[{THEME['primary']}]›[/{THEME['primary']}] "
        )

    import msvcrt

    buffer: list[str] = []

    console.print(
        f"[{THEME['primary']}]›[/{THEME['primary']}] ",
        end="",
    )

    while True:
        try:
            key = msvcrt.getwch()

        except KeyboardInterrupt:
            raise

        # ----------------------------------------------------
        # Ctrl+C
        # ----------------------------------------------------

        if key == "\x03":
            raise KeyboardInterrupt

        # ----------------------------------------------------
        # Enter
        # ----------------------------------------------------

        if key in ("\r", "\n"):
            console.print()
            return "".join(buffer)

        # ----------------------------------------------------
        # Backspace
        # ----------------------------------------------------

        if key == "\x08":
            if buffer:
                removed = buffer.pop()

                if removed == "\n":
                    console.print(
                        "\r\033[K"
                        f"[{THEME['primary']}]›[/{THEME['primary']}] "
                        + "".join(buffer),
                        end="",
                    )
                else:
                    console.print(
                        "\b \b",
                        end="",
                    )

            continue

        # ----------------------------------------------------
        # Ctrl+V
        # ----------------------------------------------------

        if key == "\x16":
            clipboard = get_clipboard_text()

            if clipboard is None:
                continue

            clipboard = clipboard.replace("\r\n", "\n")
            clipboard = clipboard.replace("\r", "\n")

            buffer.extend(clipboard)

            console.print(
                "\r\033[K"
                f"[{THEME['primary']}]›[/{THEME['primary']}] "
                + "".join(buffer),
                end="",
            )

            continue

        # ----------------------------------------------------
        # Ctrl+Backspace
        # ----------------------------------------------------

        if key == "\x7f":
            while buffer and buffer[-1].isspace():
                buffer.pop()

            while buffer and not buffer[-1].isspace():
                buffer.pop()

            console.print(
                "\r\033[K"
                f"[{THEME['primary']}]›[/{THEME['primary']}] "
                + "".join(buffer),
                end="",
            )

            continue

        # ----------------------------------------------------
        # Extended keys
        # ----------------------------------------------------

        if key in ("\x00", "\xe0"):
            try:
                msvcrt.getwch()
            except KeyboardInterrupt:
                raise

            continue

        # ----------------------------------------------------
        # Printable character
        # ----------------------------------------------------

        if key.isprintable():
            buffer.append(key)

            console.print(
                key,
                end="",
            )


# ============================================================
# Project location
# ============================================================

def choose_directory(workspace: Path) -> str | None:
    """
    Ask the user where a project should be created.

    1 = Manual path
    2 = Windows File Explorer
    3 = Agent workspace
    0 = Cancel
    """

    console.print()

    console.print(
        Panel(
            Text(
                "Choose where the project should be created.",
                style=THEME["text"],
            ),
            title=Text(
                " PROJECT LOCATION ",
                style=f"bold {THEME['primary']}",
            ),
            border_style=THEME["border"],
            padding=(1, 2),
        )
    )

    table = Table.grid(
        padding=(0, 2),
    )

    table.add_row(
        Text("1", style=f"bold {THEME['primary']}"),
        Text(
            "Enter a folder path manually",
            style=THEME["text"],
        ),
    )

    table.add_row(
        Text("2", style=f"bold {THEME['primary']}"),
        Text(
            "Browse with File Explorer",
            style=THEME["text"],
        ),
    )

    table.add_row(
        Text("3", style=f"bold {THEME['primary']}"),
        Text(
            f"Use agent workspace  ({workspace})",
            style=THEME["text"],
        ),
    )

    table.add_row(
        Text("0", style=f"bold {THEME['muted']}"),
        Text(
            "Cancel",
            style=THEME["muted"],
        ),
    )

    console.print(table)
    console.print()

    while True:
        try:
            choice = console.input(
                f"[{THEME['primary']}]›[/{THEME['primary']}] "
                "Choose [1/2/3/0]: "
            ).strip()

        except (KeyboardInterrupt, EOFError):
            console.print()
            return None

        # ----------------------------------------------------
        # Cancel
        # ----------------------------------------------------

        if choice == "0":
            console.print(
                f"[{THEME['warning']}]! Project creation "
                f"cancelled.[/{THEME['warning']}]"
            )
            return None

        # ----------------------------------------------------
        # Manual path
        # ----------------------------------------------------

        if choice == "1":
            try:
                path = console.input(
                    f"[{THEME['primary']}]›[/{THEME['primary']}] "
                    "Destination folder: "
                ).strip()

            except (KeyboardInterrupt, EOFError):
                console.print()
                return None

            if not path:
                console.print(
                    f"[{THEME['warning']}]! Path cannot be empty."
                    f"[/{THEME['warning']}]"
                )
                continue

            path = path.strip('"')

            console.print(
                f"[{THEME['success']}]✓ Destination:"
                f"[/{THEME['success']}] {path}"
            )

            return path

        # ----------------------------------------------------
        # File Explorer
        # ----------------------------------------------------

        if choice == "2":
            selected = open_folder_dialog()

            if selected:
                console.print()

                console.print(
                    Panel(
                        selected,
                        title=Text(
                            " SELECTED DESTINATION ",
                            style=f"bold {THEME['success']}",
                        ),
                        border_style=THEME["success"],
                        padding=(0, 1),
                    )
                )

                return selected

            console.print(
                f"[{THEME['warning']}]! No folder selected."
                f"[/{THEME['warning']}]"
            )

            continue

        # ----------------------------------------------------
        # Workspace
        # ----------------------------------------------------

        if choice == "3":
            selected = str(workspace)

            console.print(
                f"[{THEME['success']}]✓ Using workspace:"
                f"[/{THEME['success']}] {selected}"
            )

            return selected

        # ----------------------------------------------------
        # Invalid
        # ----------------------------------------------------

        console.print(
            f"[{THEME['warning']}]! Please choose "
            f"1, 2, 3, or 0.[/{THEME['warning']}]"
        )


# ============================================================
# Windows folder picker
# ============================================================

def open_folder_dialog() -> str | None:
    """
    Open the native Windows folder picker.

    The selected folder is returned to the application.
    """

    if sys.platform != "win32":
        console.print(
            f"[{THEME['error']}]File Explorer folder selection "
            f"is only available on Windows.[/{THEME['error']}]"
        )
        return None

    powershell_script = r"""
Add-Type -AssemblyName System.Windows.Forms

$dialog = New-Object System.Windows.Forms.FolderBrowserDialog

$dialog.Description = "Select project destination"
$dialog.ShowNewFolderButton = $true

$result = $dialog.ShowDialog()

if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
    Write-Output $dialog.SelectedPath
}
"""

    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-STA",
                "-Command",
                powershell_script,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

    except subprocess.TimeoutExpired:
        console.print(
            f"[{THEME['error']}]File Explorer selection "
            f"timed out.[/{THEME['error']}]"
        )
        return None

    except OSError as exc:
        console.print(
            f"[{THEME['error']}]Could not open folder picker: "
            f"{exc}[/{THEME['error']}]"
        )
        return None

    if result.returncode != 0:
        return None

    selected = result.stdout.strip()

    return selected or None


# ============================================================
# Thinking
# ============================================================

@contextmanager
def thinking(step: int, max_steps: int):
    start = time.perf_counter()

    with console.status(
        f"[{THEME['primary']}]◌ Thinking[/{THEME['primary']}] "
        f"[{THEME['muted']}]step {step}/{max_steps}"
        f"[/{THEME['muted']}]",
        spinner="dots",
    ):
        yield

    elapsed = time.perf_counter() - start

    console.print(
        f"[{THEME['success']}]✓[/{THEME['success']}] "
        f"Thinking completed "
        f"[{THEME['muted']}]{elapsed:.2f}s"
        f"[/{THEME['muted']}]"
    )


# ============================================================
# Tool UI
# ============================================================

def tool_running(tool_name: str):
    console.print(
        f"[{THEME['secondary']}]›[/{THEME['secondary']}] "
        f"Running tool: "
        f"[bold {THEME['text']}]{tool_name}"
        f"[/bold {THEME['text']}]"
    )


def show_tool(
    tool_name: str,
    arguments: dict,
    result: str,
    success: bool = True,
):
    symbol = "✓" if success else "✗"

    status_color = (
        THEME["success"]
        if success
        else THEME["error"]
    )

    console.print()

    title = Text()
    title.append(
        f"{symbol} ",
        style=f"bold {status_color}",
    )
    title.append(
        tool_name,
        style=f"bold {THEME['text']}",
    )

    argument_text = "\n".join(
        f"{key}: {value}"
        for key, value in arguments.items()
    )

    if argument_text:
        console.print(
            Panel(
                argument_text,
                title=title,
                border_style=THEME["border"],
                padding=(0, 1),
            )
        )

    if result:
        console.print(
            Panel(
                result,
                title=Text(
                    " RESULT ",
                    style=f"bold {THEME['secondary']}",
                ),
                border_style=THEME["border"],
                padding=(0, 1),
            )
        )


# ============================================================
# Agent output
# ============================================================

def show_agent(content: str):
    if not content:
        return

    console.print()

    console.print(
        Panel(
            content,
            title=Text(
                " AGENT ",
                style=f"bold {THEME['primary']}",
            ),
            border_style=THEME["primary"],
            padding=(1, 2),
        )
    )

    console.print()


# ============================================================
# Confirmation
# ============================================================

def request_confirmation(
    title: str,
    details: str,
) -> bool:
    console.print()

    console.print(
        Panel(
            details,
            title=Text(
                f" {title.upper()} ",
                style=f"bold {THEME['warning']}",
            ),
            border_style=THEME["warning"],
            padding=(1, 2),
        )
    )

    while True:
        try:
            answer = console.input(
                f"[{THEME['warning']}]›[/{THEME['warning']}] "
                "Approve? [yes/no]: "
            ).strip().lower()

        except (KeyboardInterrupt, EOFError):
            console.print()
            return False

        if answer in {
            "yes",
            "y",
            "yeah",
            "yep",
            "sure",
            "okay",
            "ok",
            "approve",
            "approved",
        }:
            console.print(
                f"[{THEME['success']}]✓ Approved"
                f"[/{THEME['success']}]"
            )
            return True

        if answer in {
            "no",
            "n",
            "nope",
            "deny",
            "denied",
            "cancel",
            "cancelled",
        }:
            console.print(
                f"[{THEME['error']}]✗ Denied"
                f"[/{THEME['error']}]"
            )
            return False

        console.print(
            f"[{THEME['warning']}]! Please answer "
            f"yes or no.[/{THEME['warning']}]"
        )


# ============================================================
# Error
# ============================================================

def show_error(message: str):
    console.print()

    console.print(
        Panel(
            message,
            title=Text(
                " ERROR ",
                style=f"bold {THEME['error']}",
            ),
            border_style=THEME["error"],
            padding=(1, 2),
        )
    )


# ============================================================
# Status
# ============================================================

def show_status(
    model: str,
    workspace: Path,
    step: int,
    max_steps: int,
):
    table = Table(
        title=Text(
            "AGENT STATUS",
            style=f"bold {THEME['primary']}",
        ),
        border_style=THEME["border"],
    )

    table.add_column(
        "Property",
        style=f"bold {THEME['muted']}",
    )

    table.add_column(
        "Value",
        style=THEME["text"],
    )

    table.add_row("Model", model)
    table.add_row("Workspace", str(workspace))
    table.add_row("Current step", str(step))
    table.add_row("Maximum steps", str(max_steps))
    table.add_row("Runtime", "Ollama")
    table.add_row(
        "Security",
        "Sandbox + approval gates",
    )

    console.print()
    console.print(table)
    console.print()


# ============================================================
# Help
# ============================================================

def show_help():
    console.print()

    table = Table(
        title=Text(
            "COMMANDS",
            style=f"bold {THEME['primary']}",
        ),
        border_style=THEME["border"],
    )

    table.add_column(
        "Command",
        style=f"bold {THEME['secondary']}",
    )

    table.add_column(
        "Description",
        style=THEME["text"],
    )

    table.add_row(
        "/help",
        "Show this help",
    )

    table.add_row(
        "/status",
        "Show agent status",
    )

    table.add_row(
        "/clear",
        "Clear terminal and redraw banner",
    )

    table.add_row(
        "/exit",
        "Close the agent",
    )

    table.add_row(
        "/quit",
        "Close the agent",
    )

    console.print(table)
    console.print()


# ============================================================
# Separator
# ============================================================

def separator():
    console.print(
        "─" * 70,
        style=THEME["border"],
    )