"""Tale-til-tekst service med Whisper.

Provider-prioritet:
  1. LM Studio Whisper (lokalt, foretrukket — data forlader ikke kommunen)
  2. OpenAI Whisper API (fallback hvis LM Studio ikke har model loaded)

LM Studio kan loade fx `lmstudio-community/whisper-large-v3-turbo` og
eksponere det via OpenAI-compatible /v1/audio/transcriptions endpoint.

Brug:
    from src.services.transcribe_service import transcribe_audio
    text = transcribe_audio(audio_bytes, mime="audio/webm")
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger("bifrost.transcribe")


SUPPORTED_MIME_TYPES = {
    "audio/webm",
    "audio/ogg",
    "audio/mp3",
    "audio/mpeg",
    "audio/mp4",
    "audio/wav",
    "audio/x-wav",
    "audio/flac",
}

MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25 MB matches OpenAI's limit


class TranscribeError(Exception):
    """Raised når transcription fejler."""


def transcribe_audio(
    audio_bytes: bytes,
    *,
    mime: str = "audio/webm",
    language: str = "da",
    prompt: Optional[str] = None,
) -> str:
    """Transcribér audio til tekst via Whisper.

    Args:
        audio_bytes: rå audio data (max 25 MB)
        mime: MIME-type af audio (audio/webm, audio/mp3, audio/wav, ...)
        language: ISO 639-1 sprog-kode (default: 'da' for dansk)
        prompt: valgfri context-prompt for at biase model'en (fx termer den skal genkende)

    Returns:
        Transkriberet tekst

    Raises:
        TranscribeError: hvis ingen provider er konfigureret eller transcription fejler
        ValueError: hvis input er ugyldigt
    """
    if not audio_bytes:
        raise ValueError("audio_bytes må ikke være tom")
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise ValueError(
            f"audio for stor ({len(audio_bytes)} bytes, max {MAX_AUDIO_BYTES})"
        )
    if mime not in SUPPORTED_MIME_TYPES:
        logger.warning("Ukendt MIME-type %s, forsøger alligevel", mime)

    # Prøv LM Studio først (lokal)
    lm_studio_url = (os.getenv("LM_STUDIO_BASE_URL") or "").rstrip("/")
    if lm_studio_url:
        try:
            return _transcribe_via_openai_compatible(
                base_url=lm_studio_url,
                api_key=os.getenv("LM_STUDIO_API_KEY", "lm-studio"),
                model=os.getenv("LM_STUDIO_WHISPER_MODEL", "whisper-1"),
                audio_bytes=audio_bytes,
                mime=mime,
                language=language,
                prompt=prompt,
            )
        except Exception as exc:
            logger.warning("LM Studio Whisper fejlede, prøver fallback: %s", exc)

    # Fallback til OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        return _transcribe_via_openai_compatible(
            base_url="https://api.openai.com/v1",
            api_key=openai_key,
            model=os.getenv("OPENAI_WHISPER_MODEL", "whisper-1"),
            audio_bytes=audio_bytes,
            mime=mime,
            language=language,
            prompt=prompt,
        )

    raise TranscribeError(
        "Ingen Whisper-provider konfigureret. Sæt LM_STUDIO_BASE_URL (med whisper-model "
        "loaded) eller OPENAI_API_KEY i .env"
    )


def _transcribe_via_openai_compatible(
    *,
    base_url: str,
    api_key: str,
    model: str,
    audio_bytes: bytes,
    mime: str,
    language: str,
    prompt: Optional[str],
) -> str:
    """Send audio til en OpenAI-kompatibel /audio/transcriptions endpoint."""
    url = f"{base_url}/audio/transcriptions"
    ext = (mime.split("/")[-1] or "webm").replace("x-", "")
    files = {"file": (f"audio.{ext}", audio_bytes, mime)}
    data = {"model": model, "language": language}
    if prompt:
        data["prompt"] = prompt
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, files=files, data=data, headers=headers)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise TranscribeError(
            f"Whisper-API returnerede {exc.response.status_code}: {exc.response.text[:200]}"
        ) from exc
    except httpx.RequestError as exc:
        raise TranscribeError(f"Whisper-API connection failed: {exc}") from exc

    body = resp.json()
    text = body.get("text")
    if not text:
        raise TranscribeError(f"Whisper-svar manglede 'text': {body}")
    return text.strip()
