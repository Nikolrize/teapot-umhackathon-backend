import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.api.routes import router
from app.api.auth_routes import router as auth_router
from app.api.agent_routes import router as agent_router
from app.api.admin_routes import router as admin_router
from app.api.project_routes import router as project_router
from app.api.reference_routes import router as reference_router
from app.core.config import SECRET_KEY
from app.services.agent_service import init_agents_table
from app.services.project_service import init_project_tables
from app.services.reference_service import init_reference_table

os.environ['AUTHLIB_INSECURE_TRANSPORT'] = 'true'

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_agents_table()
    init_project_tables()
    init_reference_table()
    yield

app = FastAPI(lifespan=lifespan)

# ONLY ONE SessionMiddleware
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="fastapi_session",
    same_site="lax",
    https_only=True
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(auth_router)
app.include_router(agent_router, prefix="/client-dashboard")
app.include_router(project_router, prefix="/client-dashboard")
app.include_router(reference_router, prefix="/client-dashboard")
app.include_router(admin_router, prefix="/admin-dashboard")