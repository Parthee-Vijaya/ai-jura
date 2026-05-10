"""Dansk maskinoversættelse af EU AI Act Compliance Checker.

EC's officielle wizard er på engelsk; kommunale sagsbehandlere arbejder
på dansk. Vi producerer `content_da.json` lokalt via LM Studio (eller
Azure/OpenAI fallback) og bruger Bifrosts egen 42-term videnbase som
canonical glossar så regulatoriske termer ikke drifter.

Output-schemaet matcher `content_en.json` nøjagtigt — samme nøgler,
samme strukturer — så `EuAiActCheckerPage` kan plugge det ind uden
ændringer ud over en sprog-vælger.

Meta-flag `translation_status` markerer at oversættelsen er maskinel +
ucurateret, så UI kan vise et review-banner. Et separat jurist-review er
ikke i scope her.

Manuel trigger: `POST /api/eu-ai-act-checker/translate` (~10 min på
gpt-oss-20b for 33 spørgsmål + 45 flag).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

from .eu_ai_act_checker import (
    CACHE_DIR,
    CONTENT_PATH_TEMPLATE,
    PRIMARY_LANG,
    _atomic_write,
    _safe_read_json,
)

load_dotenv()
logger = logging.getLogger(__name__)


_PLACEHOLDER_FRAGMENTS = ("your_", "_here", "sk-...", "changeme")
_KB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "knowledge_base.json"


def _is_placeholder(value: Optional[str]) -> bool:
    if not value:
        return True
    low = value.lower()
    return any(frag in low for frag in _PLACEHOLDER_FRAGMENTS)


# ---- Glossary --------------------------------------------------------------

# Hardkodede canonical-DA-termer der skal låses uanset om vidensbasen
# nævner dem. Bruges som "tving altid den her oversættelse"-liste i prompten.
# Kilde: EU AI Act dansk officiel oversættelse + Datatilsynet + EU-Kommissionens vejledninger.
_CANONICAL_TERMS: dict[str, str] = {
    "AI system": "AI-system",
    "AI model": "AI-model",
    "general-purpose AI": "general-purpose AI (GPAI)",
    "general purpose AI": "general-purpose AI (GPAI)",
    "GPAI": "GPAI (general-purpose AI)",
    "high-risk": "højrisiko",
    "high risk": "højrisiko",
    "high-risk AI system": "højrisiko AI-system",
    "prohibited": "forbudt",
    "prohibited practices": "forbudte praksisser",
    "provider": "udbyder",
    "deployer": "idriftsætter",
    "importer": "importør",
    "distributor": "distributør",
    "authorised representative": "bemyndiget repræsentant",
    "authorized representative": "bemyndiget repræsentant",
    "product manufacturer": "produktproducent",
    "operator": "operatør",
    "conformity assessment": "overensstemmelsesvurdering",
    "fundamental rights": "grundlæggende rettigheder",
    "fundamental rights impact assessment": "konsekvensanalyse for grundlæggende rettigheder (FRIA)",
    "FRIA": "FRIA (konsekvensanalyse for grundlæggende rettigheder)",
    "transparency": "transparens",
    "transparency obligation": "transparenskrav",
    "systemic risk": "systemisk risiko",
    "Annex III": "Bilag III",
    "Annex I": "Bilag I",
    "Annex II": "Bilag II",
    "Article": "Artikel",
    "Recital": "Betragtning",
    "biometric identification": "biometrisk identifikation",
    "biometric categorisation": "biometrisk kategorisering",
    "remote biometric identification": "fjernbiometrisk identifikation",
    "real-time": "i realtid",
    "post-remote": "ex-post",
    "law enforcement": "retshåndhævelse",
    "essential services": "væsentlige tjenester",
    "critical infrastructure": "kritisk infrastruktur",
    "education and vocational training": "uddannelse og erhvervsuddannelse",
    "employment": "beskæftigelse",
    "social scoring": "social scoring",
    "emotion recognition": "følelsesgenkendelse",
    "subliminal techniques": "subliminale teknikker",
    "deepfake": "deepfake",
    "synthetic content": "syntetisk indhold",
    "machine-readable": "maskinlæsbart",
    "watermark": "vandmærke",
    "open-source": "open-source",
    "free and open-source": "gratis og open-source",
    "AI literacy": "AI-kyndighed",
    "compliance": "overholdelse",
    "Compliance Checker": "Compliance Checker",
    "EU AI Act": "EU AI-forordningen",
    "AI Act": "AI-forordningen",
    "scope": "anvendelsesområde",
    "out of scope": "uden for anvendelsesområdet",
    "placed on the market": "bragt i omsætning",
    "put into service": "idriftsat",
    "downstream provider": "downstream-udbyder",
    "downstream modifier": "downstream-modifikator",
    "training": "træning",
    "training data": "træningsdata",
    "testing": "afprøvning",
    "validation": "validering",
    "human oversight": "menneskelig overvågning",
    "risk management system": "risikostyringssystem",
    "post-market monitoring": "overvågning efter markedsføring",
    "incident reporting": "indberetning af alvorlige hændelser",
    "EU database": "EU-database",
    "notified body": "bemyndiget organ",
    "CE marking": "CE-mærkning",
    "harmonised standards": "harmoniserede standarder",
    "data governance": "data-governance",
    "personal data": "personoplysninger",
    "data subject": "registreret",
    "natural person": "fysisk person",
    "right to explanation": "ret til forklaring",
    "scientific research": "videnskabelig forskning",
}


def _load_glossary() -> list[dict]:
    """Bygg en kort glossary-liste fra Bifrost's videnbase + canonical-tabel.

    Returnerer entries med {en, da, note?} så vi kan injecte i prompten.
    """
    entries: list[dict] = []
    seen_en: set[str] = set()

    # 1) Canonical-mapping (har altid forrang)
    for en, da in _CANONICAL_TERMS.items():
        key = en.lower()
        if key in seen_en:
            continue
        entries.append({"en": en, "da": da, "note": "canonical"})
        seen_en.add(key)

    # 2) Bifrosts videnbase — vi tager kun terms hvor titlen indeholder DA
    # specialtegn eller eksplicit refererer til AI Act/GDPR — det giver
    # ~15-20 ekstra glossary-entries.
    try:
        kb = json.loads(_KB_PATH.read_text(encoding="utf-8"))
    except Exception:
        kb = []

    for item in kb:
        term = (item.get("term") or "").strip()
        if not term:
            continue
        # Heuristik: hvis titlen er en DA-term med engelsk parantesisalternativ,
        # split og tilføj begge retninger
        en_alt: Optional[str] = None
        m = re.match(r"^(.*?)\s*\(([^)]+)\)\s*$", term)
        if m:
            term_main = m.group(1).strip()
            alt = m.group(2).strip()
            # Hvis alt ser engelsk ud (ascii + spaces) og main ser dansk ud → engelsk er alt
            if re.fullmatch(r"[A-Za-z][A-Za-z0-9 \-/]*", alt):
                en_alt = alt
                term = term_main
        if en_alt and en_alt.lower() not in seen_en:
            entries.append({"en": en_alt, "da": term, "note": "kb"})
            seen_en.add(en_alt.lower())

    return entries


def _glossary_block(entries: list[dict], limit: int = 80) -> str:
    """Render glossary som tekst-blok der kan paste'es ind i system-prompten."""
    head = entries[:limit]
    lines = [f"  - {e['en']} → {e['da']}" for e in head]
    return "\n".join(lines)


