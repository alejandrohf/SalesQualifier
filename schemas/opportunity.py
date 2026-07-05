"""Schemas de entrada y persistencia lógica para oportunidades comerciales."""

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
    """Persona de contacto asociada a la oportunidad y su capacidad de influencia."""
    name: str
    role: DecisionRole = "unknown"
    seniority: Seniority = "employee"


class OpportunityInput(AppBaseModel):
    """Datos mínimos y contexto comercial necesarios para cualificar una oportunidad."""
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

    relationship_trust: conint(ge=1, le=5) = 3
    sales_confidence: str = Field(
        default="unknown",
        description="Percepción inicial del comercial sobre la probabilidad o solidez de la oportunidad.",
    )

    needs_date: bool = False
    proposal_due_date: Optional[datetime] = None

    deal_size: DealSize = "S"

    notes: Optional[str] = None


class OpportunityRecord(OpportunityInput):
    """Versión persistible de la oportunidad con metadatos de trazabilidad e identificador."""
    metadata: Metadata = Field(default_factory=Metadata)
    opportunity_id: Optional[str] = None
