from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("newsroom_api_starting", environment=settings.ENVIRONMENT)
    yield
    logger.info("newsroom_api_shutdown")


app = FastAPI(
    title="AI Newsroom Platform API",
    description="Autonomous AI-powered newsroom with LangGraph agent orchestration",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
from app.routers.auth import router as auth_router
from app.routers.stories import router as stories_router
from app.routers.stream import router as stream_router
from app.routers.ws import router as ws_router
from app.routers.social_accounts import router as social_accounts_router

app.include_router(auth_router, prefix="/api")
app.include_router(stories_router, prefix="/api")
app.include_router(stream_router, prefix="/api")
app.include_router(ws_router)
app.include_router(social_accounts_router, prefix="/api")

# Serve generated social card images
media_dir = Path("/app/media")
media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(media_dir)), name="media")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "newsroom-api", "version": "1.0.0"}
