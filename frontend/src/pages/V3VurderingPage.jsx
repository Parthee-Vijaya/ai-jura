import React, { useMemo, useState } from 'react';
import styled from 'styled-components';
import { useMutation } from 'react-query';
import axios from 'axios';
import {
  ComplianceVerdict,
  EvidenceChecklist,
  SidenotesColumn,
  toSuperscript,
} from '../components/rules';

/**
 * V3VurderingPage — Design C "Editorial workspace" rendering of the v3
 * rule_engine output.
 *
 * Layout:
 *   - Form-card (single column) for input.
 *   - On result: 2-column shell (doc | sidenotes). The doc column renders
 *     each triggered rule as a document paragraph with inline ¹²³ footnote
 *     refs that anchor to the SidenotesColumn on the right.
 *   - Verdict is a cream banner with a teglrod left-border (no horizontal
 *     hero card) and a counter row: lov-kilder · artefakter · krav.
 *   - Krav-list uses § bullets in cream-paper-soft surface.
 *
 * The kilde citations live ONLY in the sidenotes — body text reads
 * uninterrupted.
 */

// ---- Sample input --------------------------------------------------------

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
  'system.classifies_individuals': true,
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

// ---- Layout shell --------------------------------------------------------

const Page = styled.div`
  max-width: 1180px;
  margin: 0 auto;
  padding: 3rem 2.5rem 5rem;
`;

const Eyebrow = styled.div`
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: ${(p) => p.theme.colors.inkFaded};
  margin-bottom: 0.6rem;
  font-weight: 600;
`;

const Title = styled.h1`
  font-family: ${(p) => p.theme.fonts.display};
  font-size: 2.4rem;
  font-weight: 700;
  letter-spacing: -0.022em;
  line-height: 1.12;
  margin: 0 0 0.6rem;
  color: ${(p) => p.theme.colors.ink};
`;

const Lede = styled.p`
  font-family: ${(p) => p.theme.fonts.body};
  margin: 0 0 2.5rem;
  color: ${(p) => p.theme.colors.inkSoft};
  font-size: 1.05rem;
  line-height: 1.65;
  max-width: 720px;
`;

// ---- Result-mode header (case-focused, mirroring Design C mockup) -------

const BackLink = styled.button`
  display: inline-block;
  font-family: ${(p) => p.theme.fonts.sans};
  margin-bottom: 1.5rem;
  font-size: 0.82rem;
  color: ${(p) => p.theme.colors.inkSoft};
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;

  &:hover { color: ${(p) => p.theme.colors.ink}; }
`;

const Breadcrumb = styled.div`
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.82rem;
  color: ${(p) => p.theme.colors.inkFaded};
  margin-bottom: 1.5rem;
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;

  span.crumb-sep { color: ${(p) => p.theme.colors.borderSoft}; }
  span.crumb-current { color: ${(p) => p.theme.colors.inkSoft}; }
`;

const CaseId = styled.div`
  font-family: ${(p) => p.theme.fonts.mono};
  font-size: 0.7rem;
  color: ${(p) => p.theme.colors.inkFaded};
  letter-spacing: 0.16em;
  text-transform: uppercase;
  margin-bottom: 0.6rem;
`;

const CaseTitle = styled.h1`
  font-family: ${(p) => p.theme.fonts.display};
  font-size: 2.2rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.15;
  margin: 0 0 0.65rem;
  color: ${(p) => p.theme.colors.ink};
`;

const CaseMeta = styled.p`
  font-family: ${(p) => p.theme.fonts.sans};
  color: ${(p) => p.theme.colors.inkSoft};
  font-size: 0.92rem;
  margin: 0 0 1.75rem;
  line-height: 1.55;
`;

const Shell = styled.div`
  display: grid;
  grid-template-columns: 1fr minmax(280px, 320px);
  column-gap: 3rem;

  @media (max-width: 980px) {
    grid-template-columns: 1fr;
    column-gap: 0;
  }
`;

const Doc = styled.article`
  max-width: 720px;
  min-width: 0;
`;

// ---- Form card -----------------------------------------------------------

const FormCard = styled.form`
  background: ${(p) => p.theme.colors.card};
  border: 1px solid ${(p) => p.theme.colors.line};
  border-radius: 10px;
  padding: 1.75rem;
  margin-bottom: 2.5rem;
`;

