"""Tests for risikovurderingsmotorens deterministiske kerne:
  - models: normalisering, helpers
  - document_extract: pdf/docx/txt + afvisning
  - docx_assembler: udfyldning mod den RIGTIGE master-template
  - verifier: detekterer placeholder-rester + forkert rækkeantal

LLM-services testes separat med mocks (test_risk_assessment_llm.py).
"""

import io
import os

import pytest
from docx import Document

from src.services.risk_assessment.models import (
    DataKategori,
    Niveau,
    Risiko,
    Risikovurdering,
    SystemFacts,
    normalize_niveau,
)
from src.services.risk_assessment.document_extract import (
    DocumentExtractError,
    extract_document,
    combine_for_prompt,
)
from src.services.risk_assessment.docx_assembler import (
    assemble_docx,
    get_template_path,
    output_filename,
)
from src.services.risk_assessment.verifier import verify_docx


# ---- models --------------------------------------------------------------


class TestModels:
    def test_normalize_niveau_aliases(self):
        assert normalize_niveau("mellem") == Niveau.MIDDEL
        assert normalize_niveau("high") == Niveau.HOEJ
        assert normalize_niveau("Lav-middel") == Niveau.LAV_MIDDEL
        assert normalize_niveau("hoj") == Niveau.HOEJ

    def test_normalize_niveau_fallback(self):
        assert normalize_niveau("garbage") == Niveau.MIDDEL
        assert normalize_niveau("") == Niveau.MIDDEL
        assert normalize_niveau(None) == Niveau.MIDDEL

    def test_har_foelsomme_data(self):
        f = SystemFacts(persondata_kategorier=[DataKategori.CPR])
        assert f.har_foelsomme_data()
        f2 = SystemFacts(persondata_kategorier=[DataKategori.ALMINDELIGE])
        assert not f2.har_foelsomme_data()

    def test_er_ekstern_leverandoer(self):
        ekstern = SystemFacts(leverandoer_navn="Acme", internt_udviklet=False)
        assert ekstern.er_ekstern_leverandoer()
        intern = SystemFacts(leverandoer_navn="", internt_udviklet=True)
        assert not intern.er_ekstern_leverandoer()

    def test_alle_felttekster_count(self):
        rv = Risikovurdering(facts=SystemFacts())
        assert len(rv.alle_felttekster()) == 14


# ---- document_extract ----------------------------------------------------


class TestDocumentExtract:
    def test_txt(self):
        d = extract_document("note.txt", b"hej verden")
        assert d.text == "hej verden"
        assert d.kind == "txt"
        assert d.char_count == 10

    def test_docx_roundtrip(self):
        # Byg et lille docx i hukommelsen
        doc = Document()
        doc.add_paragraph("Leverandør: Acme ApS")
        t = doc.add_table(rows=1, cols=2)
        t.rows[0].cells[0].text = "CPR"
        t.rows[0].cells[1].text = "Ja"
        buf = io.BytesIO()
        doc.save(buf)
        d = extract_document("dba.docx", buf.getvalue())
        assert "Acme ApS" in d.text
        assert "CPR" in d.text  # tabel-indhold med

    def test_rejects_unsupported(self):
        with pytest.raises(DocumentExtractError):
            extract_document("image.png", b"\x89PNG")

    def test_rejects_oversized(self):
        big = b"x" * (11 * 1024 * 1024)
        with pytest.raises(DocumentExtractError):
            extract_document("big.txt", big)

    def test_rejects_empty(self):
        with pytest.raises(DocumentExtractError):
            extract_document("empty.txt", b"")

    def test_combine_truncates(self):
        from src.services.risk_assessment.document_extract import ExtractedDoc
        docs = [ExtractedDoc("a.txt", "x" * 50000, 50000, "txt")]
        combined = combine_for_prompt(docs, max_chars_per_doc=1000)
        assert "trunkeret" in combined
        assert "a.txt" in combined


# ---- docx_assembler + verifier (mod RIGTIG master-template) --------------


