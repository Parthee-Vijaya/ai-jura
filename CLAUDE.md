# CLAUDE.md — Bifrost ᛒ (kommunal AI-compliance)

**Detaljeret memory:** `/Users/parthee/Desktop/Claude/vidensbase/projekter/tyr.md`
**Design:** Læs ALTID [DESIGN.md](./DESIGN.md) før visuelle/UI-beslutninger. `DESIGN_SYSTEM.md` er HISTORISK (Judge Dredd-æraen, teglrød) — brug den ikke.

## Identitet & navnehistorik

**Bifrost** — AI-compliance-platform til Kalundborg Kommune. Vurderer AI-systemer mod EU AI Act, GDPR og dansk regulering. Hybrid: deterministisk regelmotor + LLM-analyse.

Navnerække: Judge Dredd → Hjemmel → Forseti → Tyr (2026-05-08) → **Bifrost** (2026-05-10, ensrettet 2026-06-27).
- Mappen hedder stadig `judge-dredd/`, drift-artefakter hedder "tyr" (`scripts/start_tyr.sh`, `~/.tyr/run`, `~/Library/Logs/Tyr`, PG-db `tyr`) — bevidst legacy, ikke fejl.
- ⚠️ Grey Skull-projektet hed TIDLIGERE Bifrost — helt andet projekt.

**Git:** `main` tracker `ai-jura/main` (github.com/Parthee-Vijaya/ai-jura). `origin` (Judge_dredd) er sekundær. Verificér altid ahead/behind live før push; planlagte jobs kan opdatere `data/*.json` mellem arbejdssessioner.

## Porte & drift (verificeret)

- Backend (FastAPI): **:8001** (`API_PORT` i .env — kodens 8000-fallback i main.py gælder kun uden .env)
- Frontend: **:8090** (`FRONTEND_PORT`; prod serveres af `frontend/serve_prod.js` — express + proxy mod :8001)
- Frontend-proxy i package.json: `http://localhost:8001`
- **Kører via LaunchAgents** `com.skynet-managed.judge-dredd-api` + `-web` (autostart — IKKE manuel start længere)
- Manuel styring: `scripts/start_tyr.sh` / `status_tyr.sh` / `stop_tyr.sh` (idempotente, PID-filer i `~/.tyr/run`)
- Scheduled jobs (APScheduler i main.py): KB-opdatering UGENTLIGT mandag 03:00 + AI-projects-sync mandag 03:30 (efterlader modificerede `data/*.json` i git status — forventet); natligt: DB-backup 01:30, GDPR-retention 02:00, citation-verifier 04:00
- `API_HOST=0.0.0.0` → tilgængelig via Tailscale

## Stack

- **Backend:** FastAPI + LangGraph/LangChain (0.3.x — brug `StateGraph`, ALDRIG legacy `AgentExecutor`) + SQLAlchemy/Alembic. `main.py` er ~5.250 linjer.
- **Frontend:** React 18 (CRA) + Styled Components + Framer Motion, 26 pages.
- **LLM-prioritet (fra `src/rule_engine/signal_extractor.py`):** 1) LM Studio (`LM_STUDIO_BASE_URL`, lokal — .env kører pt. `google/gemma-4-26b-a4b`; OBS Gemma kan returnere tomme svar), 2) Azure OpenAI, 3) OpenAI `gpt-4o-mini`. Nemotron som option til risikovurderings-metadata. Anthropic kun i research-agenten.
- **DB:** PostgreSQL (`tyr`-db) anbefalet, SQLite-fallback. Qdrant :6333 til vektorer. Migration: `scripts/migrate_sqlite_to_pg.py`.

## Backend-moduler (src/)

`agents/` (LangGraph-orkestrering: compliance_orchestrator, quick_check, research_agent_langgraph, registry) · `compliance/` (ai_act_checker, gdpr_checker, compliance_control_engine, recommendation_engine) · `compliance_engine.py` (deterministisk GO/CONDITIONAL_GO/NO_GO) · **`rule_engine/`** (signal_extractor.py — v3-regelmotoren, kernen) · **`api/routers/`** (bl.a. admin, risk_assessment) · **`law/`** (lov-assistent) · **`news/`** · **`config/validation.py`** (STRICT_CONFIG_VALIDATION fail-fast) · `database/` · `research/` · `cache/` (disk + memory LRU + warming) · `services/` (~26 filer: knowledge_base_updater, citation_verifier, audit_hash_chain, retention_service, backup_service, risk_assessment/, eu_ai_act_checker …)

## Nøgle-features (nyere end maj 2026)

- **Risikovurderingsmodul:** `src/services/risk_assessment/` + `RisikovurderingPage.jsx` + dynamisk opfølgnings-motor forankret i Datatilsynets skabelon + `scripts/eval_risikovurdering.py`
- **EU AI Act-checker:** `services/eu_ai_act_checker/` + `EuAiActCheckerPage.jsx`
- **landing-bifrost/** — offentlig oplysningsside deployet på Vercel (2026-06-27)
- GDPR-retention: nat-job kl. 02:00 (`ASSESSMENT_LOG_RETENTION_DAYS=1825`, `CASE_RETENTION_DAYS=3650`)

## Kerne-endpoints (verificeret i main.py)

`POST /api/compliance/hurtig-tjek` (quick check m. web-research) · `POST /api/compliance/7-punkts-vurdering` · `POST /api/compliance/analyser` (fuld analyse) — flere i `main.py` (~5.250 linjer) og `src/api/routers/` (bl.a. risk_assessment, admin)

## Kommandoer

```bash
npm run dev          # backend + frontend samtidigt (concurrently) — dev-brug
alembic upgrade head # migrations
pytest --cov=src     # backend-tests
cd frontend && npm test -- --watch=false
```

Prod styres via LaunchAgents/`scripts/*_tyr.sh` — brug ikke `npm run dev` som drift.

## Design (Northern Modern — fra DESIGN.md)

- Kongelig blå `#0d2e54` (primær) · bronze `#b08a4a` (signatur; tekst-bronze `#6e5527` for WCAG AA — defineret i `frontend/src/theme.js`) · off-white `#f5f4ef`
- Typografi: IBM Plex Sans + Mono + Serif italic
- Verdict-farver: GO `#2f6b2f` · BETINGET-GO bronze · NO-GO `#a52822`
- Teglrød `#C94416` er LEGACY (findes kun i enkelte gamle komponenter) — brug den ikke i nyt arbejde

## Konventioner

- Python: black, flake8, mypy, snake_case, type hints på signaturer
- React: PascalCase-komponenter, styled-components co-located; nye sider er `.jsx`
- Conventional Commits (`feat:`, `fix:`, `docs:` …)
- npm workspaces: kør `npm install` fra roden; `BROWSER=none` ved npm start

## Kendte faldgruber

- HANDOFF.md og CHANGELOG.md er frosset ved 2026-05-07/08 — stol ikke på dem
- `.env.example` er kilden til env-vars (LM_STUDIO_*, NEMOTRON_*, API_PORT, FRONTEND_PORT, TYR_LOG_DIR, retention m.fl.)
- FastAPI-titlen i main.py siger stadig "The Judge" — kosmetisk legacy
