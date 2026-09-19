from pathlib import Path
import shlex

from config import (
    WORKSPACE,
    PROTECTED_NAMES,
    PROTECTED_EXTENSIONS,
    ALLOWED_COMMANDS,
    SAFE_GIT_OPERATIONS,
    CONFIRM_GIT_OPERATIONS,
    BLOCKED_GIT_OPERATIONS,
)


class PolicyError(Exception):
    pass


def resolve_path(relative_or_absolute: str) -> tuple[Path, bool]:
    """
    Resolve a path.

    Returns:
        (resolved_path, inside_workspace)
    """

    if not relative_or_absolute:
        raise PolicyError("Empty path is not allowed.")

    path = Path(relative_or_absolute).expanduser()

    if path.is_absolute():
        resolved = path.resolve()
    else:
        resolved = (WORKSPACE / path).resolve()

    workspace = WORKSPACE.resolve()

    try:
        resolved.relative_to(workspace)
        inside_workspace = True
    except ValueError:
        inside_workspace = False

    return resolved, inside_workspace


def check_protected_path(path: Path):
    protected_names = {
        name.lower()
        for name in PROTECTED_NAMES
    }

    protected_extensions = {
        ext.lower()
        for ext in PROTECTED_EXTENSIONS
    }

    for part in path.parts:
        if part.lower() in protected_names:
            raise PolicyError(
                f"Protected file or directory: {part}"
            )

    if path.suffix.lower() in protected_extensions:
        raise PolicyError(
            f"Protected file type: {path.suffix}"
        )


def validate_path(
    path_string: str,
    allow_external: bool = False,
) -> tuple[Path, bool]:
    """
    Validate a file path.

    Returns:
        (resolved_path, inside_workspace)

    External paths are allowed only when allow_external=True.
    """

    resolved, inside_workspace = resolve_path(path_string)

    check_protected_path(resolved)

    if not inside_workspace and not allow_external:
        raise PolicyError(
            "Path is outside the agent workspace."
        )

    return resolved, inside_workspace


def parse_command(command: str):
    try:
        return shlex.split(
            command,
            posix=False,
        )
    except ValueError as exc:
        raise PolicyError(
            f"Could not parse command: {exc}"
        )


def validate_command(command: str):
    parts = parse_command(command)

    if not parts:
        raise PolicyError("Empty command.")

    executable = Path(parts[0]).name.lower()

    allowed = {
        item.lower()
        for item in ALLOWED_COMMANDS
    }

    if executable not in allowed:
        raise PolicyError(
            f"Command '{executable}' is not allowed."
        )

    forbidden_tokens = {
        "|",
        "||",
        "&",
        "&&",
        ";",
        ">",
        ">>",
        "<",
        "<<",
        "$(",
        "`",
    }

    for token in parts:
        if token in forbidden_tokens:
            raise PolicyError(
                "Shell operators are not allowed."
            )

    return parts


def git_policy(command_parts):
    if len(command_parts) < 2:
        return "safe"

    operation = command_parts[1].lower()

    if operation in BLOCKED_GIT_OPERATIONS:
        return "blocked"

    if operation in SAFE_GIT_OPERATIONS:
        return "safe"

    if operation in CONFIRM_GIT_OPERATIONS:
        return "confirm"

    return "confirm"