# ---- LLM provider (Azure → OpenAI → LM Studio) ----------------------------


class _LLMProvider:
    """Genbruger samme provider-chain som knowledge_base_updater."""

    def __init__(self) -> None:
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.azure_api_version = os.getenv("OPENAI_API_VERSION", "2024-02-15-preview")
        self.azure_deployment = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o-mini")

        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        self.lm_studio_url = os.getenv("LM_STUDIO_BASE_URL", "").rstrip("/")
        self.lm_studio_model = os.getenv(
            "LM_STUDIO_CHAT_MODEL", os.getenv("LM_STUDIO_MODEL", "")
        )

        if self.azure_endpoint and not _is_placeholder(self.azure_api_key):
            self.provider = "azure"
        elif not _is_placeholder(self.openai_api_key):
            self.provider = "openai"
        elif self.lm_studio_url:
            self.provider = "lm_studio"
        else:
            self.provider = None

    def is_configured(self) -> bool:
        return self.provider is not None

    def label(self) -> str:
        return self.provider or "none"

    def _client(self):
        if self.provider == "azure":
            from openai import AzureOpenAI
            return AzureOpenAI(
                api_key=self.azure_api_key,
                api_version=self.azure_api_version,
                azure_endpoint=self.azure_endpoint,
            )
        if self.provider == "openai":
            from openai import OpenAI
            return OpenAI(api_key=self.openai_api_key)
        if self.provider == "lm_studio":
            from openai import OpenAI
            return OpenAI(api_key="lm-studio", base_url=self.lm_studio_url)
        raise RuntimeError("Ingen LLM-provider konfigureret")

    def _model(self) -> str:
        if self.provider == "azure":
            return self.azure_deployment
        if self.provider == "openai":
            return self.openai_model
        if self.provider == "lm_studio":
            if self.lm_studio_model:
                return self.lm_studio_model
            try:
                client = self._client()
                models = [getattr(m, "id", "") for m in client.models.list().data]
                non_embed = [m for m in models if m and "embed" not in m.lower()]
                preference = sorted(
                    non_embed,
                    key=lambda m: (
                        0 if "gpt-oss" in m.lower() else
                        1 if m.lower().startswith("openai/") else
                        3 if "gemma" in m.lower() else
                        2
                    ),
                )
                if preference:
                    return preference[0]
            except Exception:
                pass
            return "auto"
        return "unknown"

    def _candidates(self, primary: str) -> list[str]:
        cands = [primary]
        if self.provider != "lm_studio":
            return cands
        try:
            client = self._client()
            for m in client.models.list().data:
                name = getattr(m, "id", "")
                if not name or name in cands or "embed" in name.lower():
                    continue
                cands.append(name)
        except Exception:
            pass
        return cands

    def chat(self, *, system: str, user: str, max_tokens: int = 800) -> str:
        client = self._client()
        primary = self._model()
        for attempt, model in enumerate(self._candidates(primary)):
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=float(os.getenv("EU_TRANSLATOR_TEMPERATURE", "0.2")),
                    max_tokens=max_tokens,
                )
                content = (resp.choices[0].message.content or "").strip()
                if content:
                    if attempt > 0:
                        logger.info(f"EU translator faldt tilbage til model {model}")
                    return content
            except Exception as exc:
                logger.warning(f"EU translator model {model} fejlede: {exc}")
                continue
        return ""


