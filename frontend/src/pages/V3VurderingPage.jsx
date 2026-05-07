import React, { useMemo, useState } from 'react';
import styled from 'styled-components';
import { useMutation } from 'react-query';
import axios from 'axios';
import {
  ComplianceVerdict,
  EvidenceChecklist,
  RuleDecisionPanel,
} from '../components/rules';

/**
 * V3VurderingPage — wires the new rule_engine output into the UI.
 *
 * Workflow:
 *   1. User describes the AI system in free text (and optionally fills
 *      in sample predicates).
 *   2. We POST to /api/v3/assess.
 *   3. Backend runs the deterministic rule engine and (if configured)
 *      asks the LLM to interpret signals from the description.
 *   4. We render every triggered decision via the v3 design primitives.
 *
 * Layout follows Design A "stille autoritet" — wide whitespace, generous
 * typography, teglrød reserved for status and CTA.
 */

// ---- Sample input (one click to populate) -----------------------------

const SAMPLE_DESCRIPTION =
  'Borgerassistent — pensionsansøgning. Systemet er en AI-drevet tjeneste der ' +
  'hjælper borgere med at udfylde pensionsansøgninger og foretager profilering ' +
  'af ansøgers risikoprofil. Det træffer skriftlige afgørelser om tildeling, og ' +
  'borgere kan bestride dem. Behandler personoplysninger i fuldt automatiseret flow.';

const SAMPLE_SIGNALS = {
  'system.uses_ai': true,
  'system.processes_personal_data': true,
  'system.makes_decisions_about_persons': true,
  'system.is_used_by_public_authority': true,
  'system.makes_administrative_decisions': true,
  'system.generates_decision_text': true,
};

const SAMPLE_PREDICATES = {
  // ai_act.art5
  anvendelse: 'intet_af_ovenstaaende',
  medicinsk_eller_sikkerheds_undtagelse: false,
  // ai_act.art6
  anvendelsesomraade: 'vaesentlige_offentlige_tjenester',
  kun_forberedende: false,
  profilering: true,
  // gdpr.art6
  retsgrundlag: 'samfundets_interesse_eller_offentlig_myndighed_e',
  behandler_saerlige_kategorier: false,
  nationalt_retsgrundlag_dokumenteret: true,
  // gdpr.art22
  er_helautomatiseret: true,
  har_retsvirkning_eller_betydelig_paavirkning: true,
  retsgrundlag_til_undtagelse: 'lov',
  omfatter_saerlige_kategorier: false,
  // gdpr.art35
  art35_stk3_litra: 'litra_a_systematisk_omfattende_evaluering_med_retsvirkning',
  paa_datatilsynets_liste: true,
  art35_stk1_hoj_risiko: true,
  dpia_eksisterer: false,
  // forvaltningsloven.par19
  traeffer_afgoerelse: true,
  bruger_oplysninger_om_part: true,
  parten_kender_oplysningerne: false,
  ufordelagtig_for_parten: true,
  // forvaltningsloven.par22
  meddeles_skriftligt: true,
  fuld_medhold: false,
  kan_systemet_generere_begrundelse: 'ja_delvist',
  // forvaltningsloven.par24
  genererer_begrundelse: true,
  indeholder_lovhenvisning: true,
  angiver_hovedhensyn_ved_skon: 'ja',
  angiver_faktiske_omstaendigheder: true,
  lovhenvisninger_verificerbare: true,
  // offentlighedsloven.par13
  laver_sammenstillinger: false,
  enkle_kommandoer: false,
  indeholder_personoplysninger: false,
  anonymiseringskapacitet: true,
};

// ---- Styled --------------------------------------------------------------

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

const Lede = styled.p`
  margin: 0 0 2.5rem;
  color: ${(p) => p.theme.colors.textMuted};
  font-size: 1rem;
  max-width: 640px;
  line-height: 1.6;
`;

const FormCard = styled.form`
  background: ${(p) => p.theme.colors.surface};
  border: 1px solid ${(p) => p.theme.colors.border};
  border-radius: ${(p) => p.theme.borderRadius};
  padding: 1.75rem;
  margin-bottom: 2.5rem;
`;

