from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from config import (
    WORKSPACE,
    MAX_FILE_SIZE,
    MAX_TOOL_OUTPUT,
    COMMAND_TIMEOUT,
    PYTHON_TIMEOUT,
)

from policy import (
    PolicyError,
    resolve_path,
    check_protected_path,
    validate_command,
    git_policy,
)

from git_manager import (
    get_status,
    create_checkpoint,
)

from ui import (
    request_confirmation,
    choose_directory,
)


# ============================================================
# Output helpers
# ============================================================

def trim_output(output: str) -> str:
    if not output:
        return ""

    if len(output) <= MAX_TOOL_OUTPUT:
        return output

    return (
        output[:MAX_TOOL_OUTPUT]
        + "\n\n... output truncated ..."
    )


# ============================================================
# Path / approval helpers
# ============================================================

def validate_tool_path(
    path_string: str,
    operation: str,
    approved_external: bool = False,
) -> tuple[Path, bool]:
    """
    Resolve and validate a path.

    Paths inside the workspace are allowed automatically.

    Paths outside the workspace require explicit user approval.

    Protected files are always blocked, even when external access
    has been approved.
    """

    resolved, inside_workspace = resolve_path(path_string)

    # Protected files are NEVER allowed.
    check_protected_path(resolved)

    # Workspace paths are automatically allowed.
    if inside_workspace:
        return resolved, True

    # External path has already been approved by the caller.
    if approved_external:
        return resolved, False

    # Ask the user for permission.
    approved = request_external_access(
        resolved,
        operation,
    )

    if not approved:
        raise PolicyError(
            "User denied external access."
        )

    return resolved, False


def request_external_access(
    path: Path,
    operation: str,
) -> bool:
    workspace = WORKSPACE.resolve()

    details = (
        f"Operation: {operation}\n\n"
        f"Requested path:\n{path}\n\n"
        f"Agent workspace:\n{workspace}\n\n"
        "This path is outside the agent workspace.\n"
        "The operation requires your approval."
    )

    return request_confirmation(
        "External access requested",
        details,
    )


# ============================================================
# Project location
# ============================================================

def choose_project_location() -> str:
    """
    Ask the user where a new project should be created.

    The user can:
      1. Enter a path manually.
      2. Browse using Windows File Explorer.
      3. Use the agent workspace.
      0. Cancel.

    The selected location is returned to the agent.

    IMPORTANT:
    This function only selects the destination.
    It does not create or modify anything.
    """

    selected = choose_directory(WORKSPACE)

    if not selected:
        return "CANCELLED: No project location was selected."

    return selected


# ============================================================
# File operations
# ============================================================

def list_files(
    path: str = ".",
    _approved_external: bool = False,
):
    """
    List files and directories.

    External paths require explicit approval.
    """

    try:
        resolved, inside_workspace = validate_tool_path(
            path,
            "list files",
            approved_external=_approved_external,
        )

    except PolicyError as exc:
        return f"BLOCKED: {exc}"

    if not resolved.exists():
        return f"Path does not exist: {resolved}"

    if not resolved.is_dir():
        return f"Not a directory: {resolved}"

    entries = []

    try:
        for item in sorted(
            resolved.iterdir(),
            key=lambda p: (
                not p.is_dir(),
                p.name.lower(),
            ),
        ):
            prefix = "[DIR] " if item.is_dir() else "      "
            entries.append(
                prefix + item.name
            )

    except OSError as exc:
        return f"Could not list directory: {exc}"

    if not entries:
        return "(empty directory)"

    return "\n".join(entries)


def read_file(
    path: str,
    _approved_external: bool = False,
):
    """
    Read a UTF-8 text file.

    External files require explicit approval.
    """

    try:
        resolved, inside_workspace = validate_tool_path(
            path,
            "read file",
            approved_external=_approved_external,
        )

    except PolicyError as exc:
        return f"BLOCKED: {exc}"

    if not resolved.exists():
        return f"File does not exist: {resolved}"

    if not resolved.is_file():
        return f"Not a file: {resolved}"

    try:
        size = resolved.stat().st_size

    except OSError as exc:
        return (
            f"Could not inspect file: {exc}"
        )

    if size > MAX_FILE_SIZE:
        return (
            f"File is too large: {size} bytes. "
            f"Maximum allowed is {MAX_FILE_SIZE} bytes."
        )

    try:
        return resolved.read_text(
            encoding="utf-8"
        )

    except UnicodeDecodeError:
        return (
            "ERROR: File is not valid UTF-8 text."
        )

    except OSError as exc:
        return (
            f"Could not read file: {exc}"
        )


def write_file(
    path: str,
    content: str,
    _approved_external: bool = False,
):
    """
    Create or overwrite a UTF-8 text file.

    External files require explicit approval.
    """

    try:
        resolved, inside_workspace = validate_tool_path(
            path,
            "write file",
            approved_external=_approved_external,
        )

    except PolicyError as exc:
        return f"BLOCKED: {exc}"

    content_size = len(
        content.encode("utf-8")
    )

    if content_size > MAX_FILE_SIZE:
        return (
            "File content exceeds maximum size "
            f"of {MAX_FILE_SIZE} bytes."
        )

    try:
        resolved.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        resolved.write_text(
            content,
            encoding="utf-8",
        )

    except OSError as exc:
        return (
            f"Could not write file: {exc}"
        )

    return (
        f"File written successfully:\n"
        f"{resolved}"
    )


# ============================================================
# Command operations
# ============================================================

def command_targets_external_path(
    parts: list[str],
) -> Path | None:
    """
    Detect absolute command arguments that point outside
    the agent workspace.

    This is intentionally conservative.
    """

    workspace = WORKSPACE.resolve()

    for token in parts[1:]:
        try:
            candidate = Path(token)

            if not candidate.is_absolute():
                continue

            resolved = candidate.resolve()

            try:
                resolved.relative_to(workspace)

            except ValueError:
                return resolved

        except (
            OSError,
            RuntimeError,
        ):
            continue

    return None


