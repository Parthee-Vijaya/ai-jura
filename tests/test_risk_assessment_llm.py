"""Tests for risikovurderingsmotorens LLM-services med MOCKED LLM.

Kalder aldrig en reel LLM — monkeypatcher chat_json / _call_provider. Verificerer:
  - JSON-parsing + repair (trailing commas, fence, prose-wrapper)
  - fact_extractor coercion + normalisering
  - risk_identifier mapping + niveau-normalisering
  - content_generator field-mapping
  - clarifying questions + apply_answers
  - orchestrator generate() flow
"""

import pytest

from src.services.risk_assessment import (
    clarifying,
    content_generator,
    fact_extractor,
    orchestrator,
    risk_identifier,
)
from src.services.risk_assessment.llm_client import _parse_json, _repair_json, RiskLLMError
from src.services.risk_assessment.models import DataKategori, Niveau, SystemFacts


# ---- llm_client parsing + repair ----------------------------------------


class TestJsonRepair:
    def test_trailing_comma_object(self):
        assert _parse_json('{"a": 1, "b": 2,}') == {"a": 1, "b": 2}

    def test_trailing_comma_nested_array(self):
        out = _parse_json('{"risici": [{"x": 1,}, {"y": 2},]}', expect="array")
        assert out == [{"x": 1}, {"y": 2}]

    def test_markdown_fence(self):
        assert _parse_json('```json\n{"a": true}\n```') == {"a": True}

    def test_prose_wrapper(self):
        assert _parse_json('Her er svaret:\n{"a": 1}\nMvh') == {"a": 1}

    def test_line_comments(self):
        assert _parse_json('{"a": 1 // kommentar\n}') == {"a": 1}

    def test_smart_quotes(self):
        # _repair_json normaliserer smart-quotes
        repaired = _repair_json('{“a”: 1}')
        assert '"a"' in repaired

    def test_array_extracted_from_wrapper_key(self):
        out = _parse_json('{"items": [1, 2, 3]}', expect="array")
        assert out == [1, 2, 3]

    def test_unrepairable_raises(self):
        with pytest.raises(RiskLLMError):
            _parse_json("dette er ikke json overhovedet")

    # --- regression: intermittente gemma-fejl (rapporteret af bruger) ---

    def test_unescaped_newline_in_string_value(self):
        # gemma skriver lange tekstfelter med rå linjeskift → ugyldig JSON
        bad = '{"formaal_tekst": "Formålet er at\nvurdere systemet.", "omfang_tekst": "Alt."}'
        out = _parse_json(bad)
        assert out["omfang_tekst"] == "Alt."
        assert "vurdere systemet" in out["formaal_tekst"]

    def test_multiline_value_in_fence(self):
        bad = '```json\n{\n  "a": "linje et\nlinje to.",\n  "b": "ok"\n}\n```'
        out = _parse_json(bad)
        assert out["b"] == "ok"

    def test_lone_comma_between_fields(self):
        assert _parse_json('{"a": "x",\n,\n"b": "y"}') == {"a": "x", "b": "y"}

    def test_tab_in_string_value(self):
        out = _parse_json('{"a": "kol1\tkol2", "b": "y",}')
        assert "kol1" in out["a"]

    def test_escaped_quote_preserved(self):
        out = _parse_json('{"a": "siger \\"hej\\" til"}')
        assert out["a"] == 'siger "hej" til'

    def test_think_block_stripped(self):
        # Reasoning-modeller wrapper tankeproces i <think> — kan indeholde { }
        thinky = '<think>\nOvervejer... {"draft": 1} er ikke nok.\n</think>\n{"quality": 4}'
        assert _parse_json(thinky) == {"quality": 4}

    def test_thinking_block_case_insensitive(self):
        thinky = '<THINKING>noget {x} her</THINKING>```json\n{"ok": true}\n```'
        assert _parse_json(thinky) == {"ok": True}


class TestRiskPromptLabels:
    """Regression: leverandør-label precedence-bug (ekstern + tomt navn)."""

    def test_ekstern_uden_navn_siger_ukendt(self):
        from src.services.risk_assessment.risk_identifier import _build_user_prompt
        prompt = _build_user_prompt(SystemFacts(systemnavn="X", internt_udviklet=False))
        assert "ukendt leverandør" in prompt
        assert "(internt udviklet)" not in prompt

    def test_internt_udviklet_label(self):
        from src.services.risk_assessment.risk_identifier import _build_user_prompt
        prompt = _build_user_prompt(SystemFacts(systemnavn="X", internt_udviklet=True))
        assert "INTERNT UDVIKLET" in prompt

    def test_estimat_label_ikke_fabrikeret_beloeb(self):
        # Bucket-svar må ALDRIG vises som konkret beløb i prompts
        from src.services.risk_assessment.risk_identifier import _build_user_prompt
        from src.services.risk_assessment.clarifying import apply_answers
        f = apply_answers(SystemFacts(systemnavn="X"), {"kontraktvaerdi_bucket": "1,6 - 5 mio. kr."})
        prompt = _build_user_prompt(f)
        assert "1,6 - 5 mio. kr." in prompt          # interval vises
        assert "3,000,000" not in prompt              # det repræsentative tal vises IKKE
        assert "3.000.000" not in prompt
        assert "bruger-estimat" in prompt


