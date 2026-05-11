"""Módulo `schemas/opportunity.py` de la plataforma Sales Qualification Agent."""

# schemas/opportunity.py
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import Field, HttpUrl, conint

from .common import (
    AppBaseModel,
    CollaborationType,
    DealSize,
    DecisionRole,
    MainArea,
    Metadata,
    Partner,
    Seniority,
)

class Requester(AppBaseModel):
    """Define `Requester` dentro de este modulo."""
    name: str
    role: DecisionRole = "unknown"
    seniority: Seniority = "employee"


class OpportunityInput(AppBaseModel):
    """
    Input del comercial (formulario).
    - Es lo mínimo que tu workflow necesita para disparar MEDDICC.
    """
    client_name: str
    is_new_client: bool = False
    client_website: Optional[HttpUrl] = None

    requester: Requester

    description: str = Field(..., min_length=20)

    quote_id: Optional[str] = None
    quote_crm_url: Optional[HttpUrl] = None
    shared_folder_url: Optional[HttpUrl] = None

    collaboration_type: CollaborationType = "other"
    partner: Partner = "none"
    main_area: MainArea = "other"

    relationship_trust: conint(ge=1, le=5) = 3  # 1-5
    sales_confidence: str = Field(
        default="unknown",
        description="Alta/Media/Baja/No sabe (normalizamos si quieres).",
    )

    needs_date: bool = False
    proposal_due_date: Optional[datetime] = None

    deal_size: DealSize = "S"

    notes: Optional[str] = None


class OpportunityRecord(OpportunityInput):
    """
    Versión lista para persistir (si decides guardar en BD).
    Puedes ampliarla con IDs, estado, etc.
    """
    metadata: Metadata = Field(default_factory=Metadata)
    opportunity_id: Optional[str] = None
