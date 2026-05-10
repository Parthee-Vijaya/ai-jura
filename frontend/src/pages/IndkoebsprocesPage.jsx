import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import styled from 'styled-components';
import axios from 'axios';
import {
  FaCheckCircle,
  FaArrowRight,
  FaSpinner,
  FaShoppingCart,
  FaCode,
  FaCloudUploadAlt,
  FaCheck,
  FaFolderOpen,
  FaFileWord,
  FaFilePdf,
} from 'react-icons/fa';
import { EvidenceEditor } from '../components/rules';
import { Breadcrumb } from '../components/ui';

/**
 * IndkoebsprocesPage — 4-trins wizard der matcher Kalundborg Kommunes
 * faktiske workflow for indkøb af AI-løsninger.
 *
 * State persisteres i backend (cases.intake_state) — debounced auto-save
 * 800ms efter sidste edit. URL-param `?case_id=K-...` loader eksisterende
 * sag. "Mine sager"-strip øverst lister åbne drafts på tværs af sessions
 * og enheder (cross-device via Tailscale).
 */

// ---- Layout primitives ----------------------------------------------------

const Page = styled.div`
  max-width: 1100px;
  margin: 0 auto;
  padding: 3rem 2.5rem 5rem;
`;

const Eyebrow = styled.div`
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: ${(p) => p.theme.colors.inkFaded};
  margin-bottom: 0.5rem;
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
  margin: 0 0 1.5rem;
  color: ${(p) => p.theme.colors.inkSoft};
  font-size: 1.05rem;
  line-height: 1.6;
  max-width: 720px;
`;

const SaveStatus = styled.div`
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.78rem;
  color: ${(p) =>
    p.$status === 'saving'
      ? p.theme.colors.bronze
      : p.$status === 'saved'
      ? '#2d6a31'
      : p.$status === 'error'
      ? '#a02020'
      : p.theme.colors.inkFaded};
  margin-bottom: 1.5rem;

  svg { font-size: 0.86rem; }
`;

// ---- "Mine sager" strip ---------------------------------------------------

const DraftsStrip = styled.section`
  margin-bottom: 2rem;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid ${(p) => p.theme.colors.line};

  .strip-head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 0.85rem;

    h3 {
      font-family: ${(p) => p.theme.fonts.sans};
      font-size: 0.74rem;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: ${(p) => p.theme.colors.inkSoft};
      font-weight: 600;
      margin: 0;
    }
    .new-link {
      font-family: ${(p) => p.theme.fonts.sans};
      font-size: 0.82rem;
      color: ${(p) => p.theme.colors.primary};
      cursor: pointer;
      background: none;
      border: none;
      padding: 0;
    }
  }

  .scroll {
    display: flex;
    gap: 0.85rem;
    overflow-x: auto;
    padding-bottom: 0.5rem;
  }
`;

const DraftCard = styled.button`
  flex: 0 0 280px;
  background: ${(p) => (p.$active ? (p.theme.colors.paperSoft || 'rgba(13,46,84,0.08)') : p.theme.colors.card)};
  border: 1px solid ${(p) => (p.$active ? p.theme.colors.primary : p.theme.colors.line)};
  border-radius: 8px;
  padding: 0.85rem 1rem;
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  transition: border-color 0.15s ease;

  &:hover { border-color: ${(p) => p.theme.colors.primary}; }

  .case-id {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.74rem;
    color: ${(p) => p.theme.colors.inkFaded};
    margin-bottom: 0.3rem;
  }

  .ttl {
    font-family: ${(p) => p.theme.fonts.sans};
    font-size: 0.92rem;
    font-weight: 600;
    color: ${(p) => p.theme.colors.ink};
    margin-bottom: 0.35rem;
    line-height: 1.3;
    /* clamp 2 lines */
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .meta {
    font-family: ${(p) => p.theme.fonts.body};
    font-size: 0.78rem;
    color: ${(p) => p.theme.colors.inkSoft};
    display: flex;
    justify-content: space-between;
  }

  .progress-bar {
    height: 4px;
    background: ${(p) => p.theme.colors.line};
    border-radius: 999px;
    overflow: hidden;
    margin-top: 0.5rem;

    .fill {
      height: 100%;
      background: ${(p) => p.theme.colors.primary};
      transition: width 0.3s ease;
    }
  }
`;

