"""Base agent class with small-model resilience and file extraction logic."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any, Optional
from electorn.runtime.model_selector import ModelProfile
from electorn.runtime.ollama_client import OllamaClient, OllamaResponse

if TYPE_CHECKING:
    from electorn.workspace.project_state import ProjectState


class BaseAgent:
    """Foundational agent defining prompt styling, tool execution, and code generation."""

    def __init__(
        self,
        name: str,
        role: str,
        icon: str,
        system_prompt: str,
        client: OllamaClient,
        model_profile: ModelProfile,
        temperature: float = 0.2,
    ):
        self.name = name
        self.role = role
        self.icon = icon
        self.system_prompt = system_prompt
        self.client = client
        self.model_profile = model_profile
        self.model = model_profile.name
        self.temperature = temperature

    def _build_system_prompt(self) -> str:
        """Inject small-model instructions and role constraints."""
        prefix = f"You are the {self.name} ({self.role}) in an autonomous software development team.\n"
        if self.model_profile.tier == "small":
            # Direct, concise instructions for 1B-4B models
            constraint = (
                "CRITICAL: Be extremely concise and direct. Do not write filler conversational text. "
                "Always output complete, production-ready code without placeholders or comments like 'TODO'.\n"
            )
        else:
            constraint = (
                "Ensure modern best practices, clean design patterns, defensive programming, and modular structure.\n"
            )
        return prefix + constraint + self.system_prompt

    def ask(self, prompt: str, format_json: bool = False) -> OllamaResponse:
        """Send prompt to agent with its specialized system prompt."""
        system = self._build_system_prompt()
        return self.client.generate(
            model=self.model,
            prompt=prompt,
            system=system,
            temperature=self.temperature,
            context_tokens=self.model_profile.recommended_context,
            format_json=format_json,
        )

    def generate_files(self, task_description: str, context: str, expected_files: Optional[list[str]] = None) -> dict[str, str]:
        """Ask model to produce files and extract them into path -> code mapping."""
        expected_str = f"\nREQUIRED FILES TO IMPLEMENT:\n" + "\n".join(f"- {f}" for f in expected_files) if expected_files else ""
        prompt = f"""
TASK:
{task_description}

PROJECT CONTEXT:
{context}
{expected_str}

CRITICAL IMPLEMENTATION STANDARDS:
1. Every file MUST be 100% complete, fully implemented, working, and immediately runnable.
2. DO NOT use placeholders, stub implementations, ellipsis (...), or comments like '# TODO', '# implement here', '# logic goes here'.
3. Write real functions, classes, data models, error handling, input validation, and full execution flow.
4. If writing HTML/CSS/JS, provide a polished, modern, interactive user interface.
5. If writing Python APIs or CLI tools, include full command handling, arguments, data structures, and main entrypoint.

OUTPUT FORMAT:
Format EVERY file strictly as:
FILE: relative/path/to/filename.ext
```
// Complete working source code here
```
"""
        response = self.ask(prompt)
        files = self.extract_files_from_text(response.content)

        # If any expected files were missing from bulk response, generate them individually
        if expected_files:
            for exp in expected_files:
                clean_exp = exp.replace("\\", "/").strip()
                matching = [k for k in files if k.replace("\\", "/").strip() == clean_exp]
                if not matching:
                    single_prompt = f"""
Write the complete production source code for file '{clean_exp}'.

PROJECT CONTEXT:
{context}

TASK DETAILS:
{task_description}

CRITICAL: Provide 100% complete working implementation for '{clean_exp}'. No TODOs or placeholders.
Format as:
FILE: {clean_exp}
```
// full complete code
```
"""
                    single_resp = self.ask(single_prompt)
                    single_files = self.extract_files_from_text(single_resp.content)
                    if clean_exp in single_files:
                        files[clean_exp] = single_files[clean_exp]
                    elif single_files:
                        files.update(single_files)

        return files

    @staticmethod
    def extract_files_from_text(text: str) -> dict[str, str]:
        """Extract path -> content mapping from response using multiple heuristic parsers."""
        files: dict[str, str] = {}

        # 1. Check for JSON format first
        try:
            parsed = json.loads(text.strip())
            if isinstance(parsed, dict) and "files" in parsed:
                for item in parsed["files"]:
                    if isinstance(item, dict) and "path" in item and "content" in item:
                        files[item["path"].strip()] = item["content"]
                if files:
                    return files
        except Exception:
            pass

        # 2. Check for FILE: <path> \n ```[lang] \n <code> \n ```
        file_pattern = re.compile(
            r"(?:^|\n)(?:FILE|### File|File):\s*`?([a-zA-Z0-9_\-\.\/]+)`?\s*\n+```(?:[a-zA-Z0-9_\-]+)?\s*\n([\s\S]*?)\n```",
            re.MULTILINE,
        )
        for match in file_pattern.finditer(text):
            path = match.group(1).strip()
            code = match.group(2)
            if path and code:
                files[path] = code

        if files:
            return files

        # 3. Check for markdown comments inside code blocks: ```lang\n# path/to/file.py\n...```
        block_pattern = re.compile(
            r"```(?:[a-zA-Z0-9_\-]+)?\s*\n(?:(?:\/\/|#|<!--)\s*([a-zA-Z0-9_\-\.\/]+\.[a-zA-Z0-9]+)\s*(?:-->)?)\s*\n([\s\S]*?)\n```"
        )
        for match in block_pattern.finditer(text):
            path = match.group(1).strip()
            code = match.group(2)
            if path and code:
                files[path] = code

        return files

    def execute_simple_code_repair(self, file_path: str, repair_prompt: str) -> Optional[str]:
        """Ask model for corrected version of a single file."""
        response = self.ask(repair_prompt)
        text = response.content.strip()

        # Extract code inside backticks if present
        code_block = re.search(r"```(?:[a-zA-Z0-9_\-]+)?\s*\n([\s\S]*?)\n```", text)
        if code_block:
            return code_block.group(1)

        # Fallback: if no backticks but text looks like code, return directly
        if len(text.splitlines()) > 1:
            return text

        return None

    def execute_multifixture_repair(self, repair_prompt: str, state: "ProjectState") -> dict[str, str]:
        """Ask model to repair multiple files based on test output."""
        response = self.ask(repair_prompt)
        return self.extract_files_from_text(response.content)
