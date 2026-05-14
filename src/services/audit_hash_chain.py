"""Tamper-proof hash-chain over audit-tabeller.

Hver audit-entry får et `entry_hash = sha256(prev_hash + canonical_json(payload))`
hvor `prev_hash` er forrige entrys hash i kronologisk rækkefølge.

Det betyder:
  - Ingen middel-entry kan ændres uden at bryde kæden
  - Sletning detekteres (manglende entry → prev_hash mismatch)
  - Tilføjelse af falske entries i historikken bryder kæden ved næste verify

Dette er IKKE en kryptografisk garanti mod en angriber med DB-adgang —
de kan i princippet recompute hele kæden. Men det dokumenterer integritet
hvis kæden valideres regelmæssigt af et eksternt system.

For ægte tamper-evidens: tag chain-head + entry_hash som "ankerpunkt"
periodisk (fx daglig) og lagre dem på et separat system (S3 WORM,
GitHub-commit, blockchain hvis paranoid).

Brug:

    from src.services.audit_hash_chain import compute_entry_hash, get_chain_head

    # Ved skrivning af ny entry:
    prev_hash = get_chain_head(session, "v3_assessment_log")
    entry.prev_hash = prev_hash
    entry.entry_hash = compute_entry_hash(prev_hash, canonical_payload)

    # Ved verifikation:
    from src.services.audit_hash_chain import verify_chain
    result = verify_chain(session, "v3_assessment_log")
    if not result.valid:
        alert(result.broken_at)
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger("bifrost.audit_chain")


# Genesis-hash — den første entry refererer til denne værdi. Konstant så
# vi kan detektere "kæden er aldrig blevet manipuleret fra start".
GENESIS_HASH = "0" * 64


@dataclass
class ChainVerifyResult:
    table: str
    valid: bool
    entries_checked: int = 0
    broken_at: Optional[dict] = None  # {id, expected_hash, actual_hash}
    errors: list[str] = field(default_factory=list)
    chain_head: Optional[str] = None  # Sidste entrys hash (eller GENESIS hvis tom)

    def to_dict(self) -> dict:
        return {
            "table": self.table,
            "valid": self.valid,
            "entries_checked": self.entries_checked,
            "broken_at": self.broken_at,
            "errors": self.errors,
            "chain_head": self.chain_head,
        }


def canonical_json(payload: Any) -> str:
    """Deterministisk JSON-encoding så samme dict → samme hash.

    Bruger sort_keys=True + ensure_ascii=False så Unicode bevares.
    Floats: standard repr (kan være pålideligt nok for audit men ikke
    crypto-grade — accepteret kompromis).
    """
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)


def compute_entry_hash(prev_hash: Optional[str], payload: Any) -> str:
    """SHA-256 over (prev_hash || canonical_json(payload)).

    prev_hash er hex-streng (64 tegn) eller None for første entry.
    """
    prev = prev_hash if prev_hash else GENESIS_HASH
    data = (prev + "|" + canonical_json(payload)).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def get_chain_head(
    session: Session, table: str, *, order_column: str = "created_at"
) -> Optional[str]:
    """Returnér entry_hash for seneste entry — eller None hvis tabel tom.

    Bruger raw SQL for at undgå ORM-imports (kæden skal kunne verificeres
    på tværs af modeller).
    """
    if table not in _ALLOWED_TABLES:
        raise ValueError(f"Tabel {table!r} ikke i whitelist: {_ALLOWED_TABLES}")
    sql = text(
        f"SELECT entry_hash FROM {table} ORDER BY {order_column} DESC, id DESC LIMIT 1"
    )
    row = session.execute(sql).fetchone()
    return row[0] if row and row[0] else None


def backfill_chain(
    session: Session,
    table: str,
    *,
    order_column: str = "created_at",
) -> dict:
    """Beregn og persistér hash-chain for alle entries der mangler entry_hash.

    Bruges efter migration f6e9d234a1b3 for at "ankre" eksisterende audit-
    data ind i kæden. Skal kun køres ÉN gang efter migration — efterfølgende
    skal alle nye entries få sat hash i save-tid.

    Idempotent: hvis en entry allerede har entry_hash bliver den IKKE
    overskrevet (forhindrer ved-uheld-rebuild der ville maskere tampering).

    Returns:
        dict med backfilled (count), skipped (count), chain_head (str)
    """
    if table not in _ALLOWED_TABLES:
        raise ValueError(f"Tabel {table!r} ikke i whitelist")

    columns_spec = _ALLOWED_TABLES[table]
    payload_cols = columns_spec["payload_cols"]
    select_cols = ["id", "prev_hash", "entry_hash"] + payload_cols

    sql = text(
        f"SELECT {', '.join(select_cols)} FROM {table} "
        f"ORDER BY {order_column} ASC, id ASC"
    )
    rows = session.execute(sql).fetchall()

    backfilled = 0
    skipped = 0
    last_hash = None

    for row in rows:
        row_dict = dict(zip(select_cols, row))
        entry_id = row_dict["id"]
        existing_hash = row_dict["entry_hash"]

        if existing_hash:
            # Allerede sat — verificér at den passer til kæden og fortsæt
            last_hash = existing_hash
            skipped += 1
            continue

        payload = {col: row_dict[col] for col in payload_cols}
        new_hash = compute_entry_hash(last_hash, payload)
        # Update via raw SQL — vi rammer en kolonne på ID
        upd_sql = text(
            f"UPDATE {table} SET prev_hash = :prev, entry_hash = :curr WHERE id = :id"
        )
        session.execute(
            upd_sql,
            {"prev": last_hash, "curr": new_hash, "id": entry_id},
        )
        last_hash = new_hash
        backfilled += 1

    session.commit()
    return {
        "table": table,
        "backfilled": backfilled,
        "skipped": skipped,
        "chain_head": last_hash,
    }


def verify_chain(
    session: Session,
    table: str,
    *,
    payload_columns: list[str] = None,
    order_column: str = "created_at",
) -> ChainVerifyResult:
    """Iterér gennem alle entries i kronologisk rækkefølge og verificér hash.

    payload_columns angiver hvilke kolonner der indgår i hash'en (udover
    selve entrien). Default = alle ikke-hash, ikke-id-kolonner.

    Returnerer ChainVerifyResult med valid=True hvis alle hashes passer.
    Stopper ved første brud og rapporterer broken_at.
    """
    if table not in _ALLOWED_TABLES:
        return ChainVerifyResult(
            table=table,
            valid=False,
            errors=[f"Tabel {table!r} ikke i whitelist"],
        )

    # Hent alle entries i kronologisk rækkefølge
    columns_spec = _ALLOWED_TABLES[table]
    payload_cols = payload_columns or columns_spec["payload_cols"]
    select_cols = ["id", "prev_hash", "entry_hash"] + payload_cols

    sql = text(
        f"SELECT {', '.join(select_cols)} FROM {table} "
        f"ORDER BY {order_column} ASC, id ASC"
    )
    rows = session.execute(sql).fetchall()

    if not rows:
        return ChainVerifyResult(
            table=table,
            valid=True,
            entries_checked=0,
            chain_head=None,
        )

    expected_prev = None
    last_hash = None
    for i, row in enumerate(rows):
        row_dict = dict(zip(select_cols, row))
        entry_id = row_dict["id"]
        stored_prev = row_dict["prev_hash"]
        stored_hash = row_dict["entry_hash"]

        # Build payload from declared columns
        payload = {col: row_dict[col] for col in payload_cols}

        # Tjek prev_hash matcher forrige entrys hash
        expected_prev_str = expected_prev if expected_prev else GENESIS_HASH
        actual_prev_str = stored_prev if stored_prev else GENESIS_HASH
        if expected_prev_str != actual_prev_str:
            return ChainVerifyResult(
                table=table,
                valid=False,
                entries_checked=i,
                broken_at={
                    "id": str(entry_id),
                    "issue": "prev_hash mismatch",
                    "expected": expected_prev_str,
                    "actual": actual_prev_str,
                    "position": i,
                },
                chain_head=last_hash,
            )

        # Recompute entry_hash og sammenlign
        computed = compute_entry_hash(stored_prev, payload)
        if computed != stored_hash:
            return ChainVerifyResult(
                table=table,
                valid=False,
                entries_checked=i,
                broken_at={
                    "id": str(entry_id),
                    "issue": "entry_hash mismatch",
                    "expected": computed,
                    "actual": stored_hash,
                    "position": i,
                },
                chain_head=last_hash,
            )

        expected_prev = stored_hash
        last_hash = stored_hash

    return ChainVerifyResult(
        table=table,
        valid=True,
        entries_checked=len(rows),
        chain_head=last_hash,
    )


# Whitelist af tabeller + hvilke kolonner der indgår i hash-payload.
# 'payload_cols' = de kolonner der må påvirke hash-værdien.
# Ekskluderer normalt id (auto-genereret) og hash-kolonnerne selv.
_ALLOWED_TABLES = {
    "v3_assessment_log": {
        "payload_cols": [
            "created_at",
            "case_id",
            "user_id",
            "rule_engine_version",
            "aggregate_status",
            "rules_loaded",
            "note",
            # JSON-payloads skal også med, men de er store. Vi accepterer
            # at omfanget er stort — det er audit-trail.
            "request_payload",
            "response_payload",
        ],
    },
    "audit_access_log": {
        "payload_cols": [
            "accessed_at",
            "target_type",
            "target_id",
            "actor",
            "actor_ip",
            "action",
            "request_id",
        ],
    },
}
