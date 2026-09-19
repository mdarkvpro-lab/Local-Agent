import requests

from config import OLLAMA_URL, MODEL


class OllamaError(Exception):
    pass


def chat(messages, tools=None):

    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
    }

    if tools:
        payload["tools"] = tools

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json=payload,
            timeout=600,
        )

    except requests.RequestException as exc:
        raise OllamaError(
            f"Could not connect to Ollama: {exc}"
        )

    if response.status_code != 200:
        raise OllamaError(
            f"Ollama returned HTTP "
            f"{response.status_code}: "
            f"{response.text}"
        )

    data = response.json()

    if "message" not in data:
        raise OllamaError(
            "Ollama returned an invalid response."
        )

    return data