"""AI-assisteret intake-udfyldelse.

Sagsbehandler limer en fritekst-beskrivelse ind:
    "Vi vil bruge en AI-chatbot til borgerservice der besvarer
    pension-spørgsmål. Den skal kunne se borgerens sag og foreslå
    relevante ydelser..."

Modul ekstraherer struktureret intake:
    {
      "behov": "AI-chatbot til pension-spørgsmål i borgerservice",
      "indkoeb_eller_udvikling": "indkoeb_faerdig_loesning",
      "system_description": "...",
      "behandler_persondata": true,
      "persondata_typer": ["CPR-numre", "Sociale ydelser"],
      "automatiserede_beslutninger": false,
      "kritiske_formaal": false,
      "ai_risk_level": "limited",
      "fagomraade": "Borgerservice og Biblioteker"
    }

Provider-prioritet: LM Studio → Azure → OpenAI.
JSON-output håndteres robust (markdown-fences, parse-fejl).
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Optional

import httpx

logger = logging.getLogger("bifrost.ai_intake_assist")


SYSTEM_PROMPT = """Du er en compliance-assistent for Kalundborg Kommune. Din opgave
er at læse en sagsbehandlers fri-tekst-beskrivelse af et planlagt AI-system og
ekstrahere strukturerede intake-felter.

Du svarer KUN med valid JSON i præcis dette format (ingen markdown-fences, ingen
forklaring):

{
  "behov": "1-2 sætnings opsummering af hvad AI-systemet skal løse",
  "indkoeb_eller_udvikling": "indkoeb_faerdig_loesning" | "skraeddersyet_udvikling" | "hybrid" | null,
  "system_description": "Den fulde, struktureret beskrivelse af systemet",
  "behandler_persondata": true | false,
  "persondata_typer": ["CPR-numre", "Indkomst", "Sundhedsdata", ...],
  "automatiserede_beslutninger": true | false,
  "kritiske_formaal": true | false,
  "ai_risk_level": "minimal" | "limited" | "high" | "unacceptable",
  "fagomraade": "Jobcenter" | "Børn og Familie" | "Voksenspecialenheden" |
                "Sundhed og Myndighed" | "Borgerservice og Biblioteker" |
                "Organisationsstaben" | null,
  "ai_act_relevante_omrader": ["biometri", "beskaeftigelse", "uddannelse", ...]
}

Regler for klassificering:
- ai_risk_level: 'unacceptable' kun ved forbudt praksis (social scoring,
  real-time biometrisk overvågning, subliminal manipulation).
  'high' når sektorerne Jobcenter, Sundhed, sociale ydelser med automatiserede
  afgørelser. 'limited' for chatbots og indholdsgenerering. 'minimal' for resten.
- behandler_persondata: true hvis systemet ser borgerens data
- automatiserede_beslutninger: true KUN hvis systemet selv beslutter
  (ikke kun foreslår til en menneske)
- kritiske_formaal: true ved afgørelser med retlige konsekvenser eller
  betydelig indvirkning på borgerens liv (ydelser, helbredstilbud)

