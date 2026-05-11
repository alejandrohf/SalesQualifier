"""Módulo `schemas/reference.py` de la plataforma Sales Qualification Agent."""

# schemas/reference.py
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Industry(str, Enum):
    """Define `Industry` dentro de este modulo."""
    legal_business_services = "Legal & Business Services"
    financial_services_insurance = "Financial Services & Insurance"
    real_estate = "Real Estate"
    consumer_goods_retail = "Consumer Goods & Retail"
    energy_utilities_natural_resources = "Energy, Utilities & Natural Resources"
    automotive = "Automotive"
    engineering_manufacturing_construction = "Engineering, Manufacturing & Construction"
    defense_security_aerospace = "Defense, Security & Aerospace"
    government_public_services = "Government & Public Services"
    healthcare_pharma_biotech = "Healthcare, Pharma & Biotech"
    education = "Education"
    nonprofit = "Nonprofit"
    transport_logistics = "Transport & Logistics"
    hospitality_leisure = "Hospitality & Leisure"
    media_telecommunications = "Media & Telecommunications"
    technology_services_platforms = "Technology Services & Platforms"
    other = "Other"


class Area(str, Enum):
    """Define `Area` dentro de este modulo."""
    artificial_intelligence = "Artificial Intelligence"
    security = "Security"
    development = "Development"
    data = "Data"
    consultancy = "Consultancy"
    infrastructure = "Infrastructure"
    extended_reality = "Extended Reality"
    mobile = "Mobile"
    other = "Other"


class Cloud(str, Enum):
    """Define `Cloud` dentro de este modulo."""
    azure = "Azure"
    google_cloud = "Google Cloud"
    aws = "AWS"
    no_cloud = "No Cloud"


class Size(str, Enum):
    """Define `Size` dentro de este modulo."""
    xs = "XS"
    s = "S"
    m = "M"
    l = "L"
    xl = "XL"


class CustomerReferenceBase(BaseModel):
    """Define `CustomerReferenceBase` dentro de este modulo."""
    title: str = Field(..., min_length=3, max_length=200)
    customer: str = Field(..., min_length=2, max_length=200)
    industry: Industry
    area: Area
    cloud: Cloud
    size: Size


class CustomerReferenceCreate(CustomerReferenceBase):
    """Metadata para crear una referencia (el PDF se sube por UploadFile)."""
    pass


class CustomerReferenceUpdate(BaseModel):
    """Permite editar metadata sin tocar documento."""
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    customer: Optional[str] = Field(None, min_length=2, max_length=200)
    industry: Optional[Industry] = None
    area: Optional[Area] = None
    cloud: Optional[Cloud] = None
    size: Optional[Size] = None

    class Config:
        extra = "forbid"


class CustomerReferenceOut(CustomerReferenceBase):
    """Define `CustomerReferenceOut` dentro de este modulo."""
    id: UUID
    document_path: str
    document_version: int = 1
    indexed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        extra = "forbid"