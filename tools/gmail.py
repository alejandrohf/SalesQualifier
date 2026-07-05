"""Inicialización perezosa de herramientas Gmail para el agente de notificaciones."""

# tools/gmail.py
from __future__ import annotations

from langchain_community.agent_toolkits import GmailToolkit
from langchain_community.tools.gmail.utils import (
    get_gmail_credentials,
    build_resource_service,
)

from app.config import config

gmail_init_error: str | None = None

try:
    if not config.GMAIL_TOKEN_FILE or not config.GMAIL_CREDENTIALS_FILE:
        raise RuntimeError("Gmail OAuth no configurado")

    creds = get_gmail_credentials(
        token_file=config.GMAIL_TOKEN_FILE,
        client_secrets_file=config.GMAIL_CREDENTIALS_FILE,
        scopes=["https://mail.google.com/"],
    )

    gmail_toolkit = GmailToolkit(api_resource=build_resource_service(credentials=creds))
    gmail_tools = gmail_toolkit.get_tools()
except Exception as exc:  # pragma: no cover - depende del entorno
    gmail_init_error = str(exc)
    gmail_tools = []
