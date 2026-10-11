# ⚡ Electorn AI — Autonomous AI Software Development Engine

> **One CLI. A Complete AI Development Team.**  
> *Engineered as part of [HS AI Solutions](https://hs-ai-studio.onrender.com/).*

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://python.org)
[![PyPI](https://img.shields.io/badge/PyPI-ElectronAi-blue.svg)](https://pypi.org/project/ElectronAi/)
[![Engine](https://img.shields.io/badge/Engine-Ollama%20%2B%20Cloud-black.svg)](https://ollama.ai)
[![Studio](https://img.shields.io/badge/Studio-HS%20AI%20Solutions-blueviolet.svg)](https://hs-ai-studio.onrender.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/Tests-35%20Passed-green.svg)](#testing)

---

## 🌟 What is Electorn AI?

**Electorn AI** is not a chatbot that simply prints code snippets to the screen. It is an **autonomous software engineering and development engine** designed to plan, build, test, repair, and run complete, multi-file software applications directly on your computer.

When you give Electorn a natural-language description (e.g. *"Build a job portal REST API with FastAPI and SQLite"*), Electorn:

1. **Analyzes requirements** and creates an architectural specification.
2. **Scaffolds directories and files** cleanly in your workspace.
3. **Generates connected source code** across database models, backend APIs, frontend UI, tests, and configuration.
4. **Executes real development commands** (e.g. `pip install -r requirements.txt`, `npm install`) through its dedicated Windows PowerShell automation engine.
5. **Runs automated test suites** (`pytest`), catches syntax or assertion errors, and **iteratively self-repairs** failing code.
6. **Performs security scans** to ensure no credentials or secrets are exposed.
7. **Launches live background servers** and automatically detects active ports (`http://localhost:8000`) for instant live preview.

---

## 🚀 Quick Start Guide

### 1. Installation

Install via PyPI:
```bash
pip install ElectronAi
```

Or clone and install in editable mode for local development:
```bash
git clone https://github.com/25it038-beep/Electron.git
cd Electron
pip install -e .
```

> **Note for Windows Users:** If your Python Scripts folder is not on your system PATH, you can invoke Electorn anywhere via `python -m electorn` or `py -m electorn`.

### 2. Verify Your Environment

Run the built-in system auditor to check installed runtimes:
```bash
electorn doctor
```
This inspects your **Operating System, Python version, Ollama Engine, Git, Node.js, PowerShell (5.1 or Core), and Docker**.

### 3. Connect Local AI Inference (Ollama)

Electorn is powered locally by Ollama with 100% data privacy:
```bash
# Start Ollama engine
ollama serve

# Pull a coding model (recommended: llama3.2:1b, llama3.2:3b, or qwen2.5-coder:7b)
ollama pull llama3.2
```

---

## 📖 Complete Usage Guide

Electorn features both an **interactive terminal menu** and direct **one-line CLI commands**.

### Option A: Interactive Mode (Simply run `electorn`)

If you run `electorn` without arguments, an interactive terminal launcher appears:

```text
⚡ ELECTORN AI — One CLI. A Complete AI Development Team.
v0.1.0 | Powered by Ollama Local AI Engine
Part of HS AI Solutions: https://hs-ai-studio.onrender.com/

Choose your development mode:
  1. 🚀 Autonomous App Creator — Build a full application, generate files, run tests & self-repair
  2. 💬 Futuristic AI Chat Studio — Interactive multi-agent terminal with code streaming & web search
  3. 🩺 System Doctor — Audit developer runtimes, Ollama engine & models
  4. 🌐 HS AI Solutions Studio — Explore product ecosystem
  0. ❌ Exit
```

---

### Option B: Command-Line Interface (Full Command Reference)

| Command | Syntax | What It Does |
| :--- | :--- | :--- |
| **`build` / `run`** | `electorn "..."` or `electorn run "..."` | Builds a complete application end-to-end from prompt. |
| **`preview`** | `electorn preview` | Starts a background development server and reports active URL. |
| **`stop`** | `electorn stop` | Terminates all background dev servers started in the workspace. |
| **`analyze`** | `electorn analyze [path]` | Inspects codebase files, entry points, endpoints, and credentials. |
| **`explain`** | `electorn explain [path]` | Explains architecture, entry points, and workflows of a project/file. |
| **`fix`** | `electorn fix` | Scans workspace for syntax errors and failing tests, then repairs them. |
| **`test`** | `electorn test` | Executes test suites and outputs a structured Quality Validation Report. |
| **`refactor`** | `electorn refactor <file> -i "..."` | Rewrites a specific file for better architecture with auto-checkpoints. |
| **`docs`** | `electorn docs` | Generates comprehensive README and architecture documentation. |
| **`diff`** | `electorn diff [checkpoint_id]` | Shows unified syntax-highlighted diff against recent checkpoints. |
| **`checkpoint`** | `electorn checkpoint "message"` | Creates an instant, recoverable snapshot in `.electorn/checkpoints/`. |
| **`rollback`** | `electorn rollback [id]` | Safely restores workspace files to a previous snapshot. |
| **`status`** | `electorn status` | Displays workspace files, active model, checkpoints, and memory. |
| **`mode`** | `electorn mode <local\|cloud\|auto>` | Switches operating mode (local Ollama, cloud API, or auto). |
| **`config`** | `electorn config` | Displays and audits current `.electorn.yaml` configuration. |
| **`doctor`** | `electorn doctor` | Checks developer tools (Python, Node.js, PowerShell, Git, Docker, Ollama). |
| **`models`** | `electorn models` | Lists installed Ollama models with parameter sizes and tier ratings. |
| **`chat`** | `electorn chat` | Futuristic multi-agent conversational studio with live web search. |
| **`studio`** | `electorn studio` | Explores HS AI Solutions product ecosystem and live deployments. |
| **`version`** | `electorn version` | Displays Electorn AI version and studio metadata. |

---

## 🛠️ Step-by-Step Command Walkthroughs

### 1. Building a Full Application (`electorn run` or `electorn "<prompt>"`)

Build an entire application autonomously:

```bash
electorn "Build a REST API with FastAPI and SQLite for a job portal with applicant and recruiter endpoints"
```

To automatically install dependencies, run tests, and launch a live preview server on completion, pass `--preview` (or `-p`):

```bash
electorn "Build a responsive notes app with Flask and SQLite" --preview
```

**What Happens Under the Hood:**
* **Section 5 Task Planner:** Renders real-time stage badges:
  ```text
  ELECTORN APPLICATION ENGINE
  ========================================
  Project: job-portal-api
  Workspace: C:\Users\YourUser\Projects\job-portal

  [PASS] Requirements analyzed
  [PASS] Project structure created
  [PASS] Database & persistence layer generated
  [PASS] Backend API and services generated
  [PASS] Automated test suite generated
  [PASS] Dependency and configuration validation
  [RUN ] Code verification & quality assurance
  ```
* **Section 8 Validation Report:** Outputs an honest validation summary:
  ```text
  APPLICATION VALIDATION
  ========================================
  Files generated:       6
  Dependencies:          Installed via pip
  Syntax validation:     Passed
  Unit tests:            Passed
  Integration tests:     Passed
  Production build:      Passed
  Security checks:       Passed (No credentials exposed)

  Final status:
  READY FOR REVIEW
  ```

---

### 2. Managing Background Development Servers (`preview` & `stop`)

Electorn can run dev servers in the background without locking your terminal:

```bash
# Start background dev server (auto-detects main.py, app.py, or npm start)
electorn preview

# Or specify a custom command
electorn preview -c "uvicorn app:app --port 8000"
```
Electorn polls startup logs and outputs:
```text
🚀 Starting background dev server: uvicorn app:app --port 8000...
✨ Server live at: http://localhost:8000 (PID: 14892)
```

To stop all running servers in the workspace:
```bash
electorn stop
```

---

### 3. Auditing & Inspecting a Codebase (`analyze` & `explain`)

Audit any repository or folder for tech stacks, database models, API endpoints, and potential credential leaks:

```bash
electorn analyze .
```

To generate an architectural explanation of the project or an individual source file:
```bash
electorn explain main.py
```

---

### 4. Autonomous Bug Fixing & Self-Repair (`fix`)

If a codebase has syntax errors or failing tests, Electorn can automatically diagnose and fix them:

```bash
electorn fix
```
Electorn runs an AST static syntax check, discovers tests via `pytest`, extracts failing stack traces, generates targeted patches, and verifies that tests pass before committing.

---

### 5. Checkpoints & Instant Rollback (`checkpoint`, `diff`, `rollback`)

Electorn protects your workspace with zero-overhead snapshot management:

```bash
# 1. Create a snapshot before making big changes
electorn checkpoint "Before switching to PostgreSQL"

# 2. View what changed since the last snapshot
electorn diff

# 3. Roll back immediately if code breaks
electorn rollback
```

---

### 6. Interactive Futuristic Chat Studio with Live Web Search (`chat`)

Launch the multi-agent conversational studio:

```bash
electorn chat
```

#### Futuristic Chat Features & Slash Commands:
* **Token Streaming:** Real-time generation directly from Ollama.
* **Autonomous Web Search:** Type `/search <query>` to search DuckDuckGo without an API key.
* **Web-Augmented Synthesis:** Type `/web <prompt>` to search the web and synthesize an answer with citations.
* **Agent Switching:** Type `/agent backend` or `/agent architect` to switch specialized AI personas on the fly.
* **Live File Inspector:** Type `/files` to see the workspace tree or `/read <filename>` to inspect code.
* **Instant Application Pipeline:** Type `/build <prompt>` directly inside chat to trigger full application creation.

---

## 🔒 Security & Windows Guardrails

Electorn is engineered with production-grade safety policies:

* **Workspace Sandbox:** File operations are strictly bound to the target directory. Attempts to modify files outside the workspace are blocked.
* **Permission Engine:** Routine development operations (creating files, running `pip install`, `npm install`, `pytest`) are permitted by default for seamless flow. High-risk system actions (e.g. disk alteration, firewall edits, registry tweaks) require explicit confirmation.
* **PowerShell Execution Security:** Commands run using PowerShell's `-NoProfile -NonInteractive -ExecutionPolicy Bypass` flags with process tree isolation.
* **Credential Hygiene:** An automated regex scanner checks generated code for exposed API keys, private tokens, and credentials before declaring completion.

---

## 🧪 Testing

Run the automated test suite locally:
```bash
py -m pytest -v
```
**All 35 unit and integration tests pass with 100% reliability**, covering:
* PowerShell execution engine & background process management
* End-to-end ApplicationBuilder orchestration
* Multi-agent file generation and streaming
* AST syntax analysis and self-repair loops
* Checkpoints, diffing, and rollbacks
* CLI command routing and environment auditing

---

## 🌐 HS AI Solutions Ecosystem

Electorn AI is part of the **[HS AI Solutions](https://hs-ai-studio.onrender.com/)** platform:

| Product | Focus | Live Access |
| :--- | :--- | :--- |
| **⚡ Electorn AI** | Autonomous Dev Team Engine | Local CLI (`electorn`) / [PyPI](https://pypi.org/project/ElectronAi/) |
| **🛡️ Pendulum** | Stealth Private Desktop AI Browser | [Details](https://hs-ai-studio.onrender.com/products/pendulum) |
| **🎨 Lumina** | AI Presentation Architecture Studio | [Launch](https://lumina-pghe.onrender.com/) |
| **🤖 HSBot** | Multi-Model Unified Chat Workspace | [Launch](https://hs-chatbot-3.onrender.com/) |
| **📜 Ledger** | Digital Identity & Career Intelligence | [Launch](https://ledger-2-er3t.onrender.com/) |
| **⛨ Phishing Defence** | AI Threat Operations & Link Verification | [Launch](https://forensic-ai-1-mma4.onrender.com/) |
| **💻 HS CODE** | Native Windows AI Coding Companion | [Details](https://hs-ai-studio.onrender.com/products/hs-code) |
| **🎓 Academia AI** | Personal Learning Operating System | [Launch](https://acdemia01-2.onrender.com/) |

---

## 👨‍💻 Creator & License

* **Studio:** [https://hs-ai-studio.onrender.com/](https://hs-ai-studio.onrender.com/)
* **Author:** Harshan Seliyan
* **Email:** [harshanseliyan28@gmail.com](mailto:harshanseliyan28@gmail.com)
* **License:** [MIT](https://opensource.org/licenses/MIT)
