"""
Verity MVP - Main Application.

FastAPI application with modular architecture and feature flags.
"""

import logging
import sys
import traceback
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from verity import __version__
from verity.config import get_settings
from verity.exceptions import VerityException
from verity.schemas import ErrorDetail, ErrorResponse, HealthResponse

# Import module routers
from verity.modules.documents import router as documents_router
from verity.modules.approvals import router as approvals_router
from verity.modules.agent import router as agent_router
from verity.modules.charts import router as charts_router
from verity.modules.reports import router as reports_router
from verity.modules.forecast import router as forecast_router
from verity.modules.logs import router as logs_router
from verity.modules.audit import router as audit_router
from verity.modules.tags import router as tags_router
from verity.modules.admin import router as admin_router
from verity.modules.otp import router as otp_router

# Import v2 API (new architecture)
from verity.api.routes.query_v2 import router as query_v2_router

# Configure standard logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("verity")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    settings = get_settings()
    logger.info(
        f"Starting Verity API v{__version__} "
        f"[env={settings.app_env}] "
        f"[features={settings.features.to_dict()}]"
    )
    yield
    logger.info("Shutting down Verity API")


# Create FastAPI application
app = FastAPI(
    title="Verity API",
    description="MVP monolitico modular para gestion documental con IA, aprobaciones humanas, y agente conversacional Veri.",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Middleware
# =============================================================================


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID to all requests."""
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id

    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(f"[{request_id}] {request.method} {request.url.path}")

    response = await call_next(request)

    logger.info(f"[{request_id}] {request.method} {request.url.path} -> {response.status_code}")

    return response


# =============================================================================
# Exception Handlers
# =============================================================================


@app.exception_handler(VerityException)
async def verity_exception_handler(request: Request, exc: VerityException):
    """Handle Verity custom exceptions."""
    request_id_str = getattr(request.state, "request_id", None)
    request_id = None
    if request_id_str:
        try:
            request_id = UUID(request_id_str)
        except (ValueError, TypeError):
            pass
    
    logger.warning(f"VerityException: {exc.code} - {exc.message}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": str(request_id) if request_id else None,
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    request_id_str = getattr(request.state, "request_id", None)
    
    # Log the full traceback
    logger.error(f"Unhandled exception on {request.url.path}")
    logger.error(f"Exception type: {type(exc).__name__}")
    logger.error(f"Exception message: {str(exc)}")
    logger.error(f"Traceback:\n{traceback.format_exc()}")

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(exc) if get_settings().app_debug else "An unexpected error occurred",
                "request_id": request_id_str,
            }
        },
    )


# =============================================================================
# Health Check
# =============================================================================


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """Health check endpoint."""
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        version=__version__,
        features=settings.features.to_dict(),
        app_env=settings.app_env,
        is_production=settings.is_production,
        agent_row_ids_guard_effective=bool(settings.agent_enforce_row_ids_guard and settings.is_production),
    )


# =============================================================================
# Register Module Routers
# =============================================================================

# Legacy routers (old architecture)
app.include_router(documents_router)
app.include_router(approvals_router)
app.include_router(agent_router)
app.include_router(charts_router)
app.include_router(reports_router)
app.include_router(forecast_router)
app.include_router(logs_router)
app.include_router(audit_router)
app.include_router(tags_router)
app.include_router(admin_router)
app.include_router(otp_router)

# v2 API (new architecture - tool-based)
app.include_router(query_v2_router)


# =============================================================================
# Root Endpoint
# =============================================================================


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint redirect to docs."""
    return {"message": "Welcome to Verity API", "docs": "/docs"}
