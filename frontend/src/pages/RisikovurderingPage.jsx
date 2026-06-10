import React, { useCallback, useRef, useState } from 'react';
import styled from 'styled-components';
import axios from 'axios';
import {
  FaFileUpload, FaTimes, FaFileWord, FaSpinner, FaCheckCircle,
  FaExclamationTriangle, FaShieldAlt, FaMagic, FaDownload,
} from 'react-icons/fa';

import { useToast } from '../components/ui';

/**
 * RisikovurderingPage — automatiseret databeskyttelsesretlig risikovurdering.
 *
 * Flow (3 trin):
 *   1. Upload dokumenter (MSA, DBA, produkt-PDF) + systemnavn → POST /analyze
 *   2. Gennemgå udtrukne fakta + besvar afklarende spørgsmål → POST /generate
 *   3. Preview risici + felttekster → download Word via POST /render
 *
 * Output er et FØRSTEUDKAST som AI Program Lead + DPO efterredigerer.
 */

const NAVY = '#0d2e54';
const BRONZE = '#6e5527';

const Page = styled.div`
  max-width: 980px;
  margin: 0 auto;
  padding: 2rem 1.5rem 4rem;
`;

const Eyebrow = styled.div`
  font-family: ${(p) => p.theme?.fonts?.mono || 'monospace'};
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: ${BRONZE};
  font-weight: 700;
  margin-bottom: 0.5rem;
`;

const Title = styled.h1`
  font-family: ${(p) => p.theme?.fonts?.display || 'Georgia, serif'};
  font-size: 2rem;
  color: ${NAVY};
  margin: 0 0 0.5rem;
  letter-spacing: -0.02em;
`;

const Lede = styled.p`
  font-size: 1rem;
  color: #4a5160;
  line-height: 1.6;
  margin: 0 0 1.5rem;
  max-width: 70ch;
`;

const Disclaimer = styled.div`
  background: rgba(176, 138, 74, 0.1);
  border-left: 3px solid ${BRONZE};
  border-radius: 0 6px 6px 0;
  padding: 0.7rem 1rem;
  font-size: 0.85rem;
  color: #5a4a2a;
  margin-bottom: 1.5rem;
  display: flex;
  gap: 0.5rem;
  align-items: flex-start;

  svg { flex-shrink: 0; margin-top: 0.15rem; }
`;

const Stepper = styled.div`
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.8rem;
  flex-wrap: wrap;

  .step {
    flex: 1;
    min-width: 140px;
    padding: 0.6rem 0.9rem;
    border-radius: 6px;
    border: 1px solid #e2e6ec;
    font-size: 0.82rem;
    font-weight: 600;
    color: #8a909c;
    background: #f8fafc;
    display: flex;
    align-items: center;
    gap: 0.5rem;

    &.active { border-color: ${NAVY}; color: ${NAVY}; background: rgba(13,46,84,0.04); }
    &.done { border-color: #2d6a31; color: #2d6a31; }

    .num {
      width: 22px; height: 22px; border-radius: 50%;
      display: inline-flex; align-items: center; justify-content: center;
      font-size: 0.75rem; background: currentColor; color: white;
    }
    &.active .num { background: ${NAVY}; }
    &.done .num { background: #2d6a31; }
  }
`;

const Card = styled.section`
  background: white;
  border: 1px solid #e2e6ec;
  border-radius: 10px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
`;

const DropZone = styled.div`
  border: 2px dashed ${(p) => (p.$drag ? NAVY : '#cbd2dc')};
  border-radius: 10px;
  padding: 2.5rem 1.5rem;
  text-align: center;
  cursor: pointer;
  background: ${(p) => (p.$drag ? 'rgba(13,46,84,0.04)' : '#fafbfc')};
  transition: all 0.15s;

  svg { font-size: 2rem; color: ${NAVY}; margin-bottom: 0.6rem; }
  .hint { color: #6a7180; font-size: 0.88rem; }
  .types { color: #9aa1ad; font-size: 0.76rem; margin-top: 0.4rem; }
`;

