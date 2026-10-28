from __future__ import annotations

import os
from dataclasses import dataclass, field

from magaza_core.llm_config import LlmConfig, load_llm_config


@dataclass(frozen=True)
class Settings:
    llm_mode: str = field(default_factory=lambda: os.environ.get("LLM_MODE", "fake"))
    google_cloud_project: str | None = field(
        default_factory=lambda: os.environ.get("GOOGLE_CLOUD_PROJECT") or None
    )
    analytics_jsonl_path: str | None = field(
        default_factory=lambda: os.environ.get("ANALYTICS_JSONL_PATH") or None
    )
    tenant_cache_ttl_s: float = 30.0

    @property
    def llm(self) -> LlmConfig:
        return load_llm_config()

    @property
    def location(self) -> str:
        return os.environ.get("GOOGLE_CLOUD_LOCATION", self.llm.region)

    def configure_vertex_env(self) -> None:
        """ADK's Gemini client reads these variables when LLM_MODE=vertex."""
        if self.llm_mode not in ("fake", "vertex"):
            raise ValueError(f"LLM_MODE must be 'fake' or 'vertex', got {self.llm_mode!r}")
        if self.llm_mode != "vertex":
            return
        if not self.google_cloud_project:
            raise RuntimeError(
                "LLM_MODE=vertex requires GOOGLE_CLOUD_PROJECT and Application Default Credentials"
            )
        os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
        os.environ.setdefault("GOOGLE_CLOUD_LOCATION", self.location)
