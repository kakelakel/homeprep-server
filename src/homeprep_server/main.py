from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from homeprep_server import __version__
from homeprep_server.api.system import router as system_router
from homeprep_server.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="HomePrep Server",
    version=__version__,
    description="Self-hosted server for the HomePrep ecosystem.",
    lifespan=lifespan,
)
app.include_router(system_router)
