"""Definición del estado compartido usado por el grafo LangGraph del workflow."""

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
    """Estado compartido entre los nodos del workflow de cualificación."""

    # Mensajes intercambiados durante la ejecución del workflow.
    messages: List[BaseMessage]

    # Control general de ejecución.
    status: WorkflowStatus
    error: Optional[str]

    # Datos de entrada y destinatarios asociados.
    opportunity: Any
    recipients: Dict[str, List[str]]  # {"to": [...], "cc": [...]}
    agent_errors: List[Dict[str, Any]]

    # Resultados producidos por los agentes del workflow.
    client_website_summary_raw: Optional[str]  # JSON del client_website_analyzer
    client_website_summary: Optional[Dict[str, Any]]
    meddicc_report_raw: Optional[str]          # Respuesta JSON serializada devuelta por opportunity_analyzer.
    meddicc_report: Optional[Any]              # Informe MEDDICC validado.
    risk_report: Optional[str]                 # Informe textual de riesgos.
    delivery_fit_report: Optional[str]         # Evaluación de encaje de entrega.
    commercial_fit_report: Optional[str]       # Evaluación de encaje comercial.

    # Resultados del análisis determinista.
    dimension_scores: Optional[Dict[str, float]]
    strategic_flags: Optional[Any]             # Indicadores estratégicos derivados de la oportunidad.
    has_critical_risk: Optional[bool]
    scoring: Optional[Any]                     # Resultado serializable del scoring final.
    scoring_summary: Optional[Any]             # Resumen tipado del scoring.

    # Datos preparados para la notificación final.
    notification_payload_raw: Optional[str]    # Respuesta JSON serializada del agente de notificación.
    notification_payload: Optional[Any]        # Notificación validada antes del envío.
    notification_result: Optional[str]         # Resultado del envío o de su simulación.

    # Trazabilidad de la ejecución.
    trace: List[str]                           # Secuencia de pasos ejecutados.
    
    # Referencias recuperadas mediante búsqueda semántica.
    reference_matches: Optional[ReferenceMatchesReport]
    reference_bonus: float