const Label = styled.label`
  display: block;
  font-weight: 600;
  font-size: 0.92rem;
  color: ${(p) => p.theme.colors.text};
  margin-bottom: 0.5rem;
`;

const TextArea = styled.textarea`
  width: 100%;
  min-height: 130px;
  padding: 0.85rem 1rem;
  border: 1px solid ${(p) => p.theme.colors.border};
  border-radius: ${(p) => p.theme.borderRadius};
  font-family: ${(p) => p.theme.fonts.main};
  font-size: 0.95rem;
  line-height: 1.55;
  resize: vertical;
  background: ${(p) => p.theme.colors.inputBackground};
  color: ${(p) => p.theme.colors.text};

  &:focus {
    outline: none;
    border-color: ${(p) => p.theme.colors.primary};
    box-shadow: ${(p) => p.theme.shadows.focus};
  }
`;

const Input = styled.input`
  width: 100%;
  padding: 0.7rem 0.9rem;
  border: 1px solid ${(p) => p.theme.colors.border};
  border-radius: ${(p) => p.theme.borderRadius};
  font-family: ${(p) => p.theme.fonts.main};
  font-size: 0.92rem;
  background: ${(p) => p.theme.colors.inputBackground};
  color: ${(p) => p.theme.colors.text};

  &:focus {
    outline: none;
    border-color: ${(p) => p.theme.colors.primary};
    box-shadow: ${(p) => p.theme.shadows.focus};
  }
`;

const MetaRow = styled.div`
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 1rem;
  margin-top: 1.25rem;

  @media (max-width: 640px) {
    grid-template-columns: 1fr;
  }
`;

const MetaField = styled.div`
  display: flex;
  flex-direction: column;
`;

const Controls = styled.div`
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
  flex-wrap: wrap;
  align-items: center;
`;

const PrimaryButton = styled.button`
  background: ${(p) => p.theme.colors.primary};
  color: white;
  border: none;
  padding: 0.7rem 1.4rem;
  border-radius: ${(p) => p.theme.borderRadius};
  font-weight: 600;
  font-size: 0.95rem;
  cursor: pointer;
  transition: background ${(p) => p.theme.animations.transitionFast};

  &:hover {
    background: ${(p) => p.theme.colors.primaryDark};
  }
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const SecondaryButton = styled.button`
  background: transparent;
  color: ${(p) => p.theme.colors.text};
  border: 1px solid ${(p) => p.theme.colors.border};
  padding: 0.7rem 1.2rem;
  border-radius: ${(p) => p.theme.borderRadius};
  font-weight: 500;
  font-size: 0.92rem;
  cursor: pointer;

  &:hover {
    border-color: ${(p) => p.theme.colors.primary};
    color: ${(p) => p.theme.colors.primary};
  }
`;

const ToggleRow = styled.label`
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  font-size: 0.88rem;
  color: ${(p) => p.theme.colors.textMuted};
  cursor: pointer;
  margin-left: auto;
`;

const VerdictBox = styled.div`
  background: ${(p) => p.theme.colors.surface};
  border: 1px solid ${(p) => p.theme.colors.border};
  border-radius: ${(p) => p.theme.borderRadius};
  padding: 1.5rem 1.75rem;
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 1.25rem;
  align-items: center;
  margin-bottom: 2.5rem;
`;

const VerdictTitle = styled.h2`
  margin: 0 0 0.3rem;
  font-size: 1.2rem;
  font-weight: 600;
  color: ${(p) => p.theme.colors.text};
  letter-spacing: -0.01em;
`;

const VerdictSummary = styled.p`
  margin: 0;
  color: ${(p) => p.theme.colors.gray[700]};
  font-size: 0.92rem;
  line-height: 1.5;
`;

const StatNum = styled.div`
  font-size: 1.4rem;
  font-weight: 700;
  text-align: right;
  color: ${(p) => p.theme.colors.text};
`;

const StatLabel = styled.div`
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: ${(p) => p.theme.colors.textMuted};
  text-align: right;
