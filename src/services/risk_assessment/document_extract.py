"""Dokument-ekstraktion — pdf/docx → ren tekst.

Understøtter PDF (pypdf) og DOCX (python-docx). Andre typer afvises.
Max 10 MB pr. fil. Returnerer en liste af ExtractedDoc med filnavn + tekst
så fact-extractoren kan referere til kilden.
"""

import io
import logging
from dataclasses import dataclass

logger = logging.getLogger("bifrost.risk_assessment.extract")

MAX_BYTES = 10 * 1024 * 1024  # 10 MB
SUPPORTED_EXT = (".pdf", ".docx", ".txt", ".md")


class DocumentExtractError(Exception):
    pass


@dataclass
class ExtractedDoc:
    filename: str
    text: str
    char_count: int
    kind: str  # pdf | docx | txt


def extract_document(filename: str, content: bytes) -> ExtractedDoc:
    """Udtræk tekst fra én fil. Raises DocumentExtractError ved ikke-understøttet type."""
    if not content:
        raise DocumentExtractError(f"{filename}: tom fil")
    if len(content) > MAX_BYTES:
        raise DocumentExtractError(
            f"{filename}: for stor ({len(content) // 1024 // 1024} MB > 10 MB)"
        )

    lower = filename.lower()
    if lower.endswith(".pdf"):
        return ExtractedDoc(filename, _extract_pdf(content), 0, "pdf")._with_count()
    if lower.endswith(".docx"):
        return ExtractedDoc(filename, _extract_docx(content), 0, "docx")._with_count()
    if lower.endswith((".txt", ".md")):
        text = content.decode("utf-8", errors="replace")
        return ExtractedDoc(filename, text, 0, "txt")._with_count()

    raise DocumentExtractError(
        f"{filename}: ikke-understøttet filtype (kun {', '.join(SUPPORTED_EXT)})"
    )


def extract_many(files: list[tuple[str, bytes]]) -> list[ExtractedDoc]:
    """Udtræk fra flere filer. Springer fejlende over men logger dem.

    files: liste af (filename, content_bytes)
    """
    out: list[ExtractedDoc] = []
    for filename, content in files:
        try:
            out.append(extract_document(filename, content))
        except DocumentExtractError as exc:
            logger.warning("Dokument-ekstraktion sprunget over: %s", exc)
    return out


def _extract_pdf(content: bytes) -> str:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(content))
    except Exception as exc:
        raise DocumentExtractError(f"Kunne ikke læse PDF: {exc}") from exc

    parts = []
    for i, page in enumerate(reader.pages):
        try:
            txt = page.extract_text() or ""
        except Exception as exc:  # pragma: no cover - robusthed mod korrupte sider
            logger.warning("PDF side %d kunne ikke læses: %s", i, exc)
            txt = ""
        if txt.strip():
            parts.append(txt)
    return "\n\n".join(parts)


def _extract_docx(content: bytes) -> str:
    from docx import Document

    try:
        doc = Document(io.BytesIO(content))
    except Exception as exc:
        raise DocumentExtractError(f"Kunne ikke læse DOCX: {exc}") from exc

    parts = []
    # Paragraffer
    for p in doc.paragraphs:
        if p.text.strip():
            parts.append(p.text)
    # Tabeller — vigtigt: DBA bilag A/B/E ligger ofte i tabeller
    for t in doc.tables:
        for row in t.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return "\n".join(parts)


def _with_count(self):  # helper bound below
    self.char_count = len(self.text)
    return self


# Bind helper til dataclass (undgår at gentage i hver gren)
ExtractedDoc._with_count = _with_count


def combine_for_prompt(docs: list[ExtractedDoc], *, max_chars_per_doc: int = 30000) -> str:
    """Saml ekstraheret tekst til ét prompt-venligt input med kilde-labels.

    Trunkerer hvert dokument til max_chars_per_doc så vi ikke sprænger context.
    MSA/DBA kan være lange — 30k tegn pr. dok er typisk rigeligt til de
    relevante klausuler.
    """
    blocks = []
    for d in docs:
        text = d.text[:max_chars_per_doc]
        truncated = " [...trunkeret...]" if len(d.text) > max_chars_per_doc else ""
        blocks.append(f"=== DOKUMENT: {d.filename} ({d.kind}) ===\n{text}{truncated}")
    return "\n\n".join(blocks)
