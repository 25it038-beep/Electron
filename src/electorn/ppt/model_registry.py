"""Model Registry and Capability Matching for NVIDIA PowerPoint Multi-Model Engine.

Manages specialized role assignments, verified model identifiers, and capabilities.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional
from electorn.ppt.nvidia_client import NvidiaCloudClient


@dataclass
class ModelRoleConfig:
    """Specialized presentation generation role definition."""
    role_key: str
    role_name: str
    description: str
    default_model: str
    context_window: int
    is_reasoning: bool
    supports_vision: bool


# Canonical role definitions for Multi-Model Collaboration
PRESENTATION_ROLES: Dict[str, ModelRoleConfig] = {
    "lead_reasoning": ModelRoleConfig(
        role_key="lead_reasoning",
        role_name="Lead Reasoning & Planning Model",
        description="Analyzes subject, user intent, audience, and formulates strategic presentation outline.",
        default_model="meta/llama-3.2-11b-vision-instruct",
        context_window=128000,
        is_reasoning=True,
        supports_vision=True,
    ),
    "research": ModelRoleConfig(
        role_key="research",
        role_name="Research & Evidence Model",
        description="Analyzes live web search findings, verifies claims, organizes empirical data & citations.",
        default_model="meta/llama-3.2-11b-vision-instruct",
        context_window=128000,
        is_reasoning=False,
        supports_vision=True,
    ),
    "storytelling": ModelRoleConfig(
        role_key="storytelling",
        role_name="Content & Storytelling Model",
        description="Synthesizes topic-specific, non-generic slide narratives, concrete explanations, and notes.",
        default_model="meta/llama-3.2-11b-vision-instruct",
        context_window=128000,
        is_reasoning=False,
        supports_vision=True,
    ),
    "technical_analysis": ModelRoleConfig(
        role_key="technical_analysis",
        role_name="Technical Analysis Model",
        description="Audits technical terminology, validates architecture layers, and cross-checks logic.",
        default_model="meta/llama-3.2-11b-vision-instruct",
        context_window=128000,
        is_reasoning=True,
        supports_vision=True,
    ),
    "design_planner": ModelRoleConfig(
        role_key="design_planner",
        role_name="Presentation Design Planner",
        description="Maps slide content to visual layouts, process flows, metrics cards, and color schemes.",
        default_model="meta/llama-3.2-11b-vision-instruct",
        context_window=128000,
        is_reasoning=False,
        supports_vision=True,
    ),
    "quality_review": ModelRoleConfig(
        role_key="quality_review",
        role_name="Quality & Anti-Repetition Review Model",
        description="Audits complete slide deck for repetition, generic filler, gaps, and unsupported assertions.",
        default_model="meta/llama-3.2-11b-vision-instruct",
        context_window=128000,
        is_reasoning=True,
        supports_vision=True,
    ),
}


class NvidiaModelRegistry:
    """Registry coordinating role model assignments and verifying catalog availability."""

    def __init__(self, client: Optional[NvidiaCloudClient] = None) -> None:
        self.client = client or NvidiaCloudClient()
        self._custom_overrides: Dict[str, str] = {}

    def set_role_model(self, role_key: str, model_id: str) -> None:
        """Override the model assigned to a specific role."""
        if role_key in PRESENTATION_ROLES:
            self._custom_overrides[role_key] = model_id

    def get_model_for_role(self, role_key: str, global_override: Optional[str] = None) -> str:
        """Resolve the model to use for a given role, checking overrides and env vars."""
        # 1. Direct explicit override
        if global_override:
            return global_override

        # 2. Environment variable override
        env_override = os.environ.get("ELECTORN_PPT_MODEL")
        if env_override:
            return env_override

        # 3. Role-specific override
        if role_key in self._custom_overrides:
            return self._custom_overrides[role_key]

        # 4. Default verified model
        role_cfg = PRESENTATION_ROLES.get(role_key)
        return role_cfg.default_model if role_cfg else "meta/llama-3.2-11b-vision-instruct"

    def audit_registry(self) -> List[Dict[str, Any]]:
        """Verify responsiveness of configured models across all presentation roles."""
        available_models = set()
        if self.client.is_configured:
            try:
                available_models = set(self.client.list_available_models())
            except Exception:
                pass

        audit_results = []
        for role_key, config in PRESENTATION_ROLES.items():
            assigned_model = self.get_model_for_role(role_key)
            is_active_in_catalog = assigned_model in available_models if available_models else False
            audit_results.append({
                "role_key": role_key,
                "role_name": config.role_name,
                "assigned_model": assigned_model,
                "context_window": config.context_window,
                "catalog_verified": is_active_in_catalog,
                "description": config.description,
            })
        return audit_results
