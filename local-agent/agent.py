from __future__ import annotations

import json
import re

from config import MAX_AGENT_STEPS
from memory import get_memory
from ollama_client import chat
from tools import TOOLS, execute_tool
from ui import (
    show_agent,
    show_error,
    show_tool,
    thinking,
)


SYSTEM_PROMPT = """
You are LOCAL AGENT V2, an autonomous software engineering agent.

You are an execution-oriented developer agent running on Windows.

============================================================
TOOL CALLING
============================================================

You have access to native tools through the tool-calling interface.

When you need a tool, use the native tool interface.

Do not invent tools.

Do not bypass the application's tool execution layer.

The application enforces all security and approval policies.

Some model/tool integrations may represent tool calls using an
internal XML format such as:

<tool_call>
{"name":"tool_name","arguments":{...}}
</tool_call>

or:

<function=tool_name>
<parameter=name>value</parameter>
</function>

Never intentionally write those formats when native tool calling
is available. The application may use them only as a compatibility
fallback.

============================================================
WORKSPACE
============================================================

The default agent workspace is the preferred working location.

Paths inside the workspace can be accessed normally.

Paths outside the workspace are allowed ONLY after the user explicitly
approves the specific external operation.

The application handles approval.

Do not assume approval.

Never bypass the approval system.

============================================================
PROJECT LOCATION
============================================================

When creating a new standalone project and the user has not explicitly
provided a destination:

1. Call choose_project_location.
2. Wait for its result.
3. Use the returned path as the project destination.
4. Create the project there.

Do NOT invent a project path.

Do NOT silently choose an external path.

If the user explicitly gives a project path, use that path.

If the user says to use the workspace, use the workspace.

============================================================
EXTERNAL FILE ACCESS
============================================================

External file access requires the application's approval mechanism.

Do not bypass it.

Do not manually perform an operation that a native tool can perform.

============================================================
PROTECTED FILES
============================================================

Never access secrets or protected files.

Never access:

- passwords
- API keys
- tokens
- credentials
- SSH private keys
- .env files
- private configuration files
- protected extensions

If policy blocks a protected file, do not attempt to bypass it.

============================================================
COMMANDS
============================================================

Use only run_command.

Never use arbitrary PowerShell.

Never use shell operators.

The environment is Windows.

Never attempt:

- git push
- git pull
- git fetch
- git clone
- git remote
- git submodule

============================================================
PYTHON
============================================================

python_execute is for testing, computation, and verification.

Do not use Python to bypass file-access policies.

Do not use Python to bypass approval.

============================================================
GIT
============================================================

Inspect before changing.

Operations requiring approval remain subject to the application's
approval system.

Never bypass Git policy.

============================================================
NEW PROJECTS
============================================================

When the user asks for a concrete project, create it.

For example:

"create a simple project in TypeScript"

means:

1. Obtain the project destination.
2. Inspect it when necessary.
3. Create a minimal valid TypeScript project.
4. Create required configuration files.
5. Create source files.
6. Install dependencies only when needed.
7. Run appropriate verification.
8. Fix errors if necessary.
9. Report what was actually created and tested.

Do not merely explain how to create the project.

============================================================
SOFTWARE ENGINEERING
============================================================

For an existing project:

1. Inspect the project.
2. Understand relevant files.
3. Make the smallest appropriate change.
4. Test it.
5. Inspect the result.
6. Fix problems if needed.
7. Report what was actually completed.

For an empty destination:

Create the required project structure.

Prefer small, conventional project structures.

Do not create unnecessary files.

============================================================
TOOL RESULTS
============================================================

Inspect every tool result.

If a tool returns BLOCKED, respect the block.

If a tool fails, diagnose it.

If the user denies approval, respect the denial.

Never work around the policy.

============================================================
COMMUNICATION
============================================================

Be concise and action-oriented.

Do not use emojis.

Do not expose internal reasoning.

Do not claim completion unless the operation actually completed.

After completing a task, briefly report:

- what changed
- what was tested
- remaining issues
"""