// ---- Stepper --------------------------------------------------------------

const Stepper = styled.ol`
  list-style: none;
  margin: 0 0 2.5rem;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0;
  border: 1px solid ${(p) => p.theme.colors.line};
  border-radius: 8px;
  overflow: hidden;
  background: ${(p) => p.theme.colors.card};

  @media (max-width: 720px) {
    grid-template-columns: 1fr;
  }
`;

const StepCell = styled.li`
  padding: 1rem 1.1rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  border-right: 1px solid ${(p) => p.theme.colors.line};
  background: ${(p) =>
    p.$active
      ? p.theme.colors.paperSoft || 'rgba(13,46,84,0.06)'
      : p.$done
      ? 'rgba(45, 106, 49, 0.06)'
      : 'transparent'};
  cursor: pointer;
  transition: background 0.15s ease;

  &:hover { background: ${(p) => p.theme.colors.paperSoft || 'rgba(13,46,84,0.04)'}; }
  &:last-child { border-right: none; }

  @media (max-width: 720px) {
    border-right: none;
    border-bottom: 1px solid ${(p) => p.theme.colors.line};
    &:last-child { border-bottom: none; }
  }

  .num {
    width: 30px;
    height: 30px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: ${(p) => (p.$done ? '#2d6a31' : p.$active ? p.theme.colors.primary : p.theme.colors.line)};
    color: ${(p) => (p.$done || p.$active ? 'white' : p.theme.colors.inkSoft)};
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.86rem;
    font-weight: 700;
    flex-shrink: 0;
  }

  .label {
    font-family: ${(p) => p.theme.fonts.sans};
    font-size: 0.84rem;
    color: ${(p) => p.theme.colors.ink};
    font-weight: ${(p) => (p.$active ? 600 : 500)};
    line-height: 1.3;
  }

  .meta {
    font-family: ${(p) => p.theme.fonts.body};
    font-size: 0.74rem;
    color: ${(p) => p.theme.colors.inkSoft};
    margin-top: 0.15rem;
    display: block;
  }
`;

const Card = styled.section`
  background: ${(p) => p.theme.colors.card};
  border: 1px solid ${(p) => p.theme.colors.line};
  border-radius: 10px;
  padding: 1.75rem 2rem;
  margin-bottom: 1.5rem;
  position: relative;

  &::before {
    content: '';
    position: absolute;
    top: -1px;
    left: 2rem;
    right: 2rem;
    height: 2px;
    background: linear-gradient(
      to right,
      transparent,
      ${(p) => p.theme.colors.bronze} 50%,
      transparent
    );
    opacity: 0.4;
  }

  h2 {
    font-family: ${(p) => p.theme.fonts.display};
    font-size: 1.5rem;
    font-weight: 600;
    letter-spacing: -0.012em;
    margin: 0 0 0.4rem;
    color: ${(p) => p.theme.colors.ink};
  }

  .lede {
    font-family: ${(p) => p.theme.fonts.body};
    font-size: 0.95rem;
    color: ${(p) => p.theme.colors.inkSoft};
    line-height: 1.55;
    margin-bottom: 1.25rem;
  }
`;

const FieldGroup = styled.div`
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.1rem;
  margin-bottom: 1.5rem;
`;

const Field = styled.div`
  label {
    display: block;
    font-family: ${(p) => p.theme.fonts.sans};
    font-size: 0.85rem;
    font-weight: 600;
    color: ${(p) => p.theme.colors.ink};
    margin-bottom: 0.35rem;

    .req { color: #a03612; margin-left: 0.25rem; font-weight: 700; }
  }

  .hint {
    font-family: ${(p) => p.theme.fonts.body};
    font-size: 0.82rem;
    color: ${(p) => p.theme.colors.inkSoft};
    margin-bottom: 0.4rem;
    font-style: italic;
  }

  input, textarea, select {
    width: 100%;
    padding: 0.6rem 0.85rem;
    font-family: ${(p) => p.theme.fonts.body};
    font-size: 0.95rem;
    line-height: 1.55;
    border: 1px solid ${(p) => p.theme.colors.line};
    border-radius: 5px;
    background: ${(p) => p.theme.colors.paper};
    color: ${(p) => p.theme.colors.ink};
    box-sizing: border-box;

    &:focus {
      outline: none;
      border-color: ${(p) => p.theme.colors.primary};
      box-shadow: 0 0 0 3px rgba(13, 46, 84, 0.1);
    }
  }

  textarea { min-height: 100px; resize: vertical; }
`;

