"""LLM-resilience: retry-decorator + simpel circuit-breaker.

LM Studio (lokal) og Azure/OpenAI har forskellige fejlmønstre:

- LM Studio: enkelte kald hænger eller returnerer tom string når modellen
  endnu ikke er fuldt loadet. Andre kald fejler med 503/timeout under
  context-switch.
- OpenAI/Azure: rate-limit (429), midlertidig 5xx, transient connection-reset.

Strategi:

1. **Retry med exponential backoff** for transient fejl (timeout, 502, 503,
   504, 429, connection-reset). Max 3 forsøg, 1s → 2s → 4s.

2. **Circuit-breaker** der åbner efter X consecutive failures inden for Y
   sekunder. Når åben afvises kald straks i Z sekunder før vi prøver igen
   ("half-open"). Beskytter mod at app'en hænger på en død LLM.

Brug:

  from src.utils.llm_resilience import llm_retry, LLMCircuitBreaker

  breaker = LLMCircuitBreaker(name="lm_studio")

  @llm_retry()
  def call_llm():
      return breaker.call(lambda: client.chat.completions.create(...))

State eksponeres via /api/v3/admin/llm-health så /drift kan vise status.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

logger = logging.getLogger("bifrost.llm_resilience")


# ---- Exception types vi gerne retry'er ------------------------------------


# Catch-all retryable errors. Bevidst bred: vi vil hellere retry'e for meget
# end fejle på en transient hiccup. Circuit-breaker fanger permanente fejl.
class LLMTransientError(Exception):
    """Markerer en LLM-fejl som transient — retry'es."""


class LLMPermanentError(Exception):
    """Markerer en LLM-fejl som permanent — retry'es IKKE (fx 4xx).

    Brug fx ved invalid API-key, missing model, prompt-policy-violation.
    """


# ---- Retry decorator ------------------------------------------------------


