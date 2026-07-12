"""LLM-baseret kvalitetsreview af udfyldt evidens.

Når en sagsbehandler markerer en evidens som "færdig", trigger denne service
en LLM-analyse der returnerer:
  - quality_score (1-5)
  - issues: liste af konkrete mangler eller inkonsistens
  - suggestions: forslag til forbedring
  - missing_legal_refs: lov-paragraffer der burde være nævnt

Det er IKKE en blocker — jurist beslutter stadig. Tips vises som sidepanel
i EvidenceEditor.

Output er deterministisk struktur så frontend kan rendere checkboxes /
prioriterede issues.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import httpx

logger = logging.getLogger("bifrost.evidence_review")


SYSTEM_PROMPT = """Du er en senior compliance-jurist der reviewer udfyldte
evidens-dokumenter for Kalundborg Kommune. Din opgave er at give konstruktiv,
operativ feedback — IKKE at godkende eller afvise.

Du får:
- Evidens-skabelonens titel + lovhjemler + sections
- Brugerens udfyldte indhold pr. sektion

Du vurderer:
1. Er hver required-sektion besvaret tilstrækkeligt? (ikke kun "ja" / "ok")
2. Er der konkret reference til lovhjemler hvor relevant?
3. Er der inkonsistens mellem sektioner?
4. Mangler der oplagte detaljer (hvem, hvornår, hvordan, kontaktperson)?
5. Er sproget konkret nok til at en revisor kan forstå det?

Du svarer KUN med valid JSON i præcis dette format:

{
  "quality_score": 1-5,
  "summary": "1-2 sætnings opsummering af kvaliteten",
  "issues": [
    {
      "section_key": "key fra skabelonen",
      "severity": "blocker" | "warning" | "tip",
      "message": "Konkret beskrivelse af problemet"
    }
  ],
  "suggestions": [
    "Specifik forbedringsforslag (1 sætning)"
  ],
  "missing_legal_refs": [
    "Lov-paragraf der burde være nævnt (fx 'GDPR Art. 32')"
  ]
}

Severity-skala:
- 'blocker' = sektion er ikke besvaret eller indeholder placeholder-tekst
- 'warning' = sektion er besvaret men mangler detaljer for myndighedstilsyn
- 'tip' = forbedring der vil hjælpe jurist / leder forstå hurtigere

Vær konkret og kortfattet. Maks 5 issues og 3 suggestions."""


class EvidenceReviewError(Exception):
    """Raised når review fejler."""


def review_evidence(
    *,
    template: dict[str, Any],
    content: dict[str, Any],
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Returnerer LLM-kvalitetsreview af et udfyldt evidens-dokument."""
    if not template or not content:
        raise ValueError("Både template og content kræves")

    user_message = _build_user_prompt(template, content)
    llm_content = _call_llm(user_message, timeout=timeout)
    return _parse_review_json(llm_content)


def _build_user_prompt(template: dict[str, Any], content: dict[str, Any]) -> str:
    section_lines = []
    for s in template.get("sections", []):
        key = s["key"]
        user_value = content.get(key, "")
        marker = "[REQUIRED]" if s.get("required") else "[OPTIONAL]"
        # Trunkér lange svar
        display_value = (str(user_value) or "(tom)")[:600]
        section_lines.append(
            f"--- {key} {marker} ---\n"
            f"Heading: {s.get('heading', '')}\n"
            f"Prompt: {s.get('prompt', '')[:200]}\n"
            f"Bruger-svar: {display_value}"
        )
    sections_text = "\n\n".join(section_lines)

    legal_lines = [
        f"- {lb.get('lov')} {lb.get('artikel')}: {(lb.get('citat') or '')[:150]}"
        for lb in template.get("legal_basis", [])
    ]
    legal_text = "\n".join(legal_lines) if legal_lines else "(ingen specifik)"

    return f"""EVIDENS-SKABELON: {template.get('title', '')}

LOVHJEMLER:
{legal_text}

SEKTIONER + BRUGER-SVAR:
{sections_text}

Lever review nu."""


def _call_llm(user_message: str, *, timeout: float) -> str:
    lm_studio_url = (os.getenv("LM_STUDIO_BASE_URL") or "").rstrip("/")
    if lm_studio_url:
        return _post_chat(
            base_url=lm_studio_url,
            api_key=os.getenv("LM_STUDIO_API_KEY", "lm-studio"),
            model=os.getenv("LM_STUDIO_CHAT_MODEL") or os.getenv("LM_STUDIO_MODEL") or "local-model",
            user_message=user_message,
            timeout=timeout,
        )
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        # Respect OPENAI_BASE_URL so local OpenAI-compatible endpoints stay local.
        return _post_chat(
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            api_key=openai_key,
            model=os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini"),
            user_message=user_message,
            timeout=timeout,
        )
    raise EvidenceReviewError(
        "Ingen LLM-provider — sæt LM_STUDIO_BASE_URL eller OPENAI_API_KEY"
    )


def _post_chat(
    *, base_url: str, api_key: str, model: str, user_message: str, timeout: float,
) -> str:
    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.2,
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
            raise EvidenceReviewError(
                f"LLM {exc.response.status_code}: {exc.response.text[:200]}"
            ) from exc
    except httpx.RequestError as exc:
        raise EvidenceReviewError(f"LLM connection: {exc}") from exc

    body = resp.json()
    return body.get("choices", [{}])[0].get("message", {}).get("content", "")


_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```")


def _parse_review_json(content: str) -> dict[str, Any]:
    text = content.strip()
    m = _JSON_FENCE.search(text)
    if m:
        text = m.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m2 = re.search(r"\{[\s\S]*\}", text)
        if not m2:
            raise EvidenceReviewError(f"LLM invalid JSON: {content[:200]}")
        data = json.loads(m2.group(0))

    if not isinstance(data, dict):
        raise EvidenceReviewError("LLM returnerede ikke JSON-object")

    # Normalisering med fallbacks
    return {
        "quality_score": int(data.get("quality_score", 3)) if data.get("quality_score") else 3,
        "summary": str(data.get("summary", "")).strip(),
        "issues": [
            {
                "section_key": str(i.get("section_key", "")),
                "severity": i.get("severity", "tip"),
                "message": str(i.get("message", "")).strip(),
            }
            for i in data.get("issues", [])
            if isinstance(i, dict) and i.get("message")
        ][:5],
        "suggestions": [
            str(s).strip()
            for s in data.get("suggestions", [])
            if isinstance(s, str) and s.strip()
        ][:3],
        "missing_legal_refs": [
            str(r).strip()
            for r in data.get("missing_legal_refs", [])
            if isinstance(r, str) and r.strip()
        ][:5],
    }
