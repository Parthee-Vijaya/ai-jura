"""Tests for src.utils.llm_resilience — retry + circuit-breaker."""

import time

import pytest

from src.utils.llm_resilience import (
    LLMCircuitBreaker,
    CircuitBreakerOpen,
    LLMTransientError,
    LLMPermanentError,
    llm_retry,
    get_breaker,
    all_breaker_stats,
)


# ---- llm_retry decorator --------------------------------------------------


def test_retry_transient_eventually_succeeds():
    """Transient fejl → retry → succes på 3. forsøg."""
    attempts = {"n": 0}

    @llm_retry(min_wait=0.01, max_wait=0.05)
    def call():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise LLMTransientError("transient")
        return "ok"

    assert call() == "ok"
    assert attempts["n"] == 3


def test_retry_permanent_no_retry():
    """LLMPermanentError → retry IKKE, propagér straks."""
    attempts = {"n": 0}

    @llm_retry(min_wait=0.01, max_wait=0.05)
    def call():
        attempts["n"] += 1
        raise LLMPermanentError("invalid API key")

    with pytest.raises(LLMPermanentError):
        call()
    assert attempts["n"] == 1  # ingen retry


def test_retry_exhausts_attempts():
    """Efter max_attempts forsøg → propagér sidste exception."""
    attempts = {"n": 0}

    @llm_retry(max_attempts=3, min_wait=0.01, max_wait=0.05)
    def call():
        attempts["n"] += 1
        raise TimeoutError("timeout")

    with pytest.raises(TimeoutError):
        call()
    assert attempts["n"] == 3


def test_retry_connection_error():
    """ConnectionError er listet som retryable."""
    attempts = {"n": 0}

    @llm_retry(min_wait=0.01, max_wait=0.05)
    def call():
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise ConnectionError("connection reset")
        return "recovered"

    assert call() == "recovered"
    assert attempts["n"] == 2


# ---- Circuit breaker ------------------------------------------------------


def test_breaker_starts_closed():
    b = LLMCircuitBreaker("test_start", failure_threshold=3, reset_timeout_sec=1)
    assert b.stats.state == "closed"
    assert b.stats.failure_count == 0


def test_breaker_call_succeeds_resets_counter():
    b = LLMCircuitBreaker("test_succ", failure_threshold=3, reset_timeout_sec=1)
    result = b.call(lambda: "ok")
    assert result == "ok"
    assert b.stats.success_count == 1
    assert b.stats.state == "closed"


def test_breaker_opens_after_threshold():
    b = LLMCircuitBreaker("test_open", failure_threshold=3, reset_timeout_sec=10)

    def boom():
        raise RuntimeError("backend down")

    # 3 fejl → opens
    for i in range(3):
        with pytest.raises(RuntimeError):
            b.call(boom)
    assert b.stats.state == "open"
    assert b.stats.failure_count == 3
    assert b.stats.total_opens == 1


def test_breaker_open_rejects_calls_immediately():
    b = LLMCircuitBreaker("test_reject", failure_threshold=2, reset_timeout_sec=10)

    def boom():
        raise RuntimeError("down")

    # Åbn breakeren
    for _ in range(2):
        with pytest.raises(RuntimeError):
            b.call(boom)
    assert b.stats.state == "open"

    # Næste kald skal afvises uden at func() køres
    invocations = {"n": 0}

    def should_not_run():
        invocations["n"] += 1
        return "ran"

    with pytest.raises(CircuitBreakerOpen):
        b.call(should_not_run)
    assert invocations["n"] == 0  # func blev IKKE kørt


def test_breaker_half_open_on_timeout():
    """Efter reset_timeout går breaker til half_open og prøver ét kald."""
    b = LLMCircuitBreaker("test_halfopen", failure_threshold=2, reset_timeout_sec=0.1)

    # Åbn
    for _ in range(2):
        with pytest.raises(RuntimeError):
            b.call(lambda: (_ for _ in ()).throw(RuntimeError("down")))
    assert b.stats.state == "open"

    # Vent til timeout
    time.sleep(0.15)

    # Half-open kald skal succes → tilbage til closed
    result = b.call(lambda: "recovered")
    assert result == "recovered"
    assert b.stats.state == "closed"


def test_breaker_half_open_failure_reopens():
    """Fejl i half-open → tilbage til open igen."""
    b = LLMCircuitBreaker("test_halfopen_fail", failure_threshold=2, reset_timeout_sec=0.1)

    for _ in range(2):
        with pytest.raises(RuntimeError):
            b.call(lambda: (_ for _ in ()).throw(RuntimeError("down")))

    time.sleep(0.15)

    # Half-open kald fejler → open igen
    with pytest.raises(RuntimeError):
        b.call(lambda: (_ for _ in ()).throw(RuntimeError("still down")))
    assert b.stats.state == "open"
    assert b.stats.total_opens == 2


def test_breaker_manual_reset():
    b = LLMCircuitBreaker("test_reset", failure_threshold=1, reset_timeout_sec=10)
    with pytest.raises(RuntimeError):
        b.call(lambda: (_ for _ in ()).throw(RuntimeError("down")))
    assert b.stats.state == "open"

    b.reset()
    assert b.stats.state == "closed"
    assert b.stats.failure_count == 0


def test_get_breaker_returns_singletons():
    """get_breaker returnerer samme instance pr. provider."""
    b1 = get_breaker("lm_studio")
    b2 = get_breaker("lm_studio")
    assert b1 is b2

    b3 = get_breaker("azure_openai")
    assert b3.name == "azure_openai"


def test_get_breaker_unknown_provider():
    with pytest.raises(ValueError):
        get_breaker("nonexistent_provider")


def test_all_breaker_stats_returns_three_providers():
    stats = all_breaker_stats()
    assert set(stats.keys()) == {"lm_studio", "azure_openai", "openai"}
    for provider_stats in stats.values():
        assert "state" in provider_stats
        assert "failure_count" in provider_stats
