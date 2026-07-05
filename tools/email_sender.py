"""Envío de correo saliente a través de Gmail OAuth para notificaciones del sistema."""

from __future__ import annotations

import base64
from email.mime.text import MIMEText

from app.config import config

from langchain_community.tools.gmail.utils import (
    build_resource_service,
    get_gmail_credentials,
)


def _send_via_gmail_api(*, to_email: str, subject: str, body: str) -> None:
    if not config.GMAIL_TOKEN_FILE or not config.GMAIL_CREDENTIALS_FILE:
        raise RuntimeError("Gmail OAuth no configurado")

    creds = get_gmail_credentials(
        token_file=config.GMAIL_TOKEN_FILE,
        client_secrets_file=config.GMAIL_CREDENTIALS_FILE,
        scopes=["https://mail.google.com/"],
    )
    service = build_resource_service(credentials=creds)

    message = MIMEText(body, "plain", "utf-8")
    message["to"] = to_email
    message["from"] = config.SQA_EMAIL_SENDER or config.SMTP_FROM_EMAIL
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    service.users().messages().send(userId="me", body={"raw": raw}).execute()


def send_plain_email(*, to_email: str, subject: str, body: str) -> None:
    """Envía un correo de texto plano usando la integración configurada de Gmail."""
    _send_via_gmail_api(to_email=to_email, subject=subject, body=body)