const Label = styled.label`
  display: block;
  font-family: ${(p) => p.theme.fonts.sans};
  font-weight: 500;
  font-size: 0.82rem;
  letter-spacing: 0.02em;
  color: ${(p) => p.theme.colors.inkSoft};
  margin-bottom: 0.5rem;
  text-transform: uppercase;
`;

const TextArea = styled.textarea`
  width: 100%;
  min-height: 130px;
  padding: 0.85rem 1rem;
  border: 1px solid ${(p) => p.theme.colors.line};
  border-radius: 6px;
  font-family: ${(p) => p.theme.fonts.body};
  font-size: 1rem;
  line-height: 1.6;
  resize: vertical;
  background: ${(p) => p.theme.colors.paper};
  color: ${(p) => p.theme.colors.ink};

  &:focus {
    outline: none;
    border-color: ${(p) => p.theme.colors.primary};
    box-shadow: 0 0 0 3px rgba(201, 68, 22, 0.12);
  }
`;

const Input = styled.input`
  width: 100%;
  padding: 0.65rem 0.85rem;
  border: 1px solid ${(p) => p.theme.colors.line};
  border-radius: 6px;
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.92rem;
  background: ${(p) => p.theme.colors.paper};
  color: ${(p) => p.theme.colors.ink};

  &:focus {
    outline: none;
    border-color: ${(p) => p.theme.colors.primary};
    box-shadow: 0 0 0 3px rgba(201, 68, 22, 0.12);
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
  gap: 0.85rem;
  margin-top: 1.25rem;
  flex-wrap: wrap;
  align-items: center;
`;

const PrimaryButton = styled.button`
  background: ${(p) => p.theme.colors.primary};
  color: white;
  border: none;
  padding: 0.7rem 1.4rem;
  border-radius: 6px;
  font-family: ${(p) => p.theme.fonts.sans};
  font-weight: 600;
  font-size: 0.92rem;
  cursor: pointer;
  transition: background ${(p) => p.theme.animations.transitionFast};

  &:hover { background: ${(p) => p.theme.colors.primaryDark}; }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
`;

const SecondaryButton = styled.button`
  background: transparent;
  color: ${(p) => p.theme.colors.ink};
  border: 1px solid ${(p) => p.theme.colors.line};
  padding: 0.65rem 1.1rem;
  border-radius: 6px;
  font-family: ${(p) => p.theme.fonts.sans};
  font-weight: 500;
  font-size: 0.9rem;
  cursor: pointer;
  transition: border-color ${(p) => p.theme.animations.transitionFast},
              color ${(p) => p.theme.animations.transitionFast};

  &:hover {
    border-color: ${(p) => p.theme.colors.primary};
    color: ${(p) => p.theme.colors.primary};
  }
`;

const ToggleRow = styled.label`
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.85rem;
  color: ${(p) => p.theme.colors.inkSoft};
  cursor: pointer;
  margin-left: auto;
`;

// ---- Verdict banner (Design C: cream + red left-border, simple stack) ---

const VerdictBanner = styled.div`
  background: ${(p) => p.theme.colors.primaryBg};
  border-left: 4px solid ${(p) => p.theme.colors.primary};
  border-radius: 0 6px 6px 0;
  padding: 1.1rem 1.4rem;
  margin: 1.75rem 0 2.5rem;
`;

const VerdictStatus = styled.div`
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: ${(p) => p.theme.colors.primary};
  font-weight: 700;
  margin-bottom: 0.35rem;
`;

const VerdictText = styled.div`
  font-family: ${(p) => p.theme.fonts.body};
  font-size: 1.05rem;
  color: ${(p) => p.theme.colors.ink};
  line-height: 1.5;
`;

// ---- Section ------------------------------------------------------------

const SectionH = styled.h2`
  font-family: ${(p) => p.theme.fonts.display};
  font-size: 1.7rem;
  font-weight: 600;
  letter-spacing: -0.012em;
  margin: 3.5rem 0 0.4rem;
  color: ${(p) => p.theme.colors.ink};
`;

const SectionLede = styled.p`
  font-family: ${(p) => p.theme.fonts.body};
  font-size: 1rem;
  font-style: italic;
  color: ${(p) => p.theme.colors.inkSoft};
  margin: 0 0 1.5rem;
  line-height: 1.55;
`;

// ---- Rule paragraph (document-style) ------------------------------------

const Rule = styled.div`
  padding: 2rem 0;
  border-top: 1px solid ${(p) => p.theme.colors.line};

  &:last-child { border-bottom: 1px solid ${(p) => p.theme.colors.line}; }
`;

const RuleHead = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 1rem;
  margin-bottom: 0.85rem;