const FileList = styled.ul`
  list-style: none;
  margin: 1rem 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;

  li {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.7rem;
    background: #f4f6f9;
    border-radius: 6px;
    font-size: 0.85rem;

    .name { flex: 1; color: #2a3140; }
    .size { color: #9aa1ad; font-size: 0.76rem; }
    button { background: none; border: none; color: #a02020; cursor: pointer; padding: 2px; }
  }
`;

const Field = styled.div`
  margin-bottom: 1.1rem;

  label {
    display: block;
    font-size: 0.85rem;
    font-weight: 600;
    color: #2a3140;
    margin-bottom: 0.35rem;
  }
  .reason { font-size: 0.78rem; color: #8a909c; font-weight: 400; margin-top: 0.1rem; }

  input[type="text"], textarea {
    width: 100%;
    padding: 0.55rem 0.75rem;
    border: 1px solid #d8dde6;
    border-radius: 6px;
    font-family: inherit;
    font-size: 0.9rem;
    box-sizing: border-box;
  }
  textarea { min-height: 70px; resize: vertical; }
`;

const RadioRow = styled.div`
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;

  label {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.45rem 0.8rem;
    border: 1px solid #d8dde6;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 500;
    font-size: 0.85rem;
    margin: 0;

    &.checked { border-color: ${NAVY}; background: rgba(13,46,84,0.05); color: ${NAVY}; }
    input { margin: 0; }
  }
`;

const PrimaryBtn = styled.button`
  background: ${NAVY};
  color: white;
  border: none;
  padding: 0.7rem 1.4rem;
  border-radius: 6px;
  font-weight: 600;
  font-size: 0.92rem;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  &:hover:not(:disabled) { background: #0a2444; }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
`;

const GhostBtn = styled.button`
  background: transparent;
  color: ${NAVY};
  border: 1px solid #d8dde6;
  padding: 0.7rem 1.2rem;
  border-radius: 6px;
  font-weight: 500;
  font-size: 0.9rem;
  cursor: pointer;
  &:hover:not(:disabled) { border-color: ${NAVY}; }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
`;

const RiskTable = styled.table`
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
  margin-top: 0.5rem;

  th, td {
    text-align: left;
    padding: 0.55rem 0.6rem;
    border-bottom: 1px solid #eef1f5;
    vertical-align: top;
  }
  th { color: #8a909c; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; }
  .score {
    font-weight: 700;
    white-space: nowrap;
  }
  .Lav { color: #2d6a31; }
  .Lav-middel { color: #5a8a3a; }
  .Middel { color: ${BRONZE}; }
  .Middel-høj { color: #c2410c; }
  .Høj { color: #a02020; }
`;

const Spin = styled(FaSpinner)`
  animation: spin 1s linear infinite;
  @keyframes spin { to { transform: rotate(360deg); } }
`;

const SCORE_CLASS = (v) => (v || '').replace(/\s/g, '');

