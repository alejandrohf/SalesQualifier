"""Módulo `infrastructure/db/session.py` de la plataforma Sales Qualification Agent."""

# infrastructure/db/session.py
from __future__ import annotations
from app.config import config

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(
    config.DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)