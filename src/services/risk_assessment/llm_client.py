"""Delt LLM-klient for risikovurderingsmotoren.

PROVIDER-STRATEGI med GDPR-grænse bygget ind i koden (sensitivity-parameter):

  sensitivity="documents"  → ALTID lokal kæde (LM Studio → Azure → OpenAI).
      Bruges af fact-extraction der ser de RÅ dokumenter (MSA, DBA — kan
      indeholde persondata). Disse må aldrig sendes til en US-cloud-API.

  sensitivity="metadata"   → Nemotron først (hvis NEMOTRON_API_KEY er sat),
      fallback til lokal kæde. Bruges af risiko-identifikation + indholds-
      generering der KUN modtager den strukturerede SystemFacts (leverandør-
      navn, hosting-label, kategori-labels, proces-flags) — system-metadata,
      ikke personoplysninger. Det er de to tunge ræsonnement-trin hvor en
      stærkere hosted model løfter kvalitet + JSON-stabilitet.

Nemotron-config (.env):
  NEMOTRON_API_KEY   — nvapi-... (build.nvidia.com) eller anden OpenAI-kompatibel host
  NEMOTRON_BASE_URL  — default https://integrate.api.nvidia.com/v1
  NEMOTRON_MODEL     — default nvidia/llama-3.3-nemotron-super-49b-v1

Eksponerer chat_json() der returnerer parset JSON (dict eller list) med robust
håndtering af markdown-fence, <think>-blokke, prose-wrapper + malformed output.
"""

import json
import logging
import os
import re
from typing import Any

import httpx

logger = logging.getLogger("bifrost.risk_assessment.llm")


class RiskLLMError(Exception):
    """Raised når LLM-kald fejler eller ingen provider er konfigureret."""


