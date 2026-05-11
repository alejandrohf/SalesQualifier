"""Módulo `workflows/state.py` de la plataforma Sales Qualification Agent."""

# workflows/state.py
from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional, TypedDict
from langchain_core.messages import BaseMessage
from schemas.reference_match import ReferenceMatchesReport

WorkflowStatus = Literal[
    "draft",
    "running",
    "completed",
    "error",
]


class WorkflowState(TypedDict, total=False):
    """
    Estado compartido del grafo LangGraph.
    Nota: usamos TypedDict para evitar acoplarlo a Pydantic.
    Pydantic lo reservamos para schemas (contracts).
    """

    # Mensajería (útil si quieres trazar historial LLM)
    messages: List[BaseMessage]

    # Control
    status: WorkflowStatus
    error: Optional[str]

    # Input principal
    opportunity: Any
    recipients: Dict[str, List[str]]  # {"to": [...], "cc": [...]}
    agent_errors: List[Dict[str, Any]]

    # Outputs LLM
    client_website_summary_raw: Optional[str]  # JSON del client_website_analyzer
    client_website_summary: Optional[Dict[str, Any]]
    meddicc_report_raw: Optional[str]          # JSON string devuelto por opportunity_analyzer
    meddicc_report: Optional[Any]              # MeddiccReport (Pydantic)
    risk_report: Optional[str]                 # texto del risk_analyzer (si lo ejecutas)
    delivery_fit_report: Optional[str]         # texto del delivery_fit_analyzer
    commercial_fit_report: Optional[str]       # texto del commercial_fit_analyzer

    # Dominio (determinista)
    dimension_scores: Optional[Dict[str, float]]
    strategic_flags: Optional[Any]             # StrategicFlags (dataclass)
    has_critical_risk: Optional[bool]
    scoring: Optional[Any]                     # dict output build_scoring_summary(...)
    scoring_summary: Optional[Any]             # ScoringSummary (Pydantic) si lo usas

    # Notificación
    notification_payload_raw: Optional[str]    # JSON (to/cc/subject/html_body/priority)
    notification_payload: Optional[Any]        # EmailNotification (Pydantic)
    notification_result: Optional[str]         # mensaje/estado del envío

    # Observabilidad
    trace: List[str]                           # pasos ejecutados (debug)
    
    # RAG references
    reference_matches: Optional[ReferenceMatchesReport]
    reference_bonus: float
