# Modul 9 — main.py refaktor til APIRouter-moduler

Status: **delvist gennemført på `refaktor-9` branch** (sidst opdateret 2026-05-11).

## Mål

Splitte `main.py` (5393 linjer) til logiske router-moduler under
`src/api/routers/` så:

- Endpoints er grupperet pr. ressource (lettere at finde + teste isoleret)
- main.py reduceres til app-init + middleware + lifespan
- Unit-tests kan importere routeren uden hele appen

## Hvad er gjort (3 commits)

| Commit | Routers | Endpoints | main.py-reduktion |
|---|---|---|---|
| `474064d` | admin, dashboard | 11 | -200 linjer (-3.7%) |
| `9d8c4ee` | skabeloner, comments | 9 | -303 linjer (-5.7%) |
| `53a4260` | evidens, notifications | 7 | -192 linjer (-3.8%) |
| **Total** | **6 routers** | **27 endpoints** | **5393 → 4746 (-12%)** |

### Filer

```
src/api/routers/
├── __init__.py        register_routers(app)
├── admin.py           /api/v3/admin/* (9 endpoints)
├── comments.py        /api/v3/cases/{}/comments + /api/v3/comments/{} (5 endpoints)
├── dashboard.py       /api/v3/dashboard/portfolio[.csv] (2 endpoints)
├── evidens.py         /api/v3/evidence/* + /api/v3/cases/{}/evidence/* (4 endpoints)
├── notifications.py   /api/v3/notifications/* (3 endpoints)
└── skabeloner.py      /api/v3/skabelon-bibliotek/* (4 endpoints)
```

## Hvad mangler

main.py har stadig ~80 endpoints. De største clustres at flytte:

- **cases.py** — `/api/v3/cases/*` CRUD + transitions + intake + timeline (~10 endpoints, ~600 linjer)
- **assessments.py** — `/api/v3/assessments`, `/api/v3/audit` (~10 endpoints)
- **compliance.py** — `/api/compliance/*` legacy (~10 endpoints)
- **search.py** — `/api/v3/search` (~250 linjer enkelt endpoint)
- **knowledge_base.py** — `/api/knowledge-base/*` (3 endpoints)
- **law.py** — `/api/law/*` (6 endpoints)
- **news.py** — `/api/news/*` + ticker (~5 endpoints)
- **research.py** — `/api/research/*` (2 endpoints, ~200 linjer)
- **system.py** — `/health`, `/readyz`, `/metrics`, `/api/version` (6 endpoints)
- **eu_checker.py** — `/api/eu-ai-act-checker/*` (4 endpoints)
- **dsar.py** — `/api/v3/admin/dsar/*` (2 endpoints)
- **misc.py** — ai-projects, ai-cases, agents, requirements, frameworks, documents (~10 endpoints)

Estimat for at lukke resten: 2-3 dages arbejde.

## Pattern + faldgrupper

### Router-skabelon

```python
# src/api/routers/myresource.py
from fastapi import APIRouter
from src.api.error_envelope import AppError
from src.api.rate_limiting import limiter, ADMIN_WRITE

router = APIRouter(prefix="/api/v3/myresource", tags=["myresource"])

@router.get("")
async def list_items():
    ...

@router.post("")
@limiter.limit(ADMIN_WRITE)
async def create_item(request: Request, response: Response, body: MyPayload):
    ...
```

### Faldgrupper opdaget under refaktoren

1. **`from __future__ import annotations` + pydantic = problemer**
   - Type-hints bliver til strings (PEP 563), og pydantic kan ikke
     resolve `Dict[str, Any]` osv. når routeren importeres via
     `register_routers`. Symptom: `PydanticUndefinedAnnotation` ved import.
   - Fix: drop `from __future__ import annotations` i alle filer der
     definerer pydantic-modeller.

2. **`raise HTTPException` vs `raise AppError`**
   - Migreret til `AppError` undervejs så error-envelope-shape er konsistent.
     Behavior er identisk (samme status-kode + besked), men frontend kan stole
     på struct'en.

3. **Pydantic payload-modeller flyttes IND i routeren**
   - Tidligere defineret på top af main.py — flyttet til den specifikke router
     så scope er klart.

## Næste sprint

På `refaktor-9` branch:

1. `cases.py` — den største router (case-CRUD + transitions + intake)
2. `assessments.py` + `compliance.py` — vurderings-cluster
3. `search.py` + `knowledge_base.py` — søge-cluster
4. `system.py` + `news.py` + resten

Når alt er flyttet:

1. main.py reduceres til ~500 linjer (app-init + middleware + lifespan)
2. Merge `refaktor-9` → `main` via PR
3. Slet branchen

## Verifikation

```bash
# Hvert step verificeres med:
python -c "import main; print(len(main.app.routes))"  # Total routes uændret
pytest -q --ignore=tests/test_news_service.py          # Tests passer

# Live mod kørende backend:
curl localhost:8001/api/v3/admin/llm-health  # 200
curl localhost:8001/api/v3/skabelon-bibliotek # 200
curl localhost:8001/api/v3/notifications     # 200
```
