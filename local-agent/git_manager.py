import subprocess

from config import WORKSPACE
from policy import validate_command


def run_git_raw(args):

    command = ["git", *args]

    result = subprocess.run(
        command,
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=120,
    )

    output = ""

    if result.stdout:
        output += result.stdout

    if result.stderr:
        output += "\nSTDERR:\n"
        output += result.stderr

    return result.returncode, output.strip()


def is_git_repo():

    code, _ = run_git_raw(
        ["rev-parse", "--is-inside-work-tree"]
    )

    return code == 0


def get_status():

    if not is_git_repo():
        return "Workspace is not a Git repository."

    code, output = run_git_raw(
        ["status", "--short"]
    )

    if code != 0:
        return output

    return output or "Working tree is clean."


def create_checkpoint():

    if not is_git_repo():
        return (
            "No Git repository detected. "
            "Checkpoint skipped."
        )

    code, status = run_git_raw(
        ["status", "--porcelain"]
    )

    if code != 0:
        return status

    if not status:
        return "Working tree already clean."

    # We deliberately don't automatically commit.
    return (
        "Git checkpoint available: "
        "working tree contains changes.\n\n"
        + status
    )