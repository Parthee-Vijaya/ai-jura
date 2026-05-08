# DEPLOY — Tyr på Mac Studio

Manuel produktions-deploy af Tyr lokalt på Mac Studio. Tyr starter **ikke** automatisk ved reboot — du starter den selv når du har brug for den.

## Forudsætninger

- Python 3.11+ med venv på `./venv/`
- Node 18+ med `frontend/node_modules/` installeret (kør `npm install` fra root én gang)
- LM Studio kører lokalt med en chat-model og en embedding-model (`text-embedding-nomic-embed-text-v1.5` eller lignende)
- `.env` udfyldt — kopier `.env.example` og sæt minimum `LM_STUDIO_BASE_URL` (eller en af de andre LLM-providere)

## Daglig brug

```bash
# Start begge services
scripts/start_tyr.sh

# Tjek status (sundhedstjek af alle services)
scripts/status_tyr.sh

# Stop alt pænt
scripts/stop_tyr.sh
```

Tilgang:
- **Lokal** — http://localhost:8090
- **Tailscale fra iPhone** — http://`<din-mac-tailscale-ip>`:8090

## Forskellen fra `npm run dev`

| | `npm run dev` (udvikling) | `scripts/start_tyr.sh` (production) |
|---|---|---|
| Frontend | react-scripts dev-server, hot-reload | statisk build via `serve` |
| Backend | uvicorn med `--reload` | uvicorn uden reload |
| Performance | langsom på Tailscale | ~10× hurtigere første render |
| Logging | console only | loguru JSON → `~/Library/Logs/Tyr/backend.log` |
| Code changes | auto-reflekteres | kræver rebuild + restart |

Brug `npm run dev` når du **udvikler** Tyr. Brug `scripts/start_tyr.sh` når du **bruger** Tyr (eller når et andet teammedlem skal bruge den via Tailscale).

## Når frontend-koden ændres

`scripts/start_frontend.sh` bruger den eksisterende `frontend/build/` hvis den findes. For at rebuilde:

```bash
scripts/stop_tyr.sh
REBUILD=yes scripts/start_frontend.sh
scripts/start_backend.sh
```

Eller manuelt: `cd frontend && npm run build` derefter `scripts/start_tyr.sh`.

## Når backend-koden ændres

```bash
scripts/stop_tyr.sh
scripts/start_tyr.sh
```

Backend starter på ~5 sekunder.

## Logs

Tre log-filer:
- `~/Library/Logs/Tyr/backend.log` — strukturet JSON, dag-rotation, 7 dages bevarelse (loguru)
- `~/Library/Logs/Tyr/backend.console.log` — rå stdout/stderr fra backend-processen
- `~/Library/Logs/Tyr/frontend.console.log` — `serve` output

Drift-overblik findes også i UI: http://localhost:8090/drift

## PIDs

PIDs gemmes i `~/.tyr/run/{backend,frontend}.pid`. Hvis status_tyr.sh siger "pidfile findes men pid X kører ikke" — kør `stop_tyr.sh` for at rydde op, derefter `start_tyr.sh`.

## Tailscale-opsætning

Backend og frontend binder til `0.0.0.0` så de kan tilgås fra iPhone. Sørg for at:
- Tailscale kører på Mac Studio
- iPhone er logget ind på samme Tailscale-tailnet
- macOS firewall ikke blokerer port 8090/8001 fra Tailscale-interfacet

Find din Mac Tailscale-IP med `tailscale ip -4` på Mac'en.

## Troubleshooting

**"Backend kører allerede på port 8001"** — en gammel proces lever stadig:
```bash
scripts/stop_tyr.sh
# eller hårdere: lsof -ti:8001 | xargs kill -9
```

**"venv ikke fundet"** — opret den:
```bash
python3.11 -m venv venv
venv/bin/pip install -r requirements.txt
```

**"serve ikke installeret"** — kør npm install:
```bash
cd frontend && npm install
```

**Backend starter, men /health viser `llm: down`** — LM Studio er ikke i gang. Start LM Studio, indlæs en chat-model (fx `google/gemma-4-26b-a4b`) og en embedding-model.

**Frontend viser "Application error" ved Tailscale-adgang** — sandsynligvis CORS-problem eller backend ikke nåbar fra Tailscale-IP. Tjek at backend er bundet til `0.0.0.0` (er default i scripts).

## Stop ved Mac-genstart

Tyr starter ikke automatisk efter reboot — det er bevidst. Efter en genstart:
```bash
cd /Users/parthee/Desktop/Claude/projekter/aktive/judge-dredd
scripts/start_tyr.sh
```
