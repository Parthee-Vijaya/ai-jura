#!/usr/bin/env python
"""Verify hash-chain integrity for Bifrost audit-tables.

Exit code:
  0  — all chains valid
  1  — at least one chain broken (broken_at printed)
  2  — error (DB-connection, missing schema, etc.)

Usage:
    python scripts/verify_audit_chain.py
    python scripts/verify_audit_chain.py --table v3_assessment_log
    python scripts/verify_audit_chain.py --json   # JSON-output for cron-pipe

Designed to be run daily by cron. Output is human-readable by default;
add --json for machine-parseable output.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, UTC

# Tilføj projekt-root til sys.path så vi kan importere src/* uden at
# scriptet kun kan køres fra projektrod
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Bifrost audit hash-chains")
    parser.add_argument(
        "--table",
        choices=["all", "v3_assessment_log", "audit_access_log"],
        default="all",
        help="Hvilken tabel der skal verificeres (default: all)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output struktureret JSON i stedet for prose",
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Beregn hash-chain for eksisterende entries der mangler — kør én gang efter migration",
    )
    args = parser.parse_args()

    try:
        from src.database.connection import SessionLocal
        from src.services.audit_hash_chain import (
            backfill_chain, verify_chain, _ALLOWED_TABLES,
        )
    except Exception as exc:
        print(f"FATAL: kan ikke importere moduler: {exc}", file=sys.stderr)
        return 2

    if args.table == "all":
        tables = list(_ALLOWED_TABLES.keys())
    else:
        tables = [args.table]

    db = SessionLocal()
    results = {}
    try:
        if args.backfill:
            for t in tables:
                order_col = "accessed_at" if t == "audit_access_log" else "created_at"
                bres = backfill_chain(db, t, order_column=order_col)
                print(
                    f"Backfilled {t}: {bres['backfilled']} new, "
                    f"{bres['skipped']} skipped, head={bres['chain_head'][:16] + '…' if bres['chain_head'] else 'EMPTY'}"
                )
            print()
        for t in tables:
            order_col = "accessed_at" if t == "audit_access_log" else "created_at"
            res = verify_chain(db, t, order_column=order_col)
            results[t] = res.to_dict()
    except Exception as exc:
        print(f"FATAL: verify_chain crashed: {exc}", file=sys.stderr)
        return 2
    finally:
        db.close()

    all_valid = all(r["valid"] for r in results.values())

    if args.json:
        out = {
            "generated_at": datetime.now(UTC).isoformat(),
            "all_valid": all_valid,
            "tables": results,
        }
        print(json.dumps(out, indent=2))
    else:
        for table, res in results.items():
            status = "✓ VALID" if res["valid"] else "✗ BROKEN"
            print(f"{status}  {table}")
            print(f"  entries_checked: {res['entries_checked']}")
            if res.get("chain_head"):
                print(f"  chain_head: {res['chain_head'][:16]}…")
            if res.get("broken_at"):
                print(f"  BROKEN AT: {json.dumps(res['broken_at'], indent=4)}")
            if res.get("errors"):
                for err in res["errors"]:
                    print(f"  ERROR: {err}")
            print()

        if all_valid:
            print("✓ Alle audit-chains er intakte.")
        else:
            print("✗ MINDST ÉN audit-chain er kompromitteret. Eskalér til DPO.")

    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())
