"""LLM-genereret udkast af evidens-artefakter.

Sagsbehandler klikker "Generer udkast" på en evidens-skabelon (fx
risikostyringsplan). LLM får:
  - Skabelonens lovhjemler + sections + prompts
  - Sagens intake_state (behov, system_description, persondata-info)
  - Eventuelle eksisterende svar (bruger-input bevares)

LLM returnerer et udkast pr. sektion. Bruger reviewer + redigerer.

Output markeres i audit-trail som "AI-genereret udkast" så det ikke
forveksles med menneskelig udfyldelse.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Optional

import httpx

logger = logging.getLogger("bifrost.evidence_draft")


SYSTEM_PROMPT = """Du er en compliance-konsulent for Kalundborg Kommune.
Din opgave er at lave UDKAST til et evidens-dokument som en sagsbehandler
senere kan rette + udvide.

Du får:
- En evidens-skabelon med titel, sektioner (key + heading + prompt + required)
- Konteksten: sagens beskrivelse + intake-data + persondata-info
- Eventuelt eksisterende svar (skal bevares, ikke overskrives)

Du skal generere udkast til TOMME required-sektioner. Skriv konkret,
operativt og dansk. Brug konjunktiv ("systemet bør", "vi vil") når
detaljer er antaget. Citér aldrig juridiske paragraffer du ikke er
100% sikker på — brug i stedet generelle formuleringer.

Du svarer KUN med valid JSON i præcis dette format:

{
  "section_key_1": "Udkast-tekst...",
  "section_key_2": "Udkast-tekst...",
  ...
}

KUN tomme sektioner skal udfyldes. Eksisterende svar må IKKE overskrives.
Hvis du ikke kan lave et udkast for en sektion (mangler kontekst), undlad
nøglen helt.
"""


class EvidenceDraftError(Exception):
    """Raised når draft-generering fejler."""


def generate_evidence_draft(
    *,
    template: dict[str, Any],
    case_intake: dict[str, Any],
    existing_content: dict[str, Any] | None = None,
    timeout: float = 60.0,
) -> dict[str, str]:
    """Generer udkast for tomme sektioner i en evidens-skabelon.

    Args:
        template: dict fra ARTIFACT_TEMPLATES (id, title, summary, sections, legal_basis)
        case_intake: case.intake_state (behov, system_description, m.fl.)
        existing_content: nuværende udfyldte sektioner — disse bevares
        timeout: max sekunder for LLM

    Returns:
        Dict med {section_key: generated_text} for KUN tomme sektioner
    """
    if not template or "sections" not in template:
        raise ValueError("template mangler 'sections'")
    if not case_intake:
        raise ValueError("case_intake må ikke være tom (LLM kræver kontekst)")

    existing_content = existing_content or {}

    # Identificér tomme sektioner
    sections = template.get("sections", [])
    empty_keys = [
        s["key"]
        for s in sections
        if s.get("required") and not _is_filled(existing_content.get(s["key"]))
    ]
    if not empty_keys:
        return {}  # alt er udfyldt

    # Byg LLM-prompt
    user_message = _build_user_prompt(template, case_intake, existing_content, empty_keys)

    # Kald LLM
    content = _call_llm(user_message, timeout=timeout)

    # Parse + filtrér
    drafts = _parse_llm_json(content)
    # Behold KUN keys i empty_keys så vi ikke overskriver bruger-svar
    filtered = {k: v for k, v in drafts.items() if k in empty_keys and isinstance(v, str) and v.strip()}
    return filtered


def _is_filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return bool(value)


def _build_user_prompt(
    template: dict[str, Any],
    case_intake: dict[str, Any],
    existing_content: dict[str, Any],
    empty_keys: list[str],
) -> str:
    """Byg user-message med template + kontekst + ønskede sektioner."""
    # Sektion-beskrivelser
    section_lines = []
    for s in template.get("sections", []):
        if s["key"] in empty_keys:
            marker = "[UDFYLD]"
        elif _is_filled(existing_content.get(s["key"])):
            marker = "[EKSISTERENDE — IKKE OVERSKRIV]"
        else:
            marker = "[VALGFRI]"
        section_lines.append(
            f"- key='{s['key']}' {marker}\n"
            f"  heading: {s.get('heading', '')}\n"
            f"  prompt: {s.get('prompt', '')}\n"
            f"  field_type: {s.get('field_type', 'textarea')}"
        )
    sections_text = "\n\n".join(section_lines)

    # Lovhjemler
    legal_lines = []
    for lb in template.get("legal_basis", []):
        legal_lines.append(f"- {lb.get('lov')}, {lb.get('artikel')}: \"{(lb.get('citat') or '')[:200]}\"")
    legal_text = "\n".join(legal_lines) if legal_lines else "(ingen specifik lovhjemmel angivet)"

    # Intake-kontekst
    intake_summary = {
        k: v for k, v in case_intake.items()
        if k in {
            "behov", "system_description", "indkoeb_eller_udvikling",
            "behandler_persondata", "persondata_typer",
            "automatiserede_beslutninger", "kritiske_formaal",
            "ai_risiko_kategori", "fagomraade",
        }
    }

    return f"""EVIDENS-SKABELON: {template.get('title', '')}

