# SalesQualifier

Plataforma de cualificación inteligente de oportunidades comerciales desarrollada como **Trabajo Fin de Grado (TFG) del Grado en Ingeniería Informática de UNIR**.

El repositorio recoge una solución software completa orientada a apoyar el proceso de cualificación comercial y técnica de oportunidades. La plataforma combina captura estructurada de información, análisis MEDDICC, scoring determinista, recuperación semántica de referencias, revisión técnica GO/NO GO y explotación operativa mediante API y dashboard web.

La solución combina:

- captura estructurada de oportunidades comerciales;
- análisis de cualificación basado en **MEDDICC**;
- scoring determinista y reglas de negocio;
- recuperación semántica de referencias corporativas mediante `pgvector`;
- arquitectura multiagente con LLM;
- API REST en **FastAPI**;
- interfaz web en **Streamlit**.

## Objetivo del proyecto

El objetivo del proyecto es apoyar el proceso de cualificación comercial y técnica de oportunidades, mejorando:

- la consistencia del análisis;
- la priorización de oportunidades;
- la reutilización del conocimiento organizativo;
- la trazabilidad de las decisiones;
- la adopción de inteligencia artificial generativa como apoyo a la decisión.

## Alcance del repositorio

Este repositorio incluye:

- código fuente del backend, frontend y workflow multiagente;
- migraciones y scripts de inicialización;
- tests automáticos del núcleo de negocio y de la API;
- datos semilla y documentos de ejemplo para poblar el catálogo de referencias.

No se incluyen secretos operativos en el control de versiones. Las credenciales reales deben configurarse localmente mediante variables de entorno y ficheros ignorados por Git.

## Stack tecnológico

- **Python 3.12**
- **FastAPI** + **Uvicorn**
- **Streamlit**
- **SQLAlchemy** + **Alembic**
- **PostgreSQL** + **pgvector**
- **LangChain** + **LangGraph**
- **OpenAI**
- **Tavily**
- **Google Gmail API**

## Estructura del proyecto

```text
agents/              Agentes especializados del workflow
app/                 Configuración global de la aplicación
credentials/         Credenciales locales para integraciones externas
data/                Datos auxiliares y referencias persistidas localmente
domain/              Lógica de negocio determinista
infrastructure/db/   Modelos ORM y acceso a base de datos
interfaces/api/      API REST con FastAPI
interfaces/ui/       Interfaz web Streamlit
migrations/          Migraciones Alembic
schemas/             Esquemas Pydantic y contratos de datos
seed_data/           Datos y scripts de inicialización
tests/               Suite de pruebas automáticas
tools/               Integraciones y utilidades auxiliares
workflows/           Orquestación multiagente
```

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/alejandrohf/SalesQualifier.git
cd SalesQualifier
```

### 2. Crear entorno virtual

```bash
python3.12 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -U pip
pip install -r requirements.txt
```

## Puesta en marcha rápida

Si quieres levantar el proyecto en local con el flujo mínimo recomendado:

```bash
cp .env.example .env
docker compose up -d db
./venv/bin/alembic upgrade head
./venv/bin/python seed_data/scripts/seed_admin_user.py \
  --email admin@example.com \
  --first-name Admin \
  --last-name User \
  --password Admin1234
