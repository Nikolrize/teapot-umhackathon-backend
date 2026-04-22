import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.api.routes import router
from app.api.auth_routes import router as auth_router
from app.core.config import SECRET_KEY

# Set this BEFORE app initialization
os.environ['AUTHLIB_INSECURE_TRANSPORT'] = 'true'

app = FastAPI()

# ONLY ONE SessionMiddleware
app.add_middleware(
    SessionMiddleware, 
    secret_key=SECRET_KEY, # Use your real secret key from config
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

# Only include the routers you need
app.include_router(router)
app.include_router(auth_router)
