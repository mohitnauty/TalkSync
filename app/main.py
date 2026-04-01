from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.api.ws import router as ws_router
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    yield


app = FastAPI(
    title="TalkSync API",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(ws_router)
WEB_DIR = Path(__file__).resolve().parent / "web"


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def root() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")
