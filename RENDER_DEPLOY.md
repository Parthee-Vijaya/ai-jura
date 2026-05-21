# Deploy til Render — demo-opsætning

Bifrost kører som tre Render-tjenester defineret i [`render.yaml`](render.yaml):

| Tjeneste | Type | Hvad |
|---|---|---|
| `ai-jura-backend` | Web (Docker) | FastAPI via `Dockerfile.backend`, port via `$PORT` |
| `ai-jura-frontend` | Static site | React-build, kalder backend over HTTPS |
| `ai-jura-db` | Postgres 16 | Skema oprettes automatisk ved boot (`init_db()`) |

Vercel duer **ikke** her: backenden er en vedvarende proces med APScheduler-baggrundsjobs, disk/memory-cache og streaming — det bryder på serverless. Derfor Render.

## Trin for trin

1. **Push koden** (render.yaml ligger allerede i repoet — se nederst).
2. Gå til **Render → New → Blueprint**, og forbind GitHub-repoet `Parthee-Vijaya/ai-jura`.
3. Render læser `render.yaml` og beder om **`OPENAI_API_KEY`** — indsæt din nøgle. (LM Studio findes ikke i skyen, så LLM + embeddings kører via OpenAI.)
4. Klik **Apply**. Backend bygger på ~5-10 min (tungt image: langchain, numpy, pandas, sklearn).
5. **Tjek backendens URL** i dashboardet. Hvis den IKKE er `https://ai-jura-backend.onrender.com` (navnet kan være globalt optaget → Render tilføjer et suffiks), så:
   - ret `REACT_APP_API_BASE_URL` i `render.yaml` (eller i frontend-tjenestens env) til den faktiske URL
   - **redeploy frontend'en** (URL'en bages ind i bundlet ved build).
6. Åbn frontend-URL'en → demo klar.

## Hvad virker / hvad er degraderet i demoen

| Virker | Degraderet (kan tilføjes senere) |
|---|---|
| Kerne-vurdering (deterministisk regelmotor, GO/BETINGET-GO/NO-GO) | **Semantisk lov-søgning (RAG):** `data/law_embeddings.json` er bygget med LM Studios `nomic`-model (768-dim). OpenAI's embeddings er 1536-dim → dimensions-mismatch. Genbyg med `POST /api/law/rag/build` efter deploy for at få den til at matche cloud-provideren. |
| LLM-vurdering + rapportgenerering (Word/PDF) | **Citat-verifikation via Playwright:** chromium er ikke installeret i imaget (tungt). Det daglige verifikations-job fejler stille. Tilføj `RUN playwright install --with-deps chromium` i `Dockerfile.backend` hvis nødvendigt. |
| Postgres-data, indkøbsproces-wizard, evidens-checkliste | **Mail/SMTP:** notifikationer er slået fra (`NOTIFICATION_DIGEST_ENABLED=false`). Sæt SMTP-env hvis du vil sende. |
| Dashboard, sager, historik | **Qdrant** (sags-/evidens-vektorsøgning): ikke deployet — `law_rag` bruger lokal JSON i stedet, så kerne-flowet er upåvirket. |

## Omkostning

- **Static site:** gratis, altid på.
- **Postgres `free`:** gratis, men **udløber efter ~90 dage** → skift til `basic-256mb` for varig drift.
- **Backend `starter`:** ~$7/md (512 MB). OOM'er den ved boot, bump til `standard` (2 GB) i `render.yaml`.

For en helt gratis (men langsommere) demo: sæt backend til `plan: free` — den spinner ned ved inaktivitet og koldstarter på ~30-60 s.

## Ændringer foretaget for at gøre repoet deploy-klart

- `Dockerfile.backend`: kopierer nu også `rules/` + `config/` (regelmotor + agent-registry loader dem ved relativ sti).
- `main.py`: uvicorn binder `$PORT` (Render) før `API_PORT`.
- `src/database/connection.py`: normaliserer `postgres://` → `postgresql+psycopg2://` (Render's URL-format).
- `render.yaml` + denne fil: tilføjet.
