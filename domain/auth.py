"""Utilidades de autenticación y gestión de tokens del dominio.
Incluye hashing de contraseñas, creación y validación de JWT y helpers para
reseteo seguro de contraseñas.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable

import bcrypt

from app.config import config


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def hash_password(password: str) -> str:
    """Genera un hash bcrypt seguro a partir de una contraseña en texto plano."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Comprueba si una contraseña en texto plano coincide con su hash almacenado."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def create_access_token(*, subject: str, email: str, role: str, expires_minutes: int | None = None) -> tuple[str, int]:
    """Construye un JWT firmado con la identidad y expiración del usuario."""
    exp_minutes = expires_minutes or int(config.JWT_EXPIRE_MINUTES)
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=exp_minutes)
    payload = {
        "sub": subject,
        "email": email,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(config.JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    token = f"{header_b64}.{payload_b64}.{_b64url_encode(signature)}"
    return token, exp_minutes * 60


def decode_access_token(token: str) -> Dict[str, Any]:
    """Valida la firma y expiración de un JWT y devuelve su payload."""
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError as e:
        raise ValueError("Invalid token format") from e

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = hmac.new(config.JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    actual_sig = _b64url_decode(signature_b64)
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("Invalid token signature")

    payload_raw = _b64url_decode(payload_b64)
    payload = json.loads(payload_raw.decode("utf-8"))
    exp = int(payload.get("exp", 0) or 0)
    if exp <= int(datetime.now(timezone.utc).timestamp()):
        raise ValueError("Token expired")
    return payload


def ensure_roles(user_role: str, allowed_roles: Iterable[str]) -> None:
    """Verifica que un rol pertenece al conjunto permitido para una operación."""
    allowed = {r.strip().lower() for r in allowed_roles}
    if user_role.strip().lower() not in allowed:
        raise PermissionError("Insufficient role permissions")


def generate_secure_token() -> str:
    """Genera un token aleatorio seguro para enlaces de alta o reseteo."""
    return secrets.token_urlsafe(48)


def hash_reset_token(token: str) -> str:
    """Aplica SHA-256 al token de reseteo para persistirlo sin guardar el valor en claro."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