class TestRetry:
    def test_retries_on_parse_failure_then_succeeds(self, monkeypatch):
        from src.services.risk_assessment import llm_client
        calls = {"n": 0}

        def fake_provider(*a, **kw):
            calls["n"] += 1
            # Første svar er ugyldigt JSON, andet er gyldigt
            return "noget vrøvl" if calls["n"] == 1 else '{"ok": true}'

        monkeypatch.setattr(llm_client, "_call_provider", fake_provider)
        out = llm_client.chat_json("sys", "user", max_attempts=3)
        assert out == {"ok": True}
        assert calls["n"] == 2  # fejlede én gang, lykkedes på forsøg 2

    def test_raises_after_all_attempts(self, monkeypatch):
        from src.services.risk_assessment import llm_client
        monkeypatch.setattr(llm_client, "_call_provider", lambda *a, **kw: "ikke json")
        with pytest.raises(RiskLLMError):
            llm_client.chat_json("sys", "user", max_attempts=2)


# ---- fact_extractor ------------------------------------------------------


class TestFactExtractor:
    def test_coerce_full(self):
        data = {
            "systemnavn": "Velatir",
            "leverandoer_navn": "Velatir ApS",
            "leverandoer_land": "Danmark",
            "leverandoer_stiftet_aar": "2024",
            "hosting_lokation": "Scaleway EU",
            "persondata_kategorier": ["almindelige", "cpr", "ukendt-skip"],
            "underdatabehandlere": [{"navn": "Scaleway", "land": "FR", "rolle": "Hosting"}],
            "msa_risiko_klausuler": ["§6.2 AI-træning"],
            "internt_udviklet": False,
            "medarbejder_overvaagning": True,
        }
        f = fact_extractor._coerce_facts(data)
        assert f.systemnavn == "Velatir"
        assert f.leverandoer_stiftet_aar == 2024
        assert DataKategori.CPR in f.persondata_kategorier
        assert DataKategori.ALMINDELIGE in f.persondata_kategorier
        assert len(f.persondata_kategorier) == 2  # ukendt skipped
        assert len(f.underdatabehandlere) == 1
        assert f.medarbejder_overvaagning is True
        assert f.er_ekstern_leverandoer()

    def test_coerce_partial_defaults(self):
        f = fact_extractor._coerce_facts({"systemnavn": "X"})
        assert f.systemnavn == "X"
        assert f.persondata_kategorier == []
        assert f.leverandoer_land == "Ukendt"

    def test_systemnavn_override(self):
        f = fact_extractor._coerce_facts({"systemnavn": "FromDoc"}, systemnavn_override="FromUser")
        assert f.systemnavn == "FromUser"

    def test_invalid_year_becomes_none(self):
        f = fact_extractor._coerce_facts({"leverandoer_stiftet_aar": "ikke-et-år"})
        assert f.leverandoer_stiftet_aar is None

    def test_empty_documents_returns_skeleton(self):
        f = fact_extractor.extract_facts("", systemnavn="Tom")
        assert f.systemnavn == "Tom"
        assert f.leverandoer_navn == ""

    def test_extract_with_mocked_llm(self, monkeypatch):
        monkeypatch.setattr(
            fact_extractor, "chat_json",
            lambda *a, **kw: {"systemnavn": "Mock", "persondata_kategorier": ["cpr"]},
        )
        f = fact_extractor.extract_facts("noget dokument tekst her", systemnavn="")
        assert f.systemnavn == "Mock"
        assert DataKategori.CPR in f.persondata_kategorier


# ---- risk_identifier -----------------------------------------------------


class TestRiskIdentifier:
    def test_maps_risks_and_normalizes_niveau(self, monkeypatch):
        monkeypatch.setattr(risk_identifier, "chat_json", lambda *a, **kw: {
            "risici": [
                {"risiko": "R1", "konsekvens_beskrivelse": "K1", "sandsynlighed": "mellem", "score": "høj", "hvorfor": "fordi"},
                {"risiko": "R2", "konsekvens_beskrivelse": "K2", "sandsynlighed": "Lav-middel", "score": "Middel", "hvorfor": ""},
                {"konsekvens_beskrivelse": "ingen risiko-titel — skip"},  # no risiko → skip
            ]
        })
        risks = risk_identifier.identify_risks(SystemFacts(systemnavn="X"))
        assert len(risks) == 2
        assert risks[0].sandsynlighed == Niveau.MIDDEL
        assert risks[0].score == Niveau.HOEJ
        assert risks[1].sandsynlighed == Niveau.LAV_MIDDEL

    def test_accepts_bare_list(self, monkeypatch):
        monkeypatch.setattr(risk_identifier, "chat_json", lambda *a, **kw: [
            {"risiko": "R1", "konsekvens_beskrivelse": "K1", "sandsynlighed": "Lav", "score": "Lav"},
        ])
        risks = risk_identifier.identify_risks(SystemFacts())
        assert len(risks) == 1

    def test_non_list_raises(self, monkeypatch):
        monkeypatch.setattr(risk_identifier, "chat_json", lambda *a, **kw: {"risici": "ikke en liste"})
        with pytest.raises(RiskLLMError):
            risk_identifier.identify_risks(SystemFacts())

    def test_risk_library_present(self):
        # System-prompten skal indeholde de 5 kategorier som inspiration
        for cat in ("Leverandør", "Data og overførsel", "Adgang", "Teknisk arkitektur", "Organisatoriske"):
            assert cat in risk_identifier.SYSTEM_PROMPT


