import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.applications import router as applications_router
from app.api.auth import router as auth_router
from app.api.extract import router as extract_router
from app.api.ghost import router as ghost_router
from app.api.health import router as health_router
from app.config import settings

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.validate_for_environment()
    yield


app = FastAPI(title="Ember", lifespan=lifespan)

# Prod is same-origin through the Vercel rewrite, so this usually never runs.
if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

# Everything lives under /api so Vercel can forward one prefix to Render.
api = APIRouter(prefix="/api")
api.include_router(health_router)
api.include_router(auth_router)
api.include_router(applications_router)
api.include_router(extract_router)
api.include_router(ghost_router)
app.include_router(api)