Hvis et felt er uklart fra beskrivelsen: brug null eller false (konservativt)."""


class AIIntakeError(Exception):
    """Raised når AI-intake-extraktion fejler."""


def extract_intake_from_description(
    description: str,
    *,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Brug LLM til at ekstrahere struktureret intake fra fritekst.

    Args:
        description: rå fritekst fra sagsbehandler (1-3 afsnit typisk)
        timeout: max sekunder for LLM-kald

    Returns:
        Dict med intake-felter (samme schema som SYSTEM_PROMPT)

    Raises:
        ValueError: hvis beskrivelse er tom eller for kort
        AIIntakeError: hvis ingen LLM-provider er konfigureret eller kaldet fejler
    """
    if not description or len(description.strip()) < 20:
        raise ValueError(
            "Beskrivelse for kort (min 20 tegn) — skriv et par sætninger om systemet"
        )

    # Find LLM-provider
    lm_studio_url = (os.getenv("LM_STUDIO_BASE_URL") or "").rstrip("/")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    openai_key = os.getenv("OPENAI_API_KEY")

    if lm_studio_url:
        return _call_via_openai_compatible(
            base_url=lm_studio_url,
            api_key=os.getenv("LM_STUDIO_API_KEY", "lm-studio"),
            model=os.getenv("LM_STUDIO_CHAT_MODEL") or os.getenv("LM_STUDIO_MODEL") or "local-model",
            description=description,
            timeout=timeout,
        )
    if azure_endpoint and os.getenv("AZURE_OPENAI_API_KEY"):
        deployment = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o-mini")
        api_version = os.getenv("OPENAI_API_VERSION", "2024-02-15-preview")
        return _call_azure(
            endpoint=azure_endpoint,
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            deployment=deployment,
            api_version=api_version,
            description=description,
            timeout=timeout,
        )
    if openai_key:
        # Respect OPENAI_BASE_URL so local OpenAI-compatible endpoints stay local.
        return _call_via_openai_compatible(
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            api_key=openai_key,
            model=os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini"),
            description=description,
            timeout=timeout,
        )

    raise AIIntakeError(
        "Ingen LLM-provider konfigureret. Sæt LM_STUDIO_BASE_URL, "
        "AZURE_OPENAI_ENDPOINT eller OPENAI_API_KEY"
    )


def _call_via_openai_compatible(
    *,
    base_url: str,
    api_key: str,
    model: str,
    description: str,
    timeout: float,
) -> dict[str, Any]:
    """Kald OpenAI-compatible chat-completion endpoint."""
    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": description},
        ],
        "temperature": 0.1,  # låg variation — vi vil have konsistent struktur
        "response_format": {"type": "json_object"},  # OpenAI/LM Studio honors hvis muligt
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        # Hvis response_format ikke understøttes, prøv uden
        if exc.response.status_code == 400 and "response_format" in exc.response.text:
            payload.pop("response_format", None)
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
        else:
            raise AIIntakeError(
                f"LLM-API returnerede {exc.response.status_code}: {exc.response.text[:200]}"
            ) from exc
    except httpx.RequestError as exc:
        raise AIIntakeError(f"LLM-connection failed: {exc}") from exc

    body = resp.json()
    content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content:
        raise AIIntakeError(f"LLM returnerede tom respons: {body}")
    return _parse_llm_json(content)


def _call_azure(
    *,
    endpoint: str,
    api_key: str,
    deployment: str,
    api_version: str,
    description: str,
    timeout: float,
) -> dict[str, Any]:
    """Kald Azure OpenAI specifikt (forskellig URL-struktur fra OpenAI)."""
    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": description},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    headers = {"api-key": api_key, "Content-Type": "application/json"}

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise AIIntakeError(
            f"Azure OpenAI returnerede {exc.response.status_code}: {exc.response.text[:200]}"
        ) from exc

    body = resp.json()
    content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content:
        raise AIIntakeError(f"Azure returnerede tom respons: {body}")
    return _parse_llm_json(content)


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```")


def _parse_llm_json(content: str) -> dict[str, Any]:
    """Parse JSON fra LLM-output, robust mod markdown-fences og whitespace."""
    text = content.strip()
    # Fjern eventuelle markdown-fences
    m = _JSON_FENCE_RE.search(text)
    if m:
        text = m.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        # Sidste forsøg: find { ... } i teksten
        m2 = re.search(r"\{[\s\S]*\}", text)
        if m2:
            try:
                data = json.loads(m2.group(0))
            except json.JSONDecodeError as exc2:
                raise AIIntakeError(
                    f"LLM returnerede invalid JSON: {exc2}. Output: {content[:300]}"
                ) from exc2
        else:
            raise AIIntakeError(
                f"LLM returnerede invalid JSON: {exc}. Output: {content[:300]}"
            ) from exc

    if not isinstance(data, dict):
        raise AIIntakeError(f"LLM returnerede ikke et object: {type(data).__name__}")

    # Normalisering: trim strenge, fjern eventuelle None-keys
    return {k: v for k, v in data.items() if v is not None}
