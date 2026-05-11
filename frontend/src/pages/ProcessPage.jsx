import React, { useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery } from 'react-query';
import axios from 'axios';
import styled from 'styled-components';
import {
  FaShoppingCart,
  FaBalanceScale,
  FaClipboardCheck,
  FaCheckCircle,
  FaCircle,
  FaExclamationTriangle,
  FaArrowRight,
  FaPlay,
  FaEdit,
  FaFileWord,
  FaFilePdf,
  FaFolderOpen,
} from 'react-icons/fa';

import {
  PageShell,
  Breadcrumb,
  Button,
  Pill,
  Banner,
  EmptyState,
  LoadingState,
  ErrorState,
  Term,
} from '../components/ui';

/**
 * ProcessPage — én samlet /proces-side der binder de 3 trin sammen:
 *
 *   1. Indkøbsproces (intake — behov + sagsnummer + indkøb-vs-udvikling)
 *   2. EU AI Act-tjek (klassificering — flag der driver vurdering)
 *   3. Vurdering (Bifrosts regelmotor — endeligt GO/BETINGET-GO/NO-GO)
 *
 * Fri navigation: brugeren kan klikke direkte på ethvert trin uanset
 * progress. Tidligere færdige trin viser ✓ checkmark, kommende viser
 * advarsel hvis ikke gennemført.
 *
 * URL: /proces?case_id=K-...&step=1|2|3
 *
 * Hver trin-section embedder en SIMPLIFIED visning af det pågældende
 * trin's data + en "Åbn fuld side"-knap der dybt-linker til den
 * eksisterende detaljerede side med ?from=proces så tilbage-knap
 * navigerer korrekt.
 */

// ---- Layout primitives -------------------------------------------------

const HeaderBar = styled.header`
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  margin-bottom: 1.5rem;

  .left {
    display: flex;
    align-items: center;
    gap: 14px;
    min-width: 0;
  }

  .case-id {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.78rem;
    color: ${(p) => p.theme.colors.primary};
    font-weight: 600;
  }

  .case-title {
    font-family: ${(p) => p.theme.fonts.display};
    font-size: 1.05rem;
    font-weight: 600;
    color: ${(p) => p.theme.colors.text};
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
`;

// ---- 3-trin stepper ----------------------------------------------------

const StepperBar = styled.div`
  display: grid;
  grid-template-columns: 1fr auto 1fr auto 1fr;
  align-items: stretch;
  gap: 0;
  margin-bottom: 1.75rem;
  border: 1px solid ${(p) => p.theme.colors.border};
  border-radius: 10px;
  background: ${(p) => p.theme.colors.surface};
  overflow: hidden;

  @media (max-width: 720px) {
    grid-template-columns: 1fr;

    .connector {
      display: none;
    }
  }
`;

const StepCard = styled.button`
  background: ${(p) => (p.$active ? (p.theme.colors.paperSoft || 'rgba(13,46,84,0.06)') : 'transparent')};
  border: none;
  padding: 1rem 1.25rem;
  text-align: left;
  cursor: pointer;
  font-family: inherit;
  display: grid;
  grid-template-columns: 38px 1fr;
  gap: 12px;
  align-items: center;
  position: relative;
  border-bottom: 3px solid ${(p) => (p.$active ? p.theme.colors.primary : 'transparent')};

  &:hover {
    background: ${(p) => p.theme.colors.surfaceAlt || 'rgba(13,46,84,0.04)'};
  }
  &:focus-visible {
    outline: 2px solid ${(p) => p.theme.colors.primary};
    outline-offset: -2px;
  }

  .icon {
    width: 38px;
    height: 38px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: ${(p) => (
      p.$status === 'done' ? '#2d6a31' :
      p.$status === 'partial' ? '#6e5527' :
      p.$active ? p.theme.colors.primary :
      p.theme.colors.line
    )};
    color: ${(p) => (p.$status === 'pending' && !p.$active ? p.theme.colors.textMuted : 'white')};
    flex-shrink: 0;
  }

  .body {
    min-width: 0;
  }

  .step-num {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: ${(p) => p.theme.colors.textMuted};
    margin-bottom: 2px;
  }

  .step-title {
    font-family: ${(p) => p.theme.fonts.sans};
    font-size: 0.95rem;
    font-weight: ${(p) => (p.$active ? 700 : 600)};
    color: ${(p) => p.theme.colors.text};
    margin-bottom: 2px;
  }

  .step-meta {
    font-family: ${(p) => p.theme.fonts.body};
    font-size: 0.78rem;
    color: ${(p) => p.theme.colors.textMuted};
  }
`;