def _full_rv(systemnavn="Testsystem", n_risks=8):
    risks = [
        Risiko(
            risiko=f"Risiko {i}",
            konsekvens_beskrivelse=f"Konsekvens {i} for de registrerede.",
            sandsynlighed=Niveau.LAV_MIDDEL,
            score=Niveau.MIDDEL,
            hvorfor=f"Begrundelse {i}.",
        )
        for i in range(1, n_risks + 1)
    ]
    return Risikovurdering(
        facts=SystemFacts(systemnavn=systemnavn, leverandoer_navn="TestCorp"),
        risici=risks,
        formaal_tekst="Formålet er at vurdere systemet.",
        omfang_tekst="Vurderingen dækker hele systemet.",
        ansvarlige_tekst="Partheepan Vijayamohan og Anne Dandanell.",
        baggrund_tekst="Projektets baggrund er behovet for X.",
        funktionalitet_tekst="Systemet gør Y og Z.",
        interessenter_tekst="Dataansvarlig: Kalundborg Kommune.",
        personoplysninger_tekst="Almindelige personoplysninger og CPR.",
        lokationer_tekst="Microsoft Azure EU-region.",
        adgangsrettigheder_tekst="Entra ID SSO + MFA.",
        saarbarheder_tekst="Ingen kritiske sårbarheder.",
        tiltag_tekst="Databehandleraftale og kryptering.",
        ansvarlige_tiltag_tekst="Partheepan er ansvarlig.",
        kontrolmekanismer_tekst="Månedlig log-gennemgang.",
        opdatering_tekst="Revideres årligt.",
    )


@pytest.mark.skipif(
    not os.path.exists(get_template_path()),
    reason="master-template ikke til stede",
)
class TestAssembler:
    def test_assemble_produces_valid_docx(self):
        data = assemble_docx(_full_rv())
        assert data[:2] == b"PK"  # docx = zip
        assert len(data) > 10000

    def test_systemnavn_in_title_and_intro(self):
        data = assemble_docx(_full_rv(systemnavn="Voicecraft"))
        doc = Document(io.BytesIO(data))
        assert "Voicecraft" in doc.paragraphs[0].text
        assert "Voicecraft" in doc.paragraphs[3].text
        assert "Plan2learn" not in doc.paragraphs[3].text

    def test_risk_table_row_count(self):
        data = assemble_docx(_full_rv(n_risks=10))
        doc = Document(io.BytesIO(data))
        # header + 10 risici
        assert len(doc.tables[5].rows) == 11

    def test_no_bracket_artifacts_when_all_filled(self):
        data = assemble_docx(_full_rv())
        doc = Document(io.BytesIO(data))
        # Table 6 har legitim guidance "Eksempler [OBS: ...]" (yp[1] — rør ikke),
        # så den udelades fra streng bracket-check. Table 0,1,2,7 må være rene.
        for ti in [0, 1, 2, 7]:
            txt = doc.tables[ti].rows[0].cells[0].text
            assert "[" not in txt, f"Table {ti} har '[' artefakt: {txt[:80]}"
            assert "]" not in txt, f"Table {ti} har ']' artefakt: {txt[:80]}"
            assert ".." not in txt, f"Table {ti} har dobbelt-punktum: {txt[:80]}"
        # Table 6: verificér at de FYLDTE felter landede rent (uden brackets)
        t6 = doc.tables[6].rows[0].cells[0].text
        assert "Databehandleraftale og kryptering." in t6
        assert "Partheepan er ansvarlig." in t6

    def test_guidance_tables_untouched(self):
        data = assemble_docx(_full_rv())
        doc = Document(io.BytesIO(data))
        # Table 3 + 4 er "Eksempler"-guidance — skal stadig være der
        assert "Eksempler på risici" in doc.tables[3].rows[0].cells[0].text
        assert "Eksempler på konsekvenser" in doc.tables[4].rows[0].cells[0].text

    def test_verify_passes_for_complete_doc(self):
        data = assemble_docx(_full_rv(n_risks=8))
        res = verify_docx(data, expected_n_risks=8)
        assert res.valid, res.problems
        assert res.n_risk_rows == 8

    def test_verify_catches_wrong_risk_count(self):
        data = assemble_docx(_full_rv(n_risks=8))
        res = verify_docx(data, expected_n_risks=10)
        assert not res.valid
        assert any("forventet 10" in p for p in res.problems)

    def test_output_filename(self):
        assert output_filename("Velatir") == "Databeskyttelsesretlig risikovurdering - Velatir.docx"
        assert "/" not in output_filename("A/B")
