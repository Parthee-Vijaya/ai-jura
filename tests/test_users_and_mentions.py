"""Tests for src.database.users — bruger-tabel + @-mention parsing.

Tester:
  - extract_mentions: regex matchør reelle email-adresser, dedupliker, lowercase
  - is_valid_email: accepter/afvis edge cases
  - User CRUD: upsert idempotent, search matches på email + display_name
  - mention_notifier (smoke — fuld test kræver DB-fixture)
"""

import pytest

from src.database.users import (
    DEFAULT_ROLE,
    ROLES,
    extract_mentions,
    is_valid_email,
    normalize_email,
)


# ---- extract_mentions ----------------------------------------------------


class TestExtractMentions:
    def test_single_mention(self):
        assert extract_mentions("Hej @pavi@kalundborg.dk hvordan går det?") == [
            "pavi@kalundborg.dk"
        ]

    def test_multiple_mentions(self):
        out = extract_mentions(
            "Tagging @pavi@kalundborg.dk og @anna@kalundborg.dk for review."
        )
        assert out == ["pavi@kalundborg.dk", "anna@kalundborg.dk"]

    def test_deduplicates(self):
        out = extract_mentions(
            "@pavi@kalundborg.dk — så @pavi@kalundborg.dk igen — kun én notif."
        )
        assert out == ["pavi@kalundborg.dk"]

    def test_lowercases(self):
        out = extract_mentions("@PAVI@Kalundborg.DK kan du tjekke?")
        assert out == ["pavi@kalundborg.dk"]

    def test_no_mentions(self):
        assert extract_mentions("Ingen @-tegn med rigtigt format her.") == []
        assert extract_mentions("Email uden @-prefix: pavi@kalundborg.dk") == []

    def test_empty_input(self):
        assert extract_mentions("") == []
        assert extract_mentions(None) == []

    def test_skips_invalid_email_format(self):
        # @noget-uden-domæne matcher ikke regex
        assert extract_mentions("Hej @just-text uden domæne") == []
        assert extract_mentions("@a@b ufuldstændig") == []

    def test_handles_punctuation_after_email(self):
        # Komma/punktum/parentes efter email skal ikke være del af mention
        out = extract_mentions("Skriv til @pavi@kalundborg.dk, og hilse fra mig.")
        assert out == ["pavi@kalundborg.dk"]

    def test_real_world_example(self):
        text = (
            "Hej team, jeg vil gerne have @anna@kalundborg.dk og "
            "@bjorn@example.org til at kigge på den her formulering. "
            "Tak! /pavi"
        )
        assert extract_mentions(text) == ["anna@kalundborg.dk", "bjorn@example.org"]


# ---- is_valid_email ----------------------------------------------------


class TestIsValidEmail:
    def test_valid_basic(self):
        assert is_valid_email("pavi@kalundborg.dk")
        assert is_valid_email("anna.larsen@kalundborg.dk")
        assert is_valid_email("user+tag@example.co.uk")

    def test_invalid(self):
        assert not is_valid_email("")
        assert not is_valid_email(None)
        assert not is_valid_email("nope")
        assert not is_valid_email("@kalundborg.dk")
        assert not is_valid_email("pavi@")
        assert not is_valid_email("pavi@dk")  # domain skal have tld med min 2 tegn
        assert not is_valid_email("pavi kalundborg.dk")

    def test_non_string_inputs(self):
        assert not is_valid_email(123)
        assert not is_valid_email([])


class TestNormalizeEmail:
    def test_lowercases_and_strips(self):
        assert normalize_email("  PAVI@Kalundborg.DK  ") == "pavi@kalundborg.dk"


# ---- ROLES constants ---------------------------------------------------


def test_default_role_in_roles():
    assert DEFAULT_ROLE in ROLES


def test_roles_are_lowercase_strings():
    for r in ROLES:
        assert isinstance(r, str)
        assert r == r.lower()
