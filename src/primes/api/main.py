import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.routing import APIRouter
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from primes.api.config import API_SERVER_HOST, API_SERVER_PORT, API_WORKERS
from primes.api.websockets import router as ws_router
from primes.api.routers.presets import router as presets_router
from primes.api.routers.tests import router as tests_router
from primes.api.routers.plugins import router as plugins_router
from primes.api.routers.distributions import router as distributions_router
from primes.distributions.loader import load_plugins

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FastAPI application starting up")
    logger.info(
        f"Configuration: host={API_SERVER_HOST}, port={API_SERVER_PORT}, workers={API_WORKERS}"
    )
    load_plugins()
    yield
    logger.info("FastAPI application shutting down")


router = APIRouter()
UI_DIST_PATH = Path(__file__).resolve().parent.parent / "ui" / "dist"


@router.get("/health")
async def health():
    return {"status": "healthy"}


@router.get("/ready")
async def ready():
    return {"status": "ready"}


@router.get("/")
async def root():
    return {"name": "primes-client", "version": "0.1.0"}


@router.get("/ui")
async def ui_index():
    return FileResponse(UI_DIST_PATH / "index.html")


@router.get("/ui/{path:path}")
async def ui_assets(path: str):
    asset_path = UI_DIST_PATH / path
    if asset_path.exists() and asset_path.is_file():
        return FileResponse(asset_path)
    return FileResponse(UI_DIST_PATH / "index.html")


app = FastAPI(
    title="primes-client API",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(router)
app.mount("/ui/assets", StaticFiles(directory=UI_DIST_PATH), name="ui-assets")
app.include_router(ws_router, prefix="/api/v1")
app.include_router(presets_router, prefix="/api/v1")
app.include_router(tests_router, prefix="/api/v1/tests")
app.include_router(plugins_router, prefix="/api/v1")
app.include_router(distributions_router, prefix="/api/v1")


@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    logger.error(f"Value error: {exc}")
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.exception_handler(KeyError)
async def key_error_handler(request, exc):
    logger.error(f"Key error: {exc}")
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=404,
        content={"detail": "Resource not found"},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unexpected error: {exc}")
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
