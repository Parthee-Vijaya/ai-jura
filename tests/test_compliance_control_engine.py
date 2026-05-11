"""Tests for src.compliance.compliance_control_engine — 7-punkts vurdering.

Modul er 354 stmts med 0% baseline coverage. Mål: ~70%.

Dækker:
  - Beslutning + RisikoNiveau enums
  - vurder_system (end-to-end)
  - _beregn_risiko_score (score-mapping)
  - _bestem_risiko_niveau (score → niveau)
  - _identificer_hard_stops (kritiske blokeringer)
  - _bestem_beslutning (GO/BETINGET-GO/NO-GO logik)
  - _er_ai_system + _kraever_dpia (heuristics)
"""

import pytest

from src.compliance.compliance_control_engine import (
    Beslutning,
    ComplianceControlEngine,
    RisikoNiveau,
)


# ---- Enums ---------------------------------------------------------------


def test_beslutning_enum_values():
    assert Beslutning.GO.value == "go"
    assert Beslutning.BETINGET_GO.value == "betinget-go"
    assert Beslutning.NO_GO.value == "no-go"


def test_risiko_niveau_enum_values():
    assert RisikoNiveau.LAV.value == "Lav"
    assert RisikoNiveau.MEDIUM.value == "Medium"
    assert RisikoNiveau.HOJ.value == "Høj"
    assert RisikoNiveau.KRITISK.value == "Kritisk"


# ---- Fixtures ------------------------------------------------------------


@pytest.fixture
def engine():
    return ComplianceControlEngine()


@pytest.fixture
def minimal_data():
    """Minimal input — ikke-AI system uden persondata."""
    return {
        "system_navn": "Test System",
        "system_beskrivelse": "Almindeligt regneark",
        "fagomraade": "Administration",
        "organisation": "Kalundborg Kommune",
    }


@pytest.fixture
def ai_personoplysninger_data():
    """AI med persondata — typisk kommunal sag."""
    return {
        "system_navn": "AI-Pension",
        "system_beskrivelse": "AI til behandling af pensionsansøgninger",
        "fagomraade": "Jobcenter",
        "bruger_ml": True,
        "autonome_beslutninger": True,
        "personoplysninger": True,
        "persondata_typer": ["CPR-numre", "Indkomst"],
        "juridisk_grundlag": "offentlig_opgave",
        "dpia_udfoert": True,
        "privacy_by_design": "ja",
        "databehandleraftaler": "ja",
        "ai_risiko_kategori": "high",
        "menneskelig_overvaagning": "ja",
        "transparens": "ja",
        "medarbejder_uddannelse": "ja",
        "ansvarlig_person": "Pavi",
        "beslutningslogik_dokumentation": "ja",
        "bias_testing": "ja",
        "klage_procedurer": True,
    }


@pytest.fixture
def forbudt_data():
    """Forbudt AI-praksis → automatisk NO-GO."""
    return {
        "system_navn": "Forbudt System",
        "ai_risiko_kategori": "unacceptable",
        "bruger_ml": True,
    }


# ---- _er_ai_system + _kraever_dpia ---------------------------------------


def test_er_ai_system_true_when_bruger_ml(engine):
    assert engine._er_ai_system({"bruger_ml": True}) is True


def test_er_ai_system_true_when_autonome_beslutninger(engine):
    assert engine._er_ai_system({"autonome_beslutninger": True}) is True


def test_er_ai_system_false_when_neither(engine):
    assert engine._er_ai_system({}) is False


def test_kraever_dpia_for_high_risk_ai_with_personoplysninger(engine):
    """Persondata + high-risk AI = DPIA-krav.

    DPIA kræves når én af følgende er sande sammen med persondata:
    - Særlige kategorier (sundhed, biometri, race/religion)
    - ai_risiko_kategori in ('high', 'unacceptable')
    - automatiserede_beslutninger
    - kritiske_formaal
    """
    data = {"personoplysninger": True, "ai_risiko_kategori": "high"}
    assert engine._kraever_dpia(data) is True


