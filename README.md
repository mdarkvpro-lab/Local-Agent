# Local Agent

**A local-first AI software engineering agent for Windows, powered by Ollama and Qwen3-Coder.**

Local Agent is an autonomous development assistant that runs locally on your machine. It can inspect projects, create and modify files, execute development commands, run tests, work with Git, and complete multi-step software engineering tasks through a controlled tool-execution layer.

Unlike a simple chatbot, Local Agent is designed to **act on your development environment** while keeping tool access behind explicit application-level policies.

> **Status:** Active development

---

## Overview

Local Agent combines a local coding model with an agent loop and a controlled tool system.

You give it a software engineering task. The agent can then inspect the environment, decide which tools are required, execute them, observe their results, and continue working until the task is completed or the configured step limit is reached.

```text
User Request
     │
     ▼
┌─────────────────────┐
│     Local Agent     │
│      Agent Loop     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│       Ollama        │
│   Qwen3-Coder 30B   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│     Tool Layer      │
├─────────────────────┤
│ Files               │
│ Commands            │
│ Python              │
│ Git                 │
│ Project Location    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│    Policy Layer     │
├─────────────────────┤
│ Workspace Rules     │
│ Path Validation     │
│ Protected Files     │
│ Command Restrictions│
│ Approval Policies   │
└──────────┬──────────┘
           │
           ▼
      Local System
```

---

## Features

### Local AI