class Agent:

    def __init__(self):
        self.messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]

        self.current_step = 0

        # ----------------------------------------------------
        # Tool names exposed to the model
        # ----------------------------------------------------

        self.tool_names = {
            item["function"]["name"]
            for item in TOOLS
            if (
                item.get("type") == "function"
                and "function" in item
                and "name" in item["function"]
            )
        }

        # ----------------------------------------------------
        # Load persistent memory
        # ----------------------------------------------------

        memory = get_memory()

        if memory:
            memory_text = "\n".join(
                f"- {item['key']}: {item['value']}"
                for item in memory[-20:]
            )

            self.messages.append(
                {
                    "role": "system",
                    "content": (
                        "Relevant previous memory:\n"
                        + memory_text
                    ),
                }
            )

    # ========================================================
    # ARGUMENT NORMALIZATION
    # ========================================================

    def _normalize_arguments(self, arguments) -> dict:
        """
        Normalize tool arguments into a dictionary.
        """

        if arguments is None:
            return {}

        if isinstance(arguments, dict):
            return arguments

        if isinstance(arguments, str):
            try:
                parsed = json.loads(arguments)

                if isinstance(parsed, dict):
                    return parsed

            except json.JSONDecodeError:
                return {}

        return {}

    # ========================================================
    # TOOL-CALL VALIDATION
    # ========================================================

    def _validate_parsed_tool_call(
        self,
        tool_name: str,
        arguments,
    ):
        """
        Validate a parsed compatibility tool call.

        This function does not execute anything.

        It only accepts tool names that already exist in TOOLS.
        """

        if not tool_name:
            return None

        if tool_name not in self.tool_names:
            return None

        normalized = self._normalize_arguments(
            arguments
        )

        return {
            "name": tool_name,
            "arguments": normalized,
        }

    # ========================================================
    # TEXT TOOL-CALL PARSER
    # ========================================================

    def _parse_text_tool_calls(
        self,
        content: str,
    ) -> list[dict]:
        """
        Parse compatibility tool-call formats emitted as text.

        Supported:

        <tool_call>
        {"name":"read_file","arguments":{"path":"x.txt"}}
        </tool_call>

        and:

        <function=read_file>
        <parameter=path>x.txt</parameter>
        </function>

        Parsed calls are returned to the normal execution pipeline.
        """

        if not content:
            return []

        calls: list[dict] = []

        # ----------------------------------------------------
        # Format 1: <tool_call> JSON </tool_call>
        # ----------------------------------------------------

        tool_call_pattern = re.compile(
            r"<tool_call\s*>\s*(.*?)\s*</tool_call\s*>",
            re.IGNORECASE | re.DOTALL,
        )

        for match in tool_call_pattern.finditer(content):
            raw_json = match.group(1).strip()

            if not raw_json:
                continue

            decoder = json.JSONDecoder()
            position = 0

            while position < len(raw_json):

                while (
                    position < len(raw_json)
                    and raw_json[position].isspace()
                ):
                    position += 1

                if position >= len(raw_json):
                    break

                try:
                    value, consumed = decoder.raw_decode(
                        raw_json[position:]
                    )

                except json.JSONDecodeError:
                    break

                position += consumed

                if not isinstance(value, dict):
                    continue

                tool_name = value.get("name")

                arguments = value.get(
                    "arguments",
                    {},
                )

                parsed = self._validate_parsed_tool_call(
                    tool_name,
                    arguments,
                )

                if parsed:
                    calls.append(parsed)

        # ----------------------------------------------------
        # Format 2: <function=tool_name>
        # ----------------------------------------------------

        function_pattern = re.compile(
            r"<function\s*=\s*([A-Za-z_][A-Za-z0-9_]*)\s*>"
            r"(.*?)"
            r"</function\s*>",
            re.IGNORECASE | re.DOTALL,
        )

        parameter_pattern = re.compile(
            r"<parameter\s*=\s*([A-Za-z_][A-Za-z0-9_]*)\s*>"
            r"(.*?)"
            r"</parameter\s*>",
            re.IGNORECASE | re.DOTALL,
        )

        for match in function_pattern.finditer(content):

            tool_name = match.group(1).strip()
            body = match.group(2)

            arguments = {}

            for parameter in parameter_pattern.finditer(body):

                parameter_name = (
                    parameter.group(1).strip()
                )

                parameter_value = (
                    parameter.group(2).strip()
                )

                # Preserve JSON values when possible.
                try:
                    parameter_value = json.loads(
                        parameter_value
                    )

                except json.JSONDecodeError:
                    pass

                arguments[parameter_name] = (
                    parameter_value
                )

            parsed = self._validate_parsed_tool_call(
                tool_name,
                arguments,
            )

            if parsed:
                calls.append(parsed)

        return calls

    # ========================================================
    # COMPATIBILITY ASSISTANT MESSAGE
    # ========================================================

    def _append_compatibility_assistant_message(
        self,
        calls: list[dict],
    ):
        """
        Convert parsed textual tool calls into the same internal
        message structure used by Ollama native tool calls.
        """

        tool_calls = []

        for call in calls:

            tool_calls.append(
                {
                    "type": "function",
                    "function": {
                        "name": call["name"],
                        "arguments": call["arguments"],
                    },
                }
            )

        self.messages.append(
            {
                "role": "assistant",
                "content": "",
                "tool_calls": tool_calls,
            }
        )

    # ========================================================
    # NATIVE TOOL RETRY
    # ========================================================

    def _request_native_tool_retry(self):
        """
        Ask the model to use native tool calling if its textual
        tool-call format could not be parsed.
        """

        self.messages.append(
            {
                "role": "user",
                "content": (
                    "The previous tool-call output could not be "
                    "parsed safely.\n\n"
                    "Do not invent a tool name or use arbitrary "
                    "XML.\n\n"
                    "Use the native tool-calling interface exposed "
                    "to you.\n\n"
                    "If no tool is needed, answer normally."
                ),
            }
        )

    # ========================================================
    # TOOL EXECUTION
    # ========================================================

    def _execute_tool(
        self,
        tool_name: str,
        arguments: dict,
    ):
        """
        Execute all tools through execute_tool().

        The policy/security layer remains authoritative.
        """

        try:

            result = execute_tool(
                tool_name,
                arguments,
            )

            if result is None:
                result = ""

            if not isinstance(result, str):
                result = str(result)

            blocked = result.startswith("BLOCKED:")

            show_tool(
                tool_name=tool_name,
                arguments=arguments,
                result=result,
                success=not blocked,
            )

            return result

        except Exception as exc:

            error = (
                f"{type(exc).__name__}: {exc}"
            )

            show_tool(
                tool_name=tool_name,
                arguments=arguments,
                result=error,
                success=False,
            )

            return f"TOOL ERROR: {error}"

    # ========================================================
    # NATIVE OLLAMA TOOL CALLS
    # ========================================================

    def _handle_native_tool_calls(
        self,
        message: dict,
    ) -> bool:
        """
        Handle Ollama's normal message.tool_calls structure.

        Returns True if at least one native tool call was handled.
        """

        tool_calls = message.get(
            "tool_calls",
            [],
        )

        if not tool_calls:
            return False

        # Preserve the exact assistant response.
        self.messages.append(message)

        for call in tool_calls:

            function = call.get(
                "function",
                {},
            )

            tool_name = function.get("name")

            if not tool_name:
                continue

            arguments = self._normalize_arguments(
                function.get(
                    "arguments",
                    {},
                )
            )

            result = self._execute_tool(
                tool_name,
                arguments,
            )

            self.messages.append(
                {
                    "role": "tool",
                    "content": result,
                }
            )

        return True

    # ========================================================
    # MAIN AGENT LOOP
    # ========================================================

    def run(
        self,
        user_input: str,
    ):
        self.messages.append(
            {
                "role": "user",
                "content": user_input,
            }
        )

        self.current_step = 0

        compatibility_retries = 0
        max_compatibility_retries = 2

        for step in range(
            1,
            MAX_AGENT_STEPS + 1,
        ):

            self.current_step = step

            try:

                with thinking(
                    step,
                    MAX_AGENT_STEPS,
                ):

                    response = chat(
                        self.messages,
                        tools=TOOLS,
                    )

            except Exception as exc:

                show_error(str(exc))
                return

            message = response.get(
                "message",
                {},
            )

            if not message:

                show_error(
                    "Ollama returned an empty message."
                )

                return

            # ------------------------------------------------
            # 1. Native Ollama tool calls
            # ------------------------------------------------

            if self._handle_native_tool_calls(
                message
            ):
                compatibility_retries = 0
                continue

            # ------------------------------------------------
            # 2. Text / compatibility tool calls
            # ------------------------------------------------

            content = message.get(
                "content",
                "",
            )

            text_tool_calls = (
                self._parse_text_tool_calls(
                    content
                )
            )

            # ------------------------------------------------
            # Valid textual tool calls found
            # ------------------------------------------------

            if text_tool_calls:

                self._append_compatibility_assistant_message(
                    text_tool_calls
                )

                for call in text_tool_calls:

                    result = self._execute_tool(
                        call["name"],
                        call["arguments"],
                    )

                    self.messages.append(
                        {
                            "role": "tool",
                            "content": result,
                        }
                    )

                compatibility_retries = 0
                continue

            # ------------------------------------------------
            # Normal assistant response
            # ------------------------------------------------

            self.messages.append(message)

            if content:
                show_agent(content)

            return

        # ----------------------------------------------------
        # Maximum step limit reached
        # ----------------------------------------------------

        show_error(
            f"Agent reached the maximum step limit "
            f"({MAX_AGENT_STEPS})."
        )