# ---- content_generator ---------------------------------------------------


class TestContentGenerator:
    def test_maps_all_14_fields(self, monkeypatch):
        full = {k: f"tekst-{k}" for k in content_generator.FIELD_SPECS}
        monkeypatch.setattr(content_generator, "chat_json", lambda *a, **kw: full)
        out = content_generator.generate_content(SystemFacts(systemnavn="X"), [])
        assert len(out) == 14
        assert out["formaal_tekst"] == "tekst-formaal_tekst"

    def test_missing_fields_become_empty(self, monkeypatch):
        monkeypatch.setattr(content_generator, "chat_json", lambda *a, **kw: {"formaal_tekst": "kun denne"})
        out = content_generator.generate_content(SystemFacts(), [])
        assert out["formaal_tekst"] == "kun denne"
        assert out["omfang_tekst"] == ""

    def test_non_dict_raises(self, monkeypatch):
        monkeypatch.setattr(content_generator, "chat_json", lambda *a, **kw: ["ikke en dict"])
        with pytest.raises(RiskLLMError):
            content_generator.generate_content(SystemFacts(), [])


# ---- clarifying ----------------------------------------------------------


class TestClarifying:
    def test_always_asks_scope_and_tilgang(self):
        qs = clarifying.build_questions(SystemFacts(hosting_lokation="Azure"))
        keys = [q.key for q in qs]
        assert "scope" in keys
        assert "tilgang" in keys

    def test_asks_hosting_when_missing(self):
        qs = clarifying.build_questions(SystemFacts(hosting_lokation=""))
        assert any(q.key == "hosting_lokation" for q in qs)

    def test_question_count_within_expected_range(self):
        # Etape 2: udvidet fra 5 → 8-9 spørgsmål (4 GDPR + 4 Kalundborg + evt. hosting)
        qs_med_hosting = clarifying.build_questions(SystemFacts(hosting_lokation="Azure"))
        qs_uden_hosting = clarifying.build_questions(SystemFacts())  # +hosting-spørgsmål
        assert 8 <= len(qs_med_hosting) <= 10
        assert len(qs_uden_hosting) == len(qs_med_hosting) + 1  # hosting tilføjes

    def test_apply_answers_scope_normalization(self):
        f = SystemFacts()
        merged = clarifying.apply_answers(f, {"scope": "Bred udrulning"})
        assert merged.scope == "bred_udrulning"
        merged2 = clarifying.apply_answers(f, {"scope": "POC / pilot"})
        assert merged2.scope == "poc"

    def test_apply_answers_kategorier(self):
        merged = clarifying.apply_answers(SystemFacts(), {"persondata_kategorier": "cpr,følsomme"})
        assert DataKategori.CPR in merged.persondata_kategorier
        assert DataKategori.FOELSOMME in merged.persondata_kategorier

    def test_apply_answers_overvaagning(self):
        merged = clarifying.apply_answers(SystemFacts(), {"medarbejder_overvaagning": "Ja"})
        assert merged.medarbejder_overvaagning is True


# ---- orchestrator.generate ----------------------------------------------


class TestOrchestratorGenerate:
    def test_generate_flow(self, monkeypatch):
        monkeypatch.setattr(
            orchestrator, "identify_risks",
            lambda facts, **kw: [
                __import__("src.services.risk_assessment.models", fromlist=["Risiko"]).Risiko(
                    risiko="R1", konsekvens_beskrivelse="K1",
                )
            ],
        )
        monkeypatch.setattr(
            orchestrator, "generate_content",
            lambda facts, risks, **kw: {k: f"v-{k}" for k in content_generator.FIELD_SPECS},
        )
        facts = SystemFacts(systemnavn="Test")
        rv = orchestrator.generate(facts, {"scope": "Begge", "tilgang": "Idealiseret"})
        assert rv.facts.systemnavn == "Test"
        assert len(rv.risici) == 1
        assert rv.formaal_tekst == "v-formaal_tekst"
        # answers blev anvendt
        assert rv.facts.scope == "begge"