* Local inference through [Ollama](https://ollama.com/)
* Qwen3-Coder support
* No external AI API required for inference
* Configurable local model endpoint
* Persistent conversation and project memory

### Autonomous Development

* Multi-step task execution
* Project inspection
* File creation and modification
* Development command execution
* Test execution and verification
* Error detection and recovery
* Project creation workflows
* Git-aware development workflows

### Tool Calling

* Native Ollama tool calling
* Compatibility parsing for supported textual tool-call formats
* Centralized tool execution
* Tool-name validation
* Controlled argument handling
* Tool results returned to the agent loop

### Security Controls

* Workspace-based access control
* External path approval
* Protected file detection
* Restricted command execution
* Dangerous shell-operation restrictions
* Git operation restrictions
* Centralized policy enforcement
* Approval-aware tool execution

### Developer Experience

* Rich terminal interface
* Windows File Explorer project selection
* Persistent local memory
* Configurable execution limits
* Windows-first development workflow

---

# Security

Local Agent follows a **defense-in-depth approach**.

The model itself is not considered a security boundary.

Instead, tool requests pass through the application's execution and policy layers before reaching the underlying system.

```text
Model
  │
  ▼
Tool Request
  │
  ▼
Validation
  │
  ▼
Policy Checks
  │
  ├── Workspace validation
  ├── Protected-file checks
  ├── Command restrictions
  ├── Git restrictions
  └── Approval requirements
  │
  ▼
Tool Execution
  │
  ▼
Sanitized Result
  │
  ▼
Agent
```

The model therefore does not directly execute operating-system operations.

### Protected Resources

The application can block access to sensitive resources such as:

* API keys
* Passwords
* Tokens
* Credentials
* SSH private keys
* `.env` files
* Private configuration files
* Other protected file types

### External Paths

The default workflow is workspace-oriented.

Operations outside the approved workspace can require explicit user approval.

The agent is instructed not to bypass these controls, while the actual enforcement belongs to the application's policy and tool layers.

### Command Restrictions

Command execution is intentionally restricted.

The agent is not given unrestricted PowerShell access, and dangerous command patterns can be rejected by the command-execution layer.

Git networking operations such as the following are intentionally restricted:

```text
git push
git pull
git fetch
git clone
git remote
git submodule
```

### Important Security Notice

> **Local Agent is not a security sandbox.**

In particular, Python execution currently does **not** provide complete OS-level or filesystem isolation.

Do not use Local Agent to execute untrusted code or treat it as a hardened security boundary.

---

# Architecture

Local Agent is organized around several independent layers.

```text
┌─────────────────────────────────────────────┐
│                    User                     │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│                 Agent Loop                  │
│                                             │
│  Planning → Tool Call → Result → Continue   │
└──────────────────────┬──────────────────────┘
                       │
              ┌────────┴────────┐
              ▼                 ▼
       ┌─────────────┐   ┌─────────────┐
       │   Ollama    │   │   Memory    │
       │ Qwen3-Coder │   │   System    │
       └──────┬──────┘   └─────────────┘
              │
              ▼
       ┌─────────────┐
       │ Tool Layer  │
       └──────┬──────┘
              │
              ▼
       ┌─────────────┐
       │Policy Layer │
       └──────┬──────┘
              │
              ▼
       ┌─────────────┐
       │ Local OS    │
       └─────────────┘
```

### Agent Loop

The agent loop is responsible for:

1. Receiving the user's request.
2. Sending context and available tools to the model.
3. Processing the model response.
4. Detecting tool calls.
5. Validating requested tools.
6. Executing approved operations.
7. Returning tool results to the model.
8. Continuing until completion or the maximum step limit.

### Tool Layer

Tools provide controlled capabilities such as:

* File operations
* Command execution
* Python execution
* Git operations
* Project-location selection

All execution is routed through the application's tool layer.

### Policy Layer

The policy layer determines whether an operation is allowed.

This layer is intentionally separate from the model so that security decisions do not depend solely on model instructions.

---

# Requirements

* Windows 10/11
* Python 3.12+
* [Ollama](https://ollama.com/)
* A compatible Ollama coding model
* Node.js and npm for JavaScript/TypeScript projects

### Recommended Model

```text
qwen3-coder:30b
```

Other compatible models may work, but tool-calling behavior can vary between models.

---

# Installation

## 1. Clone the repository

```powershell
git clone <YOUR_REPOSITORY_URL>
cd local-agent
```

## 2. Create a virtual environment

```powershell
python -m venv .venv
```

## 3. Activate the environment

```powershell
.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, configure your local execution policy according to your Windows environment rather than bypassing the application's security controls.

## 4. Install dependencies

```powershell
pip install -r requirements.txt
```

## 5. Install the Ollama model

Make sure Ollama is running, then:

```powershell
ollama pull qwen3-coder:30b
```

Verify the model:

```powershell
ollama list
```

## 6. Start Local Agent

```powershell
python main.py
```

---

# Example

Give Local Agent a normal software-engineering task:

```text
Create a simple TypeScript CLI application that prints
"Hello from Local Agent".

Use the appropriate project structure and verify that it compiles.
```

The agent can then:

1. Determine where the project should be created.
2. Inspect the destination.
3. Create the project structure.
4. Create the required source files.
5. Install dependencies when necessary.
6. Run the compiler or tests.
7. Inspect errors.
8. Fix detected problems.
9. Verify the final result.
10. Report what was actually completed.

The goal is to make the workflow resemble working with a development engineer rather than simply asking an AI for code.

---

# Project Structure

```text
local-agent/
│
├── agent.py
├── config.py
├── git_manager.py
├── main.py
├── memory.py
├── ollama_client.py
├── policy.py
├── tools.py
├── ui.py
│
├── requirements.txt
├── .env.example
├── .gitignore
│
├── data/
│
└── workspace/
```

### Core Components

| File               | Responsibility                         |
| ------------------ | -------------------------------------- |
| `agent.py`         | Agent loop and tool-call orchestration |
| `ollama_client.py` | Ollama communication                   |
| `tools.py`         | Tool definitions and execution         |
| `policy.py`        | Security and access-control policies   |
| `git_manager.py`   | Git-related operations                 |
| `memory.py`        | Persistent local memory                |
| `ui.py`            | Terminal interface                     |
| `config.py`        | Runtime configuration                  |
| `main.py`          | Application entry point                |

---

# Configuration

Main configuration is located in `config.py`.

Example:

```python
OLLAMA_URL = "http://127.0.0.1:11434"
MODEL = "qwen3-coder:30b"

MAX_AGENT_STEPS = 30

MAX_TOOL_OUTPUT = 12_000

COMMAND_TIMEOUT = 120
PYTHON_TIMEOUT = 120

MAX_FILE_SIZE = 2_000_000
```

These values control the model endpoint, execution limits, timeouts, and resource restrictions.

---

# Tool Calling

Local Agent supports native tool calling through Ollama.

The agent also contains compatibility handling for models that represent tool calls as structured text.

Regardless of how a tool call is represented, execution is routed through the same application-level execution layer.

```text
Native Tool Call
       │
       ▼
┌──────────────────┐
│ Validate Request │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Policy Checks    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ execute_tool()   │
└────────┬─────────┘
         │
         ▼
     Tool Result
```

This separation is important because the model should never be treated as the authority for what operations are allowed.

---

# Workspace Model

Local Agent is designed around a workspace-first workflow.

For a new standalone project, the agent can request a project destination through the project-location tool rather than silently choosing an arbitrary path.

The intended flow is:

```text
User
 │
 ▼
New Project Request
 │
 ▼
Choose Project Location
 │
 ▼
Inspect Destination
 │
 ▼
Create Project
 │
 ▼
Develop
 │
 ▼
Test
 │
 ▼
Report
```

Explicit project paths supplied by the user can be used directly, subject to the application's access policies.

---

# Current Limitations

Local Agent is still an active development project.

Current limitations include:

* Python execution is not a complete security sandbox.
* Command execution is intentionally restricted.
* Some external filesystem operations require approval.
* Git networking operations are restricted.
* Tool-calling behavior varies between models.
* Qwen/Ollama compatibility behavior may evolve.
* The project currently targets Windows.
* Long-running autonomous tasks are limited by the configured agent-step limit.
* Persistent memory is intentionally limited to a recent subset of stored entries.

---

# Roadmap

### Agent

* More reliable autonomous execution
* Better planning and task decomposition
* Improved recovery from failed tool calls
* Better context management
* More robust tool-call parsing

### Security

* Stronger process isolation
* More granular filesystem permissions
* Improved command-policy enforcement
* Better resource limits
* Additional approval controls

### Development

* More development tools
* Better project detection
* Improved Git workflows
* Expanded language support
* Framework-aware project workflows
* Better test and build detection

### Memory

* Improved long-term memory
* Project-specific memory
* Better memory retrieval
* Context-aware memory management

---

# Philosophy

Local Agent is built around a simple idea:

> **The AI should be able to act, but the application should remain in control.**

The model handles reasoning and software-engineering decisions.

The application handles tools, permissions, approvals, and execution.

This separation allows Local Agent to become more capable without making the model itself the security boundary.

---

# License

This project is currently under development.

Choose and add an appropriate open-source license before publishing the repository.

---

## Built With

* **Python**
* **Ollama**
* **Qwen3-Coder**
* **Windows**
* **Local tool execution**
* **Policy-based access control**

---

**Local Agent — local AI, real tools, controlled execution.**
