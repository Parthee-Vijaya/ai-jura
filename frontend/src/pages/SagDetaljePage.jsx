import React, { useMemo, useState } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery } from 'react-query';
import axios from 'axios';
import styled from 'styled-components';
import {
  FaPlay,
  FaFileAlt,
  FaShoppingCart,
  FaClipboardCheck,
  FaHistory,
  FaCheckCircle,
  FaArrowRight,
  FaEdit,
  FaFileWord,
  FaFilePdf,
} from 'react-icons/fa';

import {
  PageShell,
  Breadcrumb,
  Button,
  Pill,
  Banner,
  Card,
  Tabs,
  EmptyState,
  LoadingState,
  ErrorState,
  useToast,
  Term,
} from '../components/ui';
import { EvidenceChecklist, EvidenceEditor } from '../components/rules';
import NextStepCue from '../components/NextStepCue';
import EvidenceProgressRadial from '../components/EvidenceProgressRadial';

/**
 * SagDetaljePage — samlet visning af én sag på tværs af workflow-trin.
 *
 * URL: /sag/:case_id?tab=oversigt|indkoeb|vurderinger|evidens|audit
 *
 * Henter:
 * - GET /api/v3/cases/by-case-id/{case_id}/timeline (samlet feed)
 * - GET /api/v3/cases/{case_id}/evidence (artefakt-status)
 *
 * Erstatter behov for at hoppe mellem /sager → /historik → /indkoebsproces
 * → /vurdering for at samle informationen.
 */

// ---- Layout primitives --------------------------------------------------

const HeroSection = styled.section`
  margin-bottom: 1.5rem;
`;

const HeroMeta = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  font-family: ${(p) => p.theme.fonts.mono};
  font-size: 0.78rem;
  color: ${(p) => p.theme.colors.textMuted};
  margin: 0.4rem 0 1rem;

  .case-id { color: ${(p) => p.theme.colors.primary}; font-weight: 600; }
  .sep { opacity: 0.5; }
`;

const HeroTitle = styled.h1`
  font-family: ${(p) => p.theme.fonts.display};
  font-size: clamp(1.7rem, 3vw, 2.3rem);
  font-weight: 600;
  letter-spacing: -0.018em;
  line-height: 1.15;
  margin: 0;
  color: ${(p) => p.theme.colors.text};
`;

const HeroBar = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 1rem;

  .actions { display: flex; gap: 8px; flex-wrap: wrap; }
`;

const StatStrip = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 0;
  border: 1px solid ${(p) => p.theme.colors.border};
  border-radius: 8px;
  background: ${(p) => p.theme.colors.surface};
  margin-bottom: 1.5rem;
  overflow: hidden;
`;

const Stat = styled.div`
  padding: 0.85rem 1rem;
  border-right: 1px solid ${(p) => p.theme.colors.border};
  &:last-child { border-right: none; }

  .label {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: ${(p) => p.theme.colors.textFaded};
    margin-bottom: 4px;
  }
  .value {
    font-family: ${(p) => p.theme.fonts.display};
    font-size: 1.15rem;
    font-weight: 700;
    color: ${(p) => p.theme.colors.text};
    line-height: 1.1;
  }
  .delta {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.66rem;
    color: ${(p) => p.theme.colors.textMuted};
    margin-top: 3px;
  }

  @media (max-width: 720px) {
    border-right: none;
    border-bottom: 1px solid ${(p) => p.theme.colors.border};
    &:last-child { border-bottom: none; }
  }
`;

const TabContent = styled.div`
  padding: 1.5rem 0;
`;

const TimelineList = styled.ol`
  list-style: none;
  padding: 0;
  margin: 0;
  position: relative;

  /* Vertical line that connects all dots */
  &::before {
    content: '';
    position: absolute;
    left: 11px;
    top: 8px;
    bottom: 8px;
    width: 2px;
    background: ${(p) => p.theme.colors.borderSoft};
  }
