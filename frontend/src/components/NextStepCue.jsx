import React from 'react';
import { useNavigate } from 'react-router-dom';
import styled from 'styled-components';
import {
  FaArrowRight,
  FaShoppingCart,
  FaClipboardCheck,
  FaSearch,
  FaCheckCircle,
  FaExclamationTriangle,
  FaPlay,
  FaCheck,
} from 'react-icons/fa';

/**
 * Bifrost — NextStepCue: en enkelt prominent CTA der peger på den mest
 * oplagte næste handling for sagen, baseret på dens nuværende tilstand.
 *
 * Med 28+ mulige evidens-skabeloner og 3 workflow-trin er det nemt at
 * miste overblikket. Denne komponent kondenserer "hvor er jeg nu og hvad
 * gør jeg næste" til ét synligt forslag.
 *
 * Props:
 *   intake: object — case.intake_state (behov, system_description, ec_flags, etc.)
 *   verdict: string | null — sidste vurdering (GO / BETINGET-GO / NO-GO)
 *   vurderingerCount: number
 *   evidenceProgress: { done, total, pct }
 *   evidenceItems: list — for at finde første mangler
 *   caseId: string
 *   onOpenTab: (tabId) => void — for at skifte fane på sag-detalje-siden
 *   onOpenEvidens: (artifactId) => void — åbner evidens-editor
 */

const Wrap = styled.div`
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.9rem 1.1rem;
  margin: 0 0 1.25rem;
  background: ${(p) =>
    p.$tone === 'success'
      ? 'rgba(45, 106, 49, 0.08)'
      : p.$tone === 'danger'
      ? 'rgba(160, 32, 32, 0.08)'
      : p.$tone === 'warn'
      ? 'rgba(176, 138, 74, 0.10)'
      : p.theme.colors.primarySoft || 'rgba(13, 46, 84, 0.06)'};
  border-left: 3px solid
    ${(p) =>
      p.$tone === 'success'
        ? '#2d6a31'
        : p.$tone === 'danger'
        ? '#a02020'
        : p.$tone === 'warn'
        ? '#b08a4a'
        : p.theme.colors.primary || '#0d2e54'};
  border-radius: 6px;

  .icon {
    font-size: 1.1rem;
    color: ${(p) =>
      p.$tone === 'success'
        ? '#2d6a31'
        : p.$tone === 'danger'
        ? '#a02020'
        : p.$tone === 'warn'
        ? '#b08a4a'
        : p.theme.colors.primary || '#0d2e54'};
    flex-shrink: 0;
  }

  .body {
    flex: 1;
    min-width: 0;

    .eyebrow {
      font-family: ${(p) => p.theme.fonts.mono};
      font-size: 0.65rem;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: ${(p) => p.theme.colors.textMuted};
      margin: 0 0 0.15rem;
    }
    .title {
      font-family: ${(p) => p.theme.fonts.display};
      font-size: 0.95rem;
      font-weight: 600;
      color: ${(p) => p.theme.colors.text};
      margin: 0 0 0.2rem;
    }
    .desc {
      font-size: 0.82rem;
      line-height: 1.4;
      color: ${(p) => p.theme.colors.textMuted};
      margin: 0;
    }
  }

  .cta {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: white;
    background: ${(p) =>
      p.$tone === 'success'
        ? '#2d6a31'
        : p.$tone === 'danger'
        ? '#a02020'
        : p.$tone === 'warn'
        ? '#b08a4a'
        : p.theme.colors.primary || '#0d2e54'};
    border: none;
    border-radius: 4px;
    padding: 0.55rem 0.95rem;
    cursor: pointer;
    white-space: nowrap;
    flex-shrink: 0;

    &:hover { filter: brightness(1.08); }
    &:focus-visible {
      outline: 2px solid currentColor;
      outline-offset: 2px;
    }
  }

  @media (max-width: 720px) {
    flex-direction: column;
    align-items: flex-start;
    .cta { width: 100%; justify-content: center; }
  }
`;

/**
 * Returnér det første mangler-evidens-id (eller null hvis alt er done).
 * Foretrækker required-felter via heuristik på ID-mønstre.
 */
