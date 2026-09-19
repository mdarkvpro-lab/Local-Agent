from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

WORKSPACE = BASE_DIR / "workspace"
DATA_DIR = BASE_DIR / "data"
MEMORY_FILE = DATA_DIR / "memory.json"

OLLAMA_URL = "http://127.0.0.1:11434"
MODEL = "qwen3-coder:30b"

MAX_AGENT_STEPS = 30
MAX_TOOL_OUTPUT = 12_000

COMMAND_TIMEOUT = 120
PYTHON_TIMEOUT = 120

MAX_FILE_SIZE = 2_000_000  # 2 MB

WORKSPACE.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# Files the agent must never read/write.
PROTECTED_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".gitconfig",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
    "secrets.json",
}

PROTECTED_EXTENSIONS = {
    ".pem",
    ".key",
    ".p12",
    ".pfx",
}

# Commands the agent is allowed to execute.
ALLOWED_COMMANDS = {
    "python",
    "python3",
    "py",
    "pip",
    "pip3",
    "pytest",
    "git",
    "node",
    "npm",
    "npx",
}

# Git operations that never require confirmation.
SAFE_GIT_OPERATIONS = {
    "status",
    "diff",
    "log",
    "show",
    "branch",
    "rev-parse",
    "ls-files",
}

# Operations that require user confirmation.
CONFIRM_GIT_OPERATIONS = {
    "add",
    "commit",
    "restore",
    "checkout",
    "switch",
    "reset",
    "clean",
    "merge",
    "rebase",
}

# NEVER permit these through the autonomous tool.
BLOCKED_GIT_OPERATIONS = {
    "push",
    "pull",
    "clone",
    "fetch",
    "remote",
    "submodule",
}