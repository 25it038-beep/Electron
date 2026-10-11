# ⚡ Electorn AI — Autonomous AI Software Development CLI

> **One CLI. A Complete AI Development Team.**  
> *Engineered as part of [HS AI Solutions](https://hs-ai-studio.onrender.com/).*

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://python.org)
[![PyPI](https://img.shields.io/badge/PyPI-ElectronAi-blue.svg)](https://pypi.org/project/ElectronAi/)
[![Engine](https://img.shields.io/badge/Engine-Ollama%20%2B%20Cloud-black.svg)](https://ollama.ai)
[![Studio](https://img.shields.io/badge/Studio-HS%20AI%20Solutions-blueviolet.svg)](https://hs-ai-studio.onrender.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/Tests-31%20Passed-green.svg)](#testing)

---

## 🌟 Overview

**Electorn AI** turns your terminal into a full, private, autonomous software development engineering department. It accepts natural-language software specifications (e.g. *"Build a job recommendation platform with FastAPI and SQLite"*) and executes an end-to-end engineering workflow:

1. **Requirements & Architecture** — Discovers requirements, plans file trees, and selects optimal stacks.
2. **Autonomous Multi-Agent Generation** — Sequential execution across specialized roles (Architect, Database, Backend, Frontend, DevOps, QA).
3. **Task Planning Engine** — Tracks verifiable task states (`PENDING`, `IN_PROGRESS`, `COMPLETED`, `FAILED`, `BLOCKED`, `CANCELLED`) with terminal progress badges.
4. **Codebase Intelligence & Security** — Inspects repositories, maps routes and data models, and detects hardcoded secrets.
5. **Self-Healing Code Loop** — Catches AST syntax errors and test failures, performs targeted patch generation, and rolls back if patches degrade the project.
6. **Change Management & Safe Rollbacks** — Automatic checkpoints, unified diffs, and instant rollback.
7. **Multi-Mode Runtimes** — Seamlessly operates across **Local** (Ollama offline), **Cloud** (API key), and **Auto** modes.
8. **Live Autonomous Web Search** — Queries web documentation and real-time knowledge with zero API keys required.

---

## 🛠️ Complete CLI Command Reference

| Command | Usage | Description |
| :--- | :--- | :--- |
| `build` / `run` | `electorn build "..."` | Full autonomous application generation from natural-language prompts. |
| `analyze` | `electorn analyze [path]` | Multi-file codebase discovery, file counts, entry points, routes, and secret scanner. |
| `explain` | `electorn explain [path]` | Explains project architecture, design decisions, and data workflows. |
| `fix` | `electorn fix` | Autonomous self-repair of syntax errors and failing unit tests. |
| `test` | `electorn test` | Executes quality verification and produces honest status reports. |
| `refactor` | `electorn refactor <file>` | Targeted refactoring of components with automated pre-refactor checkpoints. |
| `docs` | `electorn docs` | Generates comprehensive README and architecture documentation. |
| `diff` | `electorn diff [checkpoint_id]` | Shows unified syntax-highlighted diff against recent checkpoints. |
| `checkpoint` | `electorn checkpoint "msg"` | Creates recoverable snapshot of the workspace in `.electorn/checkpoints/`. |
| `rollback` | `electorn rollback [id]` | Safely restores workspace files from a previous snapshot. |
| `status` | `electorn status` | Displays workspace files, active model, checkpoints, and engineering memory. |
| `mode` | `electorn mode <local\|cloud\|auto>` | Inspects or switches active operating mode. |
| `config` | `electorn config` | Displays and audits current `.electorn.yaml` settings. |
| `version` | `electorn version` | Displays Electorn AI version and studio metadata. |
| `doctor` | `electorn doctor` | Audits system runtimes, Python, Ollama, Git, Node, and Docker. |
| `models` | `electorn models` | Inspects installed Ollama models and displays suitability profiles. |
| `chat` | `electorn chat` | Futuristic multi-agent conversational studio with token streaming and web search. |
| `studio` | `electorn studio` | Explores HS AI Solutions product ecosystem and live deployments. |

---

## 🚀 Installation & Setup

### 1. Install via PyPI or Local Development
```bash
# Install package
pip install ElectronAi

# Or clone and install editable
git clone https://github.com/25it038-beep/Electron.git
cd Electron
pip install -e .
```

### 2. Verify Your Environment
```bash
electorn doctor
```

### 3. Start Local Inference (Ollama)
```bash
ollama serve
ollama pull llama3.2:1b
```

---

## 💡 Usage Examples

### 1. Generating an Application
```bash
electorn build "Build a job portal REST API with FastAPI and SQLite for applicant and recruiter workflows"
```

Terminal Output:
```text
ELECTORN DEVELOPMENT AGENT
Project: job-portal

[PASS] Requirements analyzed
[PASS] Project structure created
[PASS] Database & persistence layer generated
[PASS] Backend API and services generated
[PASS] Automated test suite generated
[PASS] Dependency and configuration validation
[PASS] Code verification & quality assurance
```

### 2. Inspecting and Auditing an Existing Codebase
```bash
electorn analyze .
```
Audits file counts, languages, routes, ORM models, entry points, and scans for hardcoded secrets or exposed API keys.

### 3. Checkpoints & Rollbacks
```bash
# Create safe snapshot
electorn checkpoint "Before database migration"

# Inspect changes
electorn diff

# Restore snapshot if something breaks
electorn rollback
```

### 4. Interactive Chat Studio with Web Search
Launch the multi-agent chat interface:
```bash
electorn chat
```
Futuristic Studio Commands:
* `/search <query>` — Autonomous live web search with citations.
* `/web <prompt>` — Queries the web and feeds live findings to the agent to synthesize answers.
* `/agent <name>` — Switch personas dynamically (`architect`, `backend`, `frontend`, `database`, `qa`, `devops`).
* `/model [name]` — Inspect or switch active neural model on the fly.
* `/files` — Display workspace file tree.
* `/read <file>` — Inspect workspace file contents.
* `/build <prompt>` — Launch full autonomous generation directly from chat.

---

## 🔒 Security & Sandboxing Guardrails

* **Workspace Sandbox** — All autonomous file operations are strictly bound to the target workspace; path traversal attempts outside the boundary are rejected.
* **Argument Array Subprocess Security** — Shell execution utilizes explicit argument arrays where possible, preventing arbitrary shell injection.
* **Interactive Approvals** — Modifying existing files or executing system commands requires confirmation unless `--yes` is explicitly configured.
* **Secret Scanner** — Codebase analysis actively scans for credential leakage and blocks private keys from LLM prompts.

---

## 🧪 Testing

Run the automated test suite:
```bash
pytest -v
```
All **31 automated tests** covering agents, task planner, codebase analyzer, checkpoints, file manager, runner, web search, providers, and CLI commands pass with 100% reliability.

---

## 🌐 HS AI Solutions Ecosystem

Electorn AI is part of **[HS AI Solutions](https://hs-ai-studio.onrender.com/)**:

| Product | Focus | Live Access |
| :--- | :--- | :--- |
| **⚡ Electorn AI** | Autonomous Dev Team CLI | Local CLI (`electorn`) / [PyPI](https://pypi.org/project/ElectronAi/) |
| **🛡️ Pendulum** | Stealth Private Desktop AI Browser | [Details](https://hs-ai-studio.onrender.com/products/pendulum) |
| **🎨 Lumina** | AI Presentation Architecture Studio | [Launch](https://lumina-pghe.onrender.com/) |
| **🤖 HSBot** | Multi-Model Unified Chat Workspace | [Launch](https://hs-chatbot-3.onrender.com/) |
| **📜 Ledger** | Digital Identity & Career Intelligence | [Launch](https://ledger-2-er3t.onrender.com/) |
| **⛨ Phishing Defence** | AI Threat Operations & Link Verification | [Launch](https://forensic-ai-1-mma4.onrender.com/) |
| **💻 HS CODE** | Native Windows AI Coding Companion | [Details](https://hs-ai-studio.onrender.com/products/hs-code) |
| **🎓 Academia AI** | Personal Learning Operating System | [Launch](https://acdemia01-2.onrender.com/) |

---

## 👨‍💻 Creator & Support

* **Studio:** [https://hs-ai-studio.onrender.com/](https://hs-ai-studio.onrender.com/)
* **Author:** Harshan Seliyan
* **Email:** [harshanseliyan28@gmail.com](mailto:harshanseliyan28@gmail.com)
* **License:** MIT