function pickNextEvidence(items) {
  if (!items || items.length === 0) return null;
  // Status normalisering: vi får 'pending' fra SagDetalje's mapping
  const pending = items.filter((it) => it.status === 'pending');
  if (pending.length > 0) return pending[0];
  const inProgress = items.filter((it) => it.status === 'in_progress');
  if (inProgress.length > 0) return inProgress[0];
  return null;
}

const HUMAN_LABEL = {
  risikostyringsplan: 'Risikostyringsplan',
  dpia_dokument: 'DPIA-dokument',
  dpia_taerskelsvurdering: 'DPIA-tærskelsvurdering',
  databehandleraftale_dbs: 'Databehandleraftale (DBS)',
  ai_indkoeb_tjekliste: 'AI-indkøbs-tjekliste',
  eu_mcc_klausuler: 'EU MCC-klausuler-checklist',
  ai_faerdigheder_program: 'AI-færdighedsprogram (Art. 4)',
  leverandoer_due_diligence: 'Leverandør due-diligence',
  trustworthy_ai_rating: 'Trustworthy AI-vurdering',
  ce_maerkning_guide: 'CE-mærkning-guide',
  incident_reporting_art73: 'Incident reporting (Art. 73)',
  human_oversight_protokol: 'Menneskeligt tilsyn-protokol',
  teknisk_dokumentation_art11: 'Teknisk dokumentation (Art. 11)',
  logningsspecifikation: 'Logningsspecifikation',
  eu_database_registrering: 'EU-database-registrering',
  datasaet_dokumentation: 'Datasæt-dokumentation',
  partshoringsbrev: 'Partshøringsbrev',
  begrundelsesskabelon_godkendt_af_jurist: 'Begrundelsesskabelon',
  klagevejledning_skabelon: 'Klagevejledning',
  transparenstekst_til_registrerede: 'Transparenstekst (GDPR Art. 13/14)',
};

