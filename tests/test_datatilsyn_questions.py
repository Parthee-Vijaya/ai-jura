"""Tests for den Datatilsyn-forankrede opfølgnings-motor."""

import pytest

from src.services.risk_assessment.models import (
    DataKategori,
    SystemFacts,
    Underdatabehandler,
)
from src.services.risk_assessment.datatilsyn_questions import (
    DATATILSYN_ELEMENTER,
    build_datatilsyn_questions,
    build_dynamic_questions,
    llm_followup_questions,
)
from src.services.risk_assessment.clarifying import apply_answers


class TestDeterministiskeSpoergsmaal:
    def test_basis_spoergsmaal_stilles(self):
        # Tomme fakta → kerne-DPIA-spørgsmål skal stilles
        qs = build_datatilsyn_questions(SystemFacts(systemnavn="X"))
        keys = [q.key for q in qs]
        assert "dt_automatiske_afgoerelser" in keys   # art. 22 — altid
        assert "dt_noedvendighed" in keys             # art. 35(7)(b) — altid
        assert "dt_modtagere" in keys                 # systematisk beskrivelse

    def test_alle_keys_har_dt_praefiks(self):
        qs = build_datatilsyn_questions(SystemFacts(persondata_kategorier=[DataKategori.ALMINDELIGE]))
        assert all(q.key.startswith("dt_") for q in qs)

    def test_reason_naevner_datatilsyn_skabelon(self):
        qs = build_datatilsyn_questions(SystemFacts())
        assert all("Datatilsynets skabelon" in q.reason for q in qs)

    def test_foelsom_undtagelse_kun_ved_foelsomme(self):
        uden = build_datatilsyn_questions(SystemFacts(persondata_kategorier=[DataKategori.ALMINDELIGE]))
        assert "dt_foelsom_undtagelse" not in [q.key for q in uden]
        med = build_datatilsyn_questions(SystemFacts(persondata_kategorier=[DataKategori.CPR]))
        assert "dt_foelsom_undtagelse" in [q.key for q in med]

    def test_tredjeland_kun_udenfor_eu(self):
        eu = build_datatilsyn_questions(SystemFacts(hosting_lokation="Microsoft Azure EU-region"))
        assert "dt_tredjeland" not in [q.key for q in eu]
        usa = build_datatilsyn_questions(SystemFacts(
            underdatabehandlere=[Underdatabehandler(navn="OpenAI", land="USA", rolle="inference")]
        ))
        assert "dt_tredjeland" in [q.key for q in usa]

    def test_saarbare_kun_naar_borgere_naevnt(self):
        uden = build_datatilsyn_questions(SystemFacts(registrerede=["medarbejdere"]))
        assert "dt_saarbare" not in [q.key for q in uden]
        med = build_datatilsyn_questions(SystemFacts(registrerede=["borgere", "børn i dagtilbud"]))
        assert "dt_saarbare" in [q.key for q in med]

    def test_opbevaring_skjules_naar_kendt(self):
        kendt = build_datatilsyn_questions(SystemFacts(retention_efter_ophoer="Slettes efter 90 dage"))
        assert "dt_opbevaring" not in [q.key for q in kendt]
        ukendt = build_datatilsyn_questions(SystemFacts())
        assert "dt_opbevaring" in [q.key for q in ukendt]

    def test_behandlingsgrundlag_skjules_naar_hjemmel_kendt(self):
        kendt = build_datatilsyn_questions(SystemFacts(
            national_lovhjemmel="Serviceloven § 11",
            persondata_kategorier=[DataKategori.ALMINDELIGE],
        ))
        assert "dt_behandlingsgrundlag" not in [q.key for q in kendt]


class TestApplyAnswers:
    def test_dt_svar_samles_i_datatilsyn_svar(self):
        f = apply_answers(SystemFacts(), {
            "dt_automatiske_afgoerelser": "Ja, helt automatisk",
            "dt_modtagere": ["Til leverandøren som databehandler", "Til andre myndigheder"],
            "scope": "Begge",  # ikke-dt → ignoreres her
        })
        assert f.datatilsyn_svar["automatiske_afgoerelser"] == "Ja, helt automatisk"
        assert "leverandøren" in f.datatilsyn_svar["modtagere"]
        assert "andre myndigheder" in f.datatilsyn_svar["modtagere"]
        assert "scope" not in f.datatilsyn_svar

    def test_tomme_dt_svar_ignoreres(self):
        f = apply_answers(SystemFacts(), {"dt_modtagere": "", "dt_noedvendighed": []})
        assert f.datatilsyn_svar == {}


class TestLLMLag:
    def test_llm_followup_parser_array(self, monkeypatch):
        from src.services.risk_assessment import datatilsyn_questions as dq
        monkeypatch.setattr(dq, "chat_json", lambda *a, **kw: [
            {"key": "dt_llm_logning", "question": "Logges medarbejdernes input?", "type": "radio",
             "options": ["Ja", "Nej"], "reason": "art. 5 ansvarlighed"},
            {"question": "Hvordan sikres datakvalitet?", "type": "text"},  # mangler key → auto
        ])
        qs = dq.llm_followup_questions(SystemFacts(systemnavn="X"))
        assert len(qs) == 2
        assert all(q.key.startswith("dt_") for q in qs)
        assert qs[0].type == "radio" and qs[1].type == "text"

    def test_llm_fejl_giver_tom_liste(self, monkeypatch):
        from src.services.risk_assessment import datatilsyn_questions as dq
        from src.services.risk_assessment.llm_client import RiskLLMError
        def boom(*a, **kw):
            raise RiskLLMError("nede")
        monkeypatch.setattr(dq, "chat_json", boom)
        assert dq.llm_followup_questions(SystemFacts()) == []

    def test_llm_bruger_metadata_sensitivity(self, monkeypatch):
        # GDPR-grænse: opfølgnings-LLM må kun bruge metadata, aldrig rå dokumenter
        from src.services.risk_assessment import datatilsyn_questions as dq
        captured = {}
        def fake(*a, **kw):
            captured.update(kw)
            return []
        monkeypatch.setattr(dq, "chat_json", fake)
        dq.llm_followup_questions(SystemFacts(systemnavn="X"))
        assert captured.get("sensitivity") == "metadata"


class TestMerge:
    def test_dedup_mod_existing_keys(self, monkeypatch):
        from src.services.risk_assessment import datatilsyn_questions as dq
        monkeypatch.setattr(dq, "llm_followup_questions", lambda f, **kw: [])
        qs = build_dynamic_questions(
            SystemFacts(), use_llm=False,
            existing_keys={"dt_modtagere"},  # foregiv allerede stillet
        )
        assert "dt_modtagere" not in [q.key for q in qs]
        assert "dt_automatiske_afgoerelser" in [q.key for q in qs]

    def test_use_llm_false_springer_llm_over(self, monkeypatch):
        from src.services.risk_assessment import datatilsyn_questions as dq
        called = {"n": 0}
        def spy(*a, **kw):
            called["n"] += 1
            return []
        monkeypatch.setattr(dq, "llm_followup_questions", spy)
        build_dynamic_questions(SystemFacts(), use_llm=False)
        assert called["n"] == 0

    def test_elementer_har_unikke_ids(self):
        ids = [e.id for e in DATATILSYN_ELEMENTER]
        assert len(ids) == len(set(ids))
