"""Base declarativa compartida por todos los modelos ORM del proyecto."""

# infrastructure/db/base.py
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """Clase base de SQLAlchemy sobre la que se registran todas las tablas ORM."""
    pass