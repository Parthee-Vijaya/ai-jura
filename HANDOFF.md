# Hjemmel v3 — Handoff

**Dato:** 7. maj 2026
**Branch:** `v3-hjemmel` (på [Parthee-Vijaya/Judge_dredd](https://github.com/Parthee-Vijaya/Judge_dredd))
**Senest pushede commit:** se `git log v3-hjemmel -1` efter pull

Dette dokument lader dig fortsætte v3-arbejdet fra en anden maskine uden tab af kontekst.

---

## 1. Sådan resumer du på en ny computer

```bash
# Klon eller pull
git clone https://github.com/Parthee-Vijaya/Judge_dredd.git
cd Judge_dredd
git checkout v3-hjemmel
git pull

# Backend setup (Python 3.11+ — vi har testet med 3.13)
python3.13 -m venv venv
./venv/bin/pip install pydantic==2.9.2 PyYAML==6.0.2 jsonschema==4.23.0 \
  pytest==8.3.3 sqlalchemy==2.0.35 psycopg2-binary==2.9.10 \
  loguru==0.7.2 python-dotenv==1.0.1
# (eller bare: ./venv/bin/pip install -r requirements.txt for fuld stack)

# Verificér at alt virker
./venv/bin/python -m src.rule_engine validate rules
./venv/bin/python -m src.rule_engine.regression tests/regression/cases.yaml
./venv/bin/pytest tests/rule_engine -q
```

Forventet output:
- `Loaded 15 rule(s)` med alle 15 markeret `ok`
- `3/3 cases passed`
- `94 passed`

Frontend (kun nødvendigt hvis du vil køre browseren):
```bash
cd frontend && npm install
cd .. && npm run dev   # starter både backend + frontend via concurrently
# Åbn http://localhost:8080/v3-vurdering
```

---

## 2. Hvor er vi nu?

### Status på `v3-hjemmel`

| Tæller | Værdi |
|---|---|
| Commits siden main | 8 |
| Regler | 15 (AI Act ×5, GDPR ×4, Forvaltningslov ×4, Offentlighedslov ×1, Sektorlove: 0) |
| Unit tests | 94 grønne |
| Regression-cases | 3/3 passerer |
| API-endpoints | 4 nye (`POST /api/v3/assess`, `GET /api/v3/rules`, `GET /api/v3/audit`, `GET /api/v3/audit/{id}`) |
| LLM-providers | LM Studio, Azure OpenAI, OpenAI |

### Commit-historie (v3-arbejde)
```
1f608d8 v3.0.0-alpha.6 — audit-log + 5 nye regler (15 i alt)
85a9c2b v3.0.0-alpha.5 — LM Studio + react-query live + ⌘K command palette
68fa0dc v3.0.0-alpha.4 — /api/v3/assess + /api/v3/rules
fd12bc2 v3.0.0-alpha.3 — design-system primitives + /v3-vurdering
59f7dc0 v3.0.0-alpha.2 — signal-extractor + 7 nye regler + regression-runner
14b92f7 design(v3) — mockups + design-retning blend (A marketing, B app)
7412fce docs(v3) — evaluate CLI + jurist-vejledning
1fa20df v3.0.0-alpha.1 — deklarativ regelmotor med lovkilde-forankring
```

### Beslutninger der er taget
- **Brand:** "Hjemmel" som intern arbejdstitel (Judge Dredd er for aggressivt for offentlig sektor)
- **Rulemotor:** Hybrid YAML + LLM-fortolkning af signaler (LLM kan aldrig ændre afgørelsen)
- **Design:** Design A "stille autoritet" på marketing/login + Design B "kommandocenter" i selve app'en. Mockups ligger i `mockups/`.
- **Hosting:** Backend on-prem, LLM via API (Azure West Europe / LM Studio lokalt / OpenAI)
- **Single-tenant:** Kun Kalundborg Kommune i v1 (ingen multi-tenancy)
- **Lovdækning:** AI Act + GDPR/DBL + Forvaltningslov + Offentlighedslov + Sektorlove

---

## 3. Arbejde i gang (work in progress)

**Step 1: V3VurderingPage med audit-metadata** — *committet i denne handoff*
- Tilføjet `case_id`-felt og `note`-felt til formularen
- "Indsæt eksempel" pre-fylder også case_id + note
- audit_log_id vises i footer efter vurdering
- Status: ✅ Klar — denne ændring er med i handoff-commit

### Næste skridt jeg foreslog (i prioriteret rækkefølge)

**Step 2: `/v3-historik`-side med audit-liste** *(ikke startet)*
- Ny side under `frontend/src/pages/V3HistorikPage.jsx`
- Hent `/api/v3/audit?limit=50` via react-query
- Vis tabel: created_at · case_id · status · rules_loaded · note
- Klik på række → naviger til `/v3-historik/:id` der henter `/api/v3/audit/{id}` og viser fuld request + response
- Tilføj route i `App.js` + entry i `CommandPalette.jsx` (`g i` for "historik")

**Step 3: G-prefix shortcuts** *(ikke startet)*
- Lige nu virker kun ⌘K. Hint-tekst i palette siger "g s", "g v" men de er ikke wired
- Tilføj global key listener der lytter på "g" efterfulgt af bogstav inden for ~700ms
- Naviger til den matching kommando
- Filen er `frontend/src/components/command-palette/CommandPalette.jsx`
- Tilføj en `useGotoShortcuts(commands)` hook der kører i `App.js`

**Step 4: Sammenlign-mode (gammel vs ny engine)** *(ikke startet, mest komplekst)*
- Endpoint `POST /api/v3/compare` der kører både den gamle `ComplianceController.vurder_system()` (i `src/compliance_engine.py`) og den nye rule_engine på samme input
- Diff udregnes per regelområde: AI Act, GDPR, etc.
- Ny side `/v3-sammenlign` viser side-om-side
- Bedste vej: brug den gamle engines output-shape som "expected" og noter hvor v3 spotter ekstra/mindre

**Step 5: Sektorlove (BLOKERET på jurist-input)** *(blokeret)*
- Kræver konkret list over hvilke 5-10 paragraffer i serviceloven, beskæftigelseslov og sundhedsloven der hyppigst er relevante for AI-cases
- Bedste fremgangsmåde: kontakt jurist hos Kalundborg, lav 30-min interview, identificér paragraffer

---

## 4. Vigtige filer at kende

### Backend
- [`main.py`](main.py) (linje ~1864-2030) — v3 API-endpoints
- [`src/rule_engine/`](src/rule_engine/) — hele motoren
  - `models.py` — Pydantic Rule, RuleInput, RuleDecision
  - `expression.py` — sandbox boolean parser (ingen `eval`)
  - `loader.py` — YAML + JSON Schema validator
  - `executor.py` — deterministisk evaluator + aggregate_status
  - `signal_extractor.py` — LLM fritekst → signaler (LM Studio/Azure/OpenAI)
  - `audit.py` — V3AssessmentLog SQLAlchemy-model
  - `regression.py` — YAML-baseret test-harness
  - `__main__.py` — CLI: `validate`, `list`, `evaluate`
- [`rules/`](rules/) — 15 YAML-regler i 4 mapper
  - `_schema.json` — JSON Schema (rør ikke uden grund)
- [`tests/regression/cases.yaml`](tests/regression/cases.yaml) — start-casebase

### Frontend
- [`frontend/src/components/rules/`](frontend/src/components/rules/) — 5 design primitives
  - `ComplianceVerdict`, `LawSourceLink`, `RuleCitation`, `EvidenceChecklist`, `RuleDecisionPanel`
- [`frontend/src/components/command-palette/CommandPalette.jsx`](frontend/src/components/command-palette/CommandPalette.jsx) — ⌘K
- [`frontend/src/pages/V3VurderingPage.jsx`](frontend/src/pages/V3VurderingPage.jsx) — live integration mod /api/v3/assess
- [`frontend/src/App.js`](frontend/src/App.js) — routes + CommandPalette wiring

### Dokumentation
- [`docs/RULE_AUTHORING.md`](docs/RULE_AUTHORING.md) — jurist-guide til at skrive regler
- [`mockups/`](mockups/) — index.html + design-a/b/c.html
- [`CHANGELOG.md`](CHANGELOG.md) — fuld historik for v3.0.0-alpha.1 → alpha.6

---

## 5. Kommandoer du ofte får brug for

```bash
# Backend tests
./venv/bin/pytest tests/rule_engine -q

# Validér alle regler
./venv/bin/python -m src.rule_engine validate rules

# Liste regler med citater
./venv/bin/python -m src.rule_engine list rules

# Kør én regel mod sample input
./venv/bin/python -m src.rule_engine evaluate \
  gdpr.art22.automatiseret_individuel_afgorelse \
  examples/rule_inputs/gdpr_art22_betinget_go.json

# Regression suite
./venv/bin/python -m src.rule_engine.regression tests/regression/cases.yaml

# Backend + frontend dev
npm run dev    # fra repo root

# API smoketest med curl
curl -X POST http://localhost:8000/api/v3/assess \
  -H 'Content-Type: application/json' \
  -d '{"system_description":"chatbot","case_id":"K-test","predicates":{}}'

curl 'http://localhost:8000/api/v3/audit?limit=5'
```

---

## 6. Konfiguration (.env)

LLM-provider vælges automatisk efter denne prioritet (første match):

```bash
# 1. Lokal LLM (LM Studio / Ollama / vLLM)
LM_STUDIO_BASE_URL=http://localhost:1234/v1
LM_STUDIO_MODEL=meta-llama-3.1-8b-instruct  # navn fra LM Studio UI

# 2. Azure OpenAI (EU-hosted)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=...
AZURE_DEPLOYMENT_NAME=gpt-4o-mini

# 3. OpenAI (fallback)
OPENAI_API_KEY=sk-...
```

Hvis ingen er sat, skipper backend signal-extraction og returnerer en advarsel — vurderingen virker stadig hvis caller selv leverer signaler/predikater.

---

## 7. Kendt teknisk gæld / blockers

| Punkt | Status | Hvorfor |
|---|---|---|
| QuickCheckPage.js (1720 linjer) refaktor | Udskudt | Bundet til gammel engine; vent til v3 vinder adoption |
| Sektorlove i `rules/sektorlove/` | Tom mappe | Kræver jurist-interview |
| Frontend tests for design-primitives | Mangler | Lav test setup virker, men har ikke skrevet komponent-tests endnu |
| Authentication / SSO (Entra ID) | Ikke startet | Kræver Kalundborg IT-koordinering |
| Old engine vs new engine sammenligning | Ikke startet | Step 4 ovenfor |

---

## 8. Når du resumerer — checklist

1. `git pull` på `v3-hjemmel`
2. Læs CHANGELOG.md sektion 3.0.0-alpha.6 (eller seneste)
3. Kør `./venv/bin/pytest tests/rule_engine -q` — skal sige `94 passed`
4. Kør `./venv/bin/python -m src.rule_engine validate rules` — skal vise 15 regler
5. Læs Step 2 i denne fil og start derfra
6. Hvis tvivl: spørg `/v3-vurdering` med "Indsæt eksempel" → "Vurder" som rygmarvs-test af at hele kæden virker

God arbejdslyst.
