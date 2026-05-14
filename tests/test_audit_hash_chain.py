"""Tests for src.services.audit_hash_chain — tamper-evidens.

Test-fokus:
  - canonical_json: deterministic key-ordering
  - compute_entry_hash: stabil + ændring i payload bryder hash
  - Chain-state: prev_hash + entry_hash matcher kæden
"""

import pytest

from src.services.audit_hash_chain import (
    GENESIS_HASH,
    canonical_json,
    compute_entry_hash,
)


# ---- canonical_json -----------------------------------------------------


class TestCanonicalJson:
    def test_sorts_keys(self):
        a = canonical_json({"b": 1, "a": 2})
        b = canonical_json({"a": 2, "b": 1})
        assert a == b

    def test_preserves_unicode(self):
        out = canonical_json({"name": "Bjørn"})
        assert "Bjørn" in out

    def test_nested_dicts(self):
        a = canonical_json({"outer": {"b": 1, "a": 2}})
        b = canonical_json({"outer": {"a": 2, "b": 1}})
        assert a == b

    def test_datetime_serializes(self):
        from datetime import datetime
        # default=str path
        out = canonical_json({"ts": datetime(2026, 5, 14, 12, 0)})
        assert "2026-05-14" in out


# ---- compute_entry_hash -------------------------------------------------


class TestComputeEntryHash:
    def test_stable_for_same_input(self):
        h1 = compute_entry_hash(None, {"action": "read", "id": 1})
        h2 = compute_entry_hash(None, {"action": "read", "id": 1})
        assert h1 == h2

    def test_changes_with_payload(self):
        h1 = compute_entry_hash(None, {"action": "read"})
        h2 = compute_entry_hash(None, {"action": "write"})
        assert h1 != h2

    def test_changes_with_prev_hash(self):
        h1 = compute_entry_hash(None, {"x": 1})
        h2 = compute_entry_hash("abc", {"x": 1})
        assert h1 != h2

    def test_genesis_when_prev_is_none(self):
        # None and genesis-hash should produce same result (defensive)
        h_none = compute_entry_hash(None, {"x": 1})
        h_genesis = compute_entry_hash(GENESIS_HASH, {"x": 1})
        assert h_none == h_genesis

    def test_hash_is_64_hex(self):
        h = compute_entry_hash(None, {"x": 1})
        assert len(h) == 64
        # All hex characters
        int(h, 16)  # raises if non-hex

    def test_dict_key_order_doesnt_matter(self):
        h1 = compute_entry_hash(None, {"a": 1, "b": 2})
        h2 = compute_entry_hash(None, {"b": 2, "a": 1})
        assert h1 == h2

    def test_chain_simulation(self):
        """Simulér en kæde af 3 entries og verificér hver leds hash."""
        payload1 = {"id": 1, "action": "create"}
        h1 = compute_entry_hash(None, payload1)

        payload2 = {"id": 2, "action": "update"}
        h2 = compute_entry_hash(h1, payload2)

        payload3 = {"id": 3, "action": "delete"}
        h3 = compute_entry_hash(h2, payload3)

        # Recompute med samme input → samme hash
        assert h1 == compute_entry_hash(None, payload1)
        assert h2 == compute_entry_hash(h1, payload2)
        assert h3 == compute_entry_hash(h2, payload3)

        # Ændring i midten bryder kæden
        tampered_payload2 = {"id": 2, "action": "update_TAMPERED"}
        h2_tampered = compute_entry_hash(h1, tampered_payload2)
        assert h2 != h2_tampered
        # h3 ville være beregnet fra h2 — hvis vi forsøger at validere h3
        # med h2_tampered, vil det fejle
        h3_from_tampered = compute_entry_hash(h2_tampered, payload3)
        assert h3 != h3_from_tampered


# ---- GENESIS_HASH -------------------------------------------------------


def test_genesis_is_64_zeros():
    assert GENESIS_HASH == "0" * 64


# ---- ChainVerifyResult --------------------------------------------------


def test_chain_verify_result_to_dict():
    from src.services.audit_hash_chain import ChainVerifyResult
    r = ChainVerifyResult(table="t", valid=True, entries_checked=5, chain_head="abc")
    d = r.to_dict()
    assert d["table"] == "t"
    assert d["valid"] is True
    assert d["entries_checked"] == 5
    assert d["chain_head"] == "abc"
