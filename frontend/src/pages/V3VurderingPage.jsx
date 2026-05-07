import React, { useMemo } from 'react';
import styled from 'styled-components';
import {
  ComplianceVerdict,
  EvidenceChecklist,
  RuleDecisionPanel,
} from '../components/rules';

/**
 * V3VurderingPage — visualizes the output of the new rule_engine.
 *
 * Currently fed by a hard-coded sample RuleDecision array that mirrors
 * the JSON shape the backend's /api/v3/assess endpoint will return.
 * When the endpoint lands (Fase 1.4), swap `SAMPLE_DECISIONS` for a
 * react-query call.
 *
 * Layout follows Design A "stille autoritet" — wide whitespace, serif
 * heading, centered content, teglrød only on status pills and CTAs.
 */

// ---- Sample data (will be replaced by /api/v3/assess response) ----------

const SAMPLE_CASE = {
  caseId: 'K-2026-0184',
  title: 'Borgerassistent — Pensionsansøgning',
  meta: 'Mette Nielsen · Center for Borgerservice · sidste vurdering 7. maj 2026',
  aggregateStatus: 'BETINGET-GO',
  summary: 'Tre lovartikler udløser krav før idriftsættelse. Otte konkrete artefakter skal etableres; tre er allerede dokumenteret.',
};

const SAMPLE_DECISIONS = [
  {
    rule_id: 'ai_act.art6.hojrisiko_klassifikation',
    triggered: true,
    status: 'BETINGET-GO',
    outcome: {
      status: 'BETINGET-GO',
      begrundelse:
        'Systemet falder ind under Bilag III og opfylder ikke undtagelsen for snæver forberedende opgave, eller foretager profilering. Det klassificeres som højrisiko.',
      krav: [
        'Etabler risikostyringssystem (art. 9)',
        'Sikr datasæt-kvalitet (art. 10)',
        'Lav teknisk dokumentation (art. 11) inden idriftsættelse',
        'Sikr menneskelig overvågning (art. 14)',
        'Registrér i EU-databasen for højrisikosystemer (art. 49)',
      ],
      evidens_påkrævet: [
        'risikostyringsplan',
        'datasaet_dokumentation',
        'teknisk_dokumentation_art11',
        'human_oversight_protokol',
        'eu_database_registrering',
      ],
    },
    kilde: {
      lov: 'EU AI-forordningen (Forordning 2024/1689)',
      artikel: 'Artikel 6, stk. 2 + Bilag III',
      citat:
        'Ud over de højrisiko-AI-systemer, der er omhandlet i stk. 1, anses AI-systemer, der er omhandlet i bilag III, som højrisiko.',
      url: 'https://eur-lex.europa.eu/eli/reg/2024/1689/oj/dan',
      sidst_verificeret: '2026-05-07',
    },
    needs_input: [],
  },
  {
    rule_id: 'gdpr.art22.automatiseret_individuel_afgorelse',
    triggered: true,
    status: 'BETINGET-GO',
    outcome: {
      status: 'BETINGET-GO',
      begrundelse:
        'Afgørelsen er omfattet af GDPR art. 22, stk. 1. Helautomatiserede afgørelser med retsvirkning kræver retsgrundlag og passende sikkerhedsforanstaltninger.',
      krav: [
        'Implementér ret til menneskelig indgriben (art. 22, stk. 3)',
        'Implementér ret til at bestride afgørelsen',
        'Informér registrerede om logikken bag afgørelsen og forventede konsekvenser',
      ],
      evidens_påkrævet: [
        'menneskelig_indgriben_proces',
        'transparenstekst_til_registrerede',
        'dpia_dokument',
      ],
    },
    kilde: {
      lov: 'Databeskyttelsesforordningen (Forordning 2016/679 - GDPR)',
      artikel: 'Artikel 22, stk. 1',
      citat:
        'Den registrerede har ret til ikke at være genstand for en afgørelse, der alene er baseret på automatisk behandling, herunder profilering, som har retsvirkning eller på tilsvarende vis betydeligt påvirker den pågældende.',
      url: 'https://eur-lex.europa.eu/eli/reg/2016/679/oj/dan#art_22',
      sidst_verificeret: '2026-05-07',
    },
    needs_input: [],
  },
  {
    rule_id: 'forvaltningsloven.par22.begrundelsespligt',
    triggered: true,
    status: 'BETINGET-GO',
    outcome: {
      status: 'BETINGET-GO',
      begrundelse:
        'Systemet træffer skriftlige afgørelser uden fuldt medhold. § 22 udløser begrundelseskrav, og § 24 kræver konkret indhold i begrundelsen.',
      krav: [
        'AI-genereret begrundelse skal verificeres af kompetent sagsbehandler INDEN afsendelse',
        'Sikr at AI ikke "opfinder" lovhenvisninger — alle paragraffer skal være verificerbare',
        'Etablér klagevejledning (§ 25) i samme dokument',
      ],
      evidens_påkrævet: [
        'sagsbehandler_review_protokol',
        'klagevejledning_skabelon',
      ],
    },
    kilde: {
      lov: 'Forvaltningsloven (lovbekendtgørelse nr. 433 af 22. april 2014 med senere ændringer)',
      artikel: '§ 22',
      citat:
        'En afgørelse skal, når den meddeles skriftligt, være ledsaget af en begrundelse, medmindre afgørelsen fuldt ud giver den pågældende part medhold.',
      url: 'https://www.retsinformation.dk/eli/lta/2014/433',
      sidst_verificeret: '2026-05-07',
    },
    needs_input: [],
  },
];

