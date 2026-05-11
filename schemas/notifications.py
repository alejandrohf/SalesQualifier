"""Módulo `schemas/notifications.py` de la plataforma Sales Qualification Agent."""

# schemas/notifications.py
from __future__ import annotations
from typing import List, Literal
from pydantic import BaseModel, EmailStr, Field

class EmailNotification(BaseModel):
    """Define `EmailNotification` dentro de este modulo."""
    to: List[EmailStr] = Field(min_length=1)
    cc: List[EmailStr] = Field(default_factory=list)
    subject: str = Field(min_length=5, max_length=180)
    html_body: str = Field(min_length=20)
    priority: Literal["high", "medium", "low"]