`;

const RuleMarker = styled.span`
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: ${(p) => p.theme.colors.primary};
  font-weight: 700;
`;

const RuleTitle = styled.h3`
  font-family: ${(p) => p.theme.fonts.display};
  font-size: 1.35rem;
  font-weight: 600;
  letter-spacing: -0.012em;
  line-height: 1.3;
  margin: 0 0 1rem;
  color: ${(p) => p.theme.colors.ink};
`;

const FootnoteRef = styled.a`
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.7rem;
  font-weight: 700;
  color: ${(p) => p.theme.colors.primary};
  text-decoration: none;
  margin-left: 2px;
  vertical-align: super;
  line-height: 1;

  &:hover { text-decoration: underline; }
`;

const RuleBody = styled.p`
  font-family: ${(p) => p.theme.fonts.body};
  font-size: 1.06rem;
  line-height: 1.7;
  color: ${(p) => p.theme.colors.ink};
  margin: 0 0 1rem;
`;

const KravBlock = styled.div`
  background: ${(p) => p.theme.colors.paperSoft};
  border: 1px solid ${(p) => p.theme.colors.line};
  border-radius: 6px;
  padding: 1.1rem 1.4rem;
  margin-top: 1rem;
`;

const KravHeader = styled.div`
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: ${(p) => p.theme.colors.inkFaded};
  font-weight: 600;
  margin-bottom: 0.7rem;
`;

const KravList = styled.ul`
  list-style: none;
  margin: 0;
  padding: 0;
`;

const KravItem = styled.li`
  display: grid;
  grid-template-columns: 1.1rem 1fr;
  gap: 0.55rem;
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.92rem;
  line-height: 1.55;
  color: ${(p) => p.theme.colors.ink};
  padding: 0.3rem 0;

  &::before {
    content: '§';
    font-family: ${(p) => p.theme.fonts.display};
    color: ${(p) => p.theme.colors.primary};
    font-weight: 700;
    font-size: 1rem;
  }
`;

const NeedsInputBox = styled.div`
  background: rgba(184, 134, 11, 0.08);
  border: 1px solid rgba(184, 134, 11, 0.3);
  border-radius: 6px;
  padding: 0.85rem 1rem;
  margin-top: 1rem;
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.85rem;
  color: ${(p) => p.theme.colors.inkSoft};

  ul {
    margin: 0.5rem 0 0;
    padding-left: 1.25rem;
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.78rem;
  }
`;

// ---- Audit footer -------------------------------------------------------

const AuditFootnote = styled.div`
  margin-top: 4rem;
  padding: 1.1rem 1.3rem;
  background: ${(p) => p.theme.colors.paperSoft};
  border: 1px solid ${(p) => p.theme.colors.line};
  border-radius: 8px;
  font-family: ${(p) => p.theme.fonts.mono};
  font-size: 0.72rem;
  color: ${(p) => p.theme.colors.inkSoft};
  line-height: 1.85;

  b {
    color: ${(p) => p.theme.colors.ink};
    font-weight: 600;
  }
`;

// ---- Status messages ----------------------------------------------------

const Empty = styled.div`
  background: ${(p) => p.theme.colors.paperSoft};
  border: 1px dashed ${(p) => p.theme.colors.line};
  border-radius: 8px;
  padding: 2.5rem;
  text-align: center;
  color: ${(p) => p.theme.colors.inkSoft};
  font-family: ${(p) => p.theme.fonts.body};
  font-size: 1rem;
  font-style: italic;
`;

const ErrorBox = styled.div`
  background: ${(p) => p.theme.colors.dangerSoft};
  border: 1px solid ${(p) => p.theme.colors.danger};
  color: ${(p) => p.theme.colors.danger};
  padding: 1rem 1.25rem;
  border-radius: 8px;
  margin-bottom: 2rem;
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.9rem;
`;

const Warnings = styled.div`
  background: rgba(184, 134, 11, 0.08);
  border-left: 3px solid ${(p) => p.theme.colors.warning};
  border-radius: 0 6px 6px 0;
  padding: 0.85rem 1.1rem;
  margin-bottom: 2rem;
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.82rem;
  color: ${(p) => p.theme.colors.inkSoft};
  word-break: break-word;

  strong { color: ${(p) => p.theme.colors.ink}; }
  ul { margin: 0.4rem 0 0; padding-left: 1.25rem; }