// Sample evidence-status (would come from case storage in real backend)
const SAMPLE_EVIDENCE_STATUS = {
  risikostyringsplan: { status: 'done', metadata: 'godkendt 2026-05-02' },
  datasaet_dokumentation: { status: 'done', metadata: 'godkendt 2026-05-04' },
  dpia_dokument: { status: 'done', metadata: 'godkendt 2026-04-30' },
  teknisk_dokumentation_art11: { status: 'pending' },
  human_oversight_protokol: { status: 'in_progress' },
  menneskelig_indgriben_proces: { status: 'pending' },
  eu_database_registrering: { status: 'blocked', metadata: 'afventer art. 49-skema' },
  transparenstekst_til_registrerede: { status: 'pending' },
  sagsbehandler_review_protokol: { status: 'in_progress' },
  klagevejledning_skabelon: { status: 'pending' },
};

// ---- Layout ------------------------------------------------------------

const Page = styled.div`
  max-width: 920px;
  margin: 0 auto;
  padding: 3rem 2rem 5rem;
`;

const Eyebrow = styled.div`
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: ${(p) => p.theme.colors.textMuted};
  margin-bottom: 1rem;
`;

const Title = styled.h1`
  font-family: ${(p) => p.theme.fonts.main};
  font-size: 2.3rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.15;
  margin: 0 0 0.6rem;
  color: ${(p) => p.theme.colors.text};
`;

const Meta = styled.p`
  margin: 0 0 2.5rem;
  color: ${(p) => p.theme.colors.textMuted};
  font-size: 0.95rem;
`;

const VerdictBox = styled.div`
  background: ${(p) => p.theme.colors.surface};
  border: 1px solid ${(p) => p.theme.colors.border};
  border-radius: ${(p) => p.theme.borderRadius};
  padding: 1.75rem 2rem;
  display: flex;
  gap: 1.5rem;
  align-items: center;
  margin-bottom: 3rem;
`;

const VerdictText = styled.div`
  flex: 1;
`;

const VerdictTitle = styled.h2`
  margin: 0 0 0.4rem;
  font-size: 1.3rem;
  font-weight: 600;
  color: ${(p) => p.theme.colors.text};
  letter-spacing: -0.01em;
`;

const VerdictSummary = styled.p`
  margin: 0;
  color: ${(p) => p.theme.colors.gray[700]};
  font-size: 0.95rem;
  line-height: 1.55;
`;

const SectionH = styled.h2`
  font-family: ${(p) => p.theme.fonts.main};
  font-size: 1.5rem;
  font-weight: 600;
  letter-spacing: -0.01em;
  margin: 0 0 0.5rem;
  color: ${(p) => p.theme.colors.text};
`;

