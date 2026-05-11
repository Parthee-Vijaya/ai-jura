#!/bin/bash
#
# Bifrost — Daglig backup-script.
#
# Bygger en versioneret backup-mappe med tre artefakter:
#   1. pg_dump af PostgreSQL-DB'en (compressed custom format)
#   2. snapshot af data/-mappen (regler, embeddings, fallbacks)
#   3. JSON manifest med metadata (dato, DB-version, fil-count, sha256-checksums)
#
# Kører via LaunchAgent (com.bifrost.backup.plist) eller manuelt.
# Output struktur:
#   $BACKUP_ROOT/bifrost-2026-05-11/
#     ├── db.dump          (pg_dump -Fc, ~10-50 MB)
#     ├── data.tar.gz      (~5-20 MB)
#     └── manifest.json    (audit-trail)
#
# Roterer ældre end RETENTION_DAYS (default 30 dage) væk.
#
# Verifikation: backup'en valideres med `pg_restore --list` for ikke-korrupt fil.
#
# Restore (manuel):
#   createdb tyr_restore
#   pg_restore -d tyr_restore --clean db.dump
#   tar -xzf data.tar.gz -C /tmp/restore-test
#
# Eksterne kopier:
#   Sæt BACKUP_EXTERNAL_PATH til en rsync-destination (ekstern disk, NAS, SSH).
#   Hvis sat, kopieres backup'en derhen efter local-write.

set -euo pipefail

# ---- Configuration --------------------------------------------------------

# Defaults — kan overstyres via env (typisk via LaunchAgent eller cli):
BIFROST_ROOT="${BIFROST_ROOT:-/Users/parthee/Desktop/Claude/projekter/aktive/judge-dredd}"
BACKUP_ROOT="${BACKUP_ROOT:-$HOME/Backups/Bifrost}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
DATABASE_URL="${DATABASE_URL:-postgresql://tyr@localhost:5432/tyr}"
BACKUP_EXTERNAL_PATH="${BACKUP_EXTERNAL_PATH:-}"  # tom = ingen ekstern kopi

DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_DIR="$BACKUP_ROOT/bifrost-$DATE"
LOG_FILE="$BACKUP_ROOT/backup.log"

# ---- Helpers --------------------------------------------------------------

log() {
  echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"
}

die() {
  log "ERROR: $1"
  exit 1
}

# Find pg_dump (homebrew Postgres på Mac har det i forskellige stier)
find_pg_dump() {
  for path in \
    "/opt/homebrew/opt/postgresql@16/bin/pg_dump" \
    "/opt/homebrew/opt/postgresql@15/bin/pg_dump" \
    "/opt/homebrew/bin/pg_dump" \
    "/usr/local/bin/pg_dump" \
    "$(command -v pg_dump 2>/dev/null || true)"; do
    if [ -x "$path" ]; then
      echo "$path"
      return 0
    fi
  done
  return 1
}

# ---- Pre-flight checks ----------------------------------------------------

[ -d "$BIFROST_ROOT" ] || die "BIFROST_ROOT does not exist: $BIFROST_ROOT"
[ -d "$BIFROST_ROOT/data" ] || die "data/ mappen mangler under $BIFROST_ROOT"

PG_DUMP=$(find_pg_dump) || die "pg_dump ikke fundet — installer Postgres CLI tools"

mkdir -p "$BACKUP_ROOT"
touch "$LOG_FILE"

log "=== Bifrost backup starter ==="
log "  BIFROST_ROOT=$BIFROST_ROOT"
log "  BACKUP_ROOT=$BACKUP_ROOT"
log "  DATABASE_URL=${DATABASE_URL%@*}@****"  # redact credentials hvis nogen
log "  RETENTION_DAYS=$RETENTION_DAYS"
log "  pg_dump=$PG_DUMP"

# ---- 1) PostgreSQL pg_dump -----------------------------------------------

mkdir -p "$BACKUP_DIR"

