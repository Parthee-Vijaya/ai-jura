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
  FaCheck,
  FaFolderOpen,
} from 'react-icons/fa';
import { Breadcrumb } from '../components/ui';

/**
 * IndkoebsprocesPage — 4-trins wizard der matcher Kalundborg Kommunes
 * faktiske workflow for indkøb af AI-løsninger.
 *
 * Før et Serviceportal-ID findes, gemmes kladden lokalt i browseren. Når
 * brugeren bekræfter `case_id`, flyttes hele state til cases.intake_state og
 * auto-gemmes derefter i backend. Dermed opstår der ikke en fælles
 * `__draft__`-sag eller dobbeltregistrering.
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
  cursor: ${(p) => (p.$disabled ? 'not-allowed' : 'pointer')};
  opacity: ${(p) => (p.$disabled ? 0.55 : 1)};
  transition: background 0.15s ease;

  &:hover { background: ${(p) => (p.$disabled ? 'transparent' : p.theme.colors.paperSoft || 'rgba(13,46,84,0.04)')}; }
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
  &:disabled { opacity: 0.5; cursor: not-allowed; }
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
  { num: 4, label: 'Klar til klassifikation', meta: 'Data følger med til resten af processen' },
];

const LOCAL_DRAFT_KEY = 'bifrost-indkoeb-local-draft-v1';
const LEGACY_DRAFT_ID = '__draft__';

function readLocalDraft() {
  if (typeof window === 'undefined') return {};
  try {
    return JSON.parse(localStorage.getItem(LOCAL_DRAFT_KEY) || '{}');
  } catch {
    return {};
  }
}

function writeLocalDraft(state) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(LOCAL_DRAFT_KEY, JSON.stringify(state));
}

function clearLocalDraft() {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(LOCAL_DRAFT_KEY);
}

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

// ---- Component -----------------------------------------------------------

const IndkoebsprocesPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const urlCaseId = searchParams.get('case_id');
  // Lazy state initialization hydrates exactly once. URL changes are handled
  // separately by the load effect below.
  const [initialDraft] = useState(() => (!urlCaseId ? readLocalDraft() : {}));

  // Wizard state
  const [step, setStep] = useState(initialDraft.current_step || 1);
  const [behov, setBehov] = useState(initialDraft.behov || '');
  const [dobbeltsystemTjekket, setDobbeltsystemTjekket] = useState(
    !!initialDraft.dobbeltsystem_tjekket,
  );
  const [sagsnummer, setSagsnummer] = useState(
    urlCaseId && urlCaseId !== LEGACY_DRAFT_ID
      ? urlCaseId
      : initialDraft.sagsnummer || '',
  );
  const [serviceportalDato, setServiceportalDato] = useState(
    initialDraft.serviceportal_dato || '',
  );
  const [indkoebEllerUdvikling, setIndkoebEllerUdvikling] = useState(
    initialDraft.indkoeb_eller_udvikling || null,
  );
  const [systemName, setSystemName] = useState(initialDraft.system_name || '');
  const [systemDescription, setSystemDescription] = useState(
    initialDraft.system_description || '',
  );
  const [caseConfirmed, setCaseConfirmed] = useState(
    Boolean(urlCaseId && urlCaseId !== LEGACY_DRAFT_ID),
  );
  const [existingCaseConflict, setExistingCaseConflict] = useState(null);

  // AI-assist state (E2.1)
  const [aiAssisting, setAiAssisting] = useState(false);
  const [aiAssistError, setAiAssistError] = useState(null);

  const runAIAssist = async () => {
    if (!systemDescription.trim() || systemDescription.trim().length < 20) {
      setAiAssistError('Beskrivelse skal være mindst 20 tegn');
      return;
    }
    setAiAssisting(true);
    setAiAssistError(null);
    try {
      const r = await axios.post('/api/v3/intake/ai-assist', {
        description: systemDescription,
      });
      const intake = r.data?.intake || {};
      // Anvend kun til felter der er tomme — bevarer bruger-input
      if (intake.behov && !behov.trim()) setBehov(intake.behov);
      if (intake.indkoeb_eller_udvikling && !indkoebEllerUdvikling) {
        setIndkoebEllerUdvikling(intake.indkoeb_eller_udvikling);
      }
      // system_description erstattes ikke, men kan udvides via prompt
    } catch (err) {
      setAiAssistError(err?.response?.data?.error?.message || err?.message || 'AI-assist fejlede');
    } finally {
      setAiAssisting(false);
    }
  };

  // Backend persistence state
  const [saveStatus, setSaveStatus] = useState(
    Object.keys(initialDraft).length > 0 ? 'saved-local' : 'idle',
  ); // idle | saving | saved-local | saved | error
  const [loadingExisting, setLoadingExisting] = useState(!!urlCaseId);
  const debounceRef = useRef(null);
  const lastSavedRef = useRef(null);
  // Felter fra senere faser (fx ec_flags/ec_completed_at) må ikke gå tabt,
  // når brugeren vender tilbage og retter intake-oplysninger.
  const preservedIntakeRef = useRef({});

  // Drafts strip
  const [drafts, setDrafts] = useState([]);
  const fetchDrafts = useCallback(async () => {
    try {
      const r = await axios.get('/api/v3/cases/drafts');
      setDrafts((r.data?.items || []).filter((item) => item.case_id !== LEGACY_DRAFT_ID));
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
    setLoadingExisting(true);
    let cancelled = false;
    (async () => {
      try {
        const r = await axios.get(`/api/v3/cases/by-case-id/${encodeURIComponent(urlCaseId)}`);
        if (cancelled) return;
        const intake = r.data?.intake_state || {};
        setExistingCaseConflict(null);
        preservedIntakeRef.current = { ...intake };
        setStep(intake.current_step || 1);
        setBehov(intake.behov || '');
        setDobbeltsystemTjekket(!!intake.dobbeltsystem_tjekket);
        setSagsnummer(urlCaseId === LEGACY_DRAFT_ID ? '' : urlCaseId);
        setServiceportalDato(intake.serviceportal_dato || '');
        setIndkoebEllerUdvikling(intake.indkoeb_eller_udvikling || null);
        setSystemName(intake.system_name || '');
        setSystemDescription(intake.system_description || '');
        setCaseConfirmed(urlCaseId !== LEGACY_DRAFT_ID);
        lastSavedRef.current = JSON.stringify(intake);
        if (urlCaseId === LEGACY_DRAFT_ID) {
          const recovered = { ...intake, sagsnummer: '' };
          writeLocalDraft(recovered);
          navigate('/indkoebsproces', { replace: true });
          setSaveStatus('saved-local');
        }
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
  }, [navigate, urlCaseId]);

  // Debounced auto-save
  const currentState = useMemo(
    () => ({
      ...preservedIntakeRef.current,
      current_step: step,
      behov,
      dobbeltsystem_tjekket: dobbeltsystemTjekket,
      sagsnummer,
      serviceportal_dato: serviceportalDato,
      indkoeb_eller_udvikling: indkoebEllerUdvikling,
      system_name: systemName,
      system_description: systemDescription,
    }),
    [step, behov, dobbeltsystemTjekket, sagsnummer, serviceportalDato,
      indkoebEllerUdvikling, systemName, systemDescription],
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
      setSaveStatus('saving');
      if (!caseConfirmed) {
        writeLocalDraft(currentState);
        lastSavedRef.current = serialized;
        setSaveStatus('saved-local');
        return;
      }
      try {
        const user = typeof window !== 'undefined' ? localStorage.getItem('tyrUser') || undefined : undefined;
        await axios.put(
          `/api/v3/cases/by-case-id/${encodeURIComponent(sagsnummer.trim())}/intake`,
          { intake_state: currentState, user },
        );
        clearLocalDraft();
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
  }, [caseConfirmed, currentState, loadingExisting, sagsnummer, behov,
    systemDescription, fetchDrafts]);

  const startNew = () => {
    if (saveStatus === 'saving' || behov.trim() || sagsnummer.trim()) {
      if (!window.confirm('Start ny sag? Den lokale kladde nulstilles. Allerede oprettede sager bevares i "Mine sager".')) {
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
    setSystemName('');
    setSystemDescription('');
    setCaseConfirmed(false);
    setExistingCaseConflict(null);
    preservedIntakeRef.current = {};
    clearLocalDraft();
    lastSavedRef.current = null;
    setSaveStatus('idle');
  };

  const openDraft = (caseRow) => {
    navigate(`/indkoebsproces?case_id=${encodeURIComponent(caseRow.case_id)}`);
  };

  const confirmCaseAndContinue = async () => {
    if (caseConfirmed) {
      setStep(3);
      return;
    }
    const confirmedId = sagsnummer.trim();
    if (!confirmedId) return;
    const nextState = { ...currentState, current_step: 3, sagsnummer: confirmedId };
    setSaveStatus('saving');
    try {
      const existing = await axios
        .get(`/api/v3/cases/by-case-id/${encodeURIComponent(confirmedId)}`)
        .then((response) => response.data)
        .catch((err) => {
          if (err?.response?.status === 404) return null;
          throw err;
        });
      if (existing) {
        setExistingCaseConflict(existing);
        setSaveStatus('saved-local');
        return;
      }
      const user = typeof window !== 'undefined'
        ? localStorage.getItem('tyrUser') || undefined
        : undefined;
      await axios.put(
        `/api/v3/cases/by-case-id/${encodeURIComponent(confirmedId)}/intake`,
        { intake_state: nextState, user },
      );
      clearLocalDraft();
      lastSavedRef.current = JSON.stringify(nextState);
      setCaseConfirmed(true);
      setStep(3);
      setSaveStatus('saved');
      navigate(`/indkoebsproces?case_id=${encodeURIComponent(confirmedId)}`, {
        replace: true,
      });
      fetchDrafts();
    } catch (err) {
      console.error('Case confirmation failed', err);
      setSaveStatus('error');
    }
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
        Fire korte intake-trin der følger Kalundborg Kommunes workflow.
        Her registrerer du behovet og sagen én gang; oplysningerne følger
        automatisk videre til EU-klassifikation, juridisk vurdering,
        risiko/evidens og den menneskelige godkendelse.
        <br />
        <strong>Auto-gemmes løbende</strong> — du kan lukke browseren og
        komme tilbage når som helst.
      </Lede>

      <SaveStatus $status={saveStatus}>
        {saveStatus === 'saving' && (<><FaSpinner style={{ animation: 'spin 1s linear infinite' }} /> Gemmer…</>)}
        {saveStatus === 'saved' && (<><FaCheck /> Gemt {sagsnummer ? `som sag ${sagsnummer}` : 'som draft'}</>)}
        {saveStatus === 'saved-local' && (<><FaCheck /> Gemt lokalt som kladde — får permanent sags-ID i trin 2</>)}
        {saveStatus === 'error' && (<>⚠ Gem fejlede — prøv igen</>)}
        {saveStatus === 'idle' && !urlCaseId && 'Ny sag — gemmes lokalt indtil sags-ID er oprettet'}
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
          const canOpen = s.num === 1
            || (s.num === 2 && Boolean(behov.trim() && dobbeltsystemTjekket))
            || (s.num === 3 && caseConfirmed)
            || (s.num === 4 && caseConfirmed && Boolean(
              indkoebEllerUdvikling && systemDescription.trim(),
            ));
          return (
            <StepCell
              key={s.num}
              $active={active}
              $done={done}
              $disabled={!canOpen}
              role="button"
              tabIndex={canOpen ? 0 : -1}
              aria-disabled={!canOpen}
              onClick={() => canOpen && setStep(s.num)}
              onKeyDown={(event) => {
                if (canOpen && (event.key === 'Enter' || event.key === ' ')) {
                  event.preventDefault();
                  setStep(s.num);
                }
              }}
            >
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
                Næste — registrér sags-ID <FaArrowRight />
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
                Når du bekræfter sagsnummeret, gemmes alle hidtidige svar samlet
                på den permanente sag. Et bekræftet sags-ID låses for at undgå
                dubletter.
              </div>
              <input
                id="sagsnummer"
                type="text"
                value={sagsnummer}
                onChange={(e) => {
                  setSagsnummer(e.target.value);
                  setExistingCaseConflict(null);
                }}
                disabled={caseConfirmed}
                placeholder="K-2026-..."
              />
            </Field>

            {existingCaseConflict && (
              <InfoBox role="alert">
                <strong>Sags-ID'et findes allerede.</strong>{' '}
                Den lokale kladde er ikke overskrevet. Åbn den eksisterende sag,
                eller indtast et andet sags-ID.
                <div style={{ marginTop: '0.65rem' }}>
                  <SecondaryButton
                    type="button"
                    onClick={() => navigate(
                      `/indkoebsproces?case_id=${encodeURIComponent(existingCaseConflict.case_id)}`,
                    )}
                  >
                    Åbn {existingCaseConflict.case_id}
                  </SecondaryButton>
                </div>
              </InfoBox>
            )}

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
              <PrimaryButton disabled={!sagsnummer.trim()} onClick={confirmCaseAndContinue}>
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
                <label htmlFor="systemnavn">Systemnavn eller arbejdstitel</label>
                <div className="hint">
                  Valgfrit. Navnet genbruges automatisk i risikovurdering,
                  rapporter og sagens overblik.
                </div>
                <input
                  id="systemnavn"
                  type="text"
                  value={systemName}
                  onChange={(e) => setSystemName(e.target.value)}
                  placeholder="Fx Borgerassistent Pension"
                />
              </Field>
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
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    onClick={runAIAssist}
                    disabled={aiAssisting || systemDescription.trim().length < 20}
                    style={{
                      background: 'transparent',
                      color: '#0d2e54',
                      border: '1px solid #0d2e54',
                      borderRadius: 4,
                      padding: '0.45rem 0.85rem',
                      cursor: aiAssisting ? 'wait' : 'pointer',
                      fontSize: '0.82rem',
                      fontFamily: 'inherit',
                      opacity: (aiAssisting || systemDescription.trim().length < 20) ? 0.5 : 1,
                    }}
                    title="LLM ekstraherer behov, indkøb-vs-udvikling og andre felter fra beskrivelsen — fylder kun tomme felter"
                  >
                    {aiAssisting ? '⏳ Analyserer…' : '✨ Auto-udfyld med AI'}
                  </button>
                  {aiAssistError && (
                    <span style={{ color: '#a02020', fontSize: '0.78rem' }}>
                      {aiAssistError}
                    </span>
                  )}
                  {!aiAssistError && !aiAssisting && (
                    <span style={{ color: '#5b6573', fontSize: '0.75rem', fontStyle: 'italic' }}>
                      AI udfylder kun tomme felter — dine svar bevares
                    </span>
                  )}
                </div>
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
                  disabled={!systemDescription.trim()}
                  onClick={() => navigate(`/eu-checker?fromIndkoeb=${encodeURIComponent(sagsnummer)}`)}
                >
                  Kør EU AI Act-tjek →
                </SecondaryButton>
              )}
              <PrimaryButton
                disabled={!indkoebEllerUdvikling || !systemDescription.trim()}
                onClick={() => setStep(4)}
              >
                Næste — gennemgå data <FaArrowRight />
              </PrimaryButton>
            </div>
          </Controls>
        </Card>
      )}

      {step === 4 && (
        <Card>
          <h2>Trin 4 — Klar til klassifikation</h2>
          <p className="lede">
            Grundlaget er nu samlet på sagen. De næste faser genbruger samme
            sags-ID, behov, systemnavn og beskrivelse, så du ikke skal skrive
            oplysningerne igen.
          </p>

          <InfoBox>
            <strong>Sag:</strong> {sagsnummer}<br />
            <strong>System:</strong> {systemName || 'Arbejdstitel ikke angivet'}<br />
            <strong>Behov:</strong> {behov}<br />
            <strong>Løsning:</strong> {systemDescription}
          </InfoBox>

          <InfoBox>
            <strong>Næste:</strong> EU AI Act-tjekket klassificerer anvendelsen.
            Derefter anvender Bifrost resultatet i den juridiske vurdering og
            viser kun den dokumentation og evidens, der faktisk er relevant.
          </InfoBox>

          <Controls style={{ marginTop: '1.5rem' }}>
            <div className="left">
              <SecondaryButton onClick={() => setStep(3)}>← Tilbage</SecondaryButton>
            </div>
            <div className="right">
              <SecondaryButton
                onClick={() => navigate(`/proces?case_id=${encodeURIComponent(sagsnummer)}&step=indkoeb`)}
              >
                Åbn samlet proces
              </SecondaryButton>
              <PrimaryButton
                onClick={() => navigate(`/eu-checker?fromIndkoeb=${encodeURIComponent(sagsnummer)}&fromProces=1`)}
              >
                Start EU AI Act-tjek <FaArrowRight />
              </PrimaryButton>
            </div>
          </Controls>
        </Card>
      )}
    </Page>
  );
};

export default IndkoebsprocesPage;
