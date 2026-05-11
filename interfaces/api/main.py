"""Módulo `interfaces/api/main.py` de la plataforma Sales Qualification Agent."""

# interfaces/api/main.py
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
    # Validar config al iniciar (estilo SOC)
    """Ejecuta `create_app` dentro de este modulo."""
    config_status = validate_config_on_startup()

    if config_status["configured"]:
        print("✅ Configuración validada correctamente")
    else:
        print("❌ Error de configuración detectado:")
        for err in config_status["errors"]:
            print(f"   - {err}")
        print("💡 Revisa tu archivo .env y asegúrate de tener las keys requeridas")

    for w in config_status.get("warnings", []):
        print(f"⚠️  Warning: {w}")

    app = FastAPI(
        title="Sales Qualification API",
        version="0.2.0",
        description="API para cualificación inteligente de oportunidades (MEDDICC + agentes + RAG de referencias + scoring determinista).",
    )

    # CORS (para Streamlit / dev)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # en prod: restringe a tu dominio
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rutas
    app.include_router(router, prefix="/api")
    app.include_router(references_router)
    app.include_router(auth_router)

    return app


app = create_app()


if __name__ == "__main__":
    port = getattr(config, "WEBHOOK_PORT", 8000)

    print("🚀 Iniciando Sales Qualification API...")
    print(f"🌐 Puerto: {port}")
    print("🔧 Estado de configuración:")
    print(f"✅ OpenAI: {'Configurada' if getattr(config, 'OPENAI_API_KEY', None) else 'FALTA'}")
    print(f"✅ Tavily: {'Configurada' if getattr(config, 'TAVILY_API_KEY', None) else 'FALTA (opcional)'}")
    print(f"✅ Gmail: {'Configurada' if getattr(config, 'GMAIL_CREDENTIALS_FILE', None) else 'FALTA (opcional)'}")
    print(f"✅ Gmail OAuth: {'Configurada' if getattr(config, 'GMAIL_TOKEN_FILE', None) else 'FALTA (opcional)'}")
    print(f"✅ Database: {'Configurada' if getattr(config, 'DATABASE_URL', None) else 'FALTA (opcional)'}")
    print("\n📍 Endpoints útiles:")
    print(f"   - Health:      http://localhost:{port}/api/health")
    print(f"   - API Status:  http://localhost:{port}/api/api-status")
    print(f"   - Qualify:     http://localhost:{port}/api/qualify")
    print(f"   - List opps:   http://localhost:{port}/api/opportunities")
    print(f"   - List references:   http://localhost:{port}/api/references")
    print(f"   - Auth login:  http://localhost:{port}/auth/login")

    uvicorn.run(app, host="0.0.0.0", port=port)
