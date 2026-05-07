# Changelog - Project Judge Dredd

Alle bemærkelsesværdige ændringer til dette projekt vil blive dokumenteret i denne fil.

Formatet er baseret på [Keep a Changelog](https://keepachangelog.com/da/1.0.0/),
og dette projekt følger [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0-alpha.1] - 2026-05-07 — "Hjemmel" (intern arbejdstitel)

Fase 0 af v3-evolutionen: fundament for deklarativ regelmotor forankret direkte i lovkilder.

### Tilføjet (Added)
- **Deklarativ regelmotor** under `src/rule_engine/` med tre underdele:
  - `models.py` — Pydantic-modeller for `Rule`, `RuleInput`, `RuleDecision`, `LawSource`
  - `expression.py` — sandbox-parser/evaluator for boolean-udtryk (AND/OR/NOT/==/!=/parens), uden brug af `eval`
  - `loader.py` — YAML + JSON Schema-validator + cross-check (decision-udtryk må kun referere definerede predikater)
  - `executor.py` — eksekverer regler mod input, plus `aggregate_status` (NO-GO > BETINGET-GO > GO)
- **Regelfiler under `rules/`** — én YAML pr. lovartikel med kilde-citat, URL og verificeringsdato
  - `rules/_schema.json` — JSON Schema (Draft 2020-12) der validerer alle regelfiler
  - `rules/ai_act/art_6_hojrisiko_klassifikation.yaml` — EU AI Act art. 6 + Bilag III
  - `rules/gdpr/art_22_automatiserede_afgorelser.yaml` — GDPR art. 22, stk. 1
  - `rules/forvaltningsloven/par_22_begrundelse.yaml` — Forvaltningsloven § 22
- **CLI** — `python -m src.rule_engine validate|list rules/`
- **Tests** — 48 enheds-tests for parser, executor og loader (alle grønne)

### Ændret (Changed)
- `requirements.txt`: tilføjet `jsonschema==4.23.0`; fjernet `streamlit==1.40.0` og `plotly==5.24.1` (ingen Python-imports henviste til dem)

### Arkitekturprincip
LLM må kun fortolke fritekst → strukturerede signaler (`signal_extractor`, kommer i Fase 1). Selve compliance-afgørelsen er altid deterministisk og kan spores til den lovartikel, reglen er hjemlet i.

## [3.0.0-alpha.6] - 2026-05-07 — Audit-log + 5 nye regler

### Tilføjet (Added)
- **Audit-log for v3-vurderinger** (`src/rule_engine/audit.py`):
  - `V3AssessmentLog` SQLAlchemy-model (append-only, JSON-payload, indekseret på created_at + status)
  - Hver `/api/v3/assess` persisterer request + response automatisk
  - Best-effort: hvis DB er nede, returneres vurderingen stadig med en advarsel
  - Optional `case_id`, `user_id`, `note` på request for senere filtrering
- **Audit-endpoints**:
  - `GET /api/v3/audit?limit=50&case_id=...&status=NO-GO` — filtreret liste
  - `GET /api/v3/audit/{log_id}` — fuld request + response til reproduktion
- **5 nye regler** (15 i alt):
  - AI Act art. 13 (transparens og brugerinformation for højrisiko)
  - AI Act art. 14 (menneskelig overvågning af højrisiko)
  - GDPR art. 5 (principper: formålsbegrænsning, dataminimering, opbevaring, rigtighed, sikkerhed)
  - GDPR art. 32 (sikkerhed ved behandling)
  - Forvaltningsloven § 3 (inhabilitet — også systemisk via leverandør og bias)

### Test-status
94 unit tests grønne (9 nye for audit) · 3/3 regression-cases passerer · 15 regler validerer

## [3.0.0-alpha.5] - 2026-05-07 — LM Studio + react-query + ⌘K command palette

### Tilføjet (Added)
- **LM Studio / lokal LLM-support** i `signal_extractor.py`. Selection priority er nu: `LM_STUDIO_BASE_URL` (LM Studio / Ollama / vLLM / llama.cpp server) → `AZURE_OPENAI_ENDPOINT` → `OPENAI_API_KEY`. Sæt fx `LM_STUDIO_BASE_URL=http://localhost:1234/v1` for at køre signal-extraction lokalt uden API-omkostninger.
- **`.env.example`** opdateret med dokumentation af alle tre LLM-options.
- **V3VurderingPage** kalder nu `/api/v3/assess` via `react-query` `useMutation`. Sample-data er flyttet til "Indsæt eksempel"-knap i formen i stedet for at være hardcoded i siden. Loading/error/empty states er på plads.
- **CommandPalette** (⌘K / Ctrl+K) under `frontend/src/components/command-palette/`. Lightweight implementering med framer-motion (ingen ny dep). Naviger mellem alle 13 sider med pil-op/ned + Enter. Globalt bundet i App.js — fungerer på alle sider.

## [3.0.0-alpha.4] - 2026-05-07 — Fase 1.4 (v3 API-endpoints)

### Tilføjet (Added)
- **`POST /api/v3/assess`**: kører hele v3-regelmotoren mod input. Tager fritekst-beskrivelse + signals + predikater og returnerer:
  - `aggregate_status` (NO-GO > BETINGET-GO > GO)
  - `decisions[]` med fuld kilde-citation, krav, evidens og evaluation_log
  - `signals_extracted_by_llm` så bruger kan auditere hvad LLM'en inferred
  - `warnings[]` for fx. manglende LLM-konfiguration
  - Caller-leverede signaler vinder altid over LLM-foreslåede
- **`GET /api/v3/rules`**: lister alle indlæste regler med deres kilde + predikater. Bruges af frontend til at vise "regler dækket" og af auditorer.
- Begge endpoints cacher rule-loading via `lru_cache` så regler kun parses én gang pr. server-instans.

### Smoke-verificeret
Med 10 regler indlæst og realistisk input: 6/10 regler triggered, aggregate = BETINGET-GO.

## [3.0.0-alpha.3] - 2026-05-07 — Fase 2 (frontend design-system primitives)

### Tilføjet (Added)
- **Design-system primitives** under `frontend/src/components/rules/`:
  - `ComplianceVerdict` — status-pille (GO / BETINGET-GO / NO-GO / NEEDS_INPUT) i tre størrelser
  - `LawSourceLink` — ekstern-link til EUR-Lex / Retsinformation med "sidst verificeret"-dato
  - `RuleCitation` — citatblok med direkte lov-citat + kilde-attribution
  - `EvidenceChecklist` — interaktiv evidens-tjekliste med status-farver (done/pending/in_progress/blocked)
  - `RuleDecisionPanel` — komplet panel for én RuleDecision: header + citat + begrundelse + krav-liste + needs_input
  - Alle primitives accepterer v3 RuleDecision-JSON direkte og bruger eksisterende theme-tokens
- **`/v3-vurdering`-side** (`V3VurderingPage.jsx`): viser primitives komponeret til en hel Quick Check-side i Design A "stille autoritet"-stil. Bruger hardcoded sample-data der mirror'er backend-output. Erstattes af /api/v3/assess-kald i Fase 1.4.

### Ændret (Changed)
- `App.js`: tilføjet lazy-import + Route for `/v3-vurdering`. Ingen ændringer til eksisterende ruter.

## [3.0.0-alpha.2] - 2026-05-07 — Fase 1 (regelbase + signal-extractor)

### Tilføjet (Added)
- **Signal-extractor** (`src/rule_engine/signal_extractor.py`): LLM-baseret fritekst → strukturerede signaler. LLM kan ALDRIG ændre selve afgørelsen, kun foreslå hvilke trigger-signaler der matcher. Bruger Azure OpenAI (eller OpenAI fallback) — samme pattern som resten af kodebasen. Stub-LLM understøttes for testning.
- **6 nye regler** (10 i alt):
  - AI Act art. 5 (forbudte praksisser → NO-GO)
  - AI Act art. 50 (transparens for chatbots/syntetisk indhold/deepfakes)
  - GDPR art. 6 (retsgrundlag for behandling)
  - GDPR art. 35 (DPIA-pligt)
  - Forvaltningsloven § 19 (partshøring)
  - Forvaltningsloven § 24 (begrundelsens indhold + AI-hallucinations-risiko)
  - Offentlighedsloven § 11 (dataudtræk og sammenstilling)
- **Regression-runner** (`src/rule_engine/regression.py` + `tests/regression/cases.yaml`): YAML-baseret test-harness der kører realistiske scenarier mod hele regelbasen og verificerer status + triggered rules + per-rule status. Kør: `python -m src.rule_engine.regression tests/regression/cases.yaml`. 3 startcases dækker BETINGET-GO, NO-GO og GO.

### Ændret (Changed)
- **Forgivende executor**: når et triggered rule mangler predikat-svar, returneres en `RuleDecision` med `needs_input: [...]` i stedet for at smide en exception. Dette gør regelmotoren brugbar i en iterativ wizard-flow: fortæl brugeren *hvad* der mangler, ikke "fejlet".
- **Strammere AI-Act triggers**: art. 5/6/50 kræver nu `system.uses_ai`-signalet (ikke bare personoplysnings-behandling). Forhindrer at rene fagsystemer uden AI udløser AI-Act-vurdering.

### Test-status
85 unit tests grønne · 3/3 regression-cases passerer

### Design-beslutning (2026-05-07)
Visuelt sprog er bekræftet via tre mockups i `mockups/`:
- **Marketing/login (`/`, `/om`, `/kontakt`):** Design A — "stille autoritet" (hvid baggrund, Source Serif Pro headlines, Inter body, lov-citater som elegante citatblokke). Sender ro og autoritet til indkøbsbeslutningstagere.
- **App (`/app/*`):** Design B — "kommandocenter" (mørk default, sidebar-navigation, ⌘K command palette, JetBrains Mono på lov-citater, status-pills). Power-user-værktøj for sagsbehandlere.

`.claude/launch.json` er sat op med dev-servers for backend (port 8000) og frontend (port 8080).

## [2.0.0] - 2025-09-20

### Ændret (Changed)
- **Major Rebranding**: Omdøbt fra "Judge Jarvis" til "Project Judge Dredd"
- **Professionel UI**: Fjernet alle emojis og implementeret mere professionelt design
- **Compliance Control**: Omdøbt "Fuld Vurdering" til "Compliance Control"
- **Sidebar**: Nu kollapsbar med bedre navigation

### Tilføjet (Added)
- **Regelmotor**: Deterministisk regelbaseret compliance vurdering
- **Evidenskatalog**: Komplet katalog over nødvendige artefakter og dokumentation
- **Beslutningslogik**: Klar GO/BETINGET-GO/NO-GO beslutningsstruktur
- **Risikoscore**: 0-100 point risiko scoring system
- **Assessment Historik**: Gem og gennemse tidligere vurderinger
- **Hjælpetekster**: Tooltips og kontekstuel hjælp
- **Relevante Links**: Sektion med links til danske AI og juridiske ressourcer
- **Versionering**: Implementeret semantic versioning

### Forbedret (Improved)
- **Navigation**: Forbedret progression bar med klikbare trin
- **Styling**: Mørkere, mere professionelt farvetema
- **Performance**: Optimeret loading states og error handling
- **Brugeroplevelse**: Auto-save, keyboard navigation, print-venlig version

## [1.0.0] - 2025-09-19

### Initial Release
- 7-punkts AI compliance vurdering
- Integration med danske nyhedskilder
- GDPR og AI Act compliance checks
- Real-time nyhedsfeed fra Datatilsynet, EDPB, EU
- Grundlæggende dashboard og rapportering