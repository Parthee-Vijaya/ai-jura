# Test coverage status

Sidst målt: 2026-05-11 (efter Phase A).

## Sammenfatning

| | Før Phase A | Efter Phase A | Delta |
|---|---|---|---|
| **Total** | 23% (7099 missed / 9180 stmts) | **28%** (6998 missed / 9685 stmts) | **+5pp / +91 nye tests** |
| Tests | 258 | **349** | +91 |
| Failing | 1 (pre-existing) | 1 (samme) | uændret |

## Phase A — kerne-regelmotor (leveret)

| Modul | Stmts | Før | Efter | Delta |
|---|---|---|---|---|
| `src/compliance_engine.py` | 273 | 0% | **78%** | **+78pp** |
| `src/compliance/compliance_control_engine.py` | 354 | 0% | **90%** | **+90pp** |
| `src/compliance/recommendation_engine.py` | 84 | 0% | **87%** | **+87pp** |

**Test-filer tilføjet:**
- `tests/test_compliance_engine.py` — 35 tests (ComplianceRule, RuleEngine, Controller)
- `tests/test_compliance_control_engine.py` — 37 tests (7-punkts vurdering, scoring, beslutning)
- `tests/test_recommendation_engine.py` — 17 tests (DPIA-trigger, anbefalinger, public API)

## Hvad er nu godt dækket

| Modul | Coverage | Hvorfor det er vigtigt |
|---|---|---|
| `src/utils/pii_redaction` | 100% | CPR/email-redaction — direkte GDPR-impact |
| `src/utils/llm_resilience` | 98% | Retry + circuit-breaker — driftsstabilitet |
| `src/api/error_envelope` | 98% | Konsistent error-shape — frontend-DX |
| `src/api/csv_exports` | 96% | Revisor-eksport |
| `src/compliance/compliance_control_engine` | 90% | 7-punkts vurdering — kerne-produkt |
| `src/services/evidence_artifacts` | 88% | 28 templates |
| `src/compliance/recommendation_engine` | 87% | Anbefalings-motor |
| `src/compliance_engine.py` | 78% | Hovedregelmotor |
| `src/rule_engine/loader` | 87% | YAML-regel-loader |
| `src/rule_engine/executor` | 83% | Regel-evaluator |

## Hvad mangler stadig (Phase B-D)

| Modul | Stmts | Coverage | Estimat |
|---|---|---|---|
| `src/services/case_report_generator.py` | 423 | 0% | DOCX/PDF — pilot-kritisk |
| `src/services/knowledge_base_updater.py` | 249 | 0% | Daglig KB-update-job |
| `src/services/citation_verifier.py` | 192 | 42% | Lov-citat-verifikation |
| `src/services/retention_service.py` | 138 | 0% | GDPR-sletning |
| `src/agents/compliance_orchestrator.py` | ~150 | 0% | LangGraph-orkestrator |
| `src/rule_engine/signal_extractor.py` | 144 | 58% | LLM-baseret signal-extraction (mocking kompleks) |
| `src/utils/observability.py` | 140 | 0% | Logging + metrics |

### Estimat for at komme videre

- **Phase B** (services-laget): retention, KB updater, document storage → ~2 dage, +15% coverage
- **Phase C** (agents + signal_extractor): LangGraph + LLM-mocking → ~2 dage, +10% coverage
- **Phase D** (case_report_generator + observability): DOCX/PDF + logging → ~1 dag, +8% coverage

**Total potential: 28% → ~60%+** med 5 dages arbejde.

## Sådan kører man coverage

```bash
cd /path/to/bifrost
source venv/bin/activate

# Full report
pytest --cov=src --cov-report=term-missing -q \
  --ignore=tests/test_news_service.py

# Kun Phase A-modulerne
pytest --cov=src/compliance --cov=src/compliance_engine -q \
  --ignore=tests/test_news_service.py

# HTML-rapport
pytest --cov=src --cov-report=html
open htmlcov/index.html
```