_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```")

# Reasoning-modeller (deepseek-r1, qwq, visse gemma-configs) wrapper deres
# tankeproces i <think>/<thinking>-tags FØR selve svaret. Indholdet kan selv
# indeholde { } som ødelægger brace-extraction — strip blokken helt.
_THINK_BLOCK = re.compile(r"<think(?:ing)?>[\s\S]*?</think(?:ing)?>\s*", re.IGNORECASE)


def chat_json(
    system_prompt: str,
    user_message: str,
    *,
    temperature: float = 0.2,
    timeout: float = 90.0,
    expect: str = "object",  # "object" | "array"
    max_tokens: int = 8192,
    max_attempts: int = 3,
    sensitivity: str = "documents",  # "documents" (lokal-only) | "metadata" (cloud ok)
) -> Any:
    """Send en chat-forespørgsel og returnér parset JSON.

    sensitivity styrer provider-valget (se modul-docstring): "documents" går
    ALDRIG til Nemotron/cloud-først; "metadata" må. Default er den sikre.

    Lokale modeller (fx gemma) producerer LEJLIGHEDSVIS ugyldig JSON (stray commas,
    unescaped newlines i lange tekstfelter). Derfor: op til max_attempts forsøg,
    med faldende temperatur for mere deterministisk output på retry. _parse_json
    reparerer almindelige fejl; retry fanger resten.

    Args:
        expect: "object" → forvent dict; "array" → forvent list (uddrages fra wrapper)
        max_tokens: høj default så lange risiko-/indholds-svar ikke trunkeres
    """
    last_err: Exception | None = None
    for attempt in range(max_attempts):
        # Sænk temperatur på retry → mere deterministisk, færre JSON-fejl
        temp = temperature if attempt == 0 else min(temperature, 0.1)
        raw = _call_provider(
            system_prompt, user_message,
            temperature=temp, timeout=timeout, max_tokens=max_tokens,
            sensitivity=sensitivity,
        )
        try:
            return _parse_json(raw, expect=expect)
        except RiskLLMError as exc:
            last_err = exc
            logger.warning(
                "JSON-parse fejlede (forsøg %d/%d): %s",
                attempt + 1, max_attempts, str(exc)[:120],
            )
    raise last_err if last_err else RiskLLMError("JSON-parse fejlede uden detaljer")


def _nemotron_configured() -> bool:
    return bool(os.getenv("NEMOTRON_API_KEY"))


def _call_provider(system_prompt, user_message, *, temperature, timeout, max_tokens, sensitivity="documents") -> str:
    # Nemotron FØRST for metadata-kald (stærkere ræsonnement + bedre JSON) —
    # men kun metadata: rå dokumenter (sensitivity="documents") går aldrig hertil.
    if sensitivity == "metadata" and _nemotron_configured():
        try:
            return _post_openai_compatible(
                base_url=(os.getenv("NEMOTRON_BASE_URL") or "https://integrate.api.nvidia.com/v1").rstrip("/"),
                api_key=os.getenv("NEMOTRON_API_KEY"),
                model=os.getenv("NEMOTRON_MODEL", "nvidia/llama-3.3-nemotron-super-49b-v1"),
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=temperature,
                timeout=timeout,
                max_tokens=max_tokens,
            )
        except RiskLLMError as exc:
            # Cloud nede / rate-limit / auth → fald tilbage til lokal kæde
            logger.warning("Nemotron fejlede (%s) — falder tilbage til lokal kæde", str(exc)[:100])

    lm_studio_url = (os.getenv("LM_STUDIO_BASE_URL") or "").rstrip("/")
    if lm_studio_url:
        return _post_openai_compatible(
            base_url=lm_studio_url,
            api_key=os.getenv("LM_STUDIO_API_KEY", "lm-studio"),
            model=os.getenv("LM_STUDIO_CHAT_MODEL") or os.getenv("LM_STUDIO_MODEL") or "local-model",
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=temperature,
            timeout=timeout,
            max_tokens=max_tokens,
        )

    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    if azure_endpoint and os.getenv("AZURE_OPENAI_API_KEY"):
        return _post_azure(
            endpoint=azure_endpoint,
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            deployment=os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o-mini"),
            api_version=os.getenv("OPENAI_API_VERSION", "2024-02-15-preview"),
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=temperature,
            timeout=timeout,
            max_tokens=max_tokens,
        )

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        # Respect OPENAI_BASE_URL so local OpenAI-compatible endpoints stay local.
        return _post_openai_compatible(
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            api_key=openai_key,
            model=os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini"),
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=temperature,
            timeout=timeout,
            max_tokens=max_tokens,
        )

    raise RiskLLMError(
        "Ingen LLM-provider konfigureret. Sæt LM_STUDIO_BASE_URL, "
        "AZURE_OPENAI_ENDPOINT eller OPENAI_API_KEY"
    )


def _post_openai_compatible(
    *, base_url, api_key, model, system_prompt, user_message, temperature, timeout, max_tokens=8192
) -> str:
    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body_text = exc.response.text
        if exc.response.status_code == 400 and (
            "response_format" in body_text or "max_tokens" in body_text
        ):
            # To kendte 400-årsager med billig retry:
            #   - provider understøtter ikke json_object → drop response_format
            #   - model capper max_tokens (fx NVIDIA-modeller ved 4096) → sænk
            if "response_format" in body_text:
                payload.pop("response_format", None)
            if "max_tokens" in body_text:
                payload["max_tokens"] = min(payload.get("max_tokens", 8192), 4096)
            try:
                with httpx.Client(timeout=timeout) as client:
                    resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
            except (httpx.HTTPStatusError, httpx.RequestError) as exc2:
                raise RiskLLMError(f"LLM-API (fallback): {exc2}") from exc2
        else:
            raise RiskLLMError(
                f"LLM-API {exc.response.status_code}: {body_text[:200]}"
            ) from exc
    except httpx.RequestError as exc:
        raise RiskLLMError(f"LLM-connection: {exc}") from exc

    try:
        body = resp.json()
    except Exception as exc:
        # 2xx med ikke-JSON body (fx HTML-fejlside fra en proxy) → klar fejl
        raise RiskLLMError(
            f"Provider returnerede ikke-JSON ({resp.status_code}): {resp.text[:150]}"
        ) from exc
    msg = body.get("choices", [{}])[0].get("message", {})
    content = msg.get("content", "")
    if not content:
        # Reasoning-modeller (fx Nemotron) kan bruge hele token-budgettet på
        # tankeprocessen og efterlade content tom — svaret ligger så i
        # reasoning_content. Observeret live i eval (Voicecraft-kørsel).
        # _parse_json udtrækker JSON-blokken hvis den findes derinde.
        content = msg.get("reasoning_content") or msg.get("reasoning") or ""
        if content:
            logger.warning("LLM content tom — bruger reasoning_content som fallback")
    if not content:
        raise RiskLLMError(f"LLM tom respons: {str(body)[:200]}")
    return content


def _post_azure(
    *, endpoint, api_key, deployment, api_version, system_prompt, user_message, temperature, timeout, max_tokens=8192
) -> str:
    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    headers = {"api-key": api_key, "Content-Type": "application/json"}

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        # Samme response_format-fallback som OpenAI-compatible: ældre Azure-
        # deployments afviser json_object med 400 — retry uden.
        if exc.response.status_code == 400 and "response_format" in exc.response.text:
            logger.warning("Azure afviste response_format — retry uden JSON-mode")
            payload.pop("response_format", None)
            try:
                with httpx.Client(timeout=timeout) as client:
                    resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
            except (httpx.HTTPStatusError, httpx.RequestError) as exc2:
                raise RiskLLMError(f"Azure (fallback): {exc2}") from exc2
        else:
            raise RiskLLMError(
                f"Azure {exc.response.status_code}: {exc.response.text[:200]}"
            ) from exc
    except httpx.RequestError as exc:
        raise RiskLLMError(f"Azure-connection: {exc}") from exc

    try:
        body = resp.json()
    except Exception as exc:
        raise RiskLLMError(
            f"Azure returnerede ikke-JSON ({resp.status_code}): {resp.text[:150]}"
        ) from exc
    return body.get("choices", [{}])[0].get("message", {}).get("content", "")


def _escape_control_chars_in_strings(text: str) -> str:
    """Escape rå newlines/tabs/CR INDE i JSON-string-værdier.

    Lokale modeller skriver ofte lange tekstfelter med rigtige linjeskift inde i
    string-værdien — det er ugyldig JSON. Vi walker tegn for tegn, holder styr på
    om vi er inde i en string, og escaper kontroltegn der. Formaterings-newlines
    UDEN for strings bevares (json.loads håndterer dem fint).
    """
    out = []
    in_str = False
    escaped = False
    for ch in text:
        if in_str:
            if escaped:
                out.append(ch)
                escaped = False
            elif ch == "\\":
                out.append(ch)
                escaped = True
            elif ch == '"':
                out.append(ch)
                in_str = False
            elif ch == "\n":
                out.append("\\n")
            elif ch == "\r":
                out.append("\\r")
            elif ch == "\t":
                out.append("\\t")
            else:
                out.append(ch)
        else:
            out.append(ch)
            if ch == '"':
                in_str = True
    return "".join(out)


def _repair_json(text: str) -> str:
    """Reparér almindelige LLM-JSON-fejl: smart-quotes, kommentarer, trailing/lone
    commas, og rå kontroltegn inde i strings."""
    # Smart-quotes → almindelige
    text = text.replace("“", '"').replace("”", '"').replace("’", "'")
    # Fjern // og /* */ kommentarer
    text = re.sub(r"//[^\n\r]*", "", text)
    text = re.sub(r"/\*[\s\S]*?\*/", "", text)
    # Trailing commas før } eller ] (mens rigtige newlines stadig er der)
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    # Lone/dobbelt commas: ",," eller "," på egen linje før en key/}-]
    text = re.sub(r",\s*,", ",", text)
    # Escape rå kontroltegn inde i string-værdier (efter comma-oprydning)
    text = _escape_control_chars_in_strings(text)
    return text


def _parse_json(content: str, *, expect: str = "object") -> Any:
    """Parse JSON robust — håndterer markdown-fence, prose-wrapper og almindelige fejl."""
    text = (content or "").strip()
    # Strip reasoning-blokke FØR brace/fence-søgning — de kan indeholde { }
    text = _THINK_BLOCK.sub("", text).strip()
    m = _JSON_FENCE.search(text)
    if m:
        text = m.group(1).strip()

    pattern = r"\[[\s\S]*\]" if expect == "array" else r"\{[\s\S]*\}"
    data = None
    # Forsøg 1: direkte
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        pass
    # Forsøg 2: udtræk { } / [ ] blok
    if data is None:
        m2 = re.search(pattern, text)
        if m2:
            try:
                data = json.loads(m2.group(0))
            except json.JSONDecodeError:
                text = m2.group(0)
    # Forsøg 3: reparér + retry
    if data is None:
        try:
            data = json.loads(_repair_json(text))
        except json.JSONDecodeError as exc:
            raise RiskLLMError(f"LLM ugyldig JSON ({exc}): {content[:200]}") from exc

    if expect == "array":
        if isinstance(data, list):
            return data
        # LLM pakker ofte arrayet i en nøgle — find første liste-værdi
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    return v
        raise RiskLLMError("Forventede JSON-array men fik andet")
    return data