const Connector = styled.div`
  width: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;

  svg {
    color: ${(p) => p.theme.colors.line};
    font-size: 0.85rem;
  }
`;

// ---- Step-content shell ------------------------------------------------

const StepShell = styled.section`
  background: ${(p) => p.theme.colors.surface};
  border: 1px solid ${(p) => p.theme.colors.border};
  border-radius: 10px;
  padding: 1.6rem 1.85rem;
  margin-bottom: 1.5rem;

  h2 {
    font-family: ${(p) => p.theme.fonts.display};
    font-size: 1.55rem;
    font-weight: 600;
    margin: 0 0 0.4rem;
    color: ${(p) => p.theme.colors.text};
    letter-spacing: -0.012em;
  }

  .lede {
    font-family: ${(p) => p.theme.fonts.body};
    font-size: 1rem;
    line-height: 1.55;
    color: ${(p) => p.theme.colors.textMuted};
    margin-bottom: 1.5rem;
    max-width: 720px;
  }
`;

const FieldList = styled.div`
  display: grid;
  grid-template-columns: 28px 1fr;
  gap: 8px 14px;
  margin: 1rem 0;

  .marker {
    margin-top: 4px;
    color: ${(p) => p.$ok ? '#2d6a31' : '#a02020'};
    font-size: 1rem;
  }
`;

const FieldRow = styled.div`
  display: contents;

  .marker {
    margin-top: 4px;
    color: ${(p) => (p.$ok ? '#2d6a31' : p.$warn ? '#6e5527' : '#a02020')};
    font-size: 1rem;
  }

  .body {
    padding: 4px 0 10px;
    border-bottom: 1px dashed ${(p) => p.theme.colors.borderSoft};
  }

  &:last-child .body {
    border-bottom: none;
  }

  .label {
    font-family: ${(p) => p.theme.fonts.sans};
    font-size: 0.86rem;
    font-weight: 600;
    color: ${(p) => p.theme.colors.text};
    margin-bottom: 2px;
  }

  .value {
    font-family: ${(p) => p.theme.fonts.body};
    font-size: 0.85rem;
    color: ${(p) => p.theme.colors.textMuted};
    line-height: 1.4;
    word-break: break-word;
  }
`;

const FlagList = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 1rem 0;
`;

const NavRow = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid ${(p) => p.theme.colors.borderSoft};
  flex-wrap: wrap;
`;

// Felt-mapping (samme som IndkoebsOverviewPanel — kondenseret)
const INTAKE_FIELDS = [
  { key: 'behov', label: 'Behovsbeskrivelse', required: true },
  { key: 'dobbeltsystem_tjekket', label: 'Dobbeltsystem-check', required: true, isBool: true },
  { key: 'sagsnummer', label: 'Serviceportal-sagsnummer', required: true },
  { key: 'serviceportal_dato', label: 'Oprettelsesdato', required: false },
  { key: 'indkoeb_eller_udvikling', label: 'Indkøb eller udvikling', required: true },
  { key: 'system_description', label: 'Systembeskrivelse', required: true },
];

const isFilled = (v) => {
  if (v === null || v === undefined) return false;
  if (typeof v === 'boolean') return v;
  if (typeof v === 'string') return v.trim() !== '';
  return true;
};

