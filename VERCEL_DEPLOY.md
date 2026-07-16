# Vercel-deploy — Tyr frontend

Denne guide deployer **frontenden** (React/CRA) til Vercel. Backenden (FastAPI)
kører **ikke** på Vercel — se afsnittet [Hvorfor ikke hele appen?](#hvorfor-ikke-hele-appen-på-vercel)
nedenfor.

## TL;DR

1. Gå til <https://vercel.com/new> → importér GitHub-repoet `parthee-vijaya/ai-jura`.
2. Vercel læser `vercel.json` i roden automatisk — du behøver **ikke** ændre
   Build/Output-settings. (Framework: Create React App, build i `frontend/`,
   output `frontend/build`.)
3. Tilføj én environment-variabel (Project → Settings → Environment Variables):

   | Navn | Værdi | Scope |
   |------|-------|-------|
   | `REACT_APP_API_BASE_URL` | `https://din-backend.onrender.com` | Production (+ Preview) |

   Det er den **offentlige URL til backenden**. Baseres ind i bundtet ved build,
   så husk **Redeploy** hvis du ændrer den.
4. Klik **Deploy**. Færdig — frontenden er live på `https://<projekt>.vercel.app`.

> Sætter du **ikke** `REACT_APP_API_BASE_URL`, kalder frontenden relative
> `/api/...`-stier på Vercel-domænet, hvor der ingen backend er → alle API-kald
> fejler. Variablen er reelt påkrævet i produktion.

## Hvad ligger i repoet

- **`vercel.json`** — bygger `frontend/` og udgiver `frontend/build` som en SPA
  med fallback-rewrite til `index.html` (så React Router-ruter virker ved direkte
  refresh) og cache-headers på statiske assets.
- **`.vercelignore`** — ekskluderer backend/Python/data fra upload, så kun
  frontenden sendes til Vercel.

## Backend (FastAPI)

Backenden skal køre et sted med en **altid-kørende proces**. Repoet har allerede
en færdig opskrift til **Render** (`render.yaml`, Frankfurt/EU-region) — se
[RENDER_DEPLOY.md](./RENDER_DEPLOY.md). Andre muligheder: Railway, Fly.io,
en VPS, eller den eksisterende Mac Studio-opsætning ([DEPLOY.md](./DEPLOY.md)).

Backendens CORS står på `allow_origins=["*"]`, så Vercel-domænet kan kalde den
uden ekstra opsætning. Vil du stramme det i produktion, så sæt en allow-list med
dit `*.vercel.app`-domæne i `main.py`.

### Alternativ: proxy /api via Vercel (undgår CORS, men ikke anbefalet)

Du kan i stedet lade Vercel proxye API-kald til backenden ved at tilføje en
rewrite i `vercel.json` **før** SPA-fallback'en:

```jsonc
"rewrites": [
  { "source": "/api/:path*", "destination": "https://din-backend.onrender.com/api/:path*" },
  { "source": "/(.*)", "destination": "/index.html" }
]
```

…og så lade `REACT_APP_API_BASE_URL` være tom. Frarådes her, fordi
nyheds-**tickerens SSE-stream** (`/api/news/ticker/stream`) og de langvarige
compliance-analyser fungerer mere stabilt med direkte kald end gennem Vercels
proxy-lag.

## Hvorfor ikke hele appen på Vercel?

Vercel kører serverless-funktioner: statsløse, korte timeouts, ingen vedvarende
proces. Backenden bygger på det modsatte:

- **APScheduler-cronjobs** — daglig retention kl. 02:00, KB-opdatering kl. 03:00.
  Kræver en proces der altid kører.
- **Vedvarende baggrundstasks** — periodisk nyheds-/ticker-refresh via `asyncio`.
- **SSE-streaming** — `/api/news/ticker/stream` holder forbindelsen åben.
- **Lange LLM-analyser** — compliance-vurderinger kan tage flere minutter (langt
  over Vercels funktions-timeouts).
- **Playwright/Chromium** — citat-verifikation scraper SPA-lovsider; browser-binær
  passer dårligt i serverless.
- **Disk-cache, Qdrant, PostgreSQL** — vedvarende state/tjenester.

Derfor: **frontend på Vercel, backend på en langtidskørende host.**