const Choice = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.85rem;

  @media (max-width: 640px) {
    grid-template-columns: 1fr;
  }
`;

const ChoiceCard = styled.button`
  background: ${(p) => (p.$active ? (p.theme.colors.paperSoft || 'rgba(13,46,84,0.06)') : 'transparent')};
  border: 2px solid ${(p) => (p.$active ? p.theme.colors.primary : p.theme.colors.line)};
  border-radius: 8px;
  padding: 1rem 1.2rem;
  text-align: left;
  cursor: pointer;
  font-family: inherit;
  transition: border-color 0.15s ease, background 0.15s ease;

  &:hover { border-color: ${(p) => p.theme.colors.primary}; }

  .icon {
    font-size: 1.4rem;
    color: ${(p) => p.theme.colors.primary};
    margin-bottom: 0.45rem;
    display: block;
  }

  .h {
    font-family: ${(p) => p.theme.fonts.sans};
    font-size: 1rem;
    font-weight: 700;
    color: ${(p) => p.theme.colors.ink};
    margin-bottom: 0.3rem;
  }

  .desc {
    font-family: ${(p) => p.theme.fonts.body};
    font-size: 0.85rem;
    color: ${(p) => p.theme.colors.inkSoft};
    line-height: 1.5;
  }
`;

const Controls = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-top: 1rem;
  flex-wrap: wrap;

  .left, .right {
    display: flex;
    gap: 0.6rem;
  }
`;

const PrimaryButton = styled.button`
  background: ${(p) => p.theme.colors.primary};
  color: white;
  border: none;
  padding: 0.7rem 1.3rem;
  border-radius: 6px;
  font-family: ${(p) => p.theme.fonts.sans};
  font-weight: 600;
  font-size: 0.92rem;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
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
  font-size: 0.88rem;
  cursor: pointer;
  &:hover { border-color: ${(p) => p.theme.colors.primary}; color: ${(p) => p.theme.colors.primary}; }
`;

const ArtifactGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 0.85rem;
  margin-top: 0.85rem;
`;

const ArtifactCard = styled.button`
  background: ${(p) => (p.$status === 'faerdig' ? 'rgba(45, 106, 49, 0.06)' : p.theme.colors.paper)};
  border: 1px solid ${(p) => (p.$status === 'faerdig' ? '#2d6a31' : p.theme.colors.line)};
  border-radius: 6px;
  padding: 0.85rem 1rem;
  text-align: left;
  cursor: pointer;
  font-family: inherit;

  &:hover { border-color: ${(p) => p.theme.colors.primary}; }

  .h {
    font-family: ${(p) => p.theme.fonts.sans};
    font-size: 0.92rem;
    font-weight: 600;
    color: ${(p) => p.theme.colors.ink};
    margin-bottom: 0.3rem;
    display: flex;
    justify-content: space-between;
    gap: 0.5rem;
    align-items: center;
  }

  .pill {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 2px 7px;
    border-radius: 999px;
    background: ${(p) =>
      p.$status === 'faerdig'
        ? '#2d6a31'
        : p.$status === 'i_gang'
        ? '#b08a4a'
        : '#a03612'};
    color: white;
  }

  .desc {
    font-family: ${(p) => p.theme.fonts.body};
    font-size: 0.78rem;
    color: ${(p) => p.theme.colors.inkSoft};
    line-height: 1.45;
  }
`;

const InfoBox = styled.div`
  background: ${(p) => p.theme.colors.paperSoft || 'rgba(13,46,84,0.04)'};
  border-left: 3px solid ${(p) => p.theme.colors.bronze};
  padding: 0.75rem 1rem;
  margin: 1rem 0;
  font-family: ${(p) => p.theme.fonts.body};
  font-size: 0.88rem;
  color: ${(p) => p.theme.colors.text};
  line-height: 1.55;
  border-radius: 0 4px 4px 0;

  strong { color: ${(p) => p.theme.colors.bronze}; }