OPSUMMERING: {template.get('summary', '')[:500]}

LOVHJEMLER:
{legal_text}

SAGENS KONTEKST:
{json.dumps(intake_summary, ensure_ascii=False, indent=2)}

EVENTUELLE EKSISTERENDE SVAR (skal bevares):
{json.dumps({k: v for k, v in existing_content.items() if _is_filled(v)}, ensure_ascii=False, indent=2)}

SEKTIONER:
{sections_text}

Generer udkast KUN for sektioner med [UDFYLD]. Returnér JSON dict med
section_key som nøgle og udkast-tekst som value."""


def _call_llm(user_message: str, *, timeout: float) -> str:
    """Kald LLM (LM Studio → Azure → OpenAI)."""
    lm_studio_url = (os.getenv("LM_STUDIO_BASE_URL") or "").rstrip("/")
    if lm_studio_url:
        return _post_openai_compatible(
            base_url=lm_studio_url,
            api_key=os.getenv("LM_STUDIO_API_KEY", "lm-studio"),
            model=os.getenv("LM_STUDIO_CHAT_MODEL") or os.getenv("LM_STUDIO_MODEL") or "local-model",
            user_message=user_message,
            timeout=timeout,
        )

    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    if azure_endpoint and os.getenv("AZURE_OPENAI_API_KEY"):
        return _post_azure(
            endpoint=azure_endpoint,
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            deployment=os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o-mini"),
            api_version=os.getenv("OPENAI_API_VERSION", "2024-02-15-preview"),
            user_message=user_message,
            timeout=timeout,
        )

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        # Respect OPENAI_BASE_URL so deployments pointing at a local
        # OpenAI-compatible endpoint (Ollama, LM Studio, vLLM, …) stay local.
        return _post_openai_compatible(
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            api_key=openai_key,
            model=os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini"),
            user_message=user_message,
            timeout=timeout,
        )

    raise EvidenceDraftError(
        "Ingen LLM-provider konfigureret. Sæt LM_STUDIO_BASE_URL, "
        "AZURE_OPENAI_ENDPOINT eller OPENAI_API_KEY"
    )


def _post_openai_compatible(
    *, base_url: str, api_key: str, model: str, user_message: str, timeout: float,
) -> str:
    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 400 and "response_format" in exc.response.text:
            payload.pop("response_format", None)
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
        else:
            raise EvidenceDraftError(
                f"LLM-API {exc.response.status_code}: {exc.response.text[:200]}"
            ) from exc
    except httpx.RequestError as exc:
        raise EvidenceDraftError(f"LLM-connection: {exc}") from exc

    body = resp.json()
    content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content:
        raise EvidenceDraftError(f"LLM tom respons: {body}")
    return content


def _post_azure(
    *, endpoint: str, api_key: str, deployment: str, api_version: str,
    user_message: str, timeout: float,
) -> str:
    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }
    headers = {"api-key": api_key, "Content-Type": "application/json"}

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise EvidenceDraftError(
            f"Azure {exc.response.status_code}: {exc.response.text[:200]}"
        ) from exc

    body = resp.json()
    return body.get("choices", [{}])[0].get("message", {}).get("content", "")


_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```")


def _parse_llm_json(content: str) -> dict[str, Any]:
    text = content.strip()
    m = _JSON_FENCE.search(text)
    if m:
        text = m.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m2 = re.search(r"\{[\s\S]*\}", text)
        if not m2:
            raise EvidenceDraftError(f"LLM invalid JSON: {content[:200]}")
        data = json.loads(m2.group(0))
    if not isinstance(data, dict):
        raise EvidenceDraftError("LLM returnerede ikke et JSON-object")
    return data