uvicorn interfaces.api.main:app --reload
```

En una segunda terminal, para la interfaz web:

```bash
source venv/bin/activate
streamlit run interfaces/ui/0_Login.py
```

## Configuración de entorno

1. Copiar el fichero de ejemplo:

```bash
cp .env.example .env
```

2. Rellenar los valores necesarios en `.env`.

### Variables de entorno documentadas

| Variable | Obligatoria | Descripción |
|---|---|---|
| `OPENAI_API_KEY` | Sí | Clave de OpenAI utilizada por los agentes LLM y por la generación de embeddings. |
| `TAVILY_API_KEY` | Sí | Clave de Tavily para enriquecimiento del contexto del cliente mediante búsqueda web. |
| `GOOGLE_APPLICATION_CREDENTIALS` | Sí | Ruta al fichero de credenciales OAuth2 de Google para integración con Gmail. |
| `GMAIL_TOKEN` | Sí | Ruta al token OAuth2 de Gmail utilizado por el envío de correos. |
| `SQA_EMAIL_RECIPIENT` | No | Destinatario principal de determinadas notificaciones. |
| `SQA_EMAIL_SENDER` | No | Dirección remitente configurada para la plataforma. |
| `DATABASE_URL` | Sí | Cadena de conexión a PostgreSQL. |
| `JWT_SECRET_KEY` | Sí en entornos reales | Clave secreta para firmar los tokens JWT. |
| `JWT_ALGORITHM` | No | Algoritmo de firma JWT. Valor habitual: `HS256`. |
| `JWT_EXPIRE_MINUTES` | No | Tiempo de expiración del token JWT en minutos. |
| `APP_PUBLIC_BASE_URL` | No | URL pública base de la aplicación, usada por ejemplo en enlaces de reseteo de contraseña. |
| `SMTP_HOST` | No | Servidor SMTP alternativo para correo saliente. |
| `SMTP_PORT` | No | Puerto del servidor SMTP. |
| `SMTP_USERNAME` | No | Usuario SMTP. |
| `SMTP_PASSWORD` | No | Contraseña o secreto SMTP. |
| `SMTP_USE_TLS` | No | Indica si la conexión SMTP usa TLS. |
| `SMTP_FROM_EMAIL` | No | Dirección remitente para el canal SMTP alternativo. |

El fichero de ejemplo disponible en `.env.example` recoge esta configuración base para entornos de desarrollo.

## Base de datos

### 1. Levantar PostgreSQL con Docker

```bash
docker compose up -d db
```

### 2. Aplicar migraciones

```bash
./venv/bin/alembic upgrade head
```

### 3. Crear usuario administrador inicial

```bash
./venv/bin/python seed_data/scripts/seed_admin_user.py \
  --email admin@example.com \
  --first-name Admin \
  --last-name User \
  --password Admin1234
```

### 4. Cargar datos de ejemplo opcionales

Si se quiere poblar el sistema con referencias corporativas y oportunidades de demostración:

```bash
./venv/bin/python seed_data/scripts/seed_references.py
./venv/bin/python seed_data/scripts/seed_qualifications.py
```

## Ejecución

### Lanzar la API

```bash
uvicorn interfaces.api.main:app --reload
```

API disponible en:

- [http://127.0.0.1:8000](http://127.0.0.1:8000)
- health check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

### Lanzar la interfaz web

```bash
streamlit run interfaces/ui/0_Login.py
```

UI disponible en:

- [http://127.0.0.1:8501](http://127.0.0.1:8501)

## Pruebas

Ejecutar la suite automatizada:

```bash
./venv/bin/pytest
```

## Evidencias de código propio

El desarrollo propio del proyecto se refleja de forma directa en los siguientes bloques del repositorio:

- `domain/scoring.py` y `domain/rules.py`: motor de scoring determinista, penalizaciones y reglas estratégicas de cualificación.
- `workflows/supervisor.py`: orquestación del workflow multiagente y consolidación de resultados.
- `agents/`: agentes especializados para análisis MEDDICC, riesgos, encaje comercial, referencias y notificación.
- `interfaces/api/`: API REST desarrollada con FastAPI, incluyendo autenticación, oportunidades, referencias y monitorización.
- `interfaces/ui/`: dashboard y pantallas de operación desarrolladas con Streamlit.
- `infrastructure/db/` y `migrations/`: persistencia relacional, integración con `pgvector` y evolución del esquema.
- `tests/`: pruebas unitarias e integración ligera sobre scoring, contratos, helpers del workflow y rutas principales.

En conjunto, estas carpetas evidencian la autoría del diseño funcional, la arquitectura software, la lógica de negocio y la implementación técnica del prototipo.

## Recomendaciones para publicación

- Mantener el repositorio en modo privado si los PDFs de ejemplo o los datos semilla no son redistribuibles públicamente.
- No versionar credenciales reales ni tokens OAuth; el repositorio ya está preparado para trabajar con `.env` y ficheros locales ignorados por Git.
- Si se quisiera una publicación abierta definitiva, conviene revisar previamente el contenido de `data/references/` y `seed_data/pdfs/`.

## Licencia

Este proyecto se distribuye bajo licencia **MIT**. Consulta el fichero `LICENSE` para más detalle.

## Autoría

**Alejandro Hidalgo Fernández**  
Trabajo Fin de Grado  
Grado en Ingeniería Informática - **UNIR**