const NextStepCue = ({
  intake = {},
  verdict = null,
  vurderingerCount = 0,
  evidenceProgress = { done: 0, total: 0, pct: 0 },
  evidenceItems = [],
  caseId,
  onOpenTab,
  onOpenEvidens,
}) => {
  const navigate = useNavigate();

  // Beregn det mest oplagte næste skridt
  const step = (() => {
    // 1. Behov ikke beskrevet
    if (!intake?.behov || intake.behov.trim().length < 10) {
      return {
        tone: 'info',
        eyebrow: 'Trin 1 — Indkøb',
        icon: <FaShoppingCart className="icon" aria-hidden="true" />,
        title: 'Beskriv behovet',
        desc: 'Start med at beskrive hvad AI-systemet skal løse — det er fundamentet for hele vurderingen.',
        ctaLabel: 'Åbn indkøb',
        action: () =>
          navigate(`/indkoebsproces?case_id=${encodeURIComponent(caseId)}`),
      };
    }

    // 2. Indkøb-vs-udvikling ikke valgt
    if (!intake?.indkoeb_eller_udvikling) {
      return {
        tone: 'info',
        eyebrow: 'Trin 1 — Indkøb',
        icon: <FaShoppingCart className="icon" aria-hidden="true" />,
        title: 'Vælg indkøb eller udvikling',
        desc: 'Påvirker hvilke krav der gælder — fx leverandørkontrol vs. interne udviklerkrav.',
        ctaLabel: 'Færdiggør indkøb',
        action: () =>
          navigate(`/indkoebsproces?case_id=${encodeURIComponent(caseId)}`),
      };
    }

    // 3. EU AI Act-tjek mangler (ec_flags er typisk udfyldt af checker)
    const ecFlagCount = Object.keys(intake?.ec_flags || {}).length;
    if (ecFlagCount === 0) {
      return {
        tone: 'info',
        eyebrow: 'Trin 2 — EU AI Act-tjek',
        icon: <FaSearch className="icon" aria-hidden="true" />,
        title: 'Klassificér systemet i EU AI Act-checker',
        desc: '33 standardspørgsmål bestemmer om systemet er forbudt, højrisiko, begrænset eller minimalt.',
        ctaLabel: 'Åbn EU-checker',
        action: () =>
          navigate(`/eu-checker?fromIndkoeb=${encodeURIComponent(caseId)}`),
      };
    }

    // 4. Ingen vurdering kørt endnu
    if (vurderingerCount === 0) {
      return {
        tone: 'info',
        eyebrow: 'Trin 3 — Vurdering',
        icon: <FaPlay className="icon" aria-hidden="true" />,
        title: 'Kør første Bifrost-vurdering',
        desc: 'Bifrost samler dine indtastninger og kører dem mod 21 lov-regler. Resultat: GO / BETINGET-GO / NO-GO med citater.',
        ctaLabel: 'Kør vurdering',
        action: () =>
          navigate(
            `/vurdering?case_id=${encodeURIComponent(caseId)}&from=indkoeb`,
          ),
      };
    }

    // 5. NO-GO — adresser blokere
    if (verdict === 'NO-GO') {
      return {
        tone: 'danger',
        eyebrow: 'Blokere fundet',
        icon: (
          <FaExclamationTriangle className="icon" aria-hidden="true" />
        ),
        title: 'Sagen er klassificeret NO-GO',
        desc: 'En eller flere regler blokerer ibrugtagning. Gennemgå krav, juster systemet eller dokumentation, og kør vurdering igen.',
        ctaLabel: 'Se sidste vurdering',
        action: () => onOpenTab && onOpenTab('vurderinger'),
      };
    }

    // 6. BETINGET-GO + evidens mangler
    if (
      (verdict === 'BETINGET-GO' || verdict === 'GO') &&
      evidenceProgress.total > 0 &&
      evidenceProgress.done < evidenceProgress.total
    ) {
      const next = pickNextEvidence(evidenceItems);
      const nextLabel = next
        ? HUMAN_LABEL[next.id] || next.label || next.id
        : 'næste evidens';
      return {
        tone: 'warn',
        eyebrow: `Evidens — ${evidenceProgress.done}/${evidenceProgress.total} udfyldt`,
        icon: <FaClipboardCheck className="icon" aria-hidden="true" />,
        title: `Udfyld næste: ${nextLabel}`,
        desc: `${evidenceProgress.total - evidenceProgress.done} evidens-skabeloner mangler stadig. Vi anbefaler at starte med "${nextLabel}".`,
        ctaLabel: 'Åbn skabelon',
        action: () => {
          if (next && onOpenEvidens) {
            onOpenEvidens(next.id);
          } else if (onOpenTab) {
            onOpenTab('evidens');
          }
        },
      };
    }

    // 7. Alt færdigt
    if (
      (verdict === 'GO' || verdict === 'BETINGET-GO') &&
      evidenceProgress.total > 0 &&
      evidenceProgress.done >= evidenceProgress.total
    ) {
      return {
        tone: 'success',
        eyebrow: 'Klar til godkendelse',
        icon: <FaCheck className="icon" aria-hidden="true" />,
        title: 'Sagen er fuldført',
        desc: 'Alle evidens udfyldt og vurderingen er positiv. Eksportér rapport og flyt sagen til godkendt.',
        ctaLabel: 'Eksportér rapport',
        action: () => {
          // Trigger DOCX download via samme mønster som hero
          const url = `/api/v3/cases/by-case-id/${encodeURIComponent(caseId)}/report?format=docx`;
          const a = document.createElement('a');
          a.href = url;
          a.rel = 'noopener';
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
        },
      };
    }

    // Fallback
    return {
      tone: 'info',
      eyebrow: 'Næste skridt',
      icon: <FaCheckCircle className="icon" aria-hidden="true" />,
      title: 'Fortsæt arbejdet',
      desc: 'Brug fanerne nedenfor for at se vurderinger, evidens og audit-trail.',
      ctaLabel: 'Se evidens',
      action: () => onOpenTab && onOpenTab('evidens'),
    };
  })();

  return (
    <Wrap $tone={step.tone} role="status" aria-live="polite">
      {step.icon}
      <div className="body">
        <p className="eyebrow">{step.eyebrow}</p>
        <p className="title">{step.title}</p>
        <p className="desc">{step.desc}</p>
      </div>
      <button type="button" className="cta" onClick={step.action}>
        {step.ctaLabel} <FaArrowRight aria-hidden="true" />
      </button>
    </Wrap>
  );
};

export default NextStepCue;
