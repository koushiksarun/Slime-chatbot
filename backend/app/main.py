import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import sentry_sdk

from app.core.config import settings
from app.core.database import create_tables
from app.core.redis_client import close_redis
from app.api.v1 import api_router

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Slime API...")

    # Initialize Sentry only when a real DSN is configured.
    if settings.SENTRY_DSN and "your-sentry-dsn" not in settings.SENTRY_DSN and "project-id" not in settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=0.2,
            environment=settings.ENVIRONMENT,
        )
        logger.info("Sentry initialized")

    # Create DB tables (use Alembic in production)
    if settings.ENVIRONMENT == "development":
        await create_tables()
        logger.info("Database tables created")

    logger.info(f"Slime API ready | env={settings.ENVIRONMENT}")
    yield

    logger.info("Shutting down...")
    await close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-grade Slime AI assistant with RAG, Memory, and RLHF",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


# ── Routes ────────────────────────────────────────────────────────────────────

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "version": settings.APP_VERSION}


@app.get("/", tags=["Root"])
async def root():
    return {"message": f"{settings.APP_NAME} API", "docs": "/docs"}


# ── Global error handler ──────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred"},
    )
