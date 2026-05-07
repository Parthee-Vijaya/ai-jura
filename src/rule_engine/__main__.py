"""CLI entry point for the rule engine.

Usage:
    python -m src.rule_engine validate [rules_dir]
    python -m src.rule_engine list [rules_dir]

Both commands default `rules_dir` to "rules".

Exit codes:
    0  success / all rules valid
    1  one or more rules failed validation
    2  CLI usage error
"""

from __future__ import annotations

import sys
from pathlib import Path

from src.rule_engine.loader import RuleLoader


def _cmd_validate(rules_dir: str) -> int:
    loader = RuleLoader(rules_dir)
    result = loader.load_all(raise_on_error=False)
    print(f"Loaded {len(result.rules)} rule(s) from {Path(rules_dir).resolve()}")
    if result.errors:
        print(f"\n{len(result.errors)} error(s):", file=sys.stderr)
        for err in result.errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    for rule in result.rules:
        print(f"  ok  {rule.id}  ({rule.kilde.lov} {rule.kilde.artikel})")
    return 0


def _cmd_list(rules_dir: str) -> int:
    loader = RuleLoader(rules_dir)
    result = loader.load_all(raise_on_error=False)
    if result.errors:
        for err in result.errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1
    for rule in result.rules:
        print(f"{rule.id}")
        print(f"  lov:        {rule.kilde.lov}")
        print(f"  artikel:    {rule.kilde.artikel}")
        print(f"  url:        {rule.kilde.url}")
        print(f"  verificeret:{rule.kilde.sidst_verificeret}")
        print(f"  predikater: {len(rule.predikater)}")
        print()
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__, file=sys.stderr)
        return 2
    cmd = argv[1]
    rules_dir = argv[2] if len(argv) > 2 else "rules"
    if cmd == "validate":
        return _cmd_validate(rules_dir)
    if cmd == "list":
        return _cmd_list(rules_dir)
    print(f"Unknown command: {cmd}", file=sys.stderr)
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
