# Bifrost-setup på ny Mac

Step-by-step guide til at få Bifrost kørende på en ny Mac med din eksisterende
data + state. Total tid: ~30 min for fresh install, +5 min for backup-restore.

## Forudsætninger på den nye Mac

- macOS Sonoma eller nyere
- Xcode Command Line Tools: `xcode-select --install`
- [Homebrew](https://brew.sh)
- 16+ GB RAM (LM Studio kræver 8+ GB for default-modellen)
- 20+ GB ledig disk

## Fresh install (uden eksisterende data)

### 1. Installer systemdependencies

```bash
# Postgres + Node + Python
brew install postgresql@16 node python@3.11

# Start postgres som service
brew services start postgresql@16

# Python-symlink hvis nødvendigt
ln -sf /opt/homebrew/bin/python3.11 /usr/local/bin/python3.11
```

### 2. Klon repository

```bash
mkdir -p ~/Desktop/Claude/projekter/aktive
cd ~/Desktop/Claude/projekter/aktive
git clone https://github.com/Parthee-Vijaya/ai-jura.git bifrost
cd bifrost
```

### 3. Backend setup

```bash
# Virtual env
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# .env
cp .env.example .env
```

**Rediger `.env`** og udfyld minimum:

```bash
DATABASE_URL=postgresql://tyr@localhost:5432/tyr
LM_STUDIO_BASE_URL=http://localhost:1234/v1
LM_STUDIO_MODEL=openai/gpt-oss-20b
SMTP_HOST=  # tom = ingen email
STRICT_CONFIG_VALIDATION=false  # tillader dev-start
API_HOST=0.0.0.0
API_PORT=8001
FRONTEND_PORT=8090
```

### 4. PostgreSQL setup

```bash
# Opret user + database
PG=/opt/homebrew/opt/postgresql@16/bin
$PG/createuser tyr 2>/dev/null || echo "user tyr findes allerede"
$PG/createdb -O tyr tyr

# Kør migrations
alembic upgrade head
```

### 5. Frontend setup

```bash
# Root + workspace install
npm install

# Build production bundle
cd frontend && npm install && npm run build && cd ..
```

### 6. Installer LM Studio (LLM)

1. Download fra <https://lmstudio.ai>
2. Åbn LM Studio → **Search** fanen
3. Søg `openai/gpt-oss-20b` og download (10-15 GB)
4. **Developer** fanen → **Start Server** (port 1234)
5. Indlæs også embedding-model: `text-embedding-nomic-embed-text-v1.5`

### 7. Start Bifrost

```bash
./scripts/start_tyr.sh
```

Åbn `http://localhost:8090` i browser.

### 8. (Valgfri) Backup-automation

```bash
# Kopiér scripts uden for Desktop-sandbox
mkdir -p ~/.bifrost/scripts
cp scripts/backup.sh scripts/backup-restore-test.sh ~/.bifrost/scripts/
chmod +x ~/.bifrost/scripts/*.sh

# Installer LaunchAgent
cp scripts/com.bifrost.backup.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.bifrost.backup.plist

# Manuel macOS-permission (kritisk!)
# System Settings → Privacy & Security → Full Disk Access
# Tilføj /opt/homebrew/bin/bash (eller /bin/bash)
```

### 9. (Valgfri) Tailscale for ekstern adgang

```bash
brew install tailscale
sudo brew services start tailscale
sudo tailscale up
# Få din Tailscale-IP: tailscale ip -4
# Åbn http://<tailscale-ip>:8090 fra iPhone/anden enhed
```

## Migrér data fra eksisterende Mac

### På GAMMEL Mac

```bash
# Kør backup
~/.bifrost/scripts/backup.sh

# Output: ~/Backups/Bifrost/bifrost-YYYY-MM-DD/
# Indeholder: db.dump, data.tar.gz, manifest.json
```

### Kopiér til ny Mac

```bash
# Option A: AirDrop hele bifrost-YYYY-MM-DD-mappen
# Option B: scp
scp -r ~/Backups/Bifrost/bifrost-2026-05-11 \
  ny-mac.local:/Users/parthee/Backups/Bifrost/

# Option C: USB-disk
cp -r ~/Backups/Bifrost/bifrost-2026-05-11 /Volumes/MyDisk/
```

### På NY Mac (efter fresh install ovenfor)

```bash
cd /path/to/bifrost
source venv/bin/activate

# Stop Bifrost først hvis den kører
./scripts/stop_tyr.sh

# Restore database
PG=/opt/homebrew/opt/postgresql@16/bin
$PG/pg_restore \
  --dbname=postgresql://tyr@localhost:5432/tyr \
  --no-owner --no-acl \
  --clean --if-exists \
  ~/Backups/Bifrost/bifrost-2026-05-11/db.dump

# Restore data/-mappen (overwrite eksisterende)
tar -xzf ~/Backups/Bifrost/bifrost-2026-05-11/data.tar.gz \
  -C .

# Verificer
python -c "
from src.database.connection import SessionLocal
from src.database.cases import Case
db = SessionLocal()
print(f'Cases: {db.query(Case).count()}')
"

# Start igen
./scripts/start_tyr.sh
```

## Verifikation

Når du har startet appen, tjek at alt virker:

```bash
# Backend health
curl http://localhost:8001/health

# Frontend
open http://localhost:8090

# LLM-forbindelse
curl http://localhost:8001/api/v3/admin/llm-health

# Database
curl http://localhost:8001/api/health/database

# Config (visér missing env-vars)
curl http://localhost:8001/api/v3/admin/config
```

## Troubleshooting

### "PostgreSQL connection refused"
```bash
brew services list | grep postgres
brew services restart postgresql@16
```

### "LM Studio: connection refused"
- Åbn LM Studio → **Developer** → bekræft "Server running" + port 1234
- Tjek model er loaded (ikke bare downloaded)

### "Frontend viser blank side"
- Tjek browser console (F12)
- Rebuild: `cd frontend && npm run build`
- Restart: `./scripts/stop_tyr.sh && ./scripts/start_tyr.sh`

### "Alembic ERROR: Can't locate revision"
```bash
# Migration history kan være out of sync
alembic stamp head  # marker som applied uden at køre
alembic upgrade head
```

### "Backup-LaunchAgent fejler tar"
Det er macOS sandbox. Giv `/bin/bash` Full Disk Access manuelt:
**System Settings → Privacy & Security → Full Disk Access → +**

## Hvad er IKKE i git og skal genskabes manuelt

- `.env` (sensitive credentials)
- `~/Backups/Bifrost/` (database-backups)
- `node_modules/`, `venv/`, `frontend/build/` (kør npm/pip install + build)
- LM Studio + downloaded modeller
- LaunchAgent (kopiér manuelt fra `scripts/com.bifrost.backup.plist`)
- macOS Full Disk Access til bash

## Demo til eksterne stakeholders

Hvis du vil vise Bifrost til nogen uden for kommunens netværk (KL, jurist,
anden kommune): brug Tailscale i stedet for at deploye til cloud.

```bash
# Inviter en specifik person til din Tailscale-tailnet
tailscale invite <email>
# De installerer Tailscale på deres enhed og får adgang til:
# http://<din-tailscale-ip>:8090
```

Fordele frem for cloud-deploy:
- Data forbliver i kommunens kontrol (ingen ny DPIA krævet)
- Samme produktion-instans, ingen drift mellem staging/prod
- $0/måned
- Du kan tilbagetrække invite når demo er slut
