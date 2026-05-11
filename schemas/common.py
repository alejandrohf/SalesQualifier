"""Módulo `schemas/common.py` de la plataforma Sales Qualification Agent."""

# schemas/common.py
# tipos compartidos (enums/literals, base model, helpers)

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# --- Literals compartidos ---
Status = Literal["complete", "partial", "insufficient"]
ClientContextSource = Literal["input", "web", "input+web"]

QualificationLevel = Literal["high", "medium", "low"]
RecommendedAction = Literal["invest_pre_sales", "request_more_info", "do_not_prioritize"]

CollaborationType = Literal[
    "t&m",
    "fixed_price",
    "profiles_request",
    "rfp",
    "consulting",
    "licenses",
    "other",
]

Partner = Literal[
    "none", "microsoft", "aws", "google", "ibm", "multiverse",
    "snowflake", "databricks", "other"
]

MainArea = Literal["development", "data", "ai", "security", "infrastructure", "other"]

DealSize = Literal["XS", "S", "M", "L", "XL", "XXL"]

Seniority = Literal["cxo", "vp_head", "director", "employee"]

DecisionRole = Literal["decision_maker", "non_decision_maker", "unknown"]


class AppBaseModel(BaseModel):
    """Base común para todos los schemas."""
    model_config = ConfigDict(
        extra="forbid",  # evita campos inesperados (muy útil con JSON de LLM)
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class Metadata(AppBaseModel):
    """Metadatos genéricos para trazabilidad."""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None
    correlation_id: Optional[str] = None
