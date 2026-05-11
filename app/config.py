"""Módulo `app/config.py` de la plataforma Sales Qualification Agent."""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys principales
    """Define `Config` dentro de este modulo."""
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    
    # Gmail Configuration
    GMAIL_CREDENTIALS_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    GMAIL_TOKEN_FILE = os.getenv("GMAIL_TOKEN")
    
    # SQA Email Configuration
    SQA_EMAIL_RECIPIENT = os.getenv("SQA_EMAIL_RECIPIENT")
    SQA_EMAIL_SENDER = os.getenv("SQA_EMAIL_SENDER")
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL")

    # Auth / JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
    APP_PUBLIC_BASE_URL = os.getenv("APP_PUBLIC_BASE_URL", "http://localhost:8501")

    # SMTP (password reset / invites)
    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", os.getenv("SQA_EMAIL_SENDER", "no-reply@example.com"))

    # Configuración de las interfaces
    WEBHOOK_PORT = 8000
    DASHBOARD_PORT = 8501

    # Validación de configuración crítica
    @classmethod
    def validate_required_config(cls):
        required_keys = [
            ("OPENAI_API_KEY", cls.OPENAI_API_KEY),
            ("TAVILY_API_KEY", cls.TAVILY_API_KEY),
            ("GMAIL_CREDENTIALS_FILE", cls.GMAIL_CREDENTIALS_FILE),
            ("GMAIL_TOKEN_FILE", cls.GMAIL_TOKEN_FILE),
            ("DATABASE_URL", cls.DATABASE_URL)
        ]
       
        missing_keys = [key for key, value in required_keys if not value]

        if missing_keys:
            raise ValueError(f"Faltan las siguientes variables de entorno: {', '.join(missing_keys)}")
        
        return True
    
config = Config()