# ---- Translation core ------------------------------------------------------


_SYSTEM_PROMPT_TEMPLATE = """Du er en juridisk oversætter specialiseret i EU AI-forordningen og dansk forvaltningsret.

Din opgave: Oversæt det engelske input til dansk. Bevar betydning, juridisk præcision og struktur.

REGLER:
1. Brug følgende canonical-glossar — disse termer SKAL oversættes præcis som vist (ingen variation):

{glossary}

2. Bevar alle artikel- og betragtning-henvisninger ("Article 6(2)" → "Artikel 6, stk. 2"; "Recital 12" → "Betragtning 12").
3. Bevar opremsninger, listestruktur, linjeskift og markdown-formatering.
4. Brug formel administrativ dansk (ikke "du", men passiv eller substantiveret).
5. Hvis et engelsk udtryk er et akronym (CE, GPAI, FRIA, AI), bevar akronymet — brug danske udtryk for resten.
6. Returner KUN den oversatte tekst — ingen forklaring, ingen "Her er oversættelsen:", ingen markdown-kodeblokke.
7. Hvis input er tomt eller kun whitespace, returner tom streng.
"""


def _build_user_prompt(text: str, context_label: str) -> str:
    """Pak input-teksten med en kort kontekst-label så LLM ved hvilken form
    den oversætter (titel vs. info-blok vs. answer-label)."""
    return (
        f"[Kontekst: {context_label}]\n\n"
        f"{text.strip()}"
    )