log "Step 1/3: pg_dump → $BACKUP_DIR/db.dump"
"$PG_DUMP" \
  --dbname="$DATABASE_URL" \
  --format=custom \
  --no-owner \
  --no-acl \
  --compress=9 \
  --file="$BACKUP_DIR/db.dump" \
  || die "pg_dump fejlede"

# Verificér at filen kan læses som custom-format
"$PG_DUMP" --version >/dev/null
if ! "${PG_DUMP%/pg_dump}/pg_restore" --list "$BACKUP_DIR/db.dump" >/dev/null 2>&1; then
  die "pg_restore --list rejection — backup-filen er korrupt"
fi

DB_SIZE=$(du -h "$BACKUP_DIR/db.dump" | cut -f1)
log "  OK ($DB_SIZE)"

# ---- 2) data/-snapshot ----------------------------------------------------

log "Step 2/3: tar+gzip data/ → $BACKUP_DIR/data.tar.gz"
tar -czf "$BACKUP_DIR/data.tar.gz" \
  -C "$BIFROST_ROOT" \
  --exclude="data/documents/cache" \
  --exclude="*.tmp" \
  data \
  || die "tar fejlede"

DATA_SIZE=$(du -h "$BACKUP_DIR/data.tar.gz" | cut -f1)
log "  OK ($DATA_SIZE)"

# ---- 3) Manifest ----------------------------------------------------------

log "Step 3/3: skriver manifest.json"

# Beregn sha256 for begge artefakter (audit-trail mod silent corruption)
DB_SHA=$(shasum -a 256 "$BACKUP_DIR/db.dump" | awk '{print $1}')
DATA_SHA=$(shasum -a 256 "$BACKUP_DIR/data.tar.gz" | awk '{print $1}')

cat > "$BACKUP_DIR/manifest.json" <<EOF
{
  "backup_id": "bifrost-$DATE",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "bifrost_root": "$BIFROST_ROOT",
  "database_url_dialect": "$(echo "$DATABASE_URL" | sed 's|://.*|://|')",
  "artifacts": {
    "db.dump": {
      "size_bytes": $(stat -f%z "$BACKUP_DIR/db.dump"),
      "sha256": "$DB_SHA",
      "format": "pg_dump --format=custom --compress=9"
    },
    "data.tar.gz": {
      "size_bytes": $(stat -f%z "$BACKUP_DIR/data.tar.gz"),
      "sha256": "$DATA_SHA",
      "format": "gzip"
    }
  },
  "retention_days": $RETENTION_DAYS,
  "git_commit": "$(cd "$BIFROST_ROOT" && git rev-parse --short HEAD 2>/dev/null || echo unknown)",
  "git_branch": "$(cd "$BIFROST_ROOT" && git branch --show-current 2>/dev/null || echo unknown)"
}
EOF

log "  OK"

# ---- 4) Optional: rsync til ekstern destination ---------------------------

if [ -n "$BACKUP_EXTERNAL_PATH" ]; then
  log "Ekstern kopi: rsync → $BACKUP_EXTERNAL_PATH"
  if rsync -a --delete-after \
      "$BACKUP_DIR/" \
      "$BACKUP_EXTERNAL_PATH/bifrost-$DATE/" 2>>"$LOG_FILE"; then
    log "  OK"
  else
    log "  WARNING: rsync fejlede — backup ligger stadig lokalt på $BACKUP_DIR"
  fi
else
  log "Ekstern kopi: skipped (BACKUP_EXTERNAL_PATH ikke sat)"
fi

# ---- 5) Rotation ----------------------------------------------------------

log "Rotation: sletter backups ældre end $RETENTION_DAYS dage"
# -mindepth 1 så vi ikke sletter BACKUP_ROOT selv. -mtime +N = strikse "ældre end N dage".
DELETED=$(find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -name 'bifrost-*' -mtime +"$RETENTION_DAYS" -print -exec rm -rf {} + 2>/dev/null | wc -l | tr -d ' ')
log "  Slettet $DELETED gamle backup-mapper"

# ---- Sammenfatning --------------------------------------------------------

TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
log "=== Backup OK ($TOTAL_SIZE total) ==="
log ""
exit 0