const STEPS = [
  {
    num: 1,
    id: 'indkoeb',
    title: 'Indkøbsproces',
    icon: FaShoppingCart,
    description: 'Registrér behov, sagsnummer og om I køber færdig løsning eller udvikler skræddersyet.',
  },
  {
    num: 2,
    id: 'eu-checker',
    title: 'EU AI Act-tjek',
    icon: FaBalanceScale,
    description: 'Klassificér AI-systemet via EC\'s officielle wizard — er det forbudt, højrisiko, transparenskrav-pligtigt, eller uden for AI-forordningen?',
  },
  {
    num: 3,
    id: 'vurdering',
    title: 'Bifrost-vurdering',
    icon: FaClipboardCheck,
    description: 'Kør den deterministiske regelmotor mod AI Act + GDPR + dansk forvaltningsret. Producerer GO / BETINGET-GO / NO-GO med konkrete krav og lovcitater.',
  },
];

// ---- Main page ---------------------------------------------------------

const ProcessPage = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const caseId = searchParams.get('case_id');
  const stepParam = searchParams.get('step') || 'indkoeb';
  const activeStep = STEPS.find((s) => s.id === stepParam) || STEPS[0];

  // If no case_id, list eksisterende drafts + opret-ny CTA
  const { data: draftsData } = useQuery(
    'process-drafts',
    async () => {
      const r = await axios.get('/api/v3/cases/drafts?limit=20');
      return r.data;
    },
    { enabled: !caseId, staleTime: 30_000 },
  );

  // Fetch case data
  const { data: caseData, isLoading, isError, error } = useQuery(
    ['process-case', caseId],
    async () => {
      const r = await axios.get(`/api/v3/cases/by-case-id/${encodeURIComponent(caseId)}`);
      return r.data;
    },
    { enabled: !!caseId, retry: false },
  );

  const { data: timelineData } = useQuery(
    ['process-timeline', caseId],
    async () => {
      const r = await axios.get(`/api/v3/cases/by-case-id/${encodeURIComponent(caseId)}/timeline?limit=20`);
      return r.data;
    },
    { enabled: !!caseId, retry: false },
  );

  const setStep = (id) => {
    const params = new URLSearchParams(searchParams);
    params.set('step', id);
    setSearchParams(params, { replace: true });
  };

  const intake = caseData?.intake_state || {};
  const events = timelineData?.events || [];

  // Compute step statuses
  const stepStatuses = useMemo(() => {
    const requiredFilled = INTAKE_FIELDS.filter((f) => f.required && isFilled(intake[f.key])).length;
    const requiredTotal = INTAKE_FIELDS.filter((f) => f.required).length;
    const indkoebStatus = requiredFilled === 0 ? 'pending'
      : requiredFilled === requiredTotal ? 'done'
      : 'partial';

    const ecFlags = intake.ec_flags || {};
    const ecFlagCount = Object.values(ecFlags).filter((v) => v && v !== false).length;
    const ecStatus = ecFlagCount > 0 ? 'done' : 'pending';

    const vurderinger = events.filter((e) => e.kind === 'vurdering');
    const vurderingStatus = vurderinger.length > 0 ? 'done' : 'pending';

    return {
      indkoeb: { status: indkoebStatus, count: requiredFilled, total: requiredTotal },
      'eu-checker': { status: ecStatus, count: ecFlagCount },
      vurdering: { status: vurderingStatus, count: vurderinger.length, latest: vurderinger[0] },
    };
  }, [intake, events]);

  // ---- No case_id: list drafts ----
  if (!caseId) {
    const drafts = draftsData?.items || [];
    return (
      <PageShell>
        <Breadcrumb items={[{ label: 'Proces' }]} />
        <h1 style={{
          fontFamily: 'IBM Plex Sans',
          fontSize: 'clamp(1.8rem, 3vw, 2.4rem)',
          fontWeight: 600,
          letterSpacing: '-0.018em',
          margin: '0 0 0.5rem',
        }}>
          Indkøb og udvikling af AI-løsninger
        </h1>
        <p style={{
          fontFamily: 'IBM Plex Sans',
          fontSize: '1.05rem',
          color: '#666',
          marginBottom: '2rem',
          maxWidth: 720,
          lineHeight: 1.55,
        }}>
          Tre-trins proces der følger Kalundborg Kommunes faktiske workflow.
          Vælg en åben sag herunder eller start en ny.
        </p>

        {drafts.length > 0 && (
          <div style={{ marginBottom: '2rem' }}>
            <h2 style={{ fontFamily: 'IBM Plex Sans', fontSize: '0.78rem', textTransform: 'uppercase', letterSpacing: '0.14em', color: '#5b6573', fontWeight: 600, marginBottom: 12 }}>
              <FaFolderOpen style={{ marginRight: 6, verticalAlign: 'middle' }} />
              Mine åbne sager — {drafts.length}
            </h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
              {drafts.map((d) => {
                const intake = d.intake_state || {};
                return (
                  <button
                    key={d.case_id}
                    onClick={() => setSearchParams({ case_id: d.case_id, step: 'indkoeb' })}
                    style={{
                      background: '#fff', border: '1px solid #d8d3c5', borderRadius: 8,
                      padding: '0.85rem 1rem', textAlign: 'left', cursor: 'pointer',
                      fontFamily: 'inherit',
                    }}
                  >
                    <div style={{ fontFamily: 'IBM Plex Mono', fontSize: '0.72rem', color: '#0d2e54', marginBottom: 4, fontWeight: 600 }}>
                      {d.case_id} · trin {intake.current_step || 1}/4
                    </div>
                    <div style={{ fontFamily: 'IBM Plex Sans', fontSize: '0.92rem', fontWeight: 600, color: '#14181f', marginBottom: 6 }}>
                      {d.title || 'Untitled'}
                    </div>
                    <div style={{ fontSize: '0.78rem', color: '#666' }}>
                      Opdateret {new Date(d.updated_at).toLocaleDateString('da-DK')}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        <Button $variant="primary" $size="lg" onClick={() => navigate('/indkoebsproces')}>
          + Start ny sag <FaArrowRight />
        </Button>
      </PageShell>
    );
  }

  if (isLoading) {
    return (
      <PageShell>
        <LoadingState rows={6} label="Henter sag…" />
      </PageShell>
    );
  }

  if (isError) {
    if (error?.response?.status === 404) {
      return (
        <PageShell>
          <Breadcrumb items={[{ label: 'Proces', to: '/proces' }, { label: caseId }]} />
          <EmptyState
            title="Sagen findes ikke"
            description={`Vi kunne ikke finde sag '${caseId}'. Den er måske slettet eller har et andet sagsnummer.`}
            action={{ label: '+ Start ny sag', onClick: () => navigate('/proces') }}
          />
        </PageShell>
      );
    }
    return (
      <PageShell>
        <ErrorState title="Kunne ikke hente sag" error={error} />
      </PageShell>
    );
  }

  const downloadReport = (fmt) => {
    const a = document.createElement('a');
    a.href = `/api/v3/cases/by-case-id/${encodeURIComponent(caseId)}/report?format=${fmt}`;
    a.rel = 'noopener';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const lastVerdict = caseData?.last_aggregate_status;

  return (
    <PageShell>
      <Breadcrumb
        items={[
          { label: 'Proces', to: '/proces' },
          { label: caseId, to: `/sag/${encodeURIComponent(caseId)}` },
        ]}
      />

      <HeaderBar>
        <div className="left">
          <span className="case-id">{caseId}</span>
          <span className="case-title">{caseData?.title || 'Untitled'}</span>
          <Pill status={caseData?.status || 'kladde'} />
          {lastVerdict && <Pill verdict={lastVerdict} />}
        </div>
        <div className="actions">
          <Button $variant="secondary" $size="sm" onClick={() => downloadReport('docx')}>
            <FaFileWord /> DOCX
          </Button>
          <Button $variant="secondary" $size="sm" onClick={() => downloadReport('pdf')}>
            <FaFilePdf /> PDF
          </Button>
        </div>
      </HeaderBar>

      <StepperBar>
        {STEPS.map((step, idx) => {
          const statusInfo = stepStatuses[step.id];
          const status = statusInfo?.status || 'pending';
          const isActive = step.id === activeStep.id;
          let metaText = '';
          if (step.id === 'indkoeb') {
            metaText = `${statusInfo.count}/${statusInfo.total} felter udfyldt`;
          } else if (step.id === 'eu-checker') {
            metaText = statusInfo.count > 0
              ? `${statusInfo.count} flag rejst`
              : 'Ikke startet';
          } else if (step.id === 'vurdering') {
            metaText = statusInfo.count > 0
              ? `${statusInfo.count} vurdering${statusInfo.count === 1 ? '' : 'er'} kørt`
              : 'Ikke kørt';
          }

          return (
            <React.Fragment key={step.id}>
              <StepCard
                $active={isActive}
                $status={status}
                onClick={() => setStep(step.id)}
                aria-current={isActive ? 'step' : undefined}
              >
                <span className="icon" aria-hidden="true">
                  {status === 'done' ? <FaCheckCircle /> : <step.icon />}
                </span>
                <div className="body">
                  <div className="step-num">Trin {step.num}</div>
                  <div className="step-title">{step.title}</div>
                  <div className="step-meta">{metaText}</div>
                </div>
              </StepCard>
              {idx < STEPS.length - 1 && (
                <Connector className="connector"><FaArrowRight /></Connector>
              )}
            </React.Fragment>
          );
        })}
      </StepperBar>

      {/* ---- Step-content sections ---- */}

      {activeStep.id === 'indkoeb' && (
        <StepShell>
          <h2><FaShoppingCart style={{ marginRight: 10, color: '#0d2e54', verticalAlign: 'middle' }} /> Trin 1 — Indkøbsproces</h2>
          <p className="lede">{activeStep.description}</p>

          <FieldList>
            {INTAKE_FIELDS.map((f) => {
              const v = intake[f.key];
              const filled = isFilled(v);
              return (
                <FieldRow key={f.key} $ok={filled} $warn={!filled && !f.required}>
                  <span className="marker" aria-hidden="true">
                    {filled ? <FaCheckCircle /> : f.required ? <FaExclamationTriangle /> : <FaCircle />}
                  </span>
                  <div className="body">
                    <div className="label">
                      {f.label}
                      {f.required && <span style={{ color: '#a02020', marginLeft: 4 }}>*</span>}
                    </div>
                    <div className="value">
                      {filled
                        ? (typeof v === 'boolean' ? (v ? 'Ja ✓' : 'Nej') : String(v).slice(0, 200))
                        : (f.required ? '(mangler — påkrævet)' : '(ikke udfyldt)')}
                    </div>
                  </div>
                </FieldRow>
              );
            })}
          </FieldList>

          <NavRow>
            <Button $variant="ghost" disabled>← Forrige</Button>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <Button
                $variant="secondary"
                onClick={() => navigate(`/indkoebsproces?case_id=${encodeURIComponent(caseId)}`)}
              >
                <FaEdit /> Åbn fuld wizard
              </Button>
              <Button $variant="primary" onClick={() => setStep('eu-checker')}>
                Næste: EU AI Act-tjek <FaArrowRight />
              </Button>
            </div>
          </NavRow>
        </StepShell>
      )}

      {activeStep.id === 'eu-checker' && (() => {
        const flags = intake.ec_flags || {};
        const activeFlags = Object.entries(flags).filter(([, v]) => v && v !== false);
        return (
          <StepShell>
            <h2><FaBalanceScale style={{ marginRight: 10, color: '#0d2e54', verticalAlign: 'middle' }} /> Trin 2 — EU AI Act-tjek</h2>
            <p className="lede">{activeStep.description}</p>

            {activeFlags.length === 0 ? (
              <Banner $tone="info">
                <strong>EU AI Act-tjek er ikke kørt endnu.</strong>
                {' '}Klassificeringen tager ~5 minutter via EC's officielle 33-spørgsmåls-wizard.
                Resultatet driver hvilke regler Bifrost-vurderingen skal anvende i Trin 3.
              </Banner>
            ) : (
              <>
                <Banner $tone={activeFlags.some(([k]) => k.includes('highrisk') || k.includes('prohibited')) ? 'warn' : 'success'}>
                  <strong>Klassificeret med {activeFlags.length} aktive flag.</strong>
                  {' '}Resultatet anvendes automatisk når du kører Trin 3.
                </Banner>
                <FlagList>
                  {activeFlags.slice(0, 12).map(([flag]) => (
                    <Pill key={flag} tone="info">
                      {flag.replace(/^flag_/, '').replace(/_/g, ' ')}
                    </Pill>
                  ))}
                  {activeFlags.length > 12 && (
                    <Pill tone="neutral">+{activeFlags.length - 12} flere</Pill>
                  )}
                </FlagList>
              </>
            )}

            <NavRow>
              <Button $variant="ghost" onClick={() => setStep('indkoeb')}>← Forrige: Indkøb</Button>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <Button
                  $variant="secondary"
                  onClick={() => navigate(`/eu-checker?fromIndkoeb=${encodeURIComponent(caseId)}&fromProces=1`)}
                >
                  {activeFlags.length > 0 ? <><FaEdit /> Kør om</> : <><FaPlay /> Start EU AI Act-tjek</>}
                </Button>
                <Button $variant="primary" onClick={() => setStep('vurdering')}>
                  Næste: Vurdering <FaArrowRight />
                </Button>
              </div>
            </NavRow>
          </StepShell>
        );
      })()}

      {activeStep.id === 'vurdering' && (() => {
        const vurderinger = events.filter((e) => e.kind === 'vurdering');
        const latest = vurderinger[0];
        const verdictFromTimeline = latest?.label?.match(/^Vurdering: (\S+)/)?.[1];
        const verdict = verdictFromTimeline || lastVerdict;

        return (
          <StepShell>
            <h2><FaClipboardCheck style={{ marginRight: 10, color: '#0d2e54', verticalAlign: 'middle' }} /> Trin 3 — Bifrost-vurdering</h2>
            <p className="lede">{activeStep.description}</p>

            {vurderinger.length === 0 ? (
              <Banner $tone="info">
                <strong>Ingen vurdering kørt endnu.</strong>
                {' '}Bifrost samler dine indtastninger fra Trin 1 + EU <Term term="ai_act">AI Act</Term>-flag fra Trin 2 og kører dem mod alle 21 deklarative regler. Resultatet er et samlet <Term>GO</Term> / <Term>BETINGET-GO</Term> / <Term>NO-GO</Term> med konkrete krav og lovcitater.
              </Banner>
            ) : (
              <>
                <Banner $tone={verdict === 'GO' ? 'success' : verdict === 'NO-GO' ? 'danger' : 'warn'}>
                  <strong>Seneste verdict: {verdict}</strong>
                  {latest?.timestamp && <> — vurderet {new Date(latest.timestamp).toLocaleDateString('da-DK')}</>}
                </Banner>
                <FieldList>
                  {vurderinger.slice(0, 5).map((v, i) => (
                    <FieldRow key={i} $ok={true}>
                      <span className="marker"><FaCheckCircle /></span>
                      <div className="body">
                        <div className="label">{v.label}</div>
                        <div className="value">
                          {v.detail || ''} · {new Date(v.timestamp).toLocaleString('da-DK', { dateStyle: 'short', timeStyle: 'short' })}
                        </div>
                      </div>
                    </FieldRow>
                  ))}
                </FieldList>
              </>
            )}

            <NavRow>
              <Button $variant="ghost" onClick={() => setStep('eu-checker')}>← Forrige: EU AI Act</Button>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {vurderinger.length > 0 && latest?.link && (
                  <Button
                    $variant="secondary"
                    onClick={() => navigate(latest.link)}
                  >
                    Åbn seneste rapport
                  </Button>
                )}
                <Button
                  $variant="primary"
                  onClick={() => navigate(`/vurdering?case_id=${encodeURIComponent(caseId)}&from=indkoeb`)}
                >
                  <FaPlay /> {vurderinger.length > 0 ? 'Kør ny vurdering' : 'Start vurdering'}
                </Button>
              </div>
            </NavRow>
          </StepShell>
        );
      })()}
    </PageShell>
  );
};

export default ProcessPage;