const RisikovurderingPage = () => {
  const toast = useToast();
  const fileInputRef = useRef(null);
  const [step, setStep] = useState(1);
  const [drag, setDrag] = useState(false);
  const [files, setFiles] = useState([]);
  const [systemnavn, setSystemnavn] = useState('');

  const [analyzing, setAnalyzing] = useState(false);
  const [facts, setFacts] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});

  const [generating, setGenerating] = useState(false);
  const [rv, setRv] = useState(null);
  const [compliance, setCompliance] = useState(null);       // server-beregnet (single source of truth)
  const [verifyPreview, setVerifyPreview] = useState(null);  // dokument-tjek FØR download
  const [assessmentId, setAssessmentId] = useState(null);    // journaliseret server-side
  const [linkCaseId, setLinkCaseId] = useState('');          // valgfri sag-kobling
  const [downloading, setDownloading] = useState(false);

  const addFiles = useCallback((fileList) => {
    const accepted = ['.pdf', '.docx', '.txt', '.md'];
    const next = [];
    for (const f of fileList) {
      const ok = accepted.some((ext) => f.name.toLowerCase().endsWith(ext));
      if (!ok) { toast.error(`${f.name}: ikke-understøttet filtype`); continue; }
      if (f.size > 10 * 1024 * 1024) { toast.error(`${f.name}: for stor (max 10 MB)`); continue; }
      next.push(f);
    }
    setFiles((prev) => [...prev, ...next].slice(0, 10));
  }, [toast]);

  const onDrop = (e) => {
    e.preventDefault();
    setDrag(false);
    if (e.dataTransfer.files?.length) addFiles(e.dataTransfer.files);
  };

  const runAnalyze = async () => {
    if (!files.length && !systemnavn.trim()) {
      toast.error('Upload mindst ét dokument eller angiv et systemnavn');
      return;
    }
    setAnalyzing(true);
    try {
      const fd = new FormData();
      files.forEach((f) => fd.append('files', f));
      if (systemnavn.trim()) fd.append('systemnavn', systemnavn.trim());
      const res = await axios.post('/api/v3/risk-assessment/analyze', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 240000,
      });
      setFacts(res.data.facts);
      setQuestions(res.data.questions || []);
      // Forudfyld answers med defaults
      const init = {};
      (res.data.questions || []).forEach((q) => {
        if (q.default != null) init[q.key] = q.default;
      });
      setAnswers(init);
      setStep(2);
      toast.success(`Analyse færdig — ${res.data.documents?.length || 0} dokument(er) læst`);
    } catch (err) {
      toast.error(`Analyse fejlede: ${err?.response?.data?.error?.message || err?.message}`);
    } finally {
      setAnalyzing(false);
    }
  };

  const runGenerate = async () => {
    setGenerating(true);
    try {
      // Timeout 600s: 2 LLM-kald × op til 3 retry-forsøg kan overstige 300s
      // på lokal model — lad backend gøre arbejdet færdigt.
      const res = await axios.post('/api/v3/risk-assessment/generate', {
        facts,
        answers,
        case_id: linkCaseId.trim() || null,
      }, { timeout: 600000 });
      setRv(res.data.risikovurdering);
      setCompliance(res.data.compliance || null);
      setVerifyPreview(res.data.verify_preview || null);
      setAssessmentId(res.data.assessment_id || null);
      setStep(3);
      toast.success(`${res.data.n_risici} risici genereret — gennemgå udkastet`);
    } catch (err) {
      toast.error(`Generering fejlede: ${err?.response?.data?.error?.message || err?.message}`);
    } finally {
      setGenerating(false);
    }
  };

  const runDownload = async () => {
    setDownloading(true);
    try {
      const res = await axios.post('/api/v3/risk-assessment/render',
        { risikovurdering: rv },
        { responseType: 'blob', timeout: 60000 },
      );
      const url = URL.createObjectURL(res.data);
      const a = document.createElement('a');
      a.href = url;
      // Sanitize filnavn — Windows afviser \ / : * ? " < > |
      const safeNavn = (rv.facts.systemnavn || 'system').replace(/[\\/:*?"<>|]/g, '-');
      a.download = `Databeskyttelsesretlig risikovurdering - ${safeNavn}.docx`;
      a.click();
      URL.revokeObjectURL(url);
      const valid = res.headers['x-verify-valid'] === 'true';
      if (valid) toast.success('Word-dokument downloadet');
      else toast.warning?.('Downloadet — men verifikation fandt mangler, tjek dokumentet') || toast.info('Downloadet — tjek dokumentet');
    } catch (err) {
      toast.error(`Download fejlede: ${err?.message}`);
    } finally {
      setDownloading(false);
    }
  };

  const setAnswer = (key, val) => setAnswers((a) => ({ ...a, [key]: val }));

  return (
    <Page>
      <Eyebrow>Databeskyttelse · Automatiseret udkast</Eyebrow>
      <Title>Risikovurdering</Title>
      <Lede>
        Upload dokumenter om et nyt system (MSA, databehandleraftale, produkt-PDF),
        svar på et par spørgsmål, og få et færdigt Word-udkast baseret på Kalundborg
        Kommunes officielle skabelon.
      </Lede>

      <Disclaimer>
        <FaShieldAlt />
        <span>
          Output er et <strong>førsteudkast</strong> til efterredigering af AI Program
          Lead og DPO — ikke en endelig godkendt risikovurdering. Dokumenterne
          behandles lokalt (LM Studio), så persondata ikke forlader kommunen.
        </span>
      </Disclaimer>

      <Stepper>
        <div className={`step ${step === 1 ? 'active' : step > 1 ? 'done' : ''}`}>
          <span className="num">{step > 1 ? '✓' : '1'}</span> Upload
        </div>
        <div className={`step ${step === 2 ? 'active' : step > 2 ? 'done' : ''}`}>
          <span className="num">{step > 2 ? '✓' : '2'}</span> Fakta & spørgsmål
        </div>
        <div className={`step ${step === 3 ? 'active' : ''}`}>
          <span className="num">3</span> Udkast & download
        </div>
      </Stepper>

      {/* ---- STEP 1: Upload ---- */}
      {step === 1 && (
        <Card>
          <Field>
            <label htmlFor="systemnavn">Systemnavn</label>
            <input
              id="systemnavn"
              type="text"
              placeholder="fx Velatir, Voicecraft, Ruteoptimering"
              value={systemnavn}
              onChange={(e) => setSystemnavn(e.target.value)}
            />
          </Field>

          <DropZone
            $drag={drag}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={onDrop}
          >
            <FaFileUpload />
            <div className="hint">Træk filer hertil eller klik for at vælge</div>
            <div className="types">PDF, DOCX, TXT, MD · max 10 MB pr. fil · op til 10 filer</div>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.docx,.txt,.md"
              style={{ display: 'none' }}
              onChange={(e) => addFiles(e.target.files)}
            />
          </DropZone>

          {files.length > 0 && (
            <FileList>
              {files.map((f, i) => (
                <li key={i}>
                  <FaFileWord style={{ color: NAVY }} />
                  <span className="name">{f.name}</span>
                  <span className="size">{(f.size / 1024).toFixed(0)} KB</span>
                  <button onClick={() => setFiles((p) => p.filter((_, j) => j !== i))} aria-label="Fjern">
                    <FaTimes />
                  </button>
                </li>
              ))}
            </FileList>
          )}

          <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end' }}>
            <PrimaryBtn onClick={runAnalyze} disabled={analyzing}>
              {analyzing ? <><Spin /> Analyserer dokumenter…</> : <><FaMagic /> Analysér</>}
            </PrimaryBtn>
          </div>
        </Card>
      )}

      {/* ---- STEP 2: Facts + questions ---- */}
      {step === 2 && facts && (
        <>
          <Card>
            <h3 style={{ marginTop: 0, color: NAVY }}>Udtrukne fakta</h3>
            <p style={{ fontSize: '0.83rem', color: '#8a909c', marginTop: '-0.5rem' }}>
              AI-udtrukket fra dokumenterne — ret hvis noget er forkert.
            </p>
            <Field>
              <label>Systemnavn</label>
              <input type="text" value={facts.systemnavn || ''}
                onChange={(e) => setFacts({ ...facts, systemnavn: e.target.value })} />
            </Field>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem' }}>
              <Field>
                <label>Leverandør</label>
                <input type="text" value={facts.leverandoer_navn || ''}
                  onChange={(e) => setFacts({ ...facts, leverandoer_navn: e.target.value })} />
              </Field>
              <Field>
                <label>Hosting</label>
                <input type="text" value={facts.hosting_lokation || ''}
                  onChange={(e) => setFacts({ ...facts, hosting_lokation: e.target.value })} />
              </Field>
            </div>
            <Field>
              <label>Formål</label>
              <textarea value={facts.formaal_kort || ''}
                onChange={(e) => setFacts({ ...facts, formaal_kort: e.target.value })} />
            </Field>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.8rem' }}>
              <Field>
                <label>
                  Kontraktværdi 4 år (kr.)
                  <span className="reason">Fra dokumenter — bucket-spørgsmålet nedenfor kan overstyre</span>
                </label>
                <input type="number" min="0" step="1000"
                  value={facts.kontraktvaerdi_4aar_kr ?? ''}
                  onChange={(e) => setFacts({
                    ...facts,
                    kontraktvaerdi_4aar_kr: e.target.value === '' ? null : Number(e.target.value),
                    kontraktvaerdi_er_estimat: false,
                  })} />
              </Field>
              <Field>
                <label>Fagområde</label>
                <input type="text" placeholder="fx Beskæftigelse"
                  value={facts.fagomraade || ''}
                  onChange={(e) => setFacts({ ...facts, fagomraade: e.target.value })} />
              </Field>
              <Field>
                <label>
                  Knyt til sag (valgfrit)
                  <span className="reason">Eksternt case-ID, fx K-2026-0042 — journaliseres på sagen</span>
                </label>
                <input type="text" placeholder="K-2026-…"
                  value={linkCaseId}
                  onChange={(e) => setLinkCaseId(e.target.value)} />
              </Field>
            </div>
            {facts.msa_risiko_klausuler?.length > 0 && (
              <div style={{
                background: 'rgba(160,32,32,0.05)', borderLeft: '3px solid #a02020',
                borderRadius: '0 4px 4px 0', padding: '0.6rem 0.9rem', fontSize: '0.82rem',
              }}>
                <strong style={{ color: '#a02020' }}>MSA-røde flag:</strong>
                <ul style={{ margin: '0.3rem 0 0', paddingLeft: '1.2rem' }}>
                  {facts.msa_risiko_klausuler.map((c, i) => <li key={i}>{c}</li>)}
                </ul>
              </div>
            )}
          </Card>

          <Card>
            <h3 style={{ marginTop: 0, color: NAVY }}>Afklarende spørgsmål</h3>
            {questions.map((q) => (
              <Field key={q.key}>
                <label>
                  {q.question}
                  {q.reason && <span className="reason">{q.reason}</span>}
                </label>
                {q.type === 'radio' && (
                  <RadioRow>
                    {q.options.map((opt) => (
                      <label key={opt} className={answers[q.key] === opt ? 'checked' : ''}>
                        <input type="radio" name={q.key} value={opt}
                          checked={answers[q.key] === opt}
                          onChange={() => setAnswer(q.key, opt)} />
                        {opt}
                      </label>
                    ))}
                  </RadioRow>
                )}
                {q.type === 'multiselect' && (
                  <RadioRow>
                    {q.options.map((opt) => {
                      const selected = (answers[q.key] || '').split(',').filter(Boolean);
                      const checked = selected.includes(opt);
                      return (
                        <label key={opt} className={checked ? 'checked' : ''}>
                          <input type="checkbox" checked={checked}
                            onChange={() => {
                              const next = checked ? selected.filter((s) => s !== opt) : [...selected, opt];
                              setAnswer(q.key, next.join(','));
                            }} />
                          {opt}
                        </label>
                      );
                    })}
                  </RadioRow>
                )}
                {q.type === 'text' && (
                  <input type="text" value={answers[q.key] || ''}
                    onChange={(e) => setAnswer(q.key, e.target.value)} />
                )}
              </Field>
            ))}

            <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'space-between' }}>
              <GhostBtn onClick={() => setStep(1)} disabled={generating}>← Tilbage</GhostBtn>
              <PrimaryBtn onClick={runGenerate} disabled={generating}>
                {generating
                  ? <><Spin /> Genererer risici + tekst… (kan tage 1-2 min lokalt)</>
                  : <><FaMagic /> Generér risikovurdering</>}
              </PrimaryBtn>
            </div>
          </Card>
        </>
      )}

      {/* ---- STEP 3: Preview + download ---- */}
      {step === 3 && rv && (
        <>
          {/* Kalundborg compliance-status — surfacer kommunale procesforhold før risikolisten */}
          {(() => {
            const f = rv.facts || {};
            const procesFlags = [
              ['D&IT tidlig involvering', f.dit_involveret_tidligt],
              ['CIO-underskrift', f.cio_har_underskrevet],
              ['DBA indgået', f.databehandleraftale_indgaaet],
              ['Styregruppe', f.styregruppe_etableret],
              ['Fortegnelse art. 30', f.fortegnelse_art30_opdateret],
              ['Oplysningspligt art. 13-14', f.oplysningspligt_opfyldt],
              ['DPIA sendt til DPO', f.dpia_sendt_til_dpo],
              ['AI-færdigheder art. 4', f.ai_faerdigheder_dokumenteret],
              ['Contract Management-plan', f.contract_management_plan],
            ];
            // Foretræk server-beregnet compliance (single source of truth i models.py);
            // lokal beregning er kun fallback hvis ældre backend-svar mangler blokken.
            const TÆRSKEL = 1601944;
            const done = compliance?.proces_done ?? procesFlags.filter(([, v]) => v).length;
            const overTærskel = compliance?.er_over_udbudsterskel
              ?? (f.kontraktvaerdi_4aar_kr && f.kontraktvaerdi_4aar_kr > TÆRSKEL);
            const mismatch = compliance?.udbudspligt_mismatch
              ?? (overTærskel && f.anskaffelsesvej && f.anskaffelsesvej !== 'eu_udbud' && f.anskaffelsesvej !== 'ukendt');
            const erEstimat = compliance?.kontraktvaerdi_er_estimat ?? f.kontraktvaerdi_er_estimat;
            return (
              <Card>
                <h3 style={{ marginTop: 0, color: NAVY }}>Kommunal compliance-status</h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.6rem 1rem', fontSize: '0.85rem', marginBottom: '0.8rem' }}>
                  <div><strong>Anskaffelsesvej:</strong> {f.anskaffelsesvej || 'ukendt'}</div>
                  <div><strong>Kontraktværdi (4 år):</strong> {f.kontraktvaerdi_4aar_kr
                    ? (erEstimat
                      ? `${f.kontraktvaerdi_bucket_label || 'estimat'} (estimat)`
                      : f.kontraktvaerdi_4aar_kr.toLocaleString('da-DK') + ' kr.')
                    : 'ukendt'} {overTærskel ? '⚠ over tærskel' : ''}</div>
                  <div><strong>Fagområde:</strong> {f.fagomraade || '(ikke angivet)'}</div>
                  <div><strong>Særlovgivning:</strong> {(f.saerlovgivning || []).join(', ') || '(ikke angivet)'}</div>
                </div>
                {mismatch && (
                  <div style={{ background: 'rgba(160,32,32,0.06)', borderLeft: '3px solid #a02020', padding: '0.5rem 0.8rem', fontSize: '0.85rem', marginBottom: '0.8rem', color: '#a02020' }}>
                    <strong>⚠ Udbudspligt-mismatch:</strong> Kontraktværdi over tærskel (kr. 1.601.944) men anskaffelsesvej er ikke EU-udbud → potentielt ulovligt indkøb. Bør indgå som blocker.
                  </div>
                )}
                <div style={{ fontSize: '0.85rem', marginBottom: '0.4rem' }}>
                  <strong>Proces-status: {done}/9 punkter gennemført</strong>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.3rem 0.6rem', fontSize: '0.8rem' }}>
                  {procesFlags.map(([label, ok]) => (
                    <div key={label} style={{ color: ok ? '#2d6a31' : '#a02020' }}>
                      {ok ? '✓' : '✗'} {label}
                    </div>
                  ))}
                </div>
              </Card>
            );
          })()}

          {/* Dokument-verifikation kørt server-side under generate — vis problemer FØR download */}
          {verifyPreview && !verifyPreview.valid && verifyPreview.problems?.length > 0 && (
            <Card style={{ borderLeft: '4px solid #b08a4a' }}>
              <h3 style={{ marginTop: 0, color: '#6e5527' }}>
                <FaExclamationTriangle style={{ marginRight: '0.4rem' }} />
                Dokument-tjek fandt {verifyPreview.problems.length} bemærkning{verifyPreview.problems.length === 1 ? '' : 'er'}
              </h3>
              <p style={{ fontSize: '0.83rem', color: '#6a7180', marginTop: '-0.3rem' }}>
                Word-dokumentet kan stadig downloades — men gennemgå disse punkter i efterredigeringen:
              </p>
              <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.85rem', lineHeight: 1.6 }}>
                {verifyPreview.problems.map((p, i) => <li key={i}>{p}</li>)}
              </ul>
            </Card>
          )}

          <Card>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <FaCheckCircle style={{ color: '#2d6a31' }} />
              <h3 style={{ margin: 0, color: NAVY }}>
                {rv.risici.length} risici identificeret
              </h3>
            </div>
            {assessmentId && (
              <p style={{ fontSize: '0.78rem', color: '#6a7180', margin: '0 0 0.6rem' }}>
                ✓ Journaliseret server-side (ID <code>{assessmentId.slice(0, 8)}…</code>
                {linkCaseId.trim() ? ` · koblet til sag ${linkCaseId.trim()}` : ''}) —
                kan re-downloades selv hvis fanen lukkes.
              </p>
            )}
            <RiskTable>
              <thead>
                <tr>
                  <th style={{ width: '28%' }}>Risiko</th>
                  <th style={{ width: '34%' }}>Konsekvens</th>
                  <th>Sandsynl.</th>
                  <th>Score</th>
                </tr>
              </thead>
              <tbody>
                {rv.risici.map((r, i) => (
                  <tr key={i}>
                    <td>{r.risiko}</td>
                    <td>{r.konsekvens_beskrivelse}</td>
                    <td>{r.sandsynlighed}</td>
                    <td className={`score ${SCORE_CLASS(r.score)}`}>{r.score}</td>
                  </tr>
                ))}
              </tbody>
            </RiskTable>
          </Card>

          <Card>
            <h3 style={{ marginTop: 0, color: NAVY }}>Felttekster (uddrag)</h3>
            {[
              ['Formål', rv.formaal_tekst],
              ['Baggrund', rv.baggrund_tekst],
              ['Tiltag', rv.tiltag_tekst],
              ['Kontrolmekanismer', rv.kontrolmekanismer_tekst],
            ].map(([label, text]) => (
              <details key={label} style={{ marginBottom: '0.6rem' }}>
                <summary style={{ cursor: 'pointer', fontWeight: 600, color: '#2a3140', fontSize: '0.88rem' }}>
                  {label}
                </summary>
                <p style={{ fontSize: '0.85rem', color: '#4a5160', lineHeight: 1.55, margin: '0.4rem 0 0' }}>
                  {text || <em>(tom)</em>}
                </p>
              </details>
            ))}
          </Card>

          <Disclaimer>
            <FaExclamationTriangle />
            <span>
              Dette er et AI-genereret udkast. Gennemgå hver risiko og hvert felt,
              og lad DPO kvalitetssikre før dokumentet anvendes.
            </span>
          </Disclaimer>

          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <GhostBtn onClick={() => setStep(2)} disabled={downloading}>← Tilbage</GhostBtn>
            <PrimaryBtn onClick={runDownload} disabled={downloading}>
              {downloading ? <><Spin /> Bygger Word…</> : <><FaDownload /> Download Word-dokument</>}
            </PrimaryBtn>
          </div>
        </>
      )}
    </Page>
  );
};

export default RisikovurderingPage;