`;

const TimelineItem = styled.li`
  position: relative;
  padding: 0.4rem 0 0.85rem 36px;
  font-family: ${(p) => p.theme.fonts.body};
  font-size: 0.9rem;

  .dot {
    position: absolute;
    left: 5px;
    top: 8px;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: ${(p) => p.theme.colors.surface};
    border: 2px solid ${(p) => {
      if (p.$kind === 'vurdering') return p.theme.colors.primary;
      if (p.$kind === 'evidens_completed') return '#2d6a31';
      if (p.$kind === 'evidens_comment') return '#0d2e54';
      if (p.$kind === 'transition') return p.theme.colors.bronze;
      return p.theme.colors.textFaded;
    }};
  }
  .label {
    font-weight: 500;
    color: ${(p) => p.theme.colors.text};
    margin-bottom: 2px;

    a { color: ${(p) => p.theme.colors.primary}; text-decoration: none; }
    a:hover { text-decoration: underline; }
  }
  .meta {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.72rem;
    color: ${(p) => p.theme.colors.textMuted};
  }
  .detail {
    font-size: 0.84rem;
    color: ${(p) => p.theme.colors.textMuted};
    margin-top: 4px;
    font-style: italic;
  }
`;

const QuickLinkGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
`;

const QuickLink = styled.button`
  background: ${(p) => p.theme.colors.surface};
  border: 1px solid ${(p) => p.theme.colors.border};
  border-radius: 8px;
  padding: 1rem 1.1rem;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-family: inherit;

  &:hover {
    border-color: ${(p) => p.theme.colors.primary};
    box-shadow: 0 2px 6px rgba(0,0,0,0.05);
  }

  .icon {
    color: ${(p) => p.theme.colors.primary};
    font-size: 1rem;
  }
  .h {
    font-family: ${(p) => p.theme.fonts.sans};
    font-weight: 600;
    font-size: 0.95rem;
    color: ${(p) => p.theme.colors.text};
    display: flex;
    align-items: center;
    gap: 8px;
    justify-content: space-between;
  }
  .desc {
    font-family: ${(p) => p.theme.fonts.body};
    font-size: 0.82rem;
    color: ${(p) => p.theme.colors.textMuted};
    line-height: 1.45;
  }
`;

const IntakeReadout = styled.dl`
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: 8px 16px;
  margin: 0;
  font-family: ${(p) => p.theme.fonts.body};
  font-size: 0.92rem;

  dt {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: ${(p) => p.theme.colors.textFaded};
    padding-top: 3px;
  }
  dd {
    margin: 0;
    color: ${(p) => p.theme.colors.text};
    word-break: break-word;
  }

  @media (max-width: 640px) {
    grid-template-columns: 1fr;
    dt { padding-top: 8px; }
    dd { padding-bottom: 8px; border-bottom: 1px dashed ${(p) => p.theme.colors.borderSoft}; }
  }
`;

// ---- Helpers ------------------------------------------------------------

const formatDate = (iso) => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleDateString('da-DK', {
      day: 'numeric', month: 'short', year: 'numeric',
    });
  } catch {
    return iso;
  }
};

const formatRelative = (iso) => {
  if (!iso) return '—';
  const d = new Date(iso);
  const diffMs = Date.now() - d.getTime();
  const days = Math.floor(diffMs / 86400000);
  if (days === 0) return 'i dag';
  if (days === 1) return 'i går';
  if (days < 7) return `${days} dage siden`;
  if (days < 30) return `${Math.floor(days / 7)} uger siden`;
  return formatDate(iso);
};

// Trigger browser download af rapport. Bruger window.open så vi får native
// browser-download-prompt (i stedet for fetch + blob-rute som kan blokeres
// af pop-up-blockers eller miste filename-headers).
const downloadReport = (caseId, format) => {
  if (!caseId) return;
  const url = `/api/v3/cases/by-case-id/${encodeURIComponent(caseId)}/report?format=${format}`;
  // Use a hidden link så download starter uden at åbne ny tab
  const a = document.createElement('a');
  a.href = url;
  a.rel = 'noopener';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
};

// ---- Main page ----------------------------------------------------------

