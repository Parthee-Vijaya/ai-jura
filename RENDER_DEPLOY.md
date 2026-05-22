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
3. Render læser `render.yaml` og beder om **`OPENAI_API_KEY`** — her indsætter du din **Gemini API-nøgle** (fra [aistudio.google.com](https://aistudio.google.com) → "Get API key"). Appen kalder Gemini via dets OpenAI-kompatible endpoint, som allerede er sat i `render.yaml` (`OPENAI_BASE_URL` + `OPENAI_MODEL=gemini-2.5-flash`) — derfor hedder nøglen `OPENAI_API_KEY` selvom det er en Gemini-nøgle.
   - Vil du bruge en anden/nyere model? Ret `OPENAI_MODEL` + `DEFAULT_LLM_MODEL` i `render.yaml`. Tilgængelige modeller: `https://generativelanguage.googleapis.com/v1beta/openai/models?key=DIN_NØGLE`.
4. Klik **Apply**. Backend bygger på ~5-10 min (tungt image: langchain, numpy, pandas, sklearn).
5. **Tjek backendens URL** i dashboardet. Hvis den IKKE er `https://ai-jura-backend.onrender.com` (navnet kan være globalt optaget → Render tilføjer et suffiks), så:
   - ret `REACT_APP_API_BASE_URL` i `render.yaml` (eller i frontend-tjenestens env) til den faktiske URL
   - **redeploy frontend'en** (URL'en bages ind i bundlet ved build).
6. Åbn frontend-URL'en → demo klar.

## Hvad virker / hvad er degraderet i demoen

| Virker | Degraderet (kan tilføjes senere) |
|---|---|
| Kerne-vurdering (deterministisk regelmotor, GO/BETINGET-GO/NO-GO) | **Semantisk lov-søgning (RAG):** `data/law_embeddings.json` er bygget med LM Studios `nomic`-model. Gemini's `gemini-embedding-001` har en anden dimension → genbyg indekset med `POST /api/law/rag/build` efter deploy, så query- og lager-vektorer matcher. |
| LLM-vurdering + rapportgenerering (Word/PDF) | **Citat-verifikation via Playwright:** chromium er ikke installeret i imaget (tungt). Det daglige verifikations-job fejler stille. Tilføj `RUN playwright install --with-deps chromium` i `Dockerfile.backend` hvis nødvendigt. |
| Postgres-data, indkøbsproces-wizard, evidens-checkliste | **Mail/SMTP:** notifikationer er slået fra (`NOTIFICATION_DIGEST_ENABLED=false`). Sæt SMTP-env hvis du vil sende. |
| Dashboard, sager, historik | **Qdrant** (sags-/evidens-vektorsøgning): ikke deployet — `law_rag` bruger lokal JSON i stedet, så kerne-flowet er upåvirket. |

## Omkostning

Hele Blueprintet er **$0** som det står (intet betalingskort krævet):

- **Static site:** gratis, altid på.
- **Postgres `free`:** gratis, men **udløber efter Render's gratis-periode** → skift til `basic-256mb` for varig drift.
- **Backend `free`:** gratis (512 MB). Spinner ned efter ~15 min inaktivitet → første besøg derefter koldstarter på ~30-60 s. OOM'er den ved boot (tung stack), bump til `starter`/`standard` i `render.yaml` (kræver betalingskort).

## Ændringer foretaget for at gøre repoet deploy-klart

- `Dockerfile.backend`: kopierer nu også `rules/` + `config/` (regelmotor + agent-registry loader dem ved relativ sti).
- `main.py`: uvicorn binder `$PORT` (Render) før `API_PORT`.
- `src/database/connection.py`: normaliserer `postgres://` → `postgresql+psycopg2://` (Render's URL-format).
- **Gemini-provider:** `render.yaml` peger `OPENAI_BASE_URL`/`OPENAI_API_BASE` på Gemini's OpenAI-kompatible endpoint og sætter Gemini-modeller. To hardcodede `gpt-4o-mini` (`main.py` juridisk-research, `src/news/llm_news_search.py`) læser nu `OPENAI_MODEL`, så Gemini-modellen bruges overalt. Ingen ny dependency.
- `render.yaml` + denne fil: tilføjet. Backend, database og frontend kører alle på Render's gratis-planer.

> Note: `/drift`-siden viser "LLM provider: OpenAI" — det er forventet. Gemini tilgås gennem OpenAI-kompatibilitets-laget, så appen ser det som en OpenAI-provider.
