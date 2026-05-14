"""Tests for AI-trio services (Etape 2):
  - ai_intake_assist: fritekst → struktureret intake
  - evidence_draft_generator: udkast for tomme sektioner
  - evidence_quality_review: kvalitetstjek af udfyldt evidens

Tests fokuserer på:
  - JSON-parsing robusthed (fenced, raw, malformed)
  - Input-validering (tom/for kort)
  - Filtrering (draft må ikke overskrive eksisterende svar)
  - Normalisering af LLM-output (truncation, fallbacks)

LLM-kaldet selv mockes via monkeypatch — ingen reelt netværk.
"""

from __future__ import annotations

import pytest

from src.services import ai_intake_assist as intake_mod
from src.services import evidence_draft_generator as draft_mod
from src.services import evidence_quality_review as review_mod


# ---- evidence_quality_review ---------------------------------------------


class TestParseReviewJson:
    def test_plain_json(self):
        out = review_mod._parse_review_json(
            '{"quality_score": 4, "summary": "ok", "issues": [], "suggestions": [], "missing_legal_refs": []}'
        )
        assert out["quality_score"] == 4
        assert out["summary"] == "ok"

    def test_json_in_markdown_fence(self):
        wrapped = '```json\n{"quality_score": 2, "summary": "needs work", "issues": []}\n```'
        out = review_mod._parse_review_json(wrapped)
        assert out["quality_score"] == 2

    def test_json_with_prose_prefix(self):
        wrapped = 'Here is my review:\n{"quality_score": 3, "summary": "ok"}\nThanks.'
        out = review_mod._parse_review_json(wrapped)
        assert out["quality_score"] == 3

    def test_invalid_json_raises(self):
        with pytest.raises(review_mod.EvidenceReviewError):
            review_mod._parse_review_json("totally not json")

    def test_issues_filtered_to_max_5(self):
        payload = {
            "quality_score": 3,
            "summary": "many issues",
            "issues": [
                {"section_key": f"s{i}", "severity": "warning", "message": f"msg{i}"}
                for i in range(10)
            ],
        }
        out = review_mod._parse_review_json(__import__("json").dumps(payload))
        assert len(out["issues"]) == 5

    def test_issues_drops_empty_messages(self):
        payload = {
            "quality_score": 3,
            "issues": [
                {"section_key": "s1", "severity": "warning", "message": "real issue"},
                {"section_key": "s2", "severity": "warning", "message": ""},
                {"section_key": "s3", "severity": "warning"},  # no message
            ],
        }
        out = review_mod._parse_review_json(__import__("json").dumps(payload))
        assert len(out["issues"]) == 1
        assert out["issues"][0]["section_key"] == "s1"

    def test_suggestions_filtered(self):
        payload = {
            "quality_score": 3,
            "suggestions": ["valid suggestion", "", "  ", "another", "third", "fourth"],
        }
        out = review_mod._parse_review_json(__import__("json").dumps(payload))
        # Truncated to 3 + non-empty filter
        assert len(out["suggestions"]) == 3
        assert "valid suggestion" in out["suggestions"]

    def test_quality_score_fallback(self):
        out = review_mod._parse_review_json('{"summary": "no score"}')
        assert out["quality_score"] == 3  # fallback default


class TestBuildUserPrompt:
    def test_includes_section_keys_and_user_answers(self):
        template = {
            "title": "Risikostyringsplan",
            "sections": [
                {"key": "scope", "heading": "Omfang", "prompt": "Beskriv scope", "required": True},
                {"key": "mitigation", "heading": "Tiltag", "prompt": "Hvad gør I?", "required": True},
            ],
            "legal_basis": [
                {"lov": "AI Act", "artikel": "Art. 9", "citat": "Et risikostyringssystem skal..."}
            ],
        }
        content = {"scope": "AI-system til sagsbehandling", "mitigation": "Manuel review af alle svar"}
        prompt = review_mod._build_user_prompt(template, content)
        assert "scope" in prompt
        assert "AI-system til sagsbehandling" in prompt
        assert "Art. 9" in prompt
        assert "Risikostyringsplan" in prompt

    def test_empty_answer_shows_placeholder(self):
        template = {
            "title": "Test",
            "sections": [{"key": "k1", "heading": "H1", "prompt": "P1", "required": True}],
        }
        prompt = review_mod._build_user_prompt(template, {})
        assert "(tom)" in prompt

    def test_long_answer_truncated(self):
        template = {
            "title": "Test",
            "sections": [{"key": "k1", "heading": "H1", "prompt": "P1", "required": True}],
        }
        long = "x" * 2000
        prompt = review_mod._build_user_prompt(template, {"k1": long})
        # Skal være trunkeret til 600 tegn pr. svar
        assert prompt.count("x") <= 700