def llm_retry(
    *,
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 8.0,
):
    """Tenacity-baseret retry-decorator for LLM-kald.

    Retryer på LLMTransientError, ConnectionError, TimeoutError. Andre
    exceptions propageres straks så bugs ikke bliver tilbageholdt.

    Eksempel:
        @llm_retry()
        def call():
            ...

        @llm_retry(max_attempts=5, min_wait=2.0)
        async def async_call():
            ...
    """
    return retry(
        retry=retry_if_exception_type(
            (LLMTransientError, ConnectionError, TimeoutError)
        ),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


# ---- Circuit breaker ------------------------------------------------------


@dataclass
class BreakerStats:
    name: str
    state: str = "closed"  # closed | open | half_open
    failure_count: int = 0
    success_count: int = 0
    last_failure_at: Optional[float] = None
    last_success_at: Optional[float] = None
    opened_at: Optional[float] = None
    total_opens: int = 0


class LLMCircuitBreaker:
    """Simpel circuit-breaker for LLM-providers.

    Stater:
      - CLOSED (normal): kald går igennem; tæller fejl
      - OPEN: kald afvises straks i `reset_timeout` sekunder
      - HALF_OPEN: efter timeout, lad ÉT kald gå igennem; succes → closed,
        fejl → open igen

    Tråd-safe via en lock.

    Konfigurerbar via env:
      LLM_BREAKER_FAILURE_THRESHOLD=5     # consecutive fails før open
      LLM_BREAKER_RESET_TIMEOUT_SEC=30    # hvor længe vi venter før half-open

    Brug:
        breaker = LLMCircuitBreaker(name="lm_studio")
        try:
            result = breaker.call(lambda: openai_client.chat.completions.create(...))
        except CircuitBreakerOpen:
            # håndtér graceful — fx vis "LLM midlertidigt nede" i UI
            ...
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        reset_timeout_sec: float = 30.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout_sec = reset_timeout_sec
        self._lock = threading.Lock()
        self._stats = BreakerStats(name=name)

    @property
    def stats(self) -> BreakerStats:
        # Snapshot — caller skal ikke mutere
        with self._lock:
            return BreakerStats(**self._stats.__dict__)

    def _transition_to(self, new_state: str, now: float) -> None:
        prev = self._stats.state
        if prev == new_state:
            return
        self._stats.state = new_state
        if new_state == "open":
            self._stats.opened_at = now
            self._stats.total_opens += 1
            logger.warning(
                f"[circuit-breaker:{self.name}] OPEN — afviser kald i "
                f"{self.reset_timeout_sec}s efter {self._stats.failure_count} fejl"
            )
        elif new_state == "half_open":
            logger.info(f"[circuit-breaker:{self.name}] HALF-OPEN — prøver ét kald")
        elif new_state == "closed":
            self._stats.failure_count = 0
            logger.info(f"[circuit-breaker:{self.name}] CLOSED — normal drift")

    def call(self, func: Callable[[], Any]) -> Any:
        """Kald func() gennem breakeren.

        Raises:
            CircuitBreakerOpen: hvis breakeren er åben
            Original exception: hvis func() fejler
        """
        now = time.monotonic()

        with self._lock:
            # Hvis open, tjek om tiden er til half-open
            if self._stats.state == "open":
                if (
                    self._stats.opened_at is not None
                    and (now - self._stats.opened_at) >= self.reset_timeout_sec
                ):
                    self._transition_to("half_open", now)
                else:
                    raise CircuitBreakerOpen(
                        f"Circuit breaker {self.name} er åben — afviser kald"
                    )

        # Eksekvér uden lock (kald kan tage flere sekunder)
        try:
            result = func()
        except Exception as exc:
            with self._lock:
                self._stats.failure_count += 1
                self._stats.last_failure_at = time.monotonic()
                if self._stats.state == "half_open":
                    # Half-open kald fejlede → tilbage til open
                    self._transition_to("open", time.monotonic())
                elif (
                    self._stats.state == "closed"
                    and self._stats.failure_count >= self.failure_threshold
                ):
                    self._transition_to("open", time.monotonic())
            raise exc

        # Succes
        with self._lock:
            self._stats.success_count += 1
            self._stats.last_success_at = time.monotonic()
            if self._stats.state in ("half_open", "open"):
                self._transition_to("closed", time.monotonic())
            else:
                # Genstart fejl-tæller hvis vi har et godt kald
                self._stats.failure_count = 0
        return result

    def reset(self) -> None:
        """Manuelt reset — bruges af /admin/llm-health endpoint hvis nogen
        manuelt vil sætte breakeren tilbage til closed."""
        with self._lock:
            self._stats = BreakerStats(name=self.name)
        logger.info(f"[circuit-breaker:{self.name}] manuelt reset til closed")


class CircuitBreakerOpen(Exception):
    """Raised når circuit breaker afviser et kald fordi den er åben."""


# ---- Module-level singletons ---------------------------------------------


# Globale breakers — én pr. LLM-provider. Importér disse direkte fra
# kald-sites så vi har én konsistent statemachine pr. provider på tværs
# af app'en.
import os  # noqa: E402

_LM_STUDIO_BREAKER = LLMCircuitBreaker(
    name="lm_studio",
    failure_threshold=int(os.getenv("LLM_BREAKER_FAILURE_THRESHOLD", "5")),
    reset_timeout_sec=float(os.getenv("LLM_BREAKER_RESET_TIMEOUT_SEC", "30")),
)
_AZURE_OPENAI_BREAKER = LLMCircuitBreaker(
    name="azure_openai",
    failure_threshold=int(os.getenv("LLM_BREAKER_FAILURE_THRESHOLD", "5")),
    reset_timeout_sec=float(os.getenv("LLM_BREAKER_RESET_TIMEOUT_SEC", "30")),
)
_OPENAI_BREAKER = LLMCircuitBreaker(
    name="openai",
    failure_threshold=int(os.getenv("LLM_BREAKER_FAILURE_THRESHOLD", "5")),
    reset_timeout_sec=float(os.getenv("LLM_BREAKER_RESET_TIMEOUT_SEC", "30")),
)


def get_breaker(provider: str) -> LLMCircuitBreaker:
    """Returnér breakeren for en given LLM-provider."""
    p = provider.lower()
    if p == "lm_studio":
        return _LM_STUDIO_BREAKER
    if p in ("azure", "azure_openai"):
        return _AZURE_OPENAI_BREAKER
    if p == "openai":
        return _OPENAI_BREAKER
    raise ValueError(f"Ukendt LLM-provider: {provider}")


def all_breaker_stats() -> dict[str, dict]:
    """For /admin/llm-health endpoint."""
    return {
        "lm_studio": _LM_STUDIO_BREAKER.stats.__dict__,
        "azure_openai": _AZURE_OPENAI_BREAKER.stats.__dict__,
        "openai": _OPENAI_BREAKER.stats.__dict__,
    }
