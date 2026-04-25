import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
import httpx

from app.api.routes import router
from app.api.auth_routes import router as auth_router
from app.api.agent_routes import router as agent_router
from app.api.admin_routes import router as admin_router
from app.api.project_routes import router as project_router
from app.api.reference_routes import router as reference_router
from app.api.chat_routes import router as chat_router
from app.api.crud_routes import router as crud_routes
from app.api.dashboard_routes import router as dashboard_router
from app.api.model_routes import router as model_router
from app.api.file_routes import router as file_router
from app.api.generation_routes import router as generation_router
from app.api import leads_routes as leads_overview
from app.api.purchase_routes import router as purchase_router
from app.api.settings_routes import router as settings_router
from app.core.config import SECRET_KEY
from app.services.agent_service import init_agents_table
from app.services.project_service import init_project_tables
from app.services.reference_service import init_reference_table
from app.services.purchase_service import init_settings_table

os.environ['AUTHLIB_INSECURE_TRANSPORT'] = 'true'

_PING_INTERVAL = 600  # 10 minutes — safely under the 15-minute sleep threshold

# CORS Origins Configuration
def _parse_allowed_origins() -> list[str]:
    """
    Parse CORS origins from env and keep localhost enabled by default.
    This avoids browser CORS failures during local frontend development.
    """
    default_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    raw = os.getenv("CORS_ORIGINS", "")
    if not raw.strip():
        return default_origins

    parsed = [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]
    if "*" in parsed:
        # With credentials enabled, explicit origins are safer than wildcard.
        return default_origins

    for origin in default_origins:
        if origin not in parsed:
            parsed.append(origin)
    return parsed


ALLOWED_ORIGINS = _parse_allowed_origins()


async def _keep_alive():
    """Pings /health every 10 minutes so the server never hits the idle timeout."""
    base_url = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    await asyncio.sleep(60)  # Wait for full startup before first ping
    while True:
        try:
            async with httpx.AsyncClient() as client:
                await client.get(f"{base_url}/health", timeout=10)
        except Exception:
            pass  # Network errors during restarts are expected — just continue
        await asyncio.sleep(_PING_INTERVAL)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_agents_table()
    init_project_tables()
    init_reference_table()
    init_settings_table()
    task = asyncio.create_task(_keep_alive())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="fastapi_session",
    same_site="lax",
    https_only=False,
)

# Keep CORS as outermost middleware so even error responses include CORS headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return JSONResponse({"status": "ok"})


app.include_router(router)
app.include_router(auth_router)
app.include_router(agent_router, prefix="/client")
app.include_router(project_router, prefix="/client")
app.include_router(reference_router, prefix="/client")
app.include_router(dashboard_router, prefix="/client")
app.include_router(file_router, prefix="/client")
app.include_router(generation_router, prefix="/client")
app.include_router(admin_router, prefix="/admin")
app.include_router(model_router, prefix="/admin")
app.include_router(settings_router, prefix="/admin")
app.include_router(purchase_router, prefix="/client")
app.include_router(crud_routes)
app.include_router(chat_router)
app.include_router(leads_overview.router)
