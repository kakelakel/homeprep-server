from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from homeprep_server import __version__
from homeprep_server.api.assets import router as assets_router
from homeprep_server.api.auth import router as auth_router
from homeprep_server.api.backups import router as backups_router
from homeprep_server.api.clients import router as clients_router
from homeprep_server.api.containers import router as containers_router
from homeprep_server.api.context import router as context_router
from homeprep_server.api.errors import install_error_handlers
from homeprep_server.api.household_profile import router as household_profile_router
from homeprep_server.api.households import router as households_router
from homeprep_server.api.inventory import router as inventory_router
from homeprep_server.api.pairing import router as pairing_router
from homeprep_server.api.plans import router as plans_router
from homeprep_server.api.system import router as system_router
from homeprep_server.api.targets import router as targets_router
from homeprep_server.api.tasks import router as tasks_router
from homeprep_server.api.users import router as users_router
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
install_error_handlers(app)
app.include_router(system_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(clients_router)
app.include_router(pairing_router)
app.include_router(context_router)
app.include_router(backups_router)
app.include_router(households_router)
app.include_router(household_profile_router)
app.include_router(containers_router)
app.include_router(assets_router)
app.include_router(tasks_router)
app.include_router(targets_router)
app.include_router(plans_router)
app.include_router(inventory_router)

if settings.web_dir.exists():
    app.mount("/", StaticFiles(directory=settings.web_dir, html=True), name="web")