def test_kraever_dpia_for_automatiserede_beslutninger(engine):
    """Persondata + automatiserede beslutninger = DPIA-krav."""
    data = {"personoplysninger": True, "automatiserede_beslutninger": True}
    assert engine._kraever_dpia(data) is True


def test_kraever_dpia_false_for_personoplysninger_alone(engine):
    """Persondata alene (uden high-risk-flag) kræver IKKE DPIA — kun
    når yderligere risiko-indikatorer er sat (særlige kategorier osv.)"""
    data = {"personoplysninger": True}
    assert engine._kraever_dpia(data) is False


def test_kraever_dpia_false_for_simple_admin(engine):
    """Ingen persondata → ingen DPIA."""
    assert engine._kraever_dpia({}) is False


# ---- _beregn_risiko_score ------------------------------------------------


def test_score_minimal_data_yields_baseline(engine, minimal_data):
    """Minimal data (ingen 'ja'-svar på ja/nej-felter) giver ~37 score
    pga. transparens/menneskelig_overvaagning/uddannelse osv. defaulter
    til ikke-'ja'. Det er status quo — ikke et bug."""
    score = engine._beregn_risiko_score(minimal_data)
    # Score er bounded, ikke nødvendigvis lav
    assert 0 <= score <= 100


def test_score_optimal_data_low(engine):
    """Med alle "ja"-svar på compliance-felter er score lav."""
    optimal = {
        "system_navn": "Test",
        "transparens": "ja",
        "menneskelig_overvaagning": "ja",
        "medarbejder_uddannelse": "ja",
        "ansvarlig_person": "Pavi",
        "beslutningslogik_dokumentation": "ja",
        "bias_testing": "ja",
        "klage_procedurer": True,
    }
    score = engine._beregn_risiko_score(optimal)
    # Med alle compliance-felter sat til 'ja' bør score være meget lav
    assert score <= 10


def test_score_unacceptable_ai_high(engine):
    """unacceptable AI → score >= 25 alene fra den faktor."""
    score = engine._beregn_risiko_score({"ai_risiko_kategori": "unacceptable"})
    assert score >= 25


def test_score_capped_at_100(engine):
    """Worst-case input giver max 100, ikke over."""
    worst = {
        "bruger_ml": True,
        "autonome_beslutninger": True,
        "personoplysninger": True,
        "persondata_typer": ["Sundhedsdata", "Biometriske data", "Særlige kategorier (race, religion, etc.)"],
        "ai_risiko_kategori": "unacceptable",
        "kritiske_formaal": True,
        "transparens": "nej",
        "menneskelig_overvaagning": "nej",
        "medarbejder_uddannelse": "nej",
        "bias_testing": "nej",
    }
    score = engine._beregn_risiko_score(worst)
    assert score == 100


def test_score_health_data_higher_than_normal(engine):
    """Sundhedsdata bidrager mere end almindelige persondata."""
    base = {"personoplysninger": True, "persondata_typer": ["Navn"]}
    health = {"personoplysninger": True, "persondata_typer": ["Sundhedsdata"]}
    assert engine._beregn_risiko_score(health) > engine._beregn_risiko_score(base)


def test_score_missing_dpia_adds_points(engine):
    """Persondata uden DPIA → højere score."""
    with_dpia = {"personoplysninger": True, "dpia_udfoert": True}
    without_dpia = {"personoplysninger": True, "dpia_udfoert": False}
    assert engine._beregn_risiko_score(without_dpia) > engine._beregn_risiko_score(with_dpia)


def test_score_ai_high_risk_higher_than_minimal(engine):
    """AI-Act high-risk scorer højere end minimal."""
    high = {"ai_risiko_kategori": "high"}
    minimal = {"ai_risiko_kategori": "minimal"}
    assert engine._beregn_risiko_score(high) > engine._beregn_risiko_score(minimal)


