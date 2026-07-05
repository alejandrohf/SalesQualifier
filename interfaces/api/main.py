"""Punto de entrada de la API FastAPI y configuración global de middlewares y rutas."""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import config
from interfaces.api.routes import router
from interfaces.api.dependencies import validate_config_on_startup
from interfaces.api.routes_references import router as references_router
from interfaces.api.auth_routes import router as auth_router

def create_app() -> FastAPI:
    """Crea la aplicación FastAPI y registra sus dependencias principales."""
    config_status = validate_config_on_startup()

    if config_status["configured"]:
        print("Configuración validada correctamente")
    else:
        print("Se han detectado errores de configuración:")
        for err in config_status["errors"]:
            print(f"   - {err}")
        print("Revise el archivo .env y complete las variables obligatorias.")

    for w in config_status.get("warnings", []):
        print(f"Advertencia de configuración: {w}")

    app = FastAPI(
        title="Sales Qualification API",
        version="0.2.0",
        description="API para cualificación inteligente de oportunidades (MEDDICC + agentes + RAG de referencias + scoring determinista).",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api")
    app.include_router(references_router)
    app.include_router(auth_router)

    return app


app = create_app()


if __name__ == "__main__":
    port = getattr(config, "WEBHOOK_PORT", 8000)

    print("Iniciando Sales Qualification API...")
    print(f"Puerto: {port}")
    print("Estado de configuración:")
    print(f"OpenAI: {'configurada' if getattr(config, 'OPENAI_API_KEY', None) else 'no configurada'}")
    print(f"Tavily: {'configurada' if getattr(config, 'TAVILY_API_KEY', None) else 'no configurada (opcional)'}")
    print(f"Gmail credentials: {'configurada' if getattr(config, 'GMAIL_CREDENTIALS_FILE', None) else 'no configurada (opcional)'}")
    print(f"Gmail OAuth: {'configurada' if getattr(config, 'GMAIL_TOKEN_FILE', None) else 'no configurada (opcional)'}")
    print(f"Base de datos: {'configurada' if getattr(config, 'DATABASE_URL', None) else 'no configurada (opcional)'}")
    print("\nEndpoints principales:")
    print(f"   - Health:      http://localhost:{port}/api/health")
    print(f"   - API Status:  http://localhost:{port}/api/api-status")
    print(f"   - Qualify:     http://localhost:{port}/api/qualify")
    print(f"   - List opps:   http://localhost:{port}/api/opportunities")
    print(f"   - List references:   http://localhost:{port}/api/references")
    print(f"   - Auth login:  http://localhost:{port}/auth/login")

    uvicorn.run(app, host="0.0.0.0", port=port)
