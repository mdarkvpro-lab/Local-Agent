import json
from datetime import datetime, timezone

from config import MEMORY_FILE


def load_memory():

    if not MEMORY_FILE.exists():
        return []

    try:
        return json.loads(
            MEMORY_FILE.read_text(
                encoding="utf-8"
            )
        )

    except (json.JSONDecodeError, OSError):
        return []


def save_memory(memory):

    MEMORY_FILE.write_text(
        json.dumps(
            memory,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def remember(key, value):

    memory = load_memory()

    memory.append({
        "key": key,
        "value": value,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
    })

    # Keep memory bounded.
    memory = memory[-100:]

    save_memory(memory)


def get_memory(limit=20):

    return load_memory()[-limit:]