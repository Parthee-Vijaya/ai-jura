# Bifrost på Render — staging/demo deploy

> ⚠️ **STAGING / DEMO ONLY**. Render egner sig IKKE til produktion med rigtig
> kommunal persondata pga. data-residency + LLM-afhængighed. Til produktion:
> brug Mac Studio + Tailscale ([SETUP_NEW_MAC.md](SETUP_NEW_MAC.md)).

## Hvorfor Render ikke er rigtigt for produktion

| Problem | Hvorfor det rammer Bifrost særligt hårdt |
|---|---|
| **Data-residency** | Render = US-firma. EU-region (Frankfurt) findes, men kræver databehandleraftale med kommunen + hjemmel jf. GDPR Art. 28. Ironisk for et compliance-værktøj |
| **LM Studio kan ikke køre** | Render har ingen GPU/lokal LLM. Du SKAL bruge OpenAI/Azure → kommunens vurderings-input forlader kontrol-zonen |
| **DPIA-konflikt** | DPIA-dokument forudsætter Mac Studio + Tailscale-only access. Render-deploy ville kræve ny DPIA-iteration + jurist-validering |
| **Free tier sover** | Backend slukker efter 15 min inaktivitet — ikke kontinuerlig drift |
| **Pris** | Starter plan = $7/måned/service + $7 for Postgres. ~$21/måned hvis alt skal være "always on" |

## Hvor Render giver mening

- **Demo til eksterne stakeholders** (KL, andre kommuner) med dummy-data
- **Staging** til at teste features før de rammer Mac Studio
- **Eksternt access** uden Tailscale-besvær
- **Stress-test** loadtest uden at risikere produktion-data

## Setup

### 1. Forudsætninger

- GitHub repo med `render.yaml` (allerede i main)
- [Render-konto](https://render.com) (gratis)
- OpenAI API-key til staging-LLM (LM Studio kan ikke køre på Render)

### 2. Deploy

1. Login på Render Dashboard
2. **New** → **Blueprint**
3. Vælg `Parthee-Vijaya/ai-jura` repo + `main` branch
4. Render læser `render.yaml` automatisk og foreslår 3 ressourcer:
   - `bifrost-staging-api` (Python web service)
   - `bifrost-staging` (statisk frontend)
   - `bifrost-staging-db` (PostgreSQL)
5. **Apply**

### 3. Sæt secret env vars

Når services er oprettet (Status = "Build failed" pga. manglende `OPENAI_API_KEY`):

1. Gå til `bifrost-staging-api` → **Environment**
2. Klik **+ Add Environment Variable** for hver:

```
OPENAI_API_KEY    sk-...   (kræves — staging LLM)
SMTP_HOST                  (valgfri — kun til mail-test)
SMTP_USER                  (valgfri)
SMTP_PASSWORD              (valgfri)
```

3. **Save Changes** → automatisk redeploy

### 4. Verifikation

```bash
# Backend
curl https://bifrost-staging-api.onrender.com/health
curl https://bifrost-staging-api.onrender.com/api/v3/admin/config

# Frontend
open https://bifrost-staging.onrender.com
```

### 5. Tilføj demo-data (valgfri)

Render-Postgres er TOM efter første deploy. For at populere med dummy-data:

```bash
# Lokalt med pg_restore mod Render-DB
# Hent connection string fra: Render Dashboard → bifrost-staging-db → External Connection
PSQL_URL="postgres://bifrost:xxx@frankfurt-pg.render.com/bifrost"

# Restore en demo-backup (uden ægte persondata!)
pg_restore --dbname="$PSQL_URL" --no-owner --no-acl --clean --if-exists \
  ./demo-data/bifrost-demo.dump
```

**Vigtigt**: Brug KUN dummy-data eller fuldt anonymiserede sager. Hvis du
uploader rigtige kommunale sager til Render: tilbagetræk dem straks og lav
ny DPIA-vurdering.

## Forskelle mellem Mac Studio og Render

| Feature | Mac Studio (prod) | Render (staging) |
|---|---|---|
| **LLM** | LM Studio lokalt (gpt-oss-20b) | OpenAI gpt-4o-mini |
| **Data-residency** | Kalundborg netværk | Render EU-region |
| **Adgang** | Tailscale-only | Public HTTPS |
| **Database** | Postgres på Mac | Render managed Postgres |
| **Backup** | LaunchAgent → ekstern disk | Manuel pg_dump (ingen automatisk på free tier) |
| **Pris** | $0 (hardware findes) | ~$21/måned (starter-tier) |
| **Pilot-readiness** | ✓ DPIA-godkendt | ✗ kræver ny DPIA |

## Hvad bygges af `render.yaml`

```
┌────────────────────────────────────────┐
│ bifrost-staging.onrender.com           │  static React build
│ ├ React 18 + styled-components         │  free tier OK
│ └ proxy til API via REACT_APP_API_*    │
└────────────────────────────────────────┘
                │
                ▼ /api/*
┌────────────────────────────────────────┐
│ bifrost-staging-api.onrender.com       │  FastAPI uvicorn
│ ├ Python 3.11 + 105+ tests             │  starter tier ($7/mo)
│ ├ Alembic migrations (auto-køres)      │
│ └ STRICT_CONFIG_VALIDATION=false       │
└────────────────────────────────────────┘
                │
                ▼ DATABASE_URL
┌────────────────────────────────────────┐
│ bifrost-staging-db                     │  PostgreSQL managed
│ ├ Frankfurt region                     │  free tier (1 GB, 90 dage)
│ ├ Auto-backups via Render              │
│ └ Auto-linked til API via fromDatabase │
└────────────────────────────────────────┘
                │
                ▼ OPENAI_API_KEY
┌────────────────────────────────────────┐
│ OpenAI API (ekstern)                   │  ⚠ data forlader Render
│ └ gpt-4o-mini for staging              │
└────────────────────────────────────────┘
```

## Tilbagetrukket fra Render (cleanup)

Hvis du vil slette Render-deploy:

1. Render Dashboard → hver service → **Settings** → **Delete Service**
2. Database → **Delete Database** (eksplicit — sletter alle data)
3. (Valgfri) Slet OpenAI-API-key hvis kun brugt til staging

## Auto-deploy fra git

`render.yaml` har `autoDeploy: true` på begge services. Hver push til
`main` trigger ny build. Hvis du ikke vil have det:

```yaml
autoDeploy: false  # i render.yaml
```

Så skal du manuelt deploy via Dashboard → service → **Manual Deploy**.

## Limitations

1. **No persistent disk** — Render's free tier har read-only filsystem efter build. Det betyder:
   - `data/`-mappen kan ikke modificeres ved runtime
   - Knowledge base auto-update fungerer ikke (skal genbuilde)
   - Backup-scripts er meningsløse

2. **No background workers** — APScheduler kører i samme proces som FastAPI. På Render free/starter sover processen ved inaktivitet → cron-jobs kører ikke pålideligt.

3. **No GPU** — embedding-rebuild + LLM kan ikke køre lokalt. Brug eksterne API'er.

4. **15 min idle timeout** (free tier) — første request efter idle er langsom (cold start ~30s).

## TL;DR

Brug Render hvis du vil vise Bifrost til nogen uden at give dem Tailscale-adgang.
Brug IKKE Render til rigtig kommunal data.
