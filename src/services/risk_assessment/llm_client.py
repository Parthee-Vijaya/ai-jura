"""Delt LLM-klient for risikovurderingsmotoren.

Følger Bifrosts standard provider-kæde: lokal LM Studio → Azure OpenAI → OpenAI.
Lokal-først af GDPR-hensyn — de uploadede dokumenter (MSA, DBA, persondata)
må ikke sendes til en US-cloud-API, da det er netop de data værktøjet vurderer.

Eksponerer chat_json() der returnerer parset JSON (dict eller list) med robust
håndtering af markdown-fence + prose-wrapper + malformed output.
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


def chat_json(
    system_prompt: str,
    user_message: str,
    *,
    temperature: float = 0.2,
    timeout: float = 90.0,
    expect: str = "object",  # "object" | "array"
    max_tokens: int = 4096,
) -> Any:
    """Send en chat-forespørgsel og returnér parset JSON.

    Provider-kæde: LM Studio → Azure → OpenAI. Bruger response_format=json_object
    hvor muligt, med fallback hvis provider ikke understøtter det.

    Args:
        expect: "object" → forvent dict; "array" → forvent list (uddrages fra wrapper)
        max_tokens: høj default så lange risiko-/indholds-svar ikke trunkeres
    """
    raw = _call_provider(
        system_prompt, user_message,
        temperature=temperature, timeout=timeout, max_tokens=max_tokens,
    )
    return _parse_json(raw, expect=expect)


def _call_provider(system_prompt, user_message, *, temperature, timeout, max_tokens) -> str:
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
        return _post_openai_compatible(
            base_url="https://api.openai.com/v1",
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
    *, base_url, api_key, model, system_prompt, user_message, temperature, timeout, max_tokens=4096
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
        if exc.response.status_code == 400 and "response_format" in exc.response.text:
            payload.pop("response_format", None)
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
        else:
            raise RiskLLMError(
                f"LLM-API {exc.response.status_code}: {exc.response.text[:200]}"
            ) from exc
    except httpx.RequestError as exc:
        raise RiskLLMError(f"LLM-connection: {exc}") from exc

    body = resp.json()
    content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content:
        raise RiskLLMError(f"LLM tom respons: {str(body)[:200]}")
    return content


def _post_azure(
    *, endpoint, api_key, deployment, api_version, system_prompt, user_message, temperature, timeout, max_tokens=4096
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
        raise RiskLLMError(
            f"Azure {exc.response.status_code}: {exc.response.text[:200]}"
        ) from exc
    except httpx.RequestError as exc:
        raise RiskLLMError(f"Azure-connection: {exc}") from exc

    body = resp.json()
    return body.get("choices", [{}])[0].get("message", {}).get("content", "")


def _repair_json(text: str) -> str:
    """Reparér almindelige LLM-JSON-fejl: trailing commas, kommentarer, smart-quotes."""
    # Smart-quotes → almindelige
    text = text.replace("“", '"').replace("”", '"').replace("’", "'")
    # Fjern // og /* */ kommentarer
    text = re.sub(r"//[^\n\r]*", "", text)
    text = re.sub(r"/\*[\s\S]*?\*/", "", text)
    # Fjern trailing commas før } eller ]
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    return text


def _parse_json(content: str, *, expect: str = "object") -> Any:
    """Parse JSON robust — håndterer markdown-fence, prose-wrapper og almindelige fejl."""
    text = (content or "").strip()
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
