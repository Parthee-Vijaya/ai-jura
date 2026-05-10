"""Tests for src.services.evidence_artifacts — curated skabeloner.

Sikrer at de 6 nye P1+P2-templates (2026-05-10) er korrekt registreret
og kan returneres som curated (ikke generic fallback). Tester også at
status-beregning virker for både tomme og delvist-udfyldte sager.
"""

import pytest

from src.services.evidence_artifacts import (
    ARTIFACT_TEMPLATES,
    ArtifactTemplate,
    Section,
    all_known_ids,
    compute_status,
    get_template,
    list_templates,
)


# ---- De 6 nye P1+P2-templates -----------------------------------------------

NEW_P1_IDS = [
    "eu_mcc_klausuler",
    "ai_faerdigheder_program",
    "leverandoer_due_diligence",
]

NEW_P2_IDS = [
    "trustworthy_ai_rating",
    "ce_maerkning_guide",
    "incident_reporting_art73",
]

ALL_NEW_IDS = NEW_P1_IDS + NEW_P2_IDS


@pytest.mark.parametrize("artifact_id", ALL_NEW_IDS)
def test_new_template_is_curated(artifact_id):
    """Hver ny P1+P2-template skal være registreret i ARTIFACT_TEMPLATES."""
    assert artifact_id in ARTIFACT_TEMPLATES, (
        f"{artifact_id} mangler fra ARTIFACT_TEMPLATES dict"
    )


@pytest.mark.parametrize("artifact_id", ALL_NEW_IDS)
def test_new_template_returned_as_curated_not_generic(artifact_id):
    """get_template() skal returnere curated skabelon (ikke generic fallback)."""
    template = get_template(artifact_id)
    assert isinstance(template, ArtifactTemplate)
    # Curated templates har specifik kategori, ikke "generic"
    assert template.category != "generic", (
        f"{artifact_id} faldt tilbage til generic — skal være curated"
    )


@pytest.mark.parametrize("artifact_id", ALL_NEW_IDS)
def test_new_template_has_legal_basis(artifact_id):
    """Hver curated template skal have mindst én lovhjemmel."""
    template = get_template(artifact_id)
    assert len(template.legal_basis) >= 1, (
        f"{artifact_id} mangler legal_basis — vigtigt for compliance-traceability"
    )
    for ref in template.legal_basis:
        assert ref.lov, f"{artifact_id} legal_basis har tom 'lov'"
        assert ref.artikel, f"{artifact_id} legal_basis har tom 'artikel'"
        assert ref.url.startswith("http"), (
            f"{artifact_id} legal_basis URL er ikke en gyldig HTTP-URL"
        )


@pytest.mark.parametrize("artifact_id", ALL_NEW_IDS)
def test_new_template_has_external_resources(artifact_id):
    """Hver curated template skal have mindst én ekstern ressource."""
    template = get_template(artifact_id)
    assert len(template.external_resources) >= 1, (
        f"{artifact_id} mangler external_resources"
    )
    for res in template.external_resources:
        assert res.title, f"{artifact_id} ekstern ressource har tom 'title'"
        assert res.publisher, f"{artifact_id} ekstern ressource har tom 'publisher'"
        assert res.url.startswith("http"), (
            f"{artifact_id} ekstern ressource URL er ikke en gyldig HTTP-URL"
        )


@pytest.mark.parametrize("artifact_id", ALL_NEW_IDS)
def test_new_template_has_minimum_sections(artifact_id):
    """Hver curated template skal have mindst 5 sektioner — ellers virker den ikke."""
    template = get_template(artifact_id)
    assert len(template.sections) >= 5, (
        f"{artifact_id} har kun {len(template.sections)} sektioner — for få"
    )


@pytest.mark.parametrize("artifact_id", ALL_NEW_IDS)
def test_new_template_has_required_sections(artifact_id):
    """Hver curated template skal have mindst én required-sektion."""
    template = get_template(artifact_id)
    required_keys = template.required_section_keys()
    assert len(required_keys) >= 1, (
        f"{artifact_id} har ingen required-sektioner — status-beregning bliver bizar"
    )


@pytest.mark.parametrize("artifact_id", ALL_NEW_IDS)
def test_new_template_section_keys_unique(artifact_id):
    """Section-keys skal være unikke inden for skabelonen."""
    template = get_template(artifact_id)
    keys = [s.key for s in template.sections]
    assert len(keys) == len(set(keys)), (
        f"{artifact_id} har duplikat-keys: {[k for k in keys if keys.count(k) > 1]}"
    )


@pytest.mark.parametrize("artifact_id", ALL_NEW_IDS)
def test_compute_status_empty_returns_mangler(artifact_id):
    """Tom content → status 'mangler'."""
    template = get_template(artifact_id)
    assert compute_status(template, {}) == "mangler"
    assert compute_status(template, None) == "mangler"


@pytest.mark.parametrize("artifact_id", ALL_NEW_IDS)
def test_compute_status_partial_returns_i_gang(artifact_id):
    """Delvist udfyldt → status 'i_gang'."""
    template = get_template(artifact_id)
    required = list(template.required_section_keys())
    assert len(required) >= 1
    # Udfyld kun én required-sektion (templates har alle ≥5 required)
    partial_content = {required[0]: "noget tekst"}
    status = compute_status(template, partial_content)
    assert status == "i_gang", (
        f"{artifact_id}: forventede 'i_gang' med kun 1 af "
        f"{len(required)} required udfyldt, fik '{status}'"
    )


