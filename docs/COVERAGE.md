# Test coverage status

Sidst målt: 2026-05-11.

## Sammenfatning

| Kategori | Coverage |
|---|---|
| **Total** | **23%** (7099 missed / 9180 stmts) |
| Nye moduler (denne uge) | 90-100% |
| Compliance-engine + agents | 0% |
| Services-laget (KB updater, RAG, retention, document storage) | 0% |
| Database-laget | 0-30% |

## Hvad er godt dækket

| Modul | Coverage | Tests |
|---|---|---|
| `src/utils/pii_redaction` | 100% | CPR-, email-, telefon-redaction (regex) |
| `src/utils/llm_resilience` | 98% | Retry + circuit-breaker states |
| `src/api/error_envelope` | 98% | Alle 4 exception-paths |
| `src/api/csv_exports` | 96% | 3 eksport-funktioner + edge-cases |
| `src/services/evidence_artifacts` | 88% | 28 templates, status-beregning |

## Hvad mangler tests (kritisk for langtidsstabilitet)

| Modul | Risiko |
|---|---|
| `src/compliance_engine.py` (273 stmts) | 0% — kerne-regelmotor uden tests |
| `src/compliance/compliance_control_engine.py` (354 stmts) | 0% — 7-punkts vurdering |
| `src/agents/compliance_orchestrator.py` | 0% — LangGraph-orchestrator |
| `src/services/case_report_generator.py` (423 stmts) | 0% — DOCX/PDF eksport |
| `src/services/knowledge_base_updater.py` (249 stmts) | 0% — daglig KB-update-job |
| `src/services/citation_verifier.py` | 42% — kerne af "hjemlet vurdering"-løftet |
| `src/services/retention_service.py` (138 stmts) | 0% — GDPR-sletning |
| `src/utils/observability.py` (140 stmts) | 0% — logging, metrics |

## Hvordan vi kommer fra 23% → 70%+ (estimat)

- **Phase A**: kerne-regelmotor (`compliance_engine.py` + `rule_engine/executor.py`)
  → fixture-baserede tests med kendte input/output. ~2 dage, +12% coverage.
- **Phase B**: services-laget (KB updater, retention, citation verifier)
  → mock'ede dependencies + unit-tests. ~3 dage, +20% coverage.
- **Phase C**: compliance-orchestrator + agents
  → integration-tests mod test-LM Studio. ~2 dage, +10% coverage.
- **Phase D**: observability, validation, agents/registry
  → unit-tests. ~1 dag, +8% coverage.

**Total**: ~8 dage for at komme til ~73% coverage på de mest kritiske moduler.

Realistisk: vi har 258 tests der passer i dag og rammer den kritiske path
for ny funktionalitet siden 2026-05-08. Lavprio-moduler kan vente til
efter pilot-feedback viser hvor brugen faktisk koncentrerer sig.

## Hvordan man kører coverage selv

```bash
cd /path/to/bifrost
source venv/bin/activate
pytest --cov=src --cov-report=term-missing -q \
  --ignore=tests/test_news_service.py
```

For HTML-rapport:
```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html
```
