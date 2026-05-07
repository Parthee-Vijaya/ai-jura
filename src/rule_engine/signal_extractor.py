"""LLM-assisted extraction of trigger signals from a free-text system description.

The signal extractor is the ONLY place an LLM participates in the rule
evaluation pipeline. Its scope is intentionally narrow:

  free text + a list of expected signal names  →  {signal_name: True | False | "usikker"}

It cannot change the rule's outcome, can't introduce new signals, and
its output is mechanically validated against the rule's schema before
being passed to the deterministic executor.

Usage:

    extractor = SignalExtractor()
    signals = extractor.extract(
        "Borgerassistenten er en chatbot der hjælper med pension...",
        rules,
    )
    # signals: {"system.processes_personal_data": True, ...}

Deterministic test mode:

    extractor = SignalExtractor(llm=StubLLM({"system.processes_personal_data": True}))

"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Iterable, Protocol

from src.rule_engine.models import Rule, TriggerCondition

logger = logging.getLogger(__name__)


SignalValue = bool | str  # bool for True/False, "usikker" for unknown


class LLMClient(Protocol):
    """Minimal protocol — anything with a `.invoke(prompt) -> str` works.

    Both `langchain_openai.ChatOpenAI` and `AzureChatOpenAI` satisfy this
    via their `.invoke` method (returns AIMessage with `.content`).
    A test stub can implement it in a few lines.
    """

    def invoke(self, prompt: str) -> object: ...


class SignalExtractionError(Exception):
    pass


def _default_llm() -> LLMClient | None:
    """Build an Azure-or-OpenAI client from environment variables.

    Mirrors the pattern in `src/news/llm_news_search.py`. Returns `None`
    if no credentials are configured — callers must handle that path
    (typically by skipping LLM extraction and relying on caller-provided
    signals).
    """
    try:
        from langchain_openai import AzureChatOpenAI, ChatOpenAI
    except ImportError:
        logger.warning("langchain_openai not installed; signal extraction disabled")
        return None

    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")

    if azure_endpoint and azure_api_key:
        return AzureChatOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=azure_api_key,
            api_version=os.getenv("OPENAI_API_VERSION", "2024-02-15-preview"),
            deployment_name=os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o-mini"),
            temperature=0.0,
            timeout=15,
        )

    if os.getenv("OPENAI_API_KEY"):
        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.0,
            timeout=15,
        )

    return None


def _signals_for_rule(rule: Rule) -> list[str]:
    conditions: Iterable[TriggerCondition] = []
    if rule.trigger.any_of:
        conditions = list(rule.trigger.any_of)
    elif rule.trigger.all_of:
        conditions = list(rule.trigger.all_of)
    return [c.signal for c in conditions]


def _normalize_value(raw: object) -> SignalValue | None:
    """Coerce LLM output into a `SignalValue`. Returns `None` for
    anything we don't recognize (caller treats that as 'usikker')."""
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        s = raw.strip().lower()
        if s in ("true", "ja", "yes", "1"):
            return True
        if s in ("false", "nej", "no", "0"):
            return False
        if s in ("usikker", "unknown", "uncertain", "maybe"):
            return "usikker"
    return None


_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_llm_json(content: str, expected_signals: set[str]) -> dict[str, SignalValue]:
    """Pull the first JSON object out of the LLM response and pick out
    only signals that the rule actually expects. Anything else is
    silently dropped — we never widen the signal set from LLM output."""
    match = _JSON_BLOCK_RE.search(content)
    if not match:
        raise SignalExtractionError(f"LLM response contained no JSON object: {content[:200]!r}")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise SignalExtractionError(f"LLM response is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SignalExtractionError(f"LLM JSON is not an object: {type(data).__name__}")

    out: dict[str, SignalValue] = {}
    for name in expected_signals:
        if name not in data:
            continue
        normalized = _normalize_value(data[name])
        if normalized is None:
            continue
        out[name] = normalized
    return out


class SignalExtractor:
    def __init__(self, llm: LLMClient | None = None):
        self._llm = llm if llm is not None else _default_llm()

    @property
    def is_configured(self) -> bool:
        return self._llm is not None

    def extract_for_rule(
        self, system_description: str, rule: Rule
    ) -> dict[str, SignalValue]:
        """Ask the LLM to interpret signals defined on a single rule.

        Returns an empty dict if the rule has no `llm_fortolkning` block,
        or if no LLM is configured. Skips signals the LLM marks 'usikker'.
        """
        if rule.llm_fortolkning is None or self._llm is None:
            return {}

        expected = set(_signals_for_rule(rule))
        if not expected:
            return {}

        # Don't use str.format here — prompt templates often contain JSON
        # examples like `{"system.x": true}` which would crash .format().
        signal_list = "\n".join(f"- {s}" for s in sorted(expected))
        prompt = (
            rule.llm_fortolkning.prompt_template
            .replace("{system_beskrivelse}", system_description)
            .replace("{signal_liste}", signal_list)
        )

        try:
            response = self._llm.invoke(prompt)
        except Exception as exc:
            raise SignalExtractionError(
                f"LLM invocation failed for rule '{rule.id}': {exc}"
            ) from exc

        content = getattr(response, "content", response)
        if not isinstance(content, str):
            content = str(content)

        parsed = _parse_llm_json(content, expected)
        # 'usikker' values are not propagated to the executor — the
        # caller can either treat them as False (default) or fall back
        # to an explicit predicate question.
        return {k: v for k, v in parsed.items() if isinstance(v, bool)}

    def extract(
        self, system_description: str, rules: list[Rule]
    ) -> dict[str, SignalValue]:
        """Extract signals across multiple rules. Later rules override
        earlier ones if they happen to share a signal name."""
        merged: dict[str, SignalValue] = {}
        for rule in rules:
            merged.update(self.extract_for_rule(system_description, rule))
        return merged
