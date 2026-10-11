"""Intelligent model selection, profiling, and small-model categorization."""

from __future__ import annotations

import re
from typing import Optional
from pydantic import BaseModel, Field
from electorn.runtime.ollama_client import OllamaClient, OllamaModelInfo


class ModelProfile(BaseModel):
    """Profile describing capabilities and memory characteristics of a model."""

    name: str
    tier: str  # "small" (1B-4B), "medium" (7B-8B), "large" (14B+)
    parameter_approx: float  # in billions, e.g. 3.0, 7.0
    recommended_context: int
    is_code_specialized: bool
    description: str


class ModelSelector:
    """Detects, ranks, and configures Ollama models for development workflows."""

    # Coding-focused keywords in model names
    CODE_KEYWORDS = ["coder", "code", "dev", "deepseek-coder", "starcoder", "codellama"]

    def __init__(self, client: OllamaClient):
        self.client = client

    def profile_model(self, model: OllamaModelInfo) -> ModelProfile:
        """Analyze a model name/metadata and produce an execution profile."""
        name_lower = model.name.lower()
        size_gb = model.size_bytes / (1024**3)

        # Estimate parameters
        param_approx = 7.0  # default assumption
        param_match = re.search(r"(\d+(?:\.\d+)?)b", name_lower)
        if param_match:
            param_approx = float(param_match.group(1))
        elif size_gb < 2.5:
            param_approx = 3.0
        elif size_gb < 5.5:
            param_approx = 7.0
        elif size_gb < 10.0:
            param_approx = 14.0
        else:
            param_approx = 32.0

        if param_approx <= 4.5:
            tier = "small"
            recommended_context = 2048
        elif param_approx <= 9.0:
            tier = "medium"
            recommended_context = 8192
        else:
            tier = "large"
            recommended_context = 16384

        is_code = any(k in name_lower for k in self.CODE_KEYWORDS)

        return ModelProfile(
            name=model.name,
            tier=tier,
            parameter_approx=param_approx,
            recommended_context=recommended_context,
            is_code_specialized=is_code,
            description=f"{tier.capitalize()} model (~{param_approx:g}B parameters, {size_gb:.1f} GB)",
        )

    def select_best_model(self, preferred_model: Optional[str] = None) -> ModelProfile:
        """Select preferred model or auto-select the best available installed model."""
        installed = self.client.list_models()
        if not installed:
            raise RuntimeError(
                "No Ollama models found installed! Run `ollama pull llama3.2` or `ollama pull qwen2.5-coder:7b`."
            )

        profiles = [self.profile_model(m) for m in installed]

        if preferred_model:
            # Check exact match
            for p in profiles:
                if p.name == preferred_model or p.name.split(":")[0] == preferred_model.split(":")[0]:
                    return p
            # If specified model wasn't found in installed list, return a default profile for it
            return ModelProfile(
                name=preferred_model,
                tier="small" if "3b" in preferred_model or "1b" in preferred_model else "medium",
                parameter_approx=3.0,
                recommended_context=4096,
                is_code_specialized=True,
                description=f"User-specified model: {preferred_model}",
            )

        # Heuristic scoring for auto-selection:
        # 1. Code specialized models get +50
        # 2. 7B-8B get +30 (sweet spot of quality and local RAM)
        # 3. 3B-4B get +25 (fast, light)
        # 4. Larger get +15
        def score(p: ModelProfile) -> float:
            s = 0.0
            if p.is_code_specialized:
                s += 40.0
            # Sweet spot: 3B-8B models run fast locally without hanging
            if p.tier == "small":
                s += 50.0
            elif p.tier == "medium":
                s += 40.0
            else:
                # Heavy 14B+ models frequently hang or exceed local GPU/VRAM limits
                s -= 50.0

            # Heavily penalize vision/multimodal models for pure source code tasks
            if "-vl" in p.name.lower() or "vision" in p.name.lower():
                s -= 60.0

            # Favor tested models with stellar speed/quality balance
            if "llama3.2" in p.name.lower():
                s += 35.0
            elif "llama3" in p.name.lower():
                s += 25.0
            elif "qwen2.5-coder" in p.name.lower():
                s += 30.0

            return s

        profiles.sort(key=score, reverse=True)
        return profiles[0]
