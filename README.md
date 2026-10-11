# ⚡ Electorn AI

> **One CLI. A Complete AI Development Team.**

Transform any compatible computer into a local AI software development company powered by **Ollama** and specialized AI agents.

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://python.org)
[![Ollama](https://img.shields.io/badge/Engine-Ollama%20Local-black.svg)](https://ollama.ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Multi-Agent](https://img.shields.io/badge/Architecture-Sequential%20Multi--Agent-green.svg)](#multi-agent-system)

---

## 🌟 Vision & Overview

Electorn AI turns your terminal into a complete, private, autonomous software development engineering department. By coordinating specialized AI agents sequentially and connecting directly to your local **Ollama** instance, Electorn builds real, production-ready applications with zero API fees, complete privacy, and minimal RAM footprint.

---

## 🎯 Core Capabilities

* 🧠 **Local AI Engine** — Runs 100% locally through Ollama with zero telemetry and zero external API costs.
* 🤖 **Multi-Agent System** — Specialized agents for UI/UX, Frontend, Backend, Databases, API Integration, Testing, and DevOps.
* 💻 **Full Application Development** — Creates complete web applications, REST APIs, desktop tools, CLI utilities, and automation bots.
* 📁 **Autonomous File Management** — Safely reads, writes, patches, and organizes project files within a secure workspace sandbox.
* ⚙️ **Automated Environment Setup** — Configures project dependencies and development environments with user permissions.
* 🔄 **Self-Repair Workflow** — Catches syntax errors and test failures, formulates patches, and reruns tests until passing.
* 🧩 **Small-Model Support** — Optimized for 1B–4B parameter models (such as `llama3.2:1b`, `llama3.2:3b`, `qwen3-vl:4b-instruct`) with concise prompts and fault-tolerant parsing.
* 🛡️ **Memory-Efficient Execution** — Executes agents sequentially to keep memory consumption low (as low as 2GB–4GB RAM).
* 🌍 **Cross-Platform Vision** — Native support for Windows, Linux, and macOS.

---

## 📦 Package Structure

```text
electorn/
├── src/
│   └── electorn/
│       ├── cli.py               # Typer & Rich interactive CLI entrypoint
│       ├── runtime/             # Ollama client, model profiling & auto-selector
│       ├── agents/              # Specialized agents (Architect, DB, Backend, Frontend, QA, etc.)
│       ├── orchestration/       # Multi-agent coordinator, workflow pipeline, memory manager
│       ├── workspace/           # Sandboxed file manager, unified diffs, project blueprint
│       ├── execution/           # Cross-platform runner & runtime detector
│       ├── verification/        # AST syntax checker, test runner & self-repair engine
│       └── storage/             # Config (.electorn.yaml) and session audit logs
├── tests/                       # Complete automated pytest test suite
├── docs/                        # Architecture and deep-dive documentation
├── pyproject.toml               # Python packaging configuration
└── README.md                    # Project documentation
```

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.9+** installed
- **Ollama** installed and running:
  ```bash
  ollama serve
  ```
- Pull your preferred model (e.g. `llama3.2`, `qwen2.5-coder:7b`, or `llama3`):
  ```bash
  ollama pull llama3.2
  ```

### 2. Installation
Install Electorn locally:
```bash
pip install -e .
```

Verify your setup with the built-in system auditor:
```bash
electorn doctor
```

Check your installed Ollama models and compatibility rankings:
```bash
electorn models
```

---

## 💻 CLI Usage

### Direct Autonomous Development
Provide a prompt directly:
```bash
electorn "Build a complete AI-powered job recommendation platform"
```

Or explicitly using the `run` subcommand:
```bash
electorn run "Build a complete REST API with SQLite for inventory tracking"
```

### Specifying Models and Workspace
```bash
# Choose a specific model
electorn "Build a task manager API" --model llama3.2:latest

# Target a dedicated directory
electorn "Build a portfolio website" --workspace ./my-portfolio

# Auto-approve all file creations and command runs
electorn "Build an image resizer CLI" --yes
```

---

## 🤖 The Multi-Agent Team

Electorn AI organizes its engineering process into specialized stages:

| Role | Specialist | Task |
| :--- | :--- | :--- |
| 🧠 **Architect** | Lead System Architect | Analyzes requirements, defines tech stack, and designs file tree |
| 🗄️ **Database** | Database Engineer | Designs schemas, ORM models, migrations, and seed data |
| ⚙️ **Backend** | Backend Developer | Implements REST routes, business logic, and security checks |
| 🎨 **UI/UX** | Design System Engineer | Generates responsive styles, CSS palettes, and layout tokens |
| 💻 **Frontend** | Frontend Developer | Constructs templates, UI components, and client-side logic |
| 🔌 **Integration** | Systems Glue Specialist | Manages environment configs (.env), API clients, and routing |
| 🧪 **QA Tester** | Test Automation Engineer | Writes unit tests and edge-case verification (`pytest`) |
| 🚀 **DevOps** | Deployment Specialist | Generates `requirements.txt`, `README.md`, and execution scripts |

---

## 🔄 Autonomous Self-Repair

When code is written, Electorn doesn't stop at generation:
1. **Syntax Check**: AST parsers verify Python, JSON, and YAML code statically.
2. **Test Discovery**: Tests are identified and executed via `pytest` or `npm test`.
3. **Traceback Diagnosis**: If a test fails, the exact stack trace is handed to the developer agent.
4. **Targeted Patching**: The agent modifies only the offending lines or files.
5. **Re-Verification**: Tests run again until green (up to 3 iterations).

---

## 🧩 Running on Small Models (1B–4B)

Electorn is optimized for small local models:
- **Sequential Pipeline**: Avoids VRAM bloat by running agents one at a time.
- **Context Compaction**: Keeps context windows under 4K/8K tokens.
- **Resilient Parsing**: Flexibly handles JSON and Markdown code blocks without crashing.

---

## 🧪 Testing

Run the full automated test suite:
```bash
pytest
```

---

## 📜 License

MIT License. Built for local, open-source, private AI development.
