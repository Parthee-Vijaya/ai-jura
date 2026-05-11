import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from 'react-query';
import axios from 'axios';
import styled from 'styled-components';
import {
  FaCheckCircle,
  FaExclamationTriangle,
  FaChevronDown,
  FaChevronRight,
  FaArrowRight,
  FaCircle,
} from 'react-icons/fa';

import { Pill } from './ui';

/**
 * IndkoebsOverviewPanel — samlet "Sag-komplet-overblik" der vises på
 * /vurdering (både form-mode og result-mode).
 *
 * Henter:
 * - Case + intake_state via /api/v3/cases/by-case-id/{id}
 * - Evidence rows via /api/v3/cases/{id}/evidence
 * - Timeline (vurderinger) via /api/v3/cases/by-case-id/{id}/timeline
 *
 * Renderer 4 collapsible sektioner:
 * 1. Indkøbsproces-felter med lov-krav-mapping (hardcoded canonical)
 * 2. EU AI Act-flag (fra intake_state.ec_flags eller sessionStorage)
 * 3. Evidens-status
 * 4. Vurderings-historik
 *
 * Hver felt har et grønt ✓ (opfylder lovkrav) eller gult ⚠ (mangler — spærrer).
 */

// ---- Felt → lovkrav-mapping ---------------------------------------------
//
// Curated mapping baseret på AI Act + GDPR + dansk forvaltningsret +
// god forvaltningsskik. Hver indkøbs-felt opfylder konkrete krav.

const INTAKE_FIELD_REQUIREMENTS = {
  behov: {
    label: 'Behovsbeskrivelse',
    required: true,
    requirements: [
      { lov: 'FVL § 22', desc: 'Begrundelsespligt — formålet skal være klart' },
      { lov: 'AI Act Art. 13(3)(b)', desc: 'Tilsigtede formål skal beskrives' },
      { lov: 'God forvaltningsskik', desc: 'Saglighedsprincip' },
    ],
  },
  dobbeltsystem_tjekket: {
    label: 'Dobbeltsystem-check',
    required: true,
    requirements: [
      { lov: 'KL IT-arkitekturprincip', desc: 'Undgå parallelle løsninger' },
      { lov: 'AI Pact-frivillig', desc: 'Effektiv ressourceanvendelse' },
    ],
  },
  sagsnummer: {
    label: 'Serviceportal-sagsnummer',
    required: true,
    requirements: [
      { lov: 'God forvaltningsskik', desc: 'Journaliseringspligt' },
      { lov: 'Offentlighedsloven § 16', desc: 'Sagsoplysning + sammenhæng' },
    ],
  },
  serviceportal_dato: {
    label: 'Sagsoprettelsesdato',
    required: false,
    requirements: [
      { lov: 'God forvaltningsskik', desc: 'Tidsregistrering for audit-trail' },
    ],
  },
  indkoeb_eller_udvikling: {
    label: 'Indkøb vs. udvikling',
    required: true,
    requirements: [
      { lov: 'AI Act Art. 25', desc: 'Substantial modification → udbyder-rolle' },
      { lov: 'AI Act Art. 16-22', desc: 'Bestemmer udbyder-forpligtelser' },
    ],
  },
  system_description: {
    label: 'Systembeskrivelse',
    required: true,
    requirements: [
      { lov: 'AI Act Art. 11 + Bilag IV', desc: 'Teknisk dokumentation — generel beskrivelse' },
      { lov: 'AI Act Art. 13', desc: 'Transparens-krav (kapabiliteter + begrænsninger)' },
      { lov: 'GDPR Art. 30', desc: 'Fortegnelse over behandlingsaktiviteter' },
    ],
  },
};

// EU AI Act-flag → kort dansk forklaring + tone
const FLAG_DISPLAY = {
  flag_risklevel_aisystem_highrisk_output: { label: 'Højrisiko AI-system (Bilag III)', tone: 'danger' },
  flag_risklevel_aisystem_nohighrisk_output: { label: 'Ikke-højrisiko AI-system', tone: 'success' },
  flag_obligations_prohibitedsystems_result_output: { label: 'Mulig forbudt praksis (Art. 5)', tone: 'danger' },
  flag_outofscope: { label: 'Uden for AI Act-anvendelsesområde', tone: 'info' },
  flag_ai_system_role_provider: { label: 'Rolle: Udbyder', tone: 'info' },
  flag_ai_system_role_deployer: { label: 'Rolle: Idriftsætter', tone: 'info' },
  flag_ai_system_role_distributor: { label: 'Rolle: Distributør', tone: 'info' },
  flag_ai_system_role_importer: { label: 'Rolle: Importør', tone: 'info' },
  flag_fr_impact_assessment_deployer: { label: 'FRIA påkrævet', tone: 'warn' },
  flag_obligation_transparency_provider: { label: 'Transparenskrav (udbyder)', tone: 'warn' },
  flag_obligation_transparency_deployer: { label: 'Transparenskrav (idriftsætter)', tone: 'warn' },
};

