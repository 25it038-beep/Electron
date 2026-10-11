# Electorn AI Architecture

**One CLI. A Complete AI Development Team.**

Electorn AI transforms any personal computer into an autonomous software engineering organization powered by local Ollama models.

---

## High-Level System Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                       Electorn CLI                          │
│               electorn "<prompt>" / electorn run            │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Multi-Agent Team Orchestrator               │
│                                                             │
│  [Architect] ──> [Database] ──> [Backend] ──> [Frontend]    │
│       │                                             │       │
│       ▼                                             ▼       │
│   [DevOps]   <──  [Self-Repair] <── [QA Tests] <── [Glue]   │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
               ▼                              ▼
┌──────────────────────────────┐ ┌────────────────────────────┐
│      Workspace & Files       │ │   Local AI Runtime Engine  │
│  - Sandboxed FileManager     │ │  - Ollama REST API Client  │
│  - Diffs & Backups           │ │  - Model Profiler & Auto   │
│  - AST Syntax Verifier       │ │  - Sequential Memory Mgr   │
└──────────────────────────────┘ └────────────────────────────┘
```

---

## Core Subsystems

### 1. Runtime (`electorn.runtime`)
- **`OllamaClient`**: Direct HTTP communication with the local Ollama daemon (`/api/chat`, `/api/generate`, `/api/tags`). Supports structured JSON mode, token streaming, and resilient markdown extraction.
- **`ModelSelector`**: Analyzes host models, categorizes them into Small (1B–4B), Medium (7B–8B), and Large (14B+), profiles code specialization, and auto-selects the optimal engine.

### 2. Autonomous Workspace (`electorn.workspace`)
- **`FileManager`**: Enforces strict directory sandboxing to prevent path traversal, generates unified diffs for modifications, and backs up files to `.electorn/backups/`.
- **`ProjectState`**: Tracks created and verified files, maintains the project blueprint, and provides compact token summaries.
- **`PermissionManager`**: Guardrail system prompting users before external commands or destructive operations unless auto-approved with `--yes`.

### 3. Execution & Verification (`electorn.execution`, `electorn.verification`)
- **`CommandRunner`**: Cross-platform shell executor (Windows/macOS/Linux) with timeouts, stderr/stdout capture, and environment isolation.
- **`SyntaxChecker`**: Static AST verification for Python, JSON, and YAML before test runs.
- **`TestRunner`**: Automatic discovery of `pytest`, `unittest`, or `npm test` suites with test count parsing.
- **`SelfRepairEngine`**: Iterative closed-loop repair mechanism that feeds runtime tracebacks back to specialized developer agents to patch code until tests pass.

### 4. Sequential Memory Manager (`electorn.orchestration.memory_manager`)
- Avoids GPU/RAM out-of-memory errors by running agent stages sequentially.
- Prunes context windows and delivers only relevant component files to each agent.
