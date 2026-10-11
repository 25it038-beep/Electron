# Small-Model Support & Memory Optimization

Electorn AI is engineered specifically to thrive on consumer hardware, laptops, and lightweight machines running local Ollama models in the **1B–4B parameter range** (such as `llama3.2:1b`, `llama3.2:3b`, `qwen3-vl:4b-instruct`, `phi3:mini`).

---

## The Challenge with Small Models
Smaller models (1B–4B) face distinct limitations compared to frontier cloud models:
1. **Limited Context Windows**: Easily degraded by huge chat transcripts.
2. **Grammar & Strict Schema Brittleness**: Strict JSON schemas can sometimes produce slight markdown irregularities or conversational chatter.
3. **Hardware Pressure**: High RAM / VRAM spikes if multiple agents run concurrently.

---

## Electorn AI's Solutions

### 1. Sequential Execution
Instead of running agents in parallel (which would demand 16GB–32GB of VRAM to hold multiple model contexts), Electorn executes tasks sequentially. Ollama reuses a single loaded model checkpoint in GPU/system RAM, dropping RAM usage to as little as **2GB–4GB**.

### 2. Multi-Format Resilient Code Parsers
Small models often wrap code in varying markdown styles (`FILE: ...`, `### File: ...`, or raw JSON). Electorn's parser uses a tiered extraction engine:
1. Native JSON parser with bracket boundary detection.
2. Markdown code block extractor (`FILE: path/to/file.py\n```...```).
3. Comment file header parser (`# path/to/file.py`).

### 3. Context Window Compaction
The `MemoryManager` dynamically prunes token usage:
- Agents receive only high-level architecture overviews rather than previous agent conversations.
- Only the specific files related to the current agent's component (e.g. database schema for the backend developer) are injected into the active prompt.
- Token budgets are strictly maintained below model context capacities (e.g., 4096 tokens for 3B models).

### 4. Micro-Task Decomposition
Rather than asking a 3B model to generate an entire repository in one prompt, Electorn splits work into focused micro-tasks: schemas, then routes, then templates, then tests.