`;

const Section = styled.section`
  margin-bottom: 3rem;
`;

const SectionH = styled.h2`
  font-size: 1.4rem;
  font-weight: 600;
  letter-spacing: -0.01em;
  margin: 0 0 0.4rem;
  color: ${(p) => p.theme.colors.text};
`;

const SectionLede = styled.p`
  margin: 0 0 1.5rem;
  color: ${(p) => p.theme.colors.textMuted};
  font-size: 0.95rem;
`;

const PanelStack = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
`;

const Empty = styled.div`
  background: ${(p) => p.theme.colors.surfaceAlt};
  border: 1px dashed ${(p) => p.theme.colors.border};
  border-radius: ${(p) => p.theme.borderRadius};
  padding: 2.5rem;
  text-align: center;
  color: ${(p) => p.theme.colors.textMuted};
  font-size: 0.95rem;
`;

const ErrorBox = styled.div`
  background: ${(p) => p.theme.colors.danger}1a;
  border: 1px solid ${(p) => p.theme.colors.danger};
  color: ${(p) => p.theme.colors.danger};
  padding: 1rem 1.25rem;
  border-radius: ${(p) => p.theme.borderRadius};
  margin-bottom: 2rem;
  font-size: 0.92rem;
`;

const Warnings = styled.div`
  background: ${(p) => p.theme.colors.warning}1a;
  border: 1px solid ${(p) => p.theme.colors.warning};
  border-radius: ${(p) => p.theme.borderRadius};
  padding: 0.85rem 1rem;
  margin-bottom: 2rem;
  font-size: 0.85rem;
  color: ${(p) => p.theme.colors.gray[800]};

  ul {
    margin: 0.4rem 0 0;
    padding-left: 1.25rem;
  }
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

// ---- API call ------------------------------------------------------------

async function postAssess(body) {
  const res = await axios.post('/api/v3/assess', body);
  return res.data;
}

// ---- Helpers -------------------------------------------------------------

const buildEvidenceItems = (decisions, statusMap = {}) => {
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

// ---- Page ----------------------------------------------------------------

const V3VurderingPage = () => {
  const [description, setDescription] = useState('');
  const [usePredicates, setUsePredicates] = useState(true);
  const [caseId, setCaseId] = useState('');
  const [note, setNote] = useState('');

  const mutation = useMutation(postAssess);

  const handleSubmit = (e) => {
    e.preventDefault();
    mutation.mutate({
      system_description: description.trim() || undefined,
      signals: {},
      predicates: usePredicates ? SAMPLE_PREDICATES : {},
      use_llm_extraction: true,
      case_id: caseId.trim() || undefined,
      note: note.trim() || undefined,
    });
  };

  const fillSample = () => {
    setDescription(SAMPLE_DESCRIPTION);
    setUsePredicates(true);
    if (!caseId) setCaseId('K-2026-0184');
    if (!note) setNote('Pilot-vurdering af pensionsassistent');
  };

  const result = mutation.data;
  const decisions = useMemo(
    () => (result?.decisions || []).filter((d) => d.triggered),
    [result],
  );
  const evidenceItems = useMemo(() => buildEvidenceItems(decisions), [decisions]);
  const totalKrav = decisions.reduce(
    (sum, d) => sum + (d.outcome?.krav?.length || 0),
    0,
  );

  return (
    <Page>
      <Eyebrow>v3 rule_engine · live API</Eyebrow>
      <Title>V3 Vurdering — Hjemmel</Title>
      <Lede>
        Beskriv AI-systemet i fri tekst. Backend kører den deterministiske
        regelmotor og spørger valgfrit en LLM om at fortolke fritekst til
        signaler. Hver afgørelse spores tilbage til konkret lov-citat med
        URL og verificeringsdato.
      </Lede>

      <FormCard onSubmit={handleSubmit}>
        <Label htmlFor="desc">Beskriv systemet</Label>
        <TextArea
          id="desc"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Fx: chatbot der hjælper borgere med pension, foretager profilering og afgørelser…"
        />

        <MetaRow>
          <MetaField>
            <Label htmlFor="caseId">Sags-ID (valgfrit)</Label>
            <Input
              id="caseId"
              value={caseId}
              onChange={(e) => setCaseId(e.target.value)}
              placeholder="K-2026-…"
            />
          </MetaField>
          <MetaField>
            <Label htmlFor="note">Note (valgfri)</Label>
            <Input
              id="note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Fx: pilot-vurdering, opdatering efter modeludskift…"
            />
          </MetaField>
        </MetaRow>

        <Controls>
          <PrimaryButton type="submit" disabled={mutation.isLoading}>
            {mutation.isLoading ? 'Vurderer…' : 'Vurder'}
          </PrimaryButton>
          <SecondaryButton type="button" onClick={fillSample}>
            Indsæt eksempel
          </SecondaryButton>
          <ToggleRow>
            <input
              type="checkbox"
              checked={usePredicates}
              onChange={(e) => setUsePredicates(e.target.checked)}
            />
            Send demo-predikater (springer needs_input over)
          </ToggleRow>
        </Controls>
      </FormCard>

      {mutation.isError && (
        <ErrorBox>
          Kunne ikke kalde /api/v3/assess: {String(mutation.error?.message || mutation.error)}
          {mutation.error?.response?.data?.detail && (
            <div style={{ marginTop: 6, fontFamily: 'monospace', fontSize: 12 }}>
              {String(mutation.error.response.data.detail)}
            </div>
          )}
        </ErrorBox>
      )}

      {!result && !mutation.isLoading && !mutation.isError && (
        <Empty>
          Ingen vurdering endnu. Klik <strong>"Indsæt eksempel"</strong> ovenfor og derefter <strong>"Vurder"</strong>
          for at se den fulde flow med 10 regler.
        </Empty>
      )}

      {result && (
        <>
          {result.warnings?.length > 0 && (
            <Warnings>
              <strong>Backend-advarsler:</strong>
              <ul>
                {result.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </Warnings>
          )}

          <VerdictBox>
            <ComplianceVerdict status={result.aggregate_status} size="lg" />
            <div>
              <VerdictTitle>
                {decisions.length} af {result.rules_loaded} regler udløser krav
              </VerdictTitle>
              <VerdictSummary>
                Aggregat-status: <strong>{result.aggregate_status}</strong>. Kilde-citation
                vises pr. regel nedenfor.
              </VerdictSummary>
            </div>
            <div>
              <StatNum>{evidenceItems.length}</StatNum>
              <StatLabel>Evidens · {totalKrav} krav</StatLabel>
            </div>
          </VerdictBox>

          {decisions.length > 0 && (
            <Section>
              <SectionH>Lov-grundlag</SectionH>
              <SectionLede>
                Hver afgørelse hjemles direkte i den lovartikel den udspringer af.
              </SectionLede>
              <PanelStack>
                {decisions.map((decision) => (
                  <RuleDecisionPanel key={decision.rule_id} decision={decision} />
                ))}
              </PanelStack>
            </Section>
          )}

          {evidenceItems.length > 0 && (
            <Section>
              <SectionH>Evidens-checkliste</SectionH>
              <SectionLede>
                {evidenceItems.length} artefakter er identificeret på tværs af de ramte regler.
              </SectionLede>
              <EvidenceChecklist items={evidenceItems} />
            </Section>
          )}

          <AuditFootnote>
            rule_engine {result.rule_engine_version} · evalueret {result.evaluated_at}
            <br />
            rules_loaded={result.rules_loaded} · triggered={decisions.length} ·
            aggregate={result.aggregate_status}
            <br />
            signals_extracted_by_llm={JSON.stringify(result.signals_extracted_by_llm)}
            <br />
            deterministisk afgørelse · ingen LLM-input til selve afgørelsen
            {result.audit_log_id && (
              <>
                <br />
                audit_log_id={result.audit_log_id}
              </>
            )}
          </AuditFootnote>
        </>
      )}
    </Page>
  );
};

export default V3VurderingPage;