// ---- Helpers ------------------------------------------------------------

const isFilled = (v) => {
  if (v === null || v === undefined) return false;
  if (typeof v === 'boolean') return v;
  if (typeof v === 'string') return v.trim() !== '';
  return true;
};

const formatRelative = (iso) => {
  if (!iso) return '—';
  const d = new Date(iso);
  const diffMs = Date.now() - d.getTime();
  const days = Math.floor(diffMs / 86400000);
  if (days === 0) return 'i dag';
  if (days === 1) return 'i går';
  if (days < 7) return `${days} dage siden`;
  return d.toLocaleDateString('da-DK', { day: 'numeric', month: 'short' });
};

// ---- Styled -------------------------------------------------------------

const Wrap = styled.section`
  background: ${(p) => p.theme.colors.surface || '#fff'};
  border: 1px solid ${(p) => p.theme.colors.border};
  border-radius: 8px;
  margin-bottom: 1.5rem;
  overflow: hidden;
`;

const TopBar = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: ${(p) => p.theme.colors.paperSoft || 'rgba(13,46,84,0.04)'};
  border-bottom: 1px solid ${(p) => p.theme.colors.border};
  cursor: pointer;
  user-select: none;

  &:hover { background: ${(p) => p.theme.colors.surfaceAlt || 'rgba(13,46,84,0.06)'}; }

  .left {
    display: flex;
    align-items: center;
    gap: 10px;
    font-family: ${(p) => p.theme.fonts.sans};
    font-weight: 600;
    font-size: 0.92rem;
    color: ${(p) => p.theme.colors.text};
  }

  .meta {
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.74rem;
    color: ${(p) => p.theme.colors.textMuted};
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .chevron {
    color: ${(p) => p.theme.colors.textFaded};
  }
`;

const Body = styled.div`
  padding: 4px 0;
`;

const Section = styled.div`
  border-bottom: 1px solid ${(p) => p.theme.colors.borderSoft};
  &:last-child { border-bottom: none; }
`;

const SectionHead = styled.button`
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: transparent;
  border: none;
  padding: 10px 16px;
  cursor: pointer;
  text-align: left;
  font-family: inherit;

  &:hover { background: ${(p) => p.theme.colors.surfaceAlt || 'rgba(0,0,0,0.02)'}; }
  &:focus-visible {
    outline: 2px solid ${(p) => p.theme.colors.primary};
    outline-offset: -2px;
  }

  .label {
    font-family: ${(p) => p.theme.fonts.sans};
    font-size: 0.86rem;
    font-weight: 600;
    color: ${(p) => p.theme.colors.text};
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .stat {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.72rem;
    color: ${(p) => p.theme.colors.textMuted};
  }

  .chevron {
    color: ${(p) => p.theme.colors.textFaded};
    margin-left: 8px;
  }
`;

const SectionContent = styled.div`
  padding: 8px 16px 14px;
`;

const FieldRow = styled.div`
  display: grid;
  grid-template-columns: 28px 1fr;
  gap: 10px;
  padding: 8px 0;
  border-top: 1px dashed ${(p) => p.theme.colors.borderSoft};

  &:first-child { border-top: none; }

  .marker {
    margin-top: 3px;
    color: ${(p) => (
      p.$status === 'ok' ? '#2d6a31' :
      p.$status === 'warn' ? '#6e5527' :
      p.$status === 'missing' ? '#a02020' :
      p.theme.colors.textFaded
    )};
    font-size: 1.05rem;
  }

  .body {
    min-width: 0;
  }

  .field-label {
    font-family: ${(p) => p.theme.fonts.sans};
    font-size: 0.9rem;
    font-weight: 600;
    color: ${(p) => p.theme.colors.text};
    margin-bottom: 2px;
    display: flex;
    align-items: baseline;
    gap: 8px;

    .req-tag {
      font-family: ${(p) => p.theme.fonts.mono};
      font-size: 0.62rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      padding: 1px 6px;
      border-radius: 999px;
      background: ${(p) => p.theme.colors.surfaceAlt || 'rgba(0,0,0,0.04)'};
      color: ${(p) => p.theme.colors.textMuted};
      font-weight: 500;

      &.req-yes { background: rgba(160, 32, 32, 0.08); color: #a02020; }
    }
  }

  .field-value {
    font-family: ${(p) => p.theme.fonts.body};
    font-size: 0.86rem;
    color: ${(p) => p.theme.colors.textMuted};
    line-height: 1.4;
    margin-bottom: 6px;
    word-break: break-word;
    font-style: italic;
  }

  .field-value.missing {
    color: #a02020;
    font-style: italic;
  }

  .req-list {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .req-item {
    font-family: ${(p) => p.theme.fonts.body};
    font-size: 0.78rem;
    color: ${(p) => p.theme.colors.textMuted};
    line-height: 1.45;

    .lov {
      font-family: ${(p) => p.theme.fonts.mono};
      font-weight: 600;
      color: ${(p) => p.theme.colors.primary};
      font-size: 0.74rem;
      margin-right: 6px;
    }
  }
`;

const FlagRow = styled.div`
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
  font-family: ${(p) => p.theme.fonts.body};
  font-size: 0.86rem;
  color: ${(p) => p.theme.colors.text};

  .marker {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: ${(p) => (
      p.$tone === 'danger' ? '#a02020' :
      p.$tone === 'warn' ? '#6e5527' :
      p.$tone === 'success' ? '#2d6a31' :
      '#0d2e54'
    )};
    flex-shrink: 0;
  }

  code {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.7rem;
    color: ${(p) => p.theme.colors.textFaded};
    margin-left: auto;
  }
`;

const VurderingItem = styled.button`
  width: 100%;
  background: transparent;
  border: 1px solid ${(p) => p.theme.colors.border};
  border-radius: 5px;
  padding: 8px 12px;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  cursor: pointer;
  font-family: inherit;
  text-align: left;

  &:hover {
    border-color: ${(p) => p.theme.colors.primary};
  }

  .meta {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.7rem;
    color: ${(p) => p.theme.colors.textMuted};
  }
`;

// ---- Main component -----------------------------------------------------

export const IndkoebsOverviewPanel = ({ caseId, defaultOpen = true }) => {
  const navigate = useNavigate();
  const [open, setOpen] = useState(defaultOpen);
  const [openSections, setOpenSections] = useState({
    intake: true,
    ec: true,
    evidens: false,
    historik: false,
  });

  const toggle = (key) => setOpenSections((s) => ({ ...s, [key]: !s[key] }));

  // Fetch case data
  const { data: caseData } = useQuery(
    ['sag-overview-case', caseId],
    async () => {
      const r = await axios.get(`/api/v3/cases/by-case-id/${encodeURIComponent(caseId)}`);
      return r.data;
    },
    { enabled: !!caseId, retry: false, staleTime: 30_000 },
  );

  const { data: evidenceData } = useQuery(
    ['sag-overview-evidence', caseId],
    async () => {
      const r = await axios.get(`/api/v3/cases/${encodeURIComponent(caseId)}/evidence`);
      return r.data;
    },
    { enabled: !!caseId, retry: false, staleTime: 30_000 },
  );

  const { data: timelineData } = useQuery(
    ['sag-overview-timeline', caseId],
    async () => {
      const r = await axios.get(`/api/v3/cases/by-case-id/${encodeURIComponent(caseId)}/timeline?limit=20`);
      return r.data;
    },
    { enabled: !!caseId, retry: false, staleTime: 30_000 },
  );

  const intake = caseData?.intake_state || {};
  const evidence = evidenceData?.items || [];
  const events = timelineData?.events || [];
  const vurderinger = events.filter((e) => e.kind === 'vurdering');

  // EC flags fra intake_state ELLER fra sessionStorage (frisk EC-tjek)
  const ecFlags = useMemo(() => {
    if (intake?.ec_flags && typeof intake.ec_flags === 'object') return intake.ec_flags;
    if (typeof window !== 'undefined') {
      try {
        const stored = sessionStorage.getItem('tyrEcCheckerFlags');
        if (stored) {
          const parsed = JSON.parse(stored);
          return parsed?.flags || {};
        }
      } catch { /* ignore */ }
    }
    return {};
  }, [intake]);

  // Compute completion-stats for top-bar
  const intakeStats = useMemo(() => {
    const fieldKeys = Object.keys(INTAKE_FIELD_REQUIREMENTS);
    const requiredKeys = fieldKeys.filter((k) => INTAKE_FIELD_REQUIREMENTS[k].required);
    const filledRequired = requiredKeys.filter((k) => isFilled(intake[k])).length;
    return {
      filled: fieldKeys.filter((k) => isFilled(intake[k])).length,
      total: fieldKeys.length,
      requiredFilled: filledRequired,
      requiredTotal: requiredKeys.length,
    };
  }, [intake]);

  const evidenceStats = useMemo(() => {
    const total = evidence.length;
    const done = evidence.filter((e) => e.status === 'faerdig' || e.status === 'godkendt').length;
    return { done, total, pct: total > 0 ? Math.round((done / total) * 100) : 0 };
  }, [evidence]);

  const flagsActive = Object.entries(ecFlags).filter(([, v]) => v && v !== false).length;

  if (!caseId) return null;

  // Don't render if there's truly nothing to show
  const hasData = intakeStats.filled > 0 || flagsActive > 0 || evidence.length > 0 || vurderinger.length > 0;
  if (!hasData) return null;

  // Overall sag-completion percentage
  const overallPct = Math.round(
    ((intakeStats.requiredFilled / Math.max(1, intakeStats.requiredTotal)) * 50)
    + ((evidenceStats.done / Math.max(1, evidenceStats.total)) * 50)
  );

  return (
    <Wrap>
      <TopBar onClick={() => setOpen((v) => !v)}>
        <div className="left">
          {open ? <FaChevronDown /> : <FaChevronRight />}
          Sag-komplet-overblik · {caseId}
        </div>
        <div className="meta">
          <span><FaCheckCircle style={{ color: '#2d6a31', verticalAlign: 'middle', marginRight: 3 }} />
            {intakeStats.requiredFilled}/{intakeStats.requiredTotal} indkøbs-felter
          </span>
          {flagsActive > 0 && (
            <span><FaCircle style={{ color: '#0d2e54', fontSize: '0.5rem', verticalAlign: 'middle', marginRight: 3 }} />
              {flagsActive} EC-flag
            </span>
          )}
          {evidence.length > 0 && (
            <span>{evidenceStats.done}/{evidenceStats.total} evidens</span>
          )}
          {vurderinger.length > 0 && (
            <span>{vurderinger.length} vurdering{vurderinger.length === 1 ? '' : 'er'}</span>
          )}
          <span style={{ fontWeight: 600, color: overallPct === 100 ? '#2d6a31' : overallPct >= 50 ? '#6e5527' : '#a02020' }}>
            {overallPct}% komplet
          </span>
        </div>
      </TopBar>

      {open && (
        <Body>
          {/* ---- Section 1: Indkøbsproces-felter ---- */}
          <Section>
            <SectionHead onClick={() => toggle('intake')} aria-expanded={openSections.intake}>
              <span className="label">
                {openSections.intake ? <FaChevronDown size={11} /> : <FaChevronRight size={11} />}
                1. Indkøbsproces-felter
              </span>
              <span className="stat">
                {intakeStats.requiredFilled}/{intakeStats.requiredTotal} påkrævede udfyldt
              </span>
            </SectionHead>
            {openSections.intake && (
              <SectionContent>
                {Object.entries(INTAKE_FIELD_REQUIREMENTS).map(([key, def]) => {
                  const value = intake[key];
                  const filled = isFilled(value);
                  let status = 'missing';
                  if (filled) status = 'ok';
                  else if (!def.required) status = 'warn';
                  return (
                    <FieldRow key={key} $status={status}>
                      <span className="marker" aria-hidden="true">
                        {filled ? <FaCheckCircle /> : <FaExclamationTriangle />}
                      </span>
                      <div className="body">
                        <div className="field-label">
                          {def.label}
                          {def.required && (
                            <span className={`req-tag ${filled ? '' : 'req-yes'}`}>
                              {filled ? 'opfyldt' : 'påkrævet'}
                            </span>
                          )}
                        </div>
                        <div className={`field-value ${filled ? '' : 'missing'}`}>
                          {filled
                            ? (typeof value === 'boolean'
                                ? (value ? 'Ja' : 'Nej')
                                : String(value).slice(0, 200))
                            : `(mangler — spærrer for ${def.requirements.length} lovkrav)`}
                        </div>
                        <div className="req-list">
                          {def.requirements.map((req, i) => (
                            <div key={i} className="req-item">
                              <span className="lov">{req.lov}</span>{req.desc}
                            </div>
                          ))}
                        </div>
                      </div>
                    </FieldRow>
                  );
                })}
              </SectionContent>
            )}
          </Section>

          {/* ---- Section 2: EU AI Act-flag ---- */}
          {flagsActive > 0 && (
            <Section>
              <SectionHead onClick={() => toggle('ec')} aria-expanded={openSections.ec}>
                <span className="label">
                  {openSections.ec ? <FaChevronDown size={11} /> : <FaChevronRight size={11} />}
                  2. EU AI Act-tjek — {flagsActive} aktive flag
                </span>
                <span className="stat">{intake.ec_flags ? 'persisteret på sag' : 'fra session'}</span>
              </SectionHead>
              {openSections.ec && (
                <SectionContent>
                  {Object.entries(ecFlags)
                    .filter(([, v]) => v && v !== false)
                    .map(([flag]) => {
                      const display = FLAG_DISPLAY[flag] || { label: flag.replace(/^flag_/, '').replace(/_/g, ' '), tone: 'info' };
                      return (
                        <FlagRow key={flag} $tone={display.tone}>
                          <span className="marker" />
                          <span>{display.label}</span>
                          <code>{flag}</code>
                        </FlagRow>
                      );
                    })}
                </SectionContent>
              )}
            </Section>
          )}

          {/* ---- Section 3: Evidens-status ---- */}
          {evidence.length > 0 && (
            <Section>
              <SectionHead onClick={() => toggle('evidens')} aria-expanded={openSections.evidens}>
                <span className="label">
                  {openSections.evidens ? <FaChevronDown size={11} /> : <FaChevronRight size={11} />}
                  3. Evidens-checkliste — {evidenceStats.done}/{evidenceStats.total} færdige ({evidenceStats.pct}%)
                </span>
                <span className="stat">
                  {evidenceStats.pct === 100 ? 'alt udfyldt ✓' : `${evidenceStats.total - evidenceStats.done} mangler`}
                </span>
              </SectionHead>
              {openSections.evidens && (
                <SectionContent>
                  {evidence.map((ev) => {
                    const status = ev.status || 'mangler';
                    return (
                      <FieldRow
                        key={ev.artifact_id}
                        $status={status === 'faerdig' || status === 'godkendt' ? 'ok' : status === 'i_gang' ? 'warn' : 'missing'}
                      >
                        <span className="marker" aria-hidden="true">
                          {status === 'faerdig' || status === 'godkendt' ? <FaCheckCircle /> : <FaExclamationTriangle />}
                        </span>
                        <div className="body">
                          <div className="field-label">
                            {ev.artifact_id.replace(/_/g, ' ')}
                            <Pill tone={status === 'faerdig' || status === 'godkendt' ? 'success' : status === 'i_gang' ? 'warn' : 'neutral'}>
                              {status === 'faerdig' ? 'Færdig' : status === 'i_gang' ? 'I gang' : status === 'godkendt' ? 'Godkendt' : 'Mangler'}
                            </Pill>
                          </div>
                          {ev.completed_at && (
                            <div className="field-value">
                              Færdig {formatRelative(ev.completed_at)}
                              {ev.completed_by && ` · ${ev.completed_by}`}
                            </div>
                          )}
                        </div>
                      </FieldRow>
                    );
                  })}
                </SectionContent>
              )}
            </Section>
          )}

          {/* ---- Section 4: Vurderings-historik ---- */}
          {vurderinger.length > 0 && (
            <Section>
              <SectionHead onClick={() => toggle('historik')} aria-expanded={openSections.historik}>
                <span className="label">
                  {openSections.historik ? <FaChevronDown size={11} /> : <FaChevronRight size={11} />}
                  4. Vurderings-historik — {vurderinger.length} {vurderinger.length === 1 ? 'kørsel' : 'kørsler'}
                </span>
                <span className="stat">nyeste først</span>
              </SectionHead>
              {openSections.historik && (
                <SectionContent>
                  {vurderinger.map((v, i) => (
                    <VurderingItem
                      key={i}
                      type="button"
                      onClick={() => v.link && navigate(v.link)}
                    >
                      <div>
                        <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{v.label}</div>
                        {v.detail && <div style={{ fontSize: '0.78rem', color: '#666', marginTop: 2 }}>{v.detail}</div>}
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span className="meta">{formatRelative(v.timestamp)}</span>
                        <FaArrowRight size={11} />
                      </div>
                    </VurderingItem>
                  ))}
                </SectionContent>
              )}
            </Section>
          )}
        </Body>
      )}
    </Wrap>
  );
};

export default IndkoebsOverviewPanel;
