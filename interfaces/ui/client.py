"""Cliente HTTP de la interfaz Streamlit para consumir la API del backend."""

# interfaces/ui/client.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests


@dataclass(frozen=True)
class ApiClientConfig:
    """Configuración base del cliente HTTP usado por la interfaz web."""
    base_url: str
    timeout_s: int = 180


class ApiError(RuntimeError):
    """Excepción de alto nivel para errores devueltos por la API."""
    def __init__(self, message: str, status_code: Optional[int] = None, detail: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


class ApiClient:
    """Wrapper de alto nivel sobre `requests` con métodos alineados con la API del proyecto."""
    def __init__(self, cfg: ApiClientConfig):
        self.cfg = cfg
        self.session = requests.Session()
        self._token: Optional[str] = None

    def set_bearer_token(self, token: str | None) -> None:
        self._token = token
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            self.session.headers.pop("Authorization", None)

    def _url(self, path: str) -> str:
        return self.cfg.base_url.rstrip("/") + "/" + path.lstrip("/")

    def _handle(self, resp: requests.Response) -> Any:
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}

        if resp.status_code >= 400:
            detail = data.get("detail", data)
            raise ApiError(
                f"API error {resp.status_code}: {detail}",
                status_code=resp.status_code,
                detail=data,
            )
        return data

    # -----------------------
    # Core endpoints
    # -----------------------
    def health(self) -> Dict[str, Any]:
        return self._handle(self.session.get(self._url("/api/health"), timeout=self.cfg.timeout_s))

    def api_status(self) -> Dict[str, Any]:
        return self._handle(self.session.get(self._url("/api/api-status"), timeout=self.cfg.timeout_s))

    def list_opportunities(self) -> Dict[str, Any]:
        return self._handle(self.session.get(self._url("/api/opportunities"), timeout=self.cfg.timeout_s))

    def qualify(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"opportunity": opportunity, "metadata": {}}
        return self._handle(self.session.post(self._url("/api/qualify"), json=payload, timeout=self.cfg.timeout_s))

    # -----------------------
    # Auth endpoints
    # -----------------------
    def login(self, *, email: str, password: str) -> Dict[str, Any]:
        data = self._handle(
            self.session.post(
                self._url("/auth/login"),
                json={"email": email, "password": password},
                timeout=self.cfg.timeout_s,
            )
        )
        token = data.get("access_token")
        if token:
            self.set_bearer_token(token)
        return data

    def me(self) -> Dict[str, Any]:
        return self._handle(self.session.get(self._url("/auth/me"), timeout=self.cfg.timeout_s))

    def reset_password(self, *, token: str, new_password: str) -> Dict[str, Any]:
        return self._handle(
            self.session.post(
                self._url("/auth/reset-password"),
                json={"token": token, "new_password": new_password},
                timeout=self.cfg.timeout_s,
            )
        )

    def list_users(self) -> Dict[str, Any]:
        return self._handle(self.session.get(self._url("/auth/users"), timeout=self.cfg.timeout_s))

    def create_user(
        self,
        *,
        email: str,
        first_name: str,
        last_name: str,
        is_admin: bool,
        can_sales: bool,
        can_engineering: bool,
        engineering_manager_id: str | None = None,
        send_reset_email: bool = True,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "is_admin": is_admin,
            "can_sales": can_sales,
            "can_engineering": can_engineering,
            "send_reset_email": send_reset_email,
        }
        if engineering_manager_id:
            payload["engineering_manager_id"] = engineering_manager_id
        return self._handle(self.session.post(self._url("/auth/users"), json=payload, timeout=self.cfg.timeout_s))

    def update_user(self, user_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        return self._handle(self.session.patch(self._url(f"/auth/users/{user_id}"), json=patch, timeout=self.cfg.timeout_s))

    def activate_user(self, user_id: str) -> Dict[str, Any]:
        return self._handle(self.session.post(self._url(f"/auth/users/{user_id}/activate"), timeout=self.cfg.timeout_s))

    def deactivate_user(self, user_id: str) -> Dict[str, Any]:
        return self._handle(self.session.post(self._url(f"/auth/users/{user_id}/deactivate"), timeout=self.cfg.timeout_s))

    def send_user_reset_email(self, user_id: str) -> Dict[str, Any]:
        return self._handle(
            self.session.post(
                self._url(f"/auth/users/{user_id}/send-reset-email"),
                timeout=self.cfg.timeout_s,
            )
        )

    def set_technical_decision(self, opportunity_id: str, *, decision: str, comment: str | None = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"decision": decision}
        if comment:
            payload["comment"] = comment
        return self._handle(
            self.session.post(
                self._url(f"/api/opportunities/{opportunity_id}/technical-decision"),
                json=payload,
                timeout=self.cfg.timeout_s,
            )
        )

    # -----------------------
    # References endpoints
    # -----------------------
    def list_references(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        return self._handle(
            self.session.get(
                self._url(f"/api/references?limit={limit}&offset={offset}"),
                timeout=self.cfg.timeout_s,
            )
        )

    def create_reference(
        self,
        *,
        title: str,
        customer: str,
        industry: str,
        area: str,
        cloud: str,
        size: str,
        pdf_bytes: bytes,
        pdf_filename: str = "reference.pdf",
    ) -> Dict[str, Any]:
        files = {"document": (pdf_filename, pdf_bytes, "application/pdf")}
        data = {
            "title": title,
            "customer": customer,
            "industry": industry,
            "area": area,
            "cloud": cloud,
            "size": size,
        }
        return self._handle(
            self.session.post(
                self._url("/api/references"),
                data=data,
                files=files,
                timeout=self.cfg.timeout_s,
            )
        )

    def reindex_reference(self, reference_id: str) -> Dict[str, Any]:
        return self._handle(
            self.session.post(
                self._url(f"/api/references/{reference_id}/reindex"),
                timeout=self.cfg.timeout_s,
            )
        )

    def reference_download_url(self, reference_id: str) -> str:
        return self._url(f"/api/references/{reference_id}/download")

    def search_references(self, query: str) -> Dict[str, Any]:
        # Si tu API no implementa /api/references/search todavía, puedes comentar este método
        payload = {"query": query}
        return self._handle(
            self.session.post(
                self._url("/api/references/search"),
                json=payload,
                timeout=self.cfg.timeout_s,
            )
        )

def get_api_client() -> ApiClient:
    # Configurable por env var. Fallback para local dev.
    """Construye un cliente API usando la configuración disponible en variables de entorno."""
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    timeout_s = int(os.getenv("API_TIMEOUT_S", "180"))
    return ApiClient(ApiClientConfig(base_url=base_url, timeout_s=timeout_s))
