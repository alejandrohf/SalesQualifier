"""Tipos y modelos compartidos entre los distintos schemas de la aplicación.

Centraliza literales reutilizables, el modelo base común y los metadatos de
trazabilidad empleados por la API y los workflows.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

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
    """Modelo base compartido por los esquemas de la aplicación."""
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class Metadata(AppBaseModel):
    """Metadatos auxiliares para trazabilidad y correlación entre procesos."""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None
    correlation_id: Optional[str] = None