class TestReviewEvidence:
    def test_empty_template_raises(self):
        with pytest.raises(ValueError):
            review_mod.review_evidence(template={}, content={"k": "v"})

    def test_empty_content_raises(self):
        with pytest.raises(ValueError):
            review_mod.review_evidence(template={"title": "X", "sections": []}, content={})

    def test_happy_path_with_mocked_llm(self, monkeypatch):
        fake_response = (
            '{"quality_score": 4, "summary": "Solid evidens", '
            '"issues": [{"section_key": "scope", "severity": "tip", "message": "Tilføj eksempel"}], '
            '"suggestions": ["Citér Art. 9"], "missing_legal_refs": ["GDPR Art. 32"]}'
        )

        def fake_call(user_message, *, timeout):
            assert "Risikostyring" in user_message
            return fake_response

        monkeypatch.setattr(review_mod, "_call_llm", fake_call)

        result = review_mod.review_evidence(
            template={
                "title": "Risikostyring",
                "sections": [{"key": "scope", "heading": "Omfang", "required": True}],
                "legal_basis": [],
            },
            content={"scope": "Et grundigt svar om scope"},
        )
        assert result["quality_score"] == 4
        assert result["summary"] == "Solid evidens"
        assert len(result["issues"]) == 1
        assert result["missing_legal_refs"] == ["GDPR Art. 32"]


# ---- evidence_draft_generator -------------------------------------------


class TestIsFilled:
    def test_empty_string(self):
        assert draft_mod._is_filled("") is False
        assert draft_mod._is_filled("   ") is False

    def test_nonempty_string(self):
        assert draft_mod._is_filled("noget") is True

    def test_none(self):
        assert draft_mod._is_filled(None) is False

    def test_bool(self):
        assert draft_mod._is_filled(True) is True
        assert draft_mod._is_filled(False) is True  # bool counts som filled (eksplicit valg)

    def test_list_dict(self):
        assert draft_mod._is_filled([]) is False
        assert draft_mod._is_filled([1]) is True
        assert draft_mod._is_filled({}) is False
        assert draft_mod._is_filled({"k": "v"}) is True


class TestGenerateEvidenceDraft:
    def test_skips_filled_sections(self, monkeypatch):
        called = {"n": 0}

        def fake_call(user_message, *, timeout):
            called["n"] += 1
            return '{"section_a": "udkast a"}'

        monkeypatch.setattr(draft_mod, "_call_llm", fake_call)

        template = {
            "title": "Test",
            "sections": [
                {"key": "section_a", "heading": "A", "required": True},
                {"key": "section_b", "heading": "B", "required": True},
            ],
            "legal_basis": [],
        }
        # section_b er udfyldt — LLM må ikke overskrive
        existing = {"section_b": "menneskelig udfyldt"}
        result = draft_mod.generate_evidence_draft(
            template=template,
            case_intake={"behov": "test"},
            existing_content=existing,
        )
        # Kun section_a er tom → kun den må have udkast
        assert "section_a" in result
        assert "section_b" not in result

    def test_returns_empty_when_all_filled(self, monkeypatch):
        # Hvis alt er udfyldt skal vi slet ikke kalde LLM
        def fake_call(*a, **kw):
            raise AssertionError("LLM må ikke kaldes når alt er udfyldt")

        monkeypatch.setattr(draft_mod, "_call_llm", fake_call)

        result = draft_mod.generate_evidence_draft(
            template={
                "title": "T",
                "sections": [{"key": "k", "heading": "H", "required": True}],
                "legal_basis": [],
            },
            case_intake={"behov": "x"},
            existing_content={"k": "fyld"},
        )
        assert result == {}

    def test_requires_intake(self):
        with pytest.raises(ValueError):
            draft_mod.generate_evidence_draft(
                template={"sections": [{"key": "k", "required": True}]},
                case_intake={},
            )


# ---- ai_intake_assist ---------------------------------------------------


class TestExtractIntake:
    def test_too_short_description_raises(self):
        with pytest.raises(ValueError):
            intake_mod.extract_intake_from_description("kort")

    def test_no_llm_provider_raises(self, monkeypatch):
        # Fjern alle providers
        for key in (
            "LM_STUDIO_BASE_URL",
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_API_KEY",
            "OPENAI_API_KEY",
        ):
            monkeypatch.delenv(key, raising=False)
        with pytest.raises(intake_mod.AIIntakeError):
            intake_mod.extract_intake_from_description(
                "Vi planlægger at indkøbe et chatbot-system til borgerservice "
                "som kan svare på spørgsmål om byggesag."
            )

    def test_parse_llm_json_handles_fence(self):
        fenced = '```json\n{"behov": "borgerservice"}\n```'
        out = intake_mod._parse_llm_json(fenced)
        assert out["behov"] == "borgerservice"

    def test_parse_llm_json_handles_prose(self):
        prose = 'Her er resultatet:\n{"behov": "test"}\nMvh.'
        out = intake_mod._parse_llm_json(prose)
        assert out["behov"] == "test"

    def test_parse_llm_json_raises_on_garbage(self):
        with pytest.raises(intake_mod.AIIntakeError):
            intake_mod._parse_llm_json("absolutely not json")
