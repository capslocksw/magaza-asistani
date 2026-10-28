"""Loads config/llm.yaml: model IDs and unit prices are configuration, not code."""

from __future__ import annotations

import os
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class PricePeriod(BaseModel):
    until: date | None = None
    input: float
    output: float


class ChatModelConfig(BaseModel):
    default_model: str
    thinking_level: str | None = None
    max_llm_calls_per_turn: int = 10


class EmbeddingModelConfig(BaseModel):
    model: str
    dimension: int = 768
    batch_size: int = 1
    concurrency: int = 8
    min_similarity: float = 0.0


class BudgetConfig(BaseModel):
    """Hard cap on real model spend (ADR 007); required so a config without it fails closed."""

    hard_cap_usd: float = Field(gt=0)
    safety_margin_usd: float = Field(ge=0)
    max_output_tokens: int = Field(gt=0)
    chars_per_token: float = Field(gt=0)


class LlmConfig(BaseModel):
    region: str
    chat: ChatModelConfig
    embedding: EmbeddingModelConfig
    pricing_usd_per_1m_tokens: dict[str, list[PricePeriod]]
    budget: BudgetConfig

    def price(self, model: str, when: datetime | date | None = None) -> PricePeriod | None:
        periods = self.pricing_usd_per_1m_tokens.get(model)
        if not periods:
            return None
        day = (when.date() if isinstance(when, datetime) else when) or date.today()
        for period in periods:
            if period.until is None or day <= period.until:
                return period
        return periods[-1]

    def estimate_cost_usd(
        self, model: str, tokens_in: int, tokens_out: int, when: datetime | date | None = None
    ) -> float:
        period = self.price(model, when)
        if period is None:
            return 0.0
        return round((tokens_in * period.input + tokens_out * period.output) / 1_000_000, 8)


def _default_path() -> Path:
    env = os.environ.get("LLM_CONFIG_PATH")
    if env:
        return Path(env)
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "config" / "llm.yaml"
        if candidate.exists():
            return candidate
    return Path("config/llm.yaml")


def repo_root() -> Path:
    """Directory that holds config/llm.yaml (local state such as the spend ledger lives under its .local/)."""
    return _default_path().resolve().parent.parent


@lru_cache(maxsize=4)
def load_llm_config(path: str | None = None) -> LlmConfig:
    data = yaml.safe_load(Path(path or _default_path()).read_text(encoding="utf-8"))
    return LlmConfig.model_validate(data)