@pytest.mark.parametrize("artifact_id", ALL_NEW_IDS)
def test_compute_status_full_returns_faerdig(artifact_id):
    """Alle required udfyldt → status 'faerdig'."""
    template = get_template(artifact_id)
    required = template.required_section_keys()
    full_content = {key: "udfyldt indhold" for key in required}
    assert compute_status(template, full_content) == "faerdig"


# ---- Generelle invarianter --------------------------------------------------

def test_artifact_templates_dict_has_no_duplicates():
    """ARTIFACT_TEMPLATES dict skal ikke have duplikat-IDs."""
    ids = list(ARTIFACT_TEMPLATES.keys())
    assert len(ids) == len(set(ids))


def test_artifact_templates_count():
    """Sanity-check at vi har 28 templates efter P1+P2-tilføjelse (22 + 6)."""
    assert len(ARTIFACT_TEMPLATES) == 28


def test_all_known_ids_includes_new():
    """all_known_ids() skal inkludere alle 6 nye templates."""
    known = all_known_ids()
    for nid in ALL_NEW_IDS:
        assert nid in known


def test_list_templates_includes_new_with_full_data():
    """list_templates() (bruges af /drift) skal returnere de nye med fuld data."""
    templates_dict = {t["id"]: t for t in list_templates()}
    for nid in ALL_NEW_IDS:
        assert nid in templates_dict
        t = templates_dict[nid]
        assert t["title"]
        assert t["summary"]
        assert t["category"] in {"ai_act", "forvaltning"}
        assert t["legal_basis"]
        assert t["sections"]


def test_no_template_id_collides_with_existing():
    """Bekræft at de 6 nye IDs ikke kolliderer med tidligere artefakter."""
    pre_existing = {
        "risikostyringsplan", "datasaet_dokumentation",
        "teknisk_dokumentation_art11", "logningsspecifikation",
        "human_oversight_protokol", "eu_database_registrering",
        "partshoringsbrev", "frist_dokumentation",
        "kvittering_for_modtagelse", "sagsbehandler_review_protokol",
        "begrundelsesskabelon_godkendt_af_jurist",
        "procedure_til_lovhenvisnings_verifikation",
        "klagevejledning_skabelon", "retsgrundlag_dokumentation",
        "menneskelig_indgriben_proces", "bestridelsesproces",
        "transparenstekst_til_registrerede", "dpia_dokument",
        "dpo_udtalelse", "dpia_taerskelsvurdering",
        "databehandleraftale_dbs", "ai_indkoeb_tjekliste",
    }
    for nid in ALL_NEW_IDS:
        assert nid not in pre_existing, (
            f"{nid} kolliderer med tidligere artifact-ID"
        )


# ---- P1+P2-specifikke krav --------------------------------------------------

def test_eu_mcc_klausuler_has_klausul_sections():
    """eu_mcc_klausuler skal have sektioner der starter med 'klausul_'."""
    t = get_template("eu_mcc_klausuler")
    klausul_keys = [s.key for s in t.sections if s.key.startswith("klausul_")]
    assert len(klausul_keys) >= 6, (
        f"eu_mcc_klausuler skal have ≥6 klausul_*-sektioner, fandt {len(klausul_keys)}"
    )


def test_trustworthy_ai_rating_has_seven_dimensions():
    """trustworthy_ai_rating skal have 7 _score-felter (HLEG's 7 principper)."""
    t = get_template("trustworthy_ai_rating")
    score_keys = [s.key for s in t.sections if s.key.endswith("_score")]
    assert len(score_keys) == 7, (
        f"trustworthy_ai_rating skal have præcis 7 _score-sektioner, fandt {len(score_keys)}"
    )
    # Alle score-felter skal være enum 1-5
    for s in t.sections:
        if s.key.endswith("_score"):
            assert s.field_type == "enum"
            assert s.enum_values == ["1", "2", "3", "4", "5"]


def test_incident_reporting_art73_has_alvors_klassifikation():
    """incident_reporting_art73 skal have alvors-klassifikation som enum."""
    t = get_template("incident_reporting_art73")
    alvors = [s for s in t.sections if s.key == "alvorsklassifikation"]
    assert len(alvors) == 1
    assert alvors[0].field_type == "enum"
    assert "doedsfald" in alvors[0].enum_values


def test_ce_maerkning_guide_covers_all_seven_steps():
    """ce_maerkning_guide skal dække alle 7 trin (Art. 43-49)."""
    t = get_template("ce_maerkning_guide")
    trin_keys = [s.key for s in t.sections if s.key.startswith("trin_")]
    # trin_5 har to felter (boolean + dato_reference) så vi forventer ≥7
    distinct_trin = {k.split("_")[1] for k in trin_keys}
    assert len(distinct_trin) >= 7, (
        f"ce_maerkning_guide skal dække 7 distinct trin, fandt {distinct_trin}"
    )


def test_ai_faerdigheder_program_references_kl_inspirationskatalog():
    """ai_faerdigheder_program skal linke til KL's inspirationskatalog."""
    t = get_template("ai_faerdigheder_program")
    has_kl_link = any(
        "kl.dk" in r.url.lower() or "KL" in r.publisher
        for r in t.external_resources
    )
    assert has_kl_link, "ai_faerdigheder_program skal henvise til KL-katalog"


def test_leverandoer_due_diligence_has_konklusion_enum():
    """leverandoer_due_diligence skal have konklusion-felt som enum."""
    t = get_template("leverandoer_due_diligence")
    konklusion = [s for s in t.sections if s.key == "konklusion"]
    assert len(konklusion) == 1
    assert konklusion[0].field_type == "enum"
    assert "godkendt" in konklusion[0].enum_values
    assert "afvist" in konklusion[0].enum_values