const SectionLede = styled.p`
  margin: 0 0 1.5rem;
  color: ${(p) => p.theme.colors.textMuted};
  font-size: 0.95rem;
`;

const Section = styled.section`
  margin-bottom: 3rem;
`;

const PanelStack = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
`;

const AuditFootnote = styled.div`
  margin-top: 3rem;
  padding: 1rem 1.25rem;
  background: ${(p) => p.theme.colors.surfaceAlt};
  border: 1px solid ${(p) => p.theme.colors.border};
  border-radius: ${(p) => p.theme.borderRadius};
  font-family: 'JetBrains Mono', SFMono-Regular, Consolas, monospace;
  font-size: 0.78rem;
  color: ${(p) => p.theme.colors.gray[600]};
  line-height: 1.7;
`;

// ---- Page --------------------------------------------------------------

const buildEvidenceItems = (decisions, statusMap) => {
  // Union of evidens_påkrævet across all triggered decisions
  const all = new Set();
  decisions.forEach((d) => {
    (d.outcome?.evidens_påkrævet || []).forEach((e) => all.add(e));
  });

  return Array.from(all).map((id) => ({
    id,
    label: id.replace(/_/g, ' '),
    status: statusMap[id]?.status || 'pending',
    metadata: statusMap[id]?.metadata,
  }));
};

const V3VurderingPage = () => {
  const triggered = useMemo(
    () => SAMPLE_DECISIONS.filter((d) => d.triggered),
    [],
  );

  const evidenceItems = useMemo(
    () => buildEvidenceItems(triggered, SAMPLE_EVIDENCE_STATUS),
    [triggered],
  );

  const evidenceDone = evidenceItems.filter((i) => i.status === 'done').length;
  const totalKrav = triggered.reduce(
    (sum, d) => sum + (d.outcome?.krav?.length || 0),
    0,
  );

  return (
    <Page>
      <Eyebrow>Sag · {SAMPLE_CASE.caseId} · v3 rule_engine</Eyebrow>
      <Title>{SAMPLE_CASE.title}</Title>
      <Meta>{SAMPLE_CASE.meta}</Meta>

      <VerdictBox>
        <ComplianceVerdict status={SAMPLE_CASE.aggregateStatus} size="lg" />
        <VerdictText>
          <VerdictTitle>{triggered.length} regler udløser krav</VerdictTitle>
          <VerdictSummary>{SAMPLE_CASE.summary}</VerdictSummary>
        </VerdictText>
        <div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, textAlign: 'right' }}>
            {evidenceDone}/{evidenceItems.length}
          </div>
          <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#94a3b8' }}>
            Evidens · {totalKrav} krav
          </div>
        </div>
      </VerdictBox>

      <Section>
        <SectionH>Lov-grundlag</SectionH>
        <SectionLede>
          Hver afgørelse hjemles direkte i den lovartikel den udspringer af. Klik på artiklen for at læse den i sin helhed.
        </SectionLede>
        <PanelStack>
          {triggered.map((decision) => (
            <RuleDecisionPanel key={decision.rule_id} decision={decision} />
          ))}
        </PanelStack>
      </Section>

      <Section>
        <SectionH>Evidens-checkliste</SectionH>
        <SectionLede>
          {evidenceItems.length} artefakter er identificeret på tværs af de ramte regler. {evidenceDone} er allerede dokumenteret.
        </SectionLede>
        <EvidenceChecklist items={evidenceItems} />
      </Section>

      <AuditFootnote>
        rule_engine v3.0.0-alpha.2 · 3 regler triggered · status:{' '}
        {SAMPLE_CASE.aggregateStatus} · aggregat-precedens: NO-GO &gt;
        BETINGET-GO &gt; GO · deterministisk afgørelse · ingen LLM-input til
        selve afgørelsen · demo-data (vil blive erstattet af /api/v3/assess i
        Fase 1.4)
      </AuditFootnote>
    </Page>
  );
};

export default V3VurderingPage;