`;

// ---- Constants & helpers --------------------------------------------------

const STEPS = [
  { num: 1, label: 'Identificér behov', meta: 'Behovsbeskrivelse + dobbeltsystem-check' },
  { num: 2, label: 'Opret sag i Serviceportalen', meta: 'AI-enheden notificeres' },
  { num: 3, label: 'Indledende screening', meta: 'Indkøb vs. udvikling, AI Act-relevans' },
  { num: 4, label: 'AI-enheden vurderer', meta: 'Tjekliste, DPIA, vurdering, endelig svar' },
];

const ARTIFACTS = [
  { id: 'ai_indkoeb_tjekliste', desc: '11-punkts tjekliste — Kalundborgs egen' },
  { id: 'dpia_taerskelsvurdering', desc: '9-kriterie tærskeltest — Datatilsynet/WP248' },
  { id: 'dpia_dokument', desc: 'KL/Datatilsynets 5-trin DPIA (hvis tærsklen udløst)' },
  { id: 'databehandleraftale_dbs', desc: 'DBS-standard, kvalitetstjek af IT-sikkerhed@kalundborg' },
  { id: 'risikostyringsplan', desc: 'AI Act Art. 9, ISO/IEC 23894-baseret' },
  { id: 'transparenstekst_til_registrerede', desc: 'GDPR Art. 13/14 + AI-oplysning' },
];

const DRAFT_PLACEHOLDER_ID = '__draft__';  // brugt indtil sagsnummer er angivet

function progressPct(intake) {
  // Crude completion-estimat baseret på antal udfyldte felter
  const fields = ['behov', 'dobbeltsystem_tjekket', 'sagsnummer', 'serviceportal_dato',
                  'indkoeb_eller_udvikling', 'system_description'];
  const filled = fields.filter((k) => {
    const v = intake?.[k];
    if (typeof v === 'boolean') return v;
    return typeof v === 'string' && v.trim() !== '';
  }).length;
  return Math.round((filled / fields.length) * 100);
}

// Trigger browser-download af sag-rapport (DOCX eller PDF).
function downloadCaseReport(caseId, format) {
  if (!caseId) return;
  const url = `/api/v3/cases/by-case-id/${encodeURIComponent(caseId)}/report?format=${format}`;
  const a = document.createElement('a');
  a.href = url;
  a.rel = 'noopener';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

// ---- Component -----------------------------------------------------------

const IndkoebsprocesPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const urlCaseId = searchParams.get('case_id');

  // Wizard state
  const [step, setStep] = useState(1);
  const [behov, setBehov] = useState('');
  const [dobbeltsystemTjekket, setDobbeltsystemTjekket] = useState(false);
  const [sagsnummer, setSagsnummer] = useState(urlCaseId || '');
  const [serviceportalDato, setServiceportalDato] = useState('');
  const [indkoebEllerUdvikling, setIndkoebEllerUdvikling] = useState(null);
  const [systemDescription, setSystemDescription] = useState('');

  // Backend persistence state
  const [saveStatus, setSaveStatus] = useState('idle'); // idle | saving | saved | error
  const [loadingExisting, setLoadingExisting] = useState(!!urlCaseId);
  const debounceRef = useRef(null);
  const lastSavedRef = useRef(null);

  // Drafts strip
  const [drafts, setDrafts] = useState([]);
  const fetchDrafts = useCallback(async () => {
    try {
      const r = await axios.get('/api/v3/cases/drafts');
      setDrafts(r.data?.items || []);
    } catch {
      setDrafts([]);
    }
  }, []);
  useEffect(() => { fetchDrafts(); }, [fetchDrafts]);

  // Load existing case from URL
  useEffect(() => {
    if (!urlCaseId) {
      setLoadingExisting(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const r = await axios.get(`/api/v3/cases/by-case-id/${encodeURIComponent(urlCaseId)}`);
        if (cancelled) return;
        const intake = r.data?.intake_state || {};
        setStep(intake.current_step || 1);
        setBehov(intake.behov || '');
        setDobbeltsystemTjekket(!!intake.dobbeltsystem_tjekket);
        setSagsnummer(urlCaseId);
        setServiceportalDato(intake.serviceportal_dato || '');
        setIndkoebEllerUdvikling(intake.indkoeb_eller_udvikling || null);
        setSystemDescription(intake.system_description || '');
        lastSavedRef.current = JSON.stringify(intake);
      } catch (err) {
        // 404 = ny sag, ok
        if (err?.response?.status !== 404) {
          console.error('Load failed', err);
        }
      } finally {
        if (!cancelled) setLoadingExisting(false);
      }
    })();
    return () => { cancelled = true; };
  }, [urlCaseId]);

  // Debounced auto-save
  const currentState = useMemo(
    () => ({
      current_step: step,
      behov,
      dobbeltsystem_tjekket: dobbeltsystemTjekket,
      sagsnummer,
      serviceportal_dato: serviceportalDato,
      indkoeb_eller_udvikling: indkoebEllerUdvikling,
      system_description: systemDescription,
    }),
    [step, behov, dobbeltsystemTjekket, sagsnummer, serviceportalDato, indkoebEllerUdvikling, systemDescription],
  );

  useEffect(() => {
    if (loadingExisting) return;
    // Skip saving før der er noget at gemme
    const hasContent = behov.trim() || sagsnummer.trim() || systemDescription.trim();
    if (!hasContent) return;
    // Skip hvis state er identisk med sidste gem
    const serialized = JSON.stringify(currentState);
    if (serialized === lastSavedRef.current) return;

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      // Bestem gemme-key: brug sagsnummer hvis sat, ellers placeholder
      const saveKey = sagsnummer.trim() || DRAFT_PLACEHOLDER_ID;
      setSaveStatus('saving');
      try {
        const user = typeof window !== 'undefined' ? localStorage.getItem('tyrUser') || undefined : undefined;
        await axios.put(
          `/api/v3/cases/by-case-id/${encodeURIComponent(saveKey)}/intake`,
          { intake_state: currentState, user },
        );
        lastSavedRef.current = serialized;
        setSaveStatus('saved');
        // Refresh drafts-strip hver gang vi gemmer (så ny sag dukker op)
        fetchDrafts();
      } catch (err) {
        console.error('Auto-save failed', err);
        setSaveStatus('error');
      }
    }, 800);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [currentState, loadingExisting, sagsnummer, behov, systemDescription, fetchDrafts]);

  // Editor modal
  const [editorOpen, setEditorOpen] = useState(false);
  const [editorArtifactId, setEditorArtifactId] = useState(null);
  const [evidenceCounter, setEvidenceCounter] = useState(0);

  // Evidence rows status — bruges til checkmarks
  const evidenceCaseKey = sagsnummer.trim() || DRAFT_PLACEHOLDER_ID;
  const [evidenceMap, setEvidenceMap] = useState({});
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await axios.get(`/api/v3/cases/${encodeURIComponent(evidenceCaseKey)}/evidence`);
        if (cancelled) return;
        const m = {};
        (r.data?.items || []).forEach((it) => { m[it.artifact_id] = it; });
        setEvidenceMap(m);
      } catch {
        if (!cancelled) setEvidenceMap({});
      }
    })();
    return () => { cancelled = true; };
  }, [evidenceCaseKey, evidenceCounter]);

  const startNew = () => {
    if (saveStatus === 'saving' || behov.trim() || sagsnummer.trim()) {
      if (!window.confirm('Start ny sag? Dine ufærdige felter gemmes som draft og kan findes i "Mine sager".')) {
        return;
      }
    }
    navigate('/indkoebsproces', { replace: true });
    setStep(1);
    setBehov('');
    setDobbeltsystemTjekket(false);
    setSagsnummer('');
    setServiceportalDato('');
    setIndkoebEllerUdvikling(null);
    setSystemDescription('');
    lastSavedRef.current = null;
    setSaveStatus('idle');
  };

  const openDraft = (caseRow) => {
    navigate(`/indkoebsproces?case_id=${encodeURIComponent(caseRow.case_id)}`);
  };

  const openArtifact = (id) => {
    setEditorArtifactId(id);
    setEditorOpen(true);
  };

  const goVurdering = () => {
    const params = new URLSearchParams({ from: 'indkoeb' });
    if (sagsnummer.trim()) params.set('case_id', sagsnummer.trim());
    navigate(`/vurdering?${params}`);
  };

  return (
    <Page>
      {sagsnummer && (
        <Breadcrumb
          items={[
            { label: 'Sager', to: '/sager' },
            { label: sagsnummer, to: `/sag/${encodeURIComponent(sagsnummer)}` },
            { label: 'Indkøbsproces' },
          ]}
        />
      )}
      <Eyebrow>Bifrost · indkøbsproces</Eyebrow>
      <Title>Indkøb og udvikling af AI-løsninger</Title>
      <Lede>
        4-trins proces der følger Kalundborg Kommunes faktiske workflow.
        Sagen oprettes i Serviceportalen så AI-enheden notificeres, og hvert
        trin viser hvilke skabeloner du skal udfylde. Slutter med en endelig
        vurdering fra AI-enheden + Bifrosts regelmotor.
        <br />
        <strong>Auto-gemmes løbende</strong> — du kan lukke browseren og
        komme tilbage når som helst.
      </Lede>

      <SaveStatus $status={saveStatus}>
        {saveStatus === 'saving' && (<><FaSpinner style={{ animation: 'spin 1s linear infinite' }} /> Gemmer…</>)}
        {saveStatus === 'saved' && (<><FaCheck /> Gemt {sagsnummer ? `som sag ${sagsnummer}` : 'som draft'}</>)}
        {saveStatus === 'error' && (<>⚠ Gem fejlede — prøv igen</>)}
        {saveStatus === 'idle' && !urlCaseId && 'Ny sag — auto-gemmes når du begynder at skrive'}
      </SaveStatus>

      {drafts.length > 0 && (
        <DraftsStrip>
          <div className="strip-head">
            <h3><FaFolderOpen style={{ marginRight: 6, verticalAlign: 'middle' }} /> Mine åbne sager · {drafts.length}</h3>
            <button className="new-link" type="button" onClick={startNew}>+ Start ny sag</button>
          </div>
          <div className="scroll">
            {drafts.map((d) => {
              const intake = d.intake_state || {};
              const pct = progressPct(intake);
              const isActive = sagsnummer === d.case_id;
              return (
                <DraftCard
                  key={d.case_id}
                  $active={isActive}
                  onClick={() => openDraft(d)}
                >
                  <div className="case-id">{d.case_id} · trin {intake.current_step || 1}/4</div>
                  <div className="ttl">{d.title || 'Untitled'}</div>
                  <div className="meta">
                    <span>{new Date(d.updated_at).toLocaleDateString('da-DK')}</span>
                    <span>{pct}% udfyldt</span>
                  </div>
                  <div className="progress-bar">
                    <div className="fill" style={{ width: `${pct}%` }} />
                  </div>
                </DraftCard>
              );
            })}
          </div>
        </DraftsStrip>
      )}

      <Stepper>
        {STEPS.map((s) => {
          const active = step === s.num;
          const done = step > s.num;
          return (
            <StepCell key={s.num} $active={active} $done={done} onClick={() => setStep(s.num)}>
              <span className="num">{done ? <FaCheckCircle /> : s.num}</span>
              <span>
                <span className="label">{s.label}</span>
                <span className="meta">{s.meta}</span>
              </span>
            </StepCell>
          );
        })}
      </Stepper>

      {step === 1 && (
        <Card>
          <h2>Trin 1 — Identificér behov</h2>
          <p className="lede">
            Fagområdet identificerer det behov, AI-løsningen skal opfylde. Overvej
            hvilke sagstyper og processer løsningen skal understøtte. Kommunen har
            stor fokus på nedbringelse af dobbeltsystemer.
          </p>

          <FieldGroup>
            <Field>
              <label htmlFor="behov">
                Behovsbeskrivelse
                <span className="req">*</span>
              </label>
              <div className="hint">
                Hvilken konkret arbejdsopgave/proces skal løsningen understøtte?
                Hvilke fagområder er involveret?
              </div>
              <textarea
                id="behov"
                value={behov}
                onChange={(e) => setBehov(e.target.value)}
                placeholder="Fx: Borgerassistent til pension der kan svare på spørgsmål om pensionsalder..."
              />
            </Field>

            <Field>
              <label>
                Dobbeltsystem-check
                <span className="req">*</span>
              </label>
              <div className="hint">
                Har I tjekket om kommunen allerede har en lignende løsning?
                Konsultér IT-arkitekturen.
              </div>
              <label style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={dobbeltsystemTjekket}
                  onChange={(e) => setDobbeltsystemTjekket(e.target.checked)}
                />
                <span>Ja — jeg har bekræftet at der ikke findes en eksisterende løsning</span>
              </label>
            </Field>
          </FieldGroup>

          <Controls>
            <div className="left">
              <SecondaryButton onClick={startNew}>Nulstil + start ny</SecondaryButton>
            </div>
            <div className="right">
              <PrimaryButton
                disabled={!behov.trim() || !dobbeltsystemTjekket}
                onClick={() => setStep(2)}
              >
                Næste — opret sag <FaArrowRight />
              </PrimaryButton>
            </div>
          </Controls>
        </Card>
      )}

      {step === 2 && (
        <Card>
          <h2>Trin 2 — Opret sag i Serviceportalen</h2>
          <p className="lede">
            Fagområdet opretter en sag i Serviceportalen til AI-enheden. Skriv
            behovsbeskrivelsen + AI-enheden notificeres automatisk.
          </p>

          <InfoBox>
            <strong>Behovsbeskrivelse fra trin 1:</strong>
            <div style={{ marginTop: '0.4rem', fontStyle: 'italic' }}>
              {behov || '(ikke udfyldt — gå tilbage til trin 1)'}
            </div>
          </InfoBox>

          <InfoBox>
            <strong>Sådan gør du:</strong> Gå til Serviceportalen
            (kalundborg.dk → IT → Anmod om service → AI). Beskriv behovet ovenfor.
            Når sagen er oprettet, indsæt sagsnummeret nedenfor — så bliver det
            din persistente sags-ID i Bifrost.
          </InfoBox>

          <FieldGroup>
            <Field>
              <label htmlFor="sagsnummer">
                Sagsnummer fra Serviceportalen
                <span className="req">*</span>
              </label>
              <div className="hint">
                Når du indtaster et sagsnummer, flyttes draft-data til den
                permanente sags-ID. Hvis sagen allerede findes loades dens
                gemte data.
              </div>
              <input
                id="sagsnummer"
                type="text"
                value={sagsnummer}
                onChange={(e) => setSagsnummer(e.target.value)}
                placeholder="K-2026-..."
              />
            </Field>

            <Field>
              <label htmlFor="oprettet_dato">Oprettelsesdato</label>
              <input
                id="oprettet_dato"
                type="date"
                value={serviceportalDato}
                onChange={(e) => setServiceportalDato(e.target.value)}
              />
            </Field>
          </FieldGroup>

          <Controls>
            <div className="left">
              <SecondaryButton onClick={() => setStep(1)}>← Tilbage</SecondaryButton>
            </div>
            <div className="right">
              <PrimaryButton disabled={!sagsnummer.trim()} onClick={() => setStep(3)}>
                Næste — indledende screening <FaArrowRight />
              </PrimaryButton>
            </div>
          </Controls>
        </Card>
      )}

      {step === 3 && (
        <Card>
          <h2>Trin 3 — Indledende screening</h2>
          <p className="lede">
            Vælg om I køber en færdig løsning eller selv udvikler skræddersyet.
            Det påvirker krav til support, opdateringer og overensstemmelse.
          </p>

          <Choice>
            <ChoiceCard
              type="button"
              $active={indkoebEllerUdvikling === 'indkoeb'}
              onClick={() => setIndkoebEllerUdvikling('indkoeb')}
            >
              <span className="icon"><FaShoppingCart /></span>
              <div className="h">Indkøb af færdig løsning</div>
              <div className="desc">
                Løsning købt hos ekstern leverandør. Hurtigere implementation, da
                den allerede er udviklet og testet. Leverandøren står for support og
                opdateringer.
              </div>
            </ChoiceCard>
            <ChoiceCard
              type="button"
              $active={indkoebEllerUdvikling === 'udvikling'}
              onClick={() => setIndkoebEllerUdvikling('udvikling')}
            >
              <span className="icon"><FaCode /></span>
              <div className="h">Skræddersyet udvikling</div>
              <div className="desc">
                Kommunen udvikler selv en løsning efter fagområdets behov. Større
                fleksibilitet, men eget ansvar for vedligeholdelse, sikkerhed og
                AI Act-overensstemmelse.
              </div>
            </ChoiceCard>
          </Choice>

          {indkoebEllerUdvikling && (
            <FieldGroup style={{ marginTop: '1.5rem' }}>
              <Field>
                <label htmlFor="systembeskrivelse">
                  Kort beskrivelse af løsningen
                  <span className="req">*</span>
                </label>
                <div className="hint">
                  Bruges af Bifrosts vurderingsmotor til AI Act-klassificering.
                  Beskriv hvad systemet gør, hvilke data det bruger, og om det
                  træffer afgørelser om personer.
                </div>
                <textarea
                  id="systembeskrivelse"
                  value={systemDescription}
                  onChange={(e) => setSystemDescription(e.target.value)}
                  placeholder="Fx: Borgerassistent baseret på Microsoft Copilot Studio. Træner ikke på persondata, foretager ikke profilering, bruges til informationssøgning..."
                />
              </Field>
            </FieldGroup>
          )}

          <Controls>
            <div className="left">
              <SecondaryButton onClick={() => setStep(2)}>← Tilbage</SecondaryButton>
            </div>
            <div className="right">
              {indkoebEllerUdvikling && (
                <SecondaryButton
                  onClick={() => navigate(`/eu-checker?fromIndkoeb=${encodeURIComponent(sagsnummer)}`)}
                >
                  Kør EU AI Act-tjek →
                </SecondaryButton>
              )}
              <PrimaryButton
                disabled={!indkoebEllerUdvikling || !systemDescription.trim()}
                onClick={() => setStep(4)}
              >
                Næste — udfyld dokumentation <FaArrowRight />
              </PrimaryButton>
            </div>
          </Controls>
        </Card>
      )}

      {step === 4 && (
        <Card>
          <h2>Trin 4 — AI-enheden vurderer</h2>
          <p className="lede">
            Udfyld de relevante artefakter nedenfor. Klik på et artefakt for
            at åbne dets udfyldnings-modal med pre-fyldt skabelon + lovhjemmel.
            Status opdateres automatisk når du gemmer. <strong>Behov + system-
            beskrivelse fra trin 1 og 3 overføres automatisk</strong> når du går
            til vurderingsmotoren.
          </p>

          <InfoBox>
            <strong>Anbefalet rækkefølge:</strong> Start med <em>Tjekliste</em> (giver
            overblik) → <em>DPIA-tærskelsvurdering</em> (afgør om DPIA er nødvendig) →
            <em> DPIA-dokument</em> (kun hvis tærsklen udløst) → <em>Databehandleraftale</em>
            (skal kvalitetstjekkes af IT-sikkerhed@kalundborg.dk) → kør Bifrosts
            vurderingsmotor for endelig GO/BETINGET-GO/NO-GO.
          </InfoBox>

          <ArtifactGrid>
            {ARTIFACTS.map((a) => {
              const row = evidenceMap[a.id];
              const status = row?.status || 'mangler';
              return (
                <ArtifactCard key={a.id} $status={status} onClick={() => openArtifact(a.id)}>
                  <div className="h">
                    <span>{a.id.replace(/_/g, ' ')}</span>
                    <span className="pill">{status === 'faerdig' ? 'Færdig' : status === 'i_gang' ? 'I gang' : 'Mangler'}</span>
                  </div>
                  <div className="desc">{a.desc}</div>
                </ArtifactCard>
              );
            })}
          </ArtifactGrid>

          <Controls style={{ marginTop: '1.5rem' }}>
            <div className="left">
              <SecondaryButton onClick={() => setStep(3)}>← Tilbage</SecondaryButton>
            </div>
            <div className="right">
              {sagsnummer && (
                <>
                  <SecondaryButton
                    onClick={() => downloadCaseReport(sagsnummer, 'docx')}
                    title="Download samlet rapport som Word-dokument"
                  >
                    <FaFileWord /> DOCX
                  </SecondaryButton>
                  <SecondaryButton
                    onClick={() => downloadCaseReport(sagsnummer, 'pdf')}
                    title="Download samlet rapport som print-klar PDF"
                  >
                    <FaFilePdf /> PDF
                  </SecondaryButton>
                </>
              )}
              <PrimaryButton onClick={goVurdering}>
                <FaCloudUploadAlt /> Kør Bifrost-vurdering
              </PrimaryButton>
            </div>
          </Controls>
        </Card>
      )}

      <EvidenceEditor
        open={editorOpen}
        artifactId={editorArtifactId}
        caseId={evidenceCaseKey}
        user={typeof window !== 'undefined' ? localStorage.getItem('tyrUser') || undefined : undefined}
        onClose={() => setEditorOpen(false)}
        onSaved={() => setEvidenceCounter((n) => n + 1)}
      />
    </Page>
  );
};

export default IndkoebsprocesPage;