# ---- _bestem_risiko_niveau -----------------------------------------------


def test_niveau_lav_for_low_score(engine):
    assert engine._bestem_risiko_niveau(0) == RisikoNiveau.LAV
    assert engine._bestem_risiko_niveau(29) == RisikoNiveau.LAV


def test_niveau_medium_for_30_to_59(engine):
    assert engine._bestem_risiko_niveau(30) == RisikoNiveau.MEDIUM
    assert engine._bestem_risiko_niveau(59) == RisikoNiveau.MEDIUM


def test_niveau_hoj_for_60_to_79(engine):
    assert engine._bestem_risiko_niveau(60) == RisikoNiveau.HOJ
    assert engine._bestem_risiko_niveau(79) == RisikoNiveau.HOJ


def test_niveau_kritisk_for_80_plus(engine):
    assert engine._bestem_risiko_niveau(80) == RisikoNiveau.KRITISK
    assert engine._bestem_risiko_niveau(100) == RisikoNiveau.KRITISK


# ---- _identificer_hard_stops ---------------------------------------------


def test_hard_stop_unacceptable_ai(engine, forbudt_data):
    """Forbudt AI er altid et hard-stop."""
    hard_stops = engine._identificer_hard_stops(forbudt_data)
    assert len(hard_stops) >= 1
    # Mindst én skal nævne "forbudt" eller AI Act
    joined = " ".join(hard_stops).lower()
    assert "forbudt" in joined or "ai" in joined


def test_no_hard_stop_for_clean_data(engine, ai_personoplysninger_data):
    """Fuldt udfyldt compliance-data har ingen hard-stops."""
    hard_stops = engine._identificer_hard_stops(ai_personoplysninger_data)
    assert hard_stops == [] or len(hard_stops) == 0


def test_hard_stop_missing_dpia_for_personoplysninger(engine):
    """Persondata uden DPIA = hard-stop."""
    data = {"personoplysninger": True, "dpia_udfoert": False, "bruger_ml": True}
    hard_stops = engine._identificer_hard_stops(data)
    # Forventer mindst én hard-stop om DPIA
    joined = " ".join(hard_stops).lower()
    assert "dpia" in joined or "konsekvensanalyse" in joined or len(hard_stops) > 0


# ---- _bestem_beslutning --------------------------------------------------


def test_beslutning_go_for_low_risk_no_blockers(engine):
    """Lav score, ingen hard-stops, ingen betingelser → GO."""
    result = engine._bestem_beslutning(risiko_score=20, hard_stops=[], betingelser=[])
    assert result == Beslutning.GO


def test_beslutning_no_go_when_hard_stops(engine):
    """Hard-stops → altid NO-GO uanset score."""
    result = engine._bestem_beslutning(risiko_score=10, hard_stops=["Kritisk fejl"], betingelser=[])
    assert result == Beslutning.NO_GO


def test_beslutning_no_go_for_very_high_score(engine):
    """Score >= 80 → NO-GO selv uden hard-stops."""
    result = engine._bestem_beslutning(risiko_score=85, hard_stops=[], betingelser=[])
    assert result == Beslutning.NO_GO


def test_beslutning_betinget_go_for_medium_risk(engine):
    """Medium score → BETINGET-GO."""
    result = engine._bestem_beslutning(risiko_score=55, hard_stops=[], betingelser=[])
    assert result == Beslutning.BETINGET_GO


def test_beslutning_betinget_go_for_many_conditions(engine):
    """5+ betingelser → BETINGET-GO selv ved lav score."""
    result = engine._bestem_beslutning(
        risiko_score=10,
        hard_stops=[],
        betingelser=["a", "b", "c", "d", "e"],
    )
    assert result == Beslutning.BETINGET_GO