def run_command(
    command: str,
):
    """
    Run an allowed command.

    Commands are validated by policy.py.

    External absolute paths require user approval.
    """

    try:
        parts = validate_command(command)

    except PolicyError as exc:
        return f"BLOCKED: {exc}"

    external_path = command_targets_external_path(
        parts
    )

    if external_path is not None:

        approved = request_external_access(
            external_path,
            "run command",
        )

        if not approved:
            return (
                "BLOCKED: User denied external "
                "command access."
            )

    try:
        result = subprocess.run(
            parts,
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT,
        )

    except subprocess.TimeoutExpired:
        return (
            f"Command timed out after "
            f"{COMMAND_TIMEOUT} seconds."
        )

    except OSError as exc:
        return (
            f"Could not execute command: {exc}"
        )

    output = ""

    if result.stdout:
        output += result.stdout

    if result.stderr:
        output += (
            "\nSTDERR:\n"
            + result.stderr
        )

    if result.returncode != 0:
        output = (
            f"Exit code: {result.returncode}\n\n"
            + output
        )

    return trim_output(
        output.strip()
    )


# ============================================================
# Python execution
# ============================================================

def python_execute(code: str):
    """
    Execute Python code in an isolated Python process.

    NOTE:
    - This is process isolation, NOT a security sandbox.
    - Python code can potentially access files available to
      the process.
    """

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                "-c",
                code,
            ],
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=PYTHON_TIMEOUT,
        )

    except subprocess.TimeoutExpired:
        return (
            f"Python execution timed out after "
            f"{PYTHON_TIMEOUT} seconds."
        )

    except OSError as exc:
        return (
            f"Could not execute Python: {exc}"
        )

    output = ""

    if result.stdout:
        output += result.stdout

    if result.stderr:
        output += (
            "\nSTDERR:\n"
            + result.stderr
        )

    if result.returncode != 0:
        output = (
            f"Exit code: {result.returncode}\n\n"
            + output
        )

    return trim_output(
        output.strip()
    )


# ============================================================
# Git
# ============================================================

def git_status():
    """
    Show Git status for the agent workspace.
    """

    return get_status()


def git_checkpoint():
    """
    Inspect current Git changes.
    """

    return create_checkpoint()


# ============================================================
# Tool definitions
# ============================================================

TOOLS = [

    # --------------------------------------------------------
    # Project location
    # --------------------------------------------------------

    {
        "type": "function",
        "function": {
            "name": "choose_project_location",
            "description": (
                "Ask the user where a new project should "
                "be created. The user can enter a folder "
                "path manually, browse using Windows File "
                "Explorer, or use the agent workspace. "
                "Use this before creating a new standalone "
                "project when the destination has not been "
                "specified."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },

    # --------------------------------------------------------
    # Files
    # --------------------------------------------------------

    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": (
                "List files and directories. "
                "Paths inside the workspace are allowed "
                "automatically. External paths require "
                "user approval."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Directory path. "
                            "Use '.' for the workspace."
                        ),
                    },
                },
                "required": [
                    "path",
                ],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read a UTF-8 text file. "
                "External files require user approval. "
                "Protected files are never accessible."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Path to the file."
                        ),
                    },
                },
                "required": [
                    "path",
                ],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Create or overwrite a UTF-8 text file. "
                "External files require user approval. "
                "Protected files are never writable."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Destination file path."
                        ),
                    },
                    "content": {
                        "type": "string",
                        "description": (
                            "Complete file content."
                        ),
                    },
                },
                "required": [
                    "path",
                    "content",
                ],
            },
        },
    },

    # --------------------------------------------------------
    # Commands
    # --------------------------------------------------------

    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": (
                "Run an allowed Windows command from "
                "the agent workspace. Only approved "
                "executables are permitted. Shell operators "
                "are forbidden. External paths require "
                "user approval."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": (
                            "Allowed command to execute."
                        ),
                    },
                },
                "required": [
                    "command",
                ],
            },
        },
    },

    # --------------------------------------------------------
    # Python
    # --------------------------------------------------------

    {
        "type": "function",
        "function": {
            "name": "python_execute",
            "description": (
                "Execute Python code for testing, "
                "computation, or project verification. "
                "Do not use it to bypass file or security "
                "policies."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": (
                            "Python code to execute."
                        ),
                    },
                },
                "required": [
                    "code",
                ],
            },
        },
    },

    # --------------------------------------------------------
    # Git
    # --------------------------------------------------------

    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": (
                "Show Git status for the agent workspace."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "git_checkpoint",
            "description": (
                "Inspect current Git changes before "
                "modifying the project."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]


# ============================================================
# Tool function registry
# ============================================================

TOOL_FUNCTIONS = {
    "choose_project_location": choose_project_location,

    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,

    "run_command": run_command,
    "python_execute": python_execute,

    "git_status": git_status,
    "git_checkpoint": git_checkpoint,
}


# ============================================================
# Tool execution
# ============================================================

def execute_tool(
    tool_name: str,
    arguments: dict,
):
    """
    Execute a native tool by name.

    Unknown tools are rejected.
    """

    function = TOOL_FUNCTIONS.get(
        tool_name
    )

    if function is None:
        raise PolicyError(
            f"Unknown tool: {tool_name}"
        )

    try:
        result = function(**arguments)

    except TypeError as exc:
        raise PolicyError(
            f"Invalid arguments for tool "
            f"'{tool_name}': {exc}"
        )

    if result is None:
        return ""

    if not isinstance(result, str):
        return str(result)

    return result