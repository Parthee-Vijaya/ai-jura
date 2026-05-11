"""Router-registry for Bifrost-API'et.

Hver router er en `APIRouter` der grupperer relaterede endpoints. Routers
registreres i `register_routers(app)` der kaldes fra `main.py` lifespan.

Pattern for nye routers:

    # src/api/routers/myresource.py
    from fastapi import APIRouter
    router = APIRouter(prefix="/api/v3/myresource", tags=["myresource"])

    @router.get("/")
    async def list_items():
        ...

    # Husk at registrere i src/api/routers/__init__.py

Fordele i denne struktur:
- main.py reduceres til app-init + middleware + lifespan
- Endpoints er gruppeerede pr. ressource (lettere at finde + teste)
- OpenAPI-docs får meningsfulde tags
- Unit-tests kan importere routeren uden at importere hele appen
"""

from __future__ import annotations

from fastapi import FastAPI


def register_routers(app: FastAPI) -> None:
    """Registrér alle Bifrost-routers på FastAPI-appen.

    Kaldes én gang i main.py efter exception-handlers + middleware er på plads.

    Rækkefølge er signifikant for præcedens — mere specifikke prefixes først.
    """
    # Importér her (ikke top-level) så vi undgår circular imports
    from src.api.routers import admin, dashboard, skabeloner, comments

    app.include_router(admin.router)
    app.include_router(dashboard.router)
    app.include_router(skabeloner.router)
    app.include_router(comments.router)