const SagDetaljePage = () => {
  const { case_id } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const toast = useToast();
  const activeTab = searchParams.get('tab') || 'oversigt';
  const setTab = (id) => setSearchParams({ tab: id }, { replace: true });

  const [editorOpen, setEditorOpen] = useState(false);
  const [editorArtifactId, setEditorArtifactId] = useState(null);
  const [evidenceCounter, setEvidenceCounter] = useState(0);

  // Fetch timeline + case
  const {
    data: timelineData,
    isLoading: timelineLoading,
    isError: timelineError,
    error: tlErr,
    refetch: refetchTimeline,
  } = useQuery(
    ['sag-timeline', case_id, evidenceCounter],
    async () => {
      const r = await axios.get(
        `/api/v3/cases/by-case-id/${encodeURIComponent(case_id)}/timeline?limit=50`,
      );
      return r.data;
    },
    { enabled: !!case_id, staleTime: 10_000, retry: 1 },
  );

  // Fetch evidence rows
  const { data: evidenceData } = useQuery(
    ['sag-evidens', case_id, evidenceCounter],
    async () => {
      const r = await axios.get(`/api/v3/cases/${encodeURIComponent(case_id)}/evidence`);
      return r.data;
    },
    { enabled: !!case_id, staleTime: 10_000 },
  );

  const caseRow = timelineData?.case;
  const events = timelineData?.events || [];
  const intake = caseRow?.intake_state || {};

  const evidenceItems = useMemo(() => {
    return (evidenceData?.items || []).map((it) => ({
      id: it.artifact_id,
      label: it.artifact_id.replace(/_/g, ' '),
      status: it.status === 'faerdig' || it.status === 'godkendt' ? 'done'
        : it.status === 'i_gang' ? 'in_progress' : 'pending',
      metadata: it.completed_at
        ? `gemt ${formatRelative(it.completed_at)}`
        : it.updated_at ? `påbegyndt ${formatRelative(it.updated_at)}` : null,
    }));
  }, [evidenceData]);

  const evidenceProgress = useMemo(() => {
    const items = evidenceData?.items || [];
    const total = items.length;
    const done = items.filter((it) => it.status === 'faerdig' || it.status === 'godkendt').length;
    return { done, total, pct: total > 0 ? Math.round((done / total) * 100) : 0 };
  }, [evidenceData]);

  const vurderinger = useMemo(
    () => events.filter((e) => e.kind === 'vurdering'),
    [events],
  );

  const transitions = useMemo(
    () => events.filter((e) => e.kind === 'transition' || e.kind === 'intake_updated'),
    [events],
  );

  const openEvidens = (id) => {
    setEditorArtifactId(id);
    setEditorOpen(true);
  };

  if (!case_id) {
    return (
      <PageShell>
        <ErrorState title="Manglende sags-id" detail="URL'en mangler et sagsnummer." />
      </PageShell>
    );
  }

  if (timelineLoading) {
    return (
      <PageShell>
        <LoadingState rows={6} label="Henter sag…" />
      </PageShell>
    );
  }

  if (timelineError) {
    const status = tlErr?.response?.status;
    if (status === 404) {
      return (
        <PageShell>
          <Breadcrumb items={[{ label: 'Sager', to: '/sager' }, { label: case_id }]} />
          <EmptyState
            title="Sagen findes ikke"
            description={`Vi kunne ikke finde sag '${case_id}'. Tjek sagsnummeret eller opret en ny sag i indkøbsprocessen.`}
            action={{ label: '+ Start ny sag', onClick: () => navigate('/indkoebsproces') }}
          />
        </PageShell>
      );
    }
    return (
      <PageShell>
        <Breadcrumb items={[{ label: 'Sager', to: '/sager' }, { label: case_id }]} />
        <ErrorState
          title="Kunne ikke hente sag"
          error={tlErr}
          onRetry={refetchTimeline}
        />
      </PageShell>
    );
  }

  const tabs = [
    { id: 'oversigt', label: 'Oversigt', icon: <FaFileAlt /> },
    { id: 'indkoeb', label: 'Indkøb', icon: <FaShoppingCart /> },
    { id: 'vurderinger', label: 'Vurderinger', icon: <FaClipboardCheck />, count: vurderinger.length },
    { id: 'evidens', label: 'Evidens', icon: <FaCheckCircle />, count: evidenceProgress.total > 0 ? `${evidenceProgress.done}/${evidenceProgress.total}` : 0 },
    { id: 'audit', label: 'Audit-trail', icon: <FaHistory /> },
  ];

  const lastVerdict = caseRow?.last_aggregate_status;
  const reviewDate = caseRow?.next_review_at ? formatDate(caseRow.next_review_at) : '—';

  return (
    <PageShell>
      <Breadcrumb
        items={[
          { label: 'Sager', to: '/sager' },
          { label: case_id },
        ]}
      />

      <HeroSection>
        <HeroBar>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <Pill status={caseRow?.status || 'kladde'} />
            {lastVerdict && <Pill verdict={lastVerdict} />}
          </div>
          <div className="actions">
            <Button
              $variant="secondary"
              $size="sm"
              onClick={() => downloadReport(case_id, 'docx')}
              title="Download som Word-dokument du kan redigere videre"
            >
              <FaFileWord /> DOCX
            </Button>
            <Button
              $variant="secondary"
              $size="sm"
              onClick={() => downloadReport(case_id, 'pdf')}
              title="Download som print-klar PDF"
            >
              <FaFilePdf /> PDF
            </Button>
            <Button
              $variant="secondary"
              $size="sm"
              onClick={() => navigate(`/indkoebsproces?case_id=${encodeURIComponent(case_id)}`)}
            >
              <FaEdit /> Rediger
            </Button>
            <Button
              $variant="primary"
              $size="sm"
              onClick={() => navigate(`/vurdering?case_id=${encodeURIComponent(case_id)}&from=indkoeb`)}
            >
              <FaPlay /> Ny vurdering
            </Button>
          </div>
        </HeroBar>
        <HeroTitle>{caseRow?.title || case_id}</HeroTitle>
        <HeroMeta>
          <span className="case-id">{case_id}</span>
          {caseRow?.assigned_to && (<><span className="sep">·</span><span>{caseRow.assigned_to}</span></>)}
          <span className="sep">·</span>
          <span>Oprettet {formatDate(caseRow?.created_at)}</span>
          <span className="sep">·</span>
          <span>Opdateret {formatRelative(caseRow?.updated_at)}</span>
        </HeroMeta>
      </HeroSection>

      <StatStrip>
        <Stat>
          <div className="label">Status</div>
          <div className="value">{caseRow?.status_label || caseRow?.status || '—'}</div>
          <div className="delta">workflow</div>
        </Stat>
        <Stat>
          <div className="label">Verdict</div>
          <div className="value">{lastVerdict || '—'}</div>
          <div className="delta">{vurderinger.length} vurdering{vurderinger.length === 1 ? '' : 'er'}</div>
        </Stat>
        <Stat>
          <div className="label">Evidens</div>
          <div className="value">{evidenceProgress.done}/{evidenceProgress.total || 0}</div>
          <div className="delta">{evidenceProgress.pct}% færdig</div>
        </Stat>
        <Stat>
          <div className="label">Næste review</div>
          <div className="value" style={{ fontSize: '0.95rem', fontWeight: 600 }}>{reviewDate}</div>
          <div className="delta">{caseRow?.next_review_at ? formatRelative(caseRow.next_review_at) : 'ikke planlagt'}</div>
        </Stat>
      </StatStrip>

      <NextStepCue
        intake={intake}
        verdict={lastVerdict}
        vurderingerCount={vurderinger.length}
        evidenceProgress={evidenceProgress}
        evidenceItems={evidenceItems}
        caseId={case_id}
        onOpenTab={setTab}
        onOpenEvidens={openEvidens}
      />

      <Tabs tabs={tabs} activeTab={activeTab} onChange={setTab} />

      <TabContent>
        {activeTab === 'oversigt' && (
          <>
            <Banner $tone="info" style={{ marginBottom: 16 }}>
              <strong>Hurtig handling:</strong> Den her side samler alt om sagen. Brug fanerne ovenfor til at se indkøbsproces, vurderinger, evidens-checkliste eller audit-trail. Klik knapperne foroven for at handle på sagen.
            </Banner>

            <h2 style={{ fontFamily: 'inherit', fontSize: '1.05rem', fontWeight: 600, margin: '1rem 0 0.6rem' }}>Næste skridt</h2>
            <QuickLinkGrid>
              <QuickLink onClick={() => setTab('evidens')}>
                <span className="h"><FaCheckCircle className="icon" /> {evidenceProgress.total - evidenceProgress.done} evidens-artefakter mangler <FaArrowRight /></span>
                <span className="desc">Udfyld <Term>DPIA</Term>, <Term term="dbs">databehandleraftale</Term>, risikostyringsplan og resten af de påkrævede skabeloner.</span>
              </QuickLink>
              <QuickLink onClick={() => setTab('vurderinger')}>
                <span className="h"><FaClipboardCheck className="icon" /> {vurderinger.length === 0 ? 'Ingen vurderinger endnu' : `Se ${vurderinger.length} tidligere vurdering${vurderinger.length === 1 ? '' : 'er'}`} <FaArrowRight /></span>
                <span className="desc">Kør Bifrost-vurderingsmotor eller åbn et tidligere resultat.</span>
              </QuickLink>
              <QuickLink onClick={() => navigate(`/eu-checker?fromIndkoeb=${encodeURIComponent(case_id)}`)}>
                <span className="h"><FaShoppingCart className="icon" /> EU AI Act-tjek <FaArrowRight /></span>
                <span className="desc">Klassificér systemet i EC's officielle compliance-wizard.</span>
              </QuickLink>
            </QuickLinkGrid>

            <h2 style={{ fontFamily: 'inherit', fontSize: '1.05rem', fontWeight: 600, margin: '2rem 0 0.6rem' }}>Seneste aktivitet</h2>
            {events.length === 0 ? (
              <EmptyState compact title="Ingen aktivitet endnu" description="Aktivitet fra vurderinger, evidens og status-skift vises her." />
            ) : (
              <TimelineList>
                {events.slice(0, 8).map((e, i) => (
                  <TimelineItem key={i} $kind={e.kind}>
                    <span className="dot" />
                    <div className="label">
                      {e.link ? <a href={e.link}>{e.label}</a> : e.label}
                    </div>
                    <div className="meta">{formatRelative(e.timestamp)} {e.actor && `· ${e.actor}`}</div>
                    {e.detail && <div className="detail">{e.detail}</div>}
                  </TimelineItem>
                ))}
              </TimelineList>
            )}
          </>
        )}

        {activeTab === 'indkoeb' && (
          <>
            {Object.keys(intake).length === 0 ? (
              <EmptyState
                title="Indkøbsproces er ikke startet"
                description="Start indkøbsproces-wizarden for at registrere behov, dobbeltsystem-check og indkøb-vs-udvikling."
                action={{ label: 'Start indkøbsproces →', onClick: () => navigate(`/indkoebsproces?case_id=${encodeURIComponent(case_id)}`) }}
              />
            ) : (
              <>
                <Banner $tone="info" style={{ marginBottom: 16 }}>
                  <strong>Læs-only visning</strong> af indkøbsprocessens state. Klik <strong>Rediger indkøb</strong> øverst for at åbne wizarden.
                </Banner>
                <Card $padding="lg">
                  <IntakeReadout>
                    <dt>Aktuelt trin</dt>
                    <dd>{intake.current_step || 1} af 4</dd>

                    <dt>Behov</dt>
                    <dd>{intake.behov || '—'}</dd>

                    <dt>Dobbeltsystem-tjekket</dt>
                    <dd>{intake.dobbeltsystem_tjekket ? 'Ja ✓' : 'Nej'}</dd>

                    <dt>Sagsnummer</dt>
                    <dd>{intake.sagsnummer || case_id}</dd>

                    <dt>Oprettelsesdato</dt>
                    <dd>{intake.serviceportal_dato ? formatDate(intake.serviceportal_dato) : '—'}</dd>

                    <dt>Indkøb / udvikling</dt>
                    <dd>{intake.indkoeb_eller_udvikling === 'indkoeb' ? 'Indkøb af færdig løsning' : intake.indkoeb_eller_udvikling === 'udvikling' ? 'Skræddersyet udvikling' : '—'}</dd>

                    <dt>Systembeskrivelse</dt>
                    <dd>{intake.system_description || '—'}</dd>
                  </IntakeReadout>
                </Card>
              </>
            )}
          </>
        )}

        {activeTab === 'vurderinger' && (
          <>
            {vurderinger.length === 0 ? (
              <EmptyState
                title="Ingen vurderinger endnu"
                description="Kør Bifrosts regelmotor for at få en GO / BETINGET-GO / NO-GO-vurdering med konkrete krav og lovcitater."
                action={{
                  label: 'Kør første vurdering →',
                  onClick: () => navigate(`/vurdering?case_id=${encodeURIComponent(case_id)}&from=indkoeb`),
                }}
              />
            ) : (
              <>
                <p style={{ fontSize: '0.92rem', color: '#777', marginTop: 0, marginBottom: '1rem' }}>
                  {vurderinger.length} vurdering{vurderinger.length === 1 ? '' : 'er'} kørt på sagen — nyeste først. Klik for at åbne den fulde rapport.
                </p>
                <TimelineList>
                  {vurderinger.map((v, i) => (
                    <TimelineItem key={i} $kind={v.kind}>
                      <span className="dot" />
                      <div className="label">
                        {v.link ? <a href={v.link}>{v.label}</a> : v.label}
                      </div>
                      <div className="meta">{formatDate(v.timestamp)} {v.actor && `· ${v.actor}`}</div>
                      {v.detail && <div className="detail">{v.detail}</div>}
                    </TimelineItem>
                  ))}
                </TimelineList>
              </>
            )}
          </>
        )}

        {activeTab === 'evidens' && (
          <>
            {evidenceItems.length === 0 ? (
              <EmptyState
                title="Ingen evidens-artefakter endnu"
                description="Når du kører en vurdering bliver de relevante artefakter (DPIA, databehandleraftale, risikostyringsplan osv.) automatisk tilføjet her."
              />
            ) : (
              <>
                <div style={{ marginBottom: 16 }}>
                  <EvidenceProgressRadial evidenceItems={evidenceItems} />
                </div>
                <EvidenceChecklist
                  items={evidenceItems}
                  onToggle={(id) => openEvidens(id)}
                />
              </>
            )}
          </>
        )}

        {activeTab === 'audit' && (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', gap: '1rem', flexWrap: 'wrap' }}>
              <p style={{ fontSize: '0.92rem', color: '#5b6573', margin: 0 }}>
                Komplet audit-trail af status-skift, intake-opdateringer og evidens-events. Append-only — kan ikke redigeres.
              </p>
              <button
                type="button"
                onClick={() => {
                  const a = document.createElement('a');
                  a.href = `/api/v3/audit/export.csv?case_id=${encodeURIComponent(case_id)}`;
                  a.download = '';
                  document.body.appendChild(a);
                  a.click();
                  document.body.removeChild(a);
                }}
                title="Download vurderings-audit for denne sag som CSV"
                style={{
                  background: 'transparent',
                  color: '#0d2e54',
                  border: '1px solid #d8d3c5',
                  padding: '0.45rem 0.85rem',
                  borderRadius: 4,
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                  fontSize: '0.82rem',
                  whiteSpace: 'nowrap',
                }}
              >
                ↓ Audit-CSV
              </button>
            </div>
            {events.length === 0 ? (
              <EmptyState compact title="Ingen audit-events" description="Sagen har ingen registrerede events endnu." />
            ) : (
              <TimelineList>
                {events.map((e, i) => (
                  <TimelineItem key={i} $kind={e.kind}>
                    <span className="dot" />
                    <div className="label">
                      {e.link ? <a href={e.link}>{e.label}</a> : e.label}
                    </div>
                    <div className="meta">
                      {formatDate(e.timestamp)} {new Date(e.timestamp).toLocaleTimeString('da-DK', { hour: '2-digit', minute: '2-digit' })}
                      {e.actor && ` · ${e.actor}`}
                      <span className="sep" style={{ margin: '0 6px' }}>·</span>
                      <span style={{ opacity: 0.7 }}>{e.kind}</span>
                    </div>
                    {e.detail && <div className="detail">{e.detail}</div>}
                  </TimelineItem>
                ))}
              </TimelineList>
            )}
          </>
        )}
      </TabContent>

      <EvidenceEditor
        open={editorOpen}
        artifactId={editorArtifactId}
        caseId={case_id}
        user={typeof window !== 'undefined' ? localStorage.getItem('tyrUser') || undefined : undefined}
        onClose={() => setEditorOpen(false)}
        onSaved={(artifactId, status) => {
          setEvidenceCounter((n) => n + 1);
          if (status === 'faerdig' || status === 'godkendt') {
            toast.success(`Gemt på sag ${case_id}`, {
              link: `/sag/${case_id}?tab=evidens`,
              linkLabel: 'Se evidens →',
            });
          }
        }}
      />
    </PageShell>
  );
};

export default SagDetaljePage;