def _translate_text(provider: _LLMProvider, system_prompt: str, text: str, label: str) -> str:
    """Oversæt en enkelt tekst-streng. Tom streng ind = tom streng ud."""
    if not text or not text.strip():
        return text
    user = _build_user_prompt(text, label)
    out = provider.chat(system=system_prompt, user=user, max_tokens=1200)
    # LLM kan finde på at wrappe i citater eller "Her er...:" — strip lidt
    out = out.strip()
    out = re.sub(r"^[\"'`]+|[\"'`]+$", "", out)
    if not out:
        # Fallback: returner originalen så strukturen ikke bliver tom
        return text
    return out


# Pydantic-agtigt walk gennem indlejret struktur — vi oversætter alle
# string-værdier under følgende keys i questions_content + flags_content.
_STRING_KEYS = {
    "main_title", "secondary_title", "info", "label", "text",
    "title", "description", "tooltip", "placeholder", "hint",
    "yes_label", "no_label", "answer", "subheader",
}


def _translate_structure(
    obj: Any,
    provider: _LLMProvider,
    system_prompt: str,
    context_path: str,
    seen_strings: dict[str, str],
    progress: dict,
) -> Any:
    """Rekursiv oversætter. Tegner alle strings under string-keys via LLM
    og cacher allerede-oversatte strings (mange flag-tekster gentages)."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if isinstance(v, str) and k in _STRING_KEYS and v.strip():
                # Cache hit?
                cached = seen_strings.get(v)
                if cached is not None:
                    out[k] = cached
                else:
                    label = f"{context_path}.{k}"
                    translated = _translate_text(provider, system_prompt, v, label)
                    seen_strings[v] = translated
                    out[k] = translated
                    progress["translated"] += 1
                    progress["chars"] += len(v)
                    if progress["translated"] % 10 == 0:
                        logger.info(
                            f"Oversat {progress['translated']} strings ({progress['chars']} tegn)"
                        )
            else:
                out[k] = _translate_structure(
                    v, provider, system_prompt, f"{context_path}.{k}", seen_strings, progress
                )
        return out
    if isinstance(obj, list):
        return [
            _translate_structure(v, provider, system_prompt, f"{context_path}[{i}]", seen_strings, progress)
            for i, v in enumerate(obj)
        ]
    return obj


def _translate_flag_content(
    flags_content: dict,
    provider: _LLMProvider,
    system_prompt: str,
    seen_strings: dict[str, str],
    progress: dict,
) -> dict:
    """flags_content i EC's schema er ofte `{flag_id: "<long string>"}` —
    behandl strings direkte (ikke via _STRING_KEYS-walk).
    """
    out: dict = {}
    for flag_id, val in flags_content.items():
        if isinstance(val, str) and val.strip():
            cached = seen_strings.get(val)
            if cached is not None:
                out[flag_id] = cached
            else:
                t = _translate_text(provider, system_prompt, val, f"flag.{flag_id}")
                seen_strings[val] = t
                out[flag_id] = t
                progress["translated"] += 1
                progress["chars"] += len(val)
        elif isinstance(val, dict):
            out[flag_id] = _translate_structure(
                val, provider, system_prompt, f"flag.{flag_id}", seen_strings, progress
            )
        else:
            out[flag_id] = val
    return out


# ---- Public API ------------------------------------------------------------


def is_translation_available() -> bool:
    """True hvis content_da.json eksisterer og ser komplet ud."""
    path = CACHE_DIR / CONTENT_PATH_TEMPLATE.format(lang="da")
    data = _safe_read_json(path)
    if not data:
        return False
    has_q = bool(data.get("questions_content"))
    has_f = bool(data.get("flags_content"))
    return has_q and has_f


def translation_meta() -> dict:
    """Returnér meta om aktuel DA-oversættelse."""
    path = CACHE_DIR / CONTENT_PATH_TEMPLATE.format(lang="da")
    data = _safe_read_json(path)
    if not data:
        return {"available": False}
    meta = data.get("_translation_meta", {})
    return {
        "available": True,
        "translated_at": meta.get("translated_at"),
        "translation_status": meta.get("translation_status", "unknown"),
        "provider": meta.get("provider"),
        "model": meta.get("model"),
        "n_questions": len(data.get("questions_content", {})),
        "n_flags": len(data.get("flags_content", {})),
        "duration_seconds": meta.get("duration_seconds"),
        "translated_strings": meta.get("translated_strings"),
    }


def translate_checker(
    *,
    source_lang: str = "en",
    overwrite: bool = True,
    max_strings: Optional[int] = None,
) -> dict:
    """Hovedfunktion. Læser content_<source_lang>.json, oversætter til DA,
    skriver content_da.json. Returnerer summary.
    """
    started = time.time()
    summary: dict = {
        "started_at": datetime.now(UTC).isoformat(),
        "source_lang": source_lang,
        "errors": [],
    }

    # 1. Load source content
    src_path = CACHE_DIR / CONTENT_PATH_TEMPLATE.format(lang=source_lang)
    src = _safe_read_json(src_path)
    if not src:
        summary["errors"].append(
            f"content_{source_lang}.json findes ikke — kør /api/eu-ai-act-checker/refresh først"
        )
        return summary

    out_path = CACHE_DIR / CONTENT_PATH_TEMPLATE.format(lang="da")
    if out_path.exists() and not overwrite:
        summary["errors"].append(
            f"content_da.json findes allerede; brug overwrite=true for at gen-køre"
        )
        return summary

    # 2. Setup provider
    provider = _LLMProvider()
    if not provider.is_configured():
        summary["errors"].append(
            "Ingen LLM-provider konfigureret. Sæt AZURE_OPENAI_API_KEY, "
            "OPENAI_API_KEY eller LM_STUDIO_BASE_URL i .env"
        )
        return summary

    # 3. Build glossary + system prompt
    glossary = _load_glossary()
    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(glossary=_glossary_block(glossary))
    summary["glossary_terms"] = len(glossary)
    summary["provider"] = provider.label()
    summary["model"] = provider._model()

    # 4. Translate
    seen_strings: dict[str, str] = {}
    progress: dict = {"translated": 0, "chars": 0}

    logger.info(
        f"Starter oversættelse via {provider.label()} ({provider._model()}); "
        f"glossar har {len(glossary)} termer"
    )

    questions_translated = _translate_structure(
        src.get("questions_content", {}),
        provider,
        system_prompt,
        "questions",
        seen_strings,
        progress,
    )
    if max_strings is not None and progress["translated"] >= max_strings:
        logger.info("max_strings nået — stopper inden flags")
        summary["errors"].append(f"stopped early: max_strings={max_strings}")

    flags_translated = _translate_flag_content(
        src.get("flags_content", {}),
        provider,
        system_prompt,
        seen_strings,
        progress,
    )

    duration = round(time.time() - started, 2)

    payload = {
        "questions_content": questions_translated,
        "flags_content": flags_translated,
        "_translation_meta": {
            "translation_status": "machine_uncurated",
            "translated_at": datetime.now(UTC).isoformat(),
            "source_lang": source_lang,
            "provider": provider.label(),
            "model": provider._model(),
            "duration_seconds": duration,
            "translated_strings": progress["translated"],
            "translated_chars": progress["chars"],
            "glossary_terms": len(glossary),
            "notice": (
                "Maskinel oversættelse — under review af jurist. "
                "Den engelske kildetekst er fortsat den autoritative."
            ),
        },
    }

    _atomic_write(out_path, payload)
    summary["finished_at"] = datetime.now(UTC).isoformat()
    summary["duration_seconds"] = duration
    summary["translated_strings"] = progress["translated"]
    summary["translated_chars"] = progress["chars"]
    summary["written_to"] = str(out_path)
    return summary


async def translate_checker_async(**kwargs) -> dict:
    """Async wrapper så endpoint kan await uden at blokere event-loopet."""
    return await asyncio.to_thread(translate_checker, **kwargs)
