"""Executor tests against the 3 pilot rules.

For each rule we verify:
  - trigger gating works (no signal -> not triggered)
  - 'så' branch hits (BETINGET-GO) for the canonical positive case
  - 'ellers' branch hits (GO) for the canonical negative case
  - missing predicate raises a helpful error
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.rule_engine.executor import RuleExecutor, RuleExecutionError, aggregate_status, evaluate_all
from src.rule_engine.loader import RuleLoader
from src.rule_engine.models import RuleInput, Status

RULES_DIR = Path(__file__).resolve().parents[2] / "rules"


@pytest.fixture(scope="module")
def rules():
    result = RuleLoader(RULES_DIR).load_all(raise_on_error=True)
    return {r.id: r for r in result.rules}


# AI Act art. 6 ----------------------------------------------------------


def test_ai_act_art6_not_triggered_without_signal(rules):
    rule = rules["ai_act.art6.hojrisiko_klassifikation"]
    decision = RuleExecutor(rule).evaluate(RuleInput(signals={}, predicates={}))
    assert decision.triggered is False
    assert decision.status is None


def test_ai_act_art6_betinget_go_for_biometri_with_profilering(rules):
    rule = rules["ai_act.art6.hojrisiko_klassifikation"]
    decision = RuleExecutor(rule).evaluate(
        RuleInput(
            signals={"system.processes_personal_data": True},
            predicates={
                "anvendelsesomraade": "biometri",
                "kun_forberedende": True,
                "profilering": True,
            },
        )
    )
    assert decision.triggered is True
    assert decision.status == Status.BETINGET_GO
    assert decision.outcome is not None
    assert any("art. 9" in k for k in decision.outcome.krav)


def test_ai_act_art6_go_for_purely_preparatory_outside_annex_iii(rules):
    rule = rules["ai_act.art6.hojrisiko_klassifikation"]
    decision = RuleExecutor(rule).evaluate(
        RuleInput(
            signals={"system.processes_personal_data": True},
            predicates={
                "anvendelsesomraade": "intet_af_ovenstaaende",
                "kun_forberedende": True,
                "profilering": False,
            },
        )
    )
    assert decision.triggered is True
    assert decision.status == Status.GO


# GDPR art. 22 -----------------------------------------------------------


def test_gdpr_art22_not_triggered_without_signal(rules):
    rule = rules["gdpr.art22.automatiseret_individuel_afgorelse"]
    decision = RuleExecutor(rule).evaluate(RuleInput(signals={}, predicates={}))
    assert decision.triggered is False


def test_gdpr_art22_betinget_go_for_fully_automated_with_legal_effect(rules):
    rule = rules["gdpr.art22.automatiseret_individuel_afgorelse"]
    decision = RuleExecutor(rule).evaluate(
        RuleInput(
            signals={"system.makes_decisions_about_persons": True},
            predicates={
                "er_helautomatiseret": True,
                "har_retsvirkning_eller_betydelig_paavirkning": True,
                "retsgrundlag_til_undtagelse": "samtykke",
                "omfatter_saerlige_kategorier": False,
            },
        )
    )
    assert decision.triggered is True
    assert decision.status == Status.BETINGET_GO


def test_gdpr_art22_go_for_human_in_the_loop(rules):
    rule = rules["gdpr.art22.automatiseret_individuel_afgorelse"]
    decision = RuleExecutor(rule).evaluate(
        RuleInput(
            signals={"system.classifies_individuals": True},
            predicates={
                "er_helautomatiseret": False,
                "har_retsvirkning_eller_betydelig_paavirkning": True,
                "retsgrundlag_til_undtagelse": "intet",
                "omfatter_saerlige_kategorier": False,
            },
        )
    )
    assert decision.triggered is True
    assert decision.status == Status.GO


# Forvaltningsloven §22 --------------------------------------------------


def test_forvaltningsloven_par22_not_triggered_without_signal(rules):
    rule = rules["forvaltningsloven.par22.begrundelsespligt"]
    decision = RuleExecutor(rule).evaluate(RuleInput(signals={}, predicates={}))
    assert decision.triggered is False


def test_forvaltningsloven_par22_betinget_go_for_written_partial_decision(rules):
    rule = rules["forvaltningsloven.par22.begrundelsespligt"]
    decision = RuleExecutor(rule).evaluate(
        RuleInput(
            signals={"system.makes_administrative_decisions": True},
            predicates={
                "traeffer_afgoerelse": True,
                "meddeles_skriftligt": True,
                "fuld_medhold": False,
                "kan_systemet_generere_begrundelse": "ja_delvist",
            },
        )
    )
    assert decision.triggered is True
    assert decision.status == Status.BETINGET_GO


def test_forvaltningsloven_par22_go_when_full_medhold(rules):
    rule = rules["forvaltningsloven.par22.begrundelsespligt"]
    decision = RuleExecutor(rule).evaluate(
        RuleInput(
            signals={"system.is_used_by_public_authority": True},
            predicates={
                "traeffer_afgoerelse": True,
                "meddeles_skriftligt": True,
                "fuld_medhold": True,
                "kan_systemet_generere_begrundelse": "ja_fuldt",
            },
        )
    )
    assert decision.triggered is True
    assert decision.status == Status.GO


# Cross-cutting ----------------------------------------------------------


def test_missing_predicate_raises(rules):
    rule = rules["gdpr.art22.automatiseret_individuel_afgorelse"]
    with pytest.raises(RuleExecutionError, match="missing answer for predicate"):
        RuleExecutor(rule).evaluate(
            RuleInput(
                signals={"system.makes_decisions_about_persons": True},
                predicates={"er_helautomatiseret": True},
            )
        )


def test_aggregate_status_picks_strictest():
    from src.rule_engine.models import LawSource, RuleDecision, RuleOutcome

    src = LawSource(
        lov="Test",
        artikel="Art 1",
        citat="placeholder citat tekst her",
        url="https://example.com",
        sidst_verificeret="2026-05-07",
    )
    decisions = [
        RuleDecision(
            rule_id="r.go",
            triggered=True,
            status=Status.GO,
            outcome=RuleOutcome(status=Status.GO),
            kilde=src,
        ),
        RuleDecision(
            rule_id="r.betinget",
            triggered=True,
            status=Status.BETINGET_GO,
            outcome=RuleOutcome(status=Status.BETINGET_GO),
            kilde=src,
        ),
    ]
    assert aggregate_status(decisions) == Status.BETINGET_GO

    decisions.append(
        RuleDecision(
            rule_id="r.no",
            triggered=True,
            status=Status.NO_GO,
            outcome=RuleOutcome(status=Status.NO_GO),
            kilde=src,
        )
    )
    assert aggregate_status(decisions) == Status.NO_GO


def test_evaluate_all_returns_one_decision_per_rule(rules):
    rule_list = list(rules.values())
    decisions = evaluate_all(
        rule_list,
        RuleInput(
            signals={
                "system.processes_personal_data": True,
                "system.makes_decisions_about_persons": True,
                "system.is_used_by_public_authority": True,
            },
            predicates={
                "anvendelsesomraade": "biometri",
                "kun_forberedende": False,
                "profilering": True,
                "er_helautomatiseret": True,
                "har_retsvirkning_eller_betydelig_paavirkning": True,
                "retsgrundlag_til_undtagelse": "samtykke",
                "omfatter_saerlige_kategorier": False,
                "traeffer_afgoerelse": True,
                "meddeles_skriftligt": True,
                "fuld_medhold": False,
                "kan_systemet_generere_begrundelse": "ja_delvist",
            },
        ),
    )
    assert len(decisions) == len(rule_list)
    assert all(d.triggered for d in decisions)
    assert aggregate_status(decisions) == Status.BETINGET_GO