`;

// ---- API + helpers ------------------------------------------------------

async function postAssess(body) {
  const res = await axios.post('/api/v3/assess', body);
  return res.data;
}

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

const ruleHumanTitle = (decision) => {
  // Fall back to artikel + lov when no nicer title is available.
  if (decision?.kilde?.artikel) {
    return `${decision.kilde.lov ? decision.kilde.lov + ' — ' : ''}${decision.kilde.artikel}`;
  }
  return decision?.rule_id || 'Ukendt regel';
};

// Drop infrastructure/config warnings — they're not relevant to the legal
// output and add visual noise. Keep anything else.
const NOISE_PATTERNS = [
  /signal extraction failed.*LLM invocation failed/i,
  /Incorrect API key|Invalid API key|api_key|api[- ]key/i,
  /Operation canceled|Model unloaded/i,
  /401|invalid_request_error|invalid_api_key/i,
];
const filterNoiseWarnings = (warnings = []) =>
  warnings.filter((w) => !NOISE_PATTERNS.some((re) => re.test(String(w))));

// Derive a human-readable case title from the description's first sentence.
const deriveTitle = (description, caseId) => {
  if (description) {
    const first = description.split(/\.|\n/)[0].trim();
    if (first.length > 0 && first.length < 120) {
      return first.charAt(0).toUpperCase() + first.slice(1);
    }
  }
  return caseId ? `Vurdering ${caseId}` : 'Vurdering';
};

const STATUS_LABELS = {
  GO: 'GO',
  'BETINGET-GO': 'Betinget GO',
  'NO-GO': 'NO-GO',
  NEEDS_INPUT: 'Mangler input',
};
const statusLabel = (s) => STATUS_LABELS[s] || s || 'Mangler input';

const formatDanishDate = (iso) => {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    return d.toLocaleDateString('da-DK', { day: 'numeric', month: 'long', year: 'numeric' });
  } catch {
    return '';
  }
};

// ---- Page ---------------------------------------------------------------

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
      // When demo predicates are used, also pre-fill the signals that the
      // rule triggers depend on — without an LLM we'd otherwise see 0/15.
      signals: usePredicates ? SAMPLE_SIGNALS : {},
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

  // Build sidenotes from triggered decisions' kilde
  const sidenotes = useMemo(
    () =>
      decisions
        .filter((d) => d.kilde)
        .map((d) => ({
          id: d.rule_id,
          citat: d.kilde.citat,
          lov: d.kilde.lov,
          artikel: d.kilde.artikel,
          url: d.kilde.url,
          sidst_verificeret: d.kilde.sidst_verificeret,
        })),
    [decisions],
  );

  // Result mode: the form is hidden entirely, replaced by a case-focused
  // document layout. The user can still trigger a new assessment via the
  // "Ny vurdering" back-link.
  const hasResult = !!result && decisions.length > 0;

  // Filter out infrastructure/config noise warnings — only show warnings
  // that are relevant to the legal output.
  const relevantWarnings = filterNoiseWarnings(result?.warnings || []);

  // Derive case display fields
  const displayTitle = deriveTitle(description, caseId);
  const displayCaseId = caseId || (result?.audit_log_id ? result.audit_log_id.slice(0, 8) : '');
  const evaluatedDate = formatDanishDate(result?.evaluated_at);

  // ----- FORM MODE -----
  if (!hasResult) {
    return (
      <Page>
        <Eyebrow>Hjemmel · v3 rule_engine</Eyebrow>
        <Title>Vurdering</Title>
        <Lede>
          Beskriv AI-systemet i fri tekst. Backend kører den deterministiske
          regelmotor og spørger valgfrit en LLM om at fortolke fritekst til
          signaler. Hver afgørelse hjemles i en konkret lovartikel — citater
          står i marginen til højre.
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
          </ErrorBox>
        )}

        {!result && !mutation.isLoading && !mutation.isError && (
          <Empty>
            Ingen vurdering endnu. Klik <strong>"Indsæt eksempel"</strong> ovenfor og derefter <strong>"Vurder"</strong> for at se den fulde flow med 15 regler.
          </Empty>
        )}

        {result && !hasResult && (
          <Empty>
            Vurderingen returnerede status <strong>{result.aggregate_status}</strong>. Ingen regler udløste krav for denne case.
          </Empty>
        )}
      </Page>
    );
  }

  // ----- RESULT MODE -----
  return (
    <Page>
      <Shell>
        <Doc>
          <BackLink type="button" onClick={() => mutation.reset()}>
            ← Ny vurdering
          </BackLink>

          <Breadcrumb>
            <span>Sager</span>
            <span className="crumb-sep">/</span>
            <span>{displayTitle}</span>
            <span className="crumb-sep">/</span>
            <span className="crumb-current">Vurdering</span>
          </Breadcrumb>

          {displayCaseId && <CaseId>Sag {displayCaseId}</CaseId>}
          <CaseTitle>{displayTitle}</CaseTitle>
          <CaseMeta>
            {note && <>{note} · </>}
            {evaluatedDate && <>Vurderet {evaluatedDate}</>}
            {evaluatedDate && ' · '}
            rule_engine {result.rule_engine_version}
          </CaseMeta>

          {relevantWarnings.length > 0 && (
            <Warnings>
              <strong>Bemærkninger:</strong>
              <ul>
                {relevantWarnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </Warnings>
          )}

          <VerdictBanner>
            <VerdictStatus>{statusLabel(result.aggregate_status)}</VerdictStatus>
            <VerdictText>
              {decisions.length} af {result.rules_loaded} lovartikler udløser krav før idriftsættelse.
              {evidenceItems.length > 0 && (
                <> {evidenceItems.length} konkrete artefakter skal etableres; {totalKrav} dokumentationskrav skal opfyldes.</>
              )}
            </VerdictText>
          </VerdictBanner>

            {decisions.length > 0 && (
              <>
                <SectionH>Vurderingens grundlag</SectionH>
                <SectionLede>
                  {decisions.length === 1
                    ? 'Én lovartikel udløser krav. Læs grundlaget her — kilden står i marginen til højre.'
                    : `${decisions.length} lovartikler regulerer tilsammen denne anvendelse. Hvert grundlag begrundes i sin egen sammenhæng — kilde-citatet står i marginen til højre.`}
                </SectionLede>

                {decisions.map((decision, idx) => {
                  const num = idx + 1;
                  const fnSup = toSuperscript(num);
                  return (
                    <Rule key={decision.rule_id}>
                      <RuleHead>
                        <RuleMarker>Lovartikel {num} af {decisions.length}</RuleMarker>
                        <ComplianceVerdict status={decision.status || 'NEEDS_INPUT'} size="sm" />
                      </RuleHead>
                      <RuleTitle>
                        {ruleHumanTitle(decision)}
                        <FootnoteRef href={`#sn${num}`}>{fnSup}</FootnoteRef>
                      </RuleTitle>

                      {decision.outcome?.begrundelse && (
                        <RuleBody>
                          {decision.outcome.begrundelse}
                          <FootnoteRef href={`#sn${num}`}>{fnSup}</FootnoteRef>
                        </RuleBody>
                      )}

                      {decision.outcome?.krav && decision.outcome.krav.length > 0 && (
                        <KravBlock>
                          <KravHeader>Krav for compliance</KravHeader>
                          <KravList>
                            {decision.outcome.krav.map((krav, i) => (
                              <KravItem key={i}>
                                <span>{krav}</span>
                              </KravItem>
                            ))}
                          </KravList>
                        </KravBlock>
                      )}

                      {decision.needs_input && decision.needs_input.length > 0 && (
                        <NeedsInputBox>
                          <strong>Mangler svar på {decision.needs_input.length} predikat(er):</strong>
                          <ul>
                            {decision.needs_input.map((pid) => (
                              <li key={pid}>{pid}</li>
                            ))}
                          </ul>
                        </NeedsInputBox>
                      )}
                    </Rule>
                  );
                })}
              </>
            )}

            {evidenceItems.length > 0 && (
              <>
                <SectionH>Evidens-checkliste</SectionH>
                <SectionLede>
                  {evidenceItems.length} artefakter er identificeret på tværs af de ramte regler.
                </SectionLede>
                <EvidenceChecklist items={evidenceItems} />
              </>
            )}

            <AuditFootnote>
              <b>Audit-spor</b>
              <br />
              rule_engine {result.rule_engine_version} · evalueret {result.evaluated_at}
              <br />
              rules_loaded={result.rules_loaded} · triggered={decisions.length} · aggregate=<b>{result.aggregate_status}</b>
              <br />
              deterministisk afgørelse · LLM blev ikke brugt til selve afgørelsen
              {result.audit_log_id && (
                <>
                  <br />
                  audit_log_id: <b>{result.audit_log_id}</b>
                </>
              )}
            </AuditFootnote>
          </Doc>

        <SidenotesColumn notes={sidenotes} />
      </Shell>
    </Page>
  );
};

export default V3VurderingPage;