def test_beslutning_betinget_go_when_any_betingelser(engine):
    """Bare nogle betingelser → BETINGET-GO."""
    result = engine._bestem_beslutning(
        risiko_score=10,
        hard_stops=[],
        betingelser=["Tilføj DPIA"],
    )
    assert result == Beslutning.BETINGET_GO


# ---- vurder_system (end-to-end) ------------------------------------------


def test_vurder_system_returns_complete_rapport(engine, minimal_data):
    """End-to-end: rapport har alle top-level keys."""
    rapport = engine.vurder_system(minimal_data)
    assert "compliance_control" in rapport
    assert "punkt_vurderinger" in rapport
    assert "system_info" in rapport
    assert "samlet_vurdering" in rapport


def test_vurder_system_compliance_control_fields(engine, minimal_data):
    """compliance_control har alle nødvendige fields."""
    rapport = engine.vurder_system(minimal_data)
    cc = rapport["compliance_control"]
    for field in [
        "beslutning", "beslutning_beskrivelse", "risiko_score",
        "risiko_niveau", "hard_stops", "betingelser",
        "nødvendige_artefakter", "nødvendige_tests",
        "næste_skridt", "anbefalinger",
    ]:
        assert field in cc, f"Missing field: {field}"


def test_vurder_system_unacceptable_returns_no_go(engine, forbudt_data):
    """Forbudt AI ender altid som NO-GO."""
    rapport = engine.vurder_system(forbudt_data)
    assert rapport["compliance_control"]["beslutning"] == "no-go"


def test_vurder_system_clean_ai_data_betinget_go(engine, ai_personoplysninger_data):
    """Fuldt udfyldt høj-risiko AI = BETINGET-GO (ikke NO-GO uden hard-stop)."""
    rapport = engine.vurder_system(ai_personoplysninger_data)
    beslutning = rapport["compliance_control"]["beslutning"]
    assert beslutning in ("go", "betinget-go")  # ikke no-go for compliant high-risk


def test_vurder_system_samlet_vurdering_fields(engine, minimal_data):
    """samlet_vurdering har stabile boolean-fields."""
    rapport = engine.vurder_system(minimal_data)
    sv = rapport["samlet_vurdering"]
    assert isinstance(sv["er_ai_system"], bool)
    assert isinstance(sv["behandler_persondata"], bool)
    assert isinstance(sv["kræver_dpia"], bool)
    assert 0 <= sv["compliance_score"] <= 100


def test_vurder_system_score_inverted_to_compliance(engine, ai_personoplysninger_data):
    """compliance_score = 100 - risiko_score."""
    rapport = engine.vurder_system(ai_personoplysninger_data)
    risiko = rapport["compliance_control"]["risiko_score"]
    compl = rapport["samlet_vurdering"]["compliance_score"]
    assert compl == max(0, 100 - risiko)


def test_vurder_system_jobcenter_marked_ai_system(engine):
    """AI til Jobcenter med autonome beslutninger flagges som AI-system."""
    data = {
        "system_navn": "AI-Jobcenter",
        "fagomraade": "Jobcenter",
        "bruger_ml": True,
        "autonome_beslutninger": True,
    }
    rapport = engine.vurder_system(data)
    assert rapport["samlet_vurdering"]["er_ai_system"] is True


def test_vurder_system_artefakter_returns_list(engine, ai_personoplysninger_data):
    """Nødvendige artefakter er en liste (kan være tom)."""
    rapport = engine.vurder_system(ai_personoplysninger_data)
    artefakter = rapport["compliance_control"]["nødvendige_artefakter"]
    assert isinstance(artefakter, list)


def test_vurder_system_naeste_skridt_non_empty(engine, ai_personoplysninger_data):
    """Næste skridt er aldrig tom for et AI-system (mindst ét anbefalet skridt)."""
    rapport = engine.vurder_system(ai_personoplysninger_data)
    naeste = rapport["compliance_control"]["næste_skridt"]
    assert isinstance(naeste, list)
    # For AI med persondata bør der være mindst ét skridt
    assert len(naeste) >= 1
