# Self-Repair Workflow

Electorn AI features an autonomous, closed-loop **Self-Repair Engine** (`electorn.verification.self_repair`) that catches mistakes early, prevents broken code from being finalized, and continuously verifies solutions.

---

## The Verification Loop

```text
    ┌──────────────────────┐
    │   Code Generation    │
    └──────────┬───────────┘
               │
               ▼
    ┌──────────────────────┐        Fail
    │ Static Syntax Check  │ ───────────────┐
    │ (AST, JSON, YAML)    │                │
    └──────────┬───────────┘                ▼
               │ Pass              ┌─────────────────┐
               ▼                   │  Self-Repair 1  │
    ┌──────────────────────┐       │ (Syntax Fixer)  │
    │ Test Suite Runner    │       └────────┬────────┘
    │ (pytest / npm test)  │                │
    └──────────┬───────────┘                ▼
               │ Pass             ┌──────────────────┐
               │                  │ Re-apply & Check │
               ▼                  └──────────────────┘
    ┌──────────────────────┐                ▲
    │ Verified Application │                │ Fail
    └──────────────────────┘        ┌───────┴─────────┐
                                    │  Self-Repair 2  │
                                    │ (Test Diagnoser)│
                                    └─────────────────┘
```

---

## 1. Static Syntax Verification
Before executing code, Electorn runs static AST parsers on all generated source files:
- Python files are parsed using Python's native `ast.parse`.
- JSON configurations are validated using `json.loads`.
- YAML files are verified with `yaml.safe_load`.

If a file has a syntax or indentation error, the Self-Repair Engine immediately passes the exact line number, column, and error message to the backend agent to patch before any code is executed.

---

## 2. Automated Test Verification & Diagnostic Patching
When the test runner executes the test suite:
1. If all tests pass, the project is marked complete.
2. If tests fail or raise tracebacks, the Self-Repair Engine:
   - Captures the exact traceback and failure output.
   - Extracts the relevant files and manifests.
   - Formulates a targeted repair prompt for the specialized developer agent.
   - Writes the corrected code and regenerates test runs.
   - Repeats up to `max_repair_attempts` (default: 3).
