import React, { useEffect, useMemo, useState } from 'react';
import styled from 'styled-components';
import axios from 'axios';
import { FaTimes, FaCheck, FaExternalLinkAlt, FaSpinner, FaPrint, FaSearch, FaExclamationTriangle, FaInfoCircle, FaLightbulb } from 'react-icons/fa';

import { useToast } from '../ui';
import SkabelonPicker from '../SkabelonPicker';
import EvidenceComments from '../EvidenceComments';

/**
 * EvidenceEditor — modal til at udfylde et enkelt evidens-artefakt direkte
 * i Bifrost.
 *
 * Henter:
 *   - GET /api/v3/evidence/templates/{artifact_id}  → skabelon (sections, lov, links)
 *   - GET /api/v3/cases/{case_id}/evidence          → eksisterende svar (hvis nogen)
 *
 * Gemmer:
 *   - PUT /api/v3/cases/{case_id}/evidence/{artifact_id}
 *
 * Status beregnes server-side. Når response.status === 'faerdig' lukker
 * modalen automatisk og kalder onSaved(artifact_id, status) → checkmark
 * bliver grønt i den underliggende EvidenceChecklist.
 *
 * Props:
 *   open: bool — om modalen vises
 *   artifactId: string — fx 'risikostyringsplan'
 *   caseId: string — sagsidentifier (auto-derived hvis tom)
 *   user: string | undefined — for audit-trail
 *   onClose: () => void — luk uden at gemme
 *   onSaved: (artifactId, status) => void — efter succesfuld save
 */

// ---- Styles -------------------------------------------------------------

const Backdrop = styled.div`
  position: fixed;
  inset: 0;
  background: rgba(20, 24, 31, 0.55);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 4vh 1rem;
  z-index: 1000;
  overflow-y: auto;
`;

const Sheet = styled.div`
  background: ${(p) => p.theme.colors.paper};
  width: 100%;
  max-width: 880px;
  border-radius: 10px;
  border: 1px solid ${(p) => p.theme.colors.line};
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
  display: flex;
  flex-direction: column;
  max-height: 92vh;
`;

const Header = styled.div`
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 1.5rem 1.75rem 1rem;
  border-bottom: 1px solid ${(p) => p.theme.colors.line};
  position: relative;

  &::before {
    content: '';
    position: absolute;
    top: -1px;
    left: 1.75rem;
    right: 1.75rem;
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
    font-size: 1.45rem;
    font-weight: 600;
    margin: 0 0 0.35rem;
    color: ${(p) => p.theme.colors.ink};
    letter-spacing: -0.012em;
  }

  .summary {
    font-family: ${(p) => p.theme.fonts.body};
    font-size: 0.95rem;
    color: ${(p) => p.theme.colors.inkSoft};
    line-height: 1.55;
    margin: 0;
  }
`;

const CloseButton = styled.button`
  background: transparent;
  border: none;
  color: ${(p) => p.theme.colors.inkFaded};
  font-size: 1.1rem;
  cursor: pointer;
  margin-left: 1rem;
  padding: 0.35rem;
  border-radius: 4px;

  &:hover {
    background: ${(p) => p.theme.colors.paperSoft || 'rgba(0,0,0,0.04)'};
    color: ${(p) => p.theme.colors.ink};
  }
`;

const Body = styled.div`
  padding: 1.4rem 1.75rem;
  overflow-y: auto;
  flex: 1;
`;

const LegalSection = styled.section`
  background: ${(p) => p.theme.colors.paperSoft || 'rgba(13,46,84,0.04)'};
  border-left: 3px solid ${(p) => p.theme.colors.bronze};
  padding: 0.9rem 1.1rem;
  border-radius: 0 6px 6px 0;
  margin-bottom: 1.4rem;

  .heading {
    font-family: ${(p) => p.theme.fonts.sans};
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: ${(p) => p.theme.colors.bronze};
    font-weight: 700;
    margin-bottom: 0.4rem;
  }

  .ref {
    font-family: ${(p) => p.theme.fonts.body};
    font-size: 0.88rem;
    color: ${(p) => p.theme.colors.ink};
    margin-bottom: 0.5rem;
    line-height: 1.55;

    .lov {
      font-weight: 600;
    }

    .citat {
      display: block;
      font-style: italic;
      color: ${(p) => p.theme.colors.inkSoft};
      margin-top: 0.2rem;
      padding-left: 0.5rem;
      border-left: 2px solid ${(p) => p.theme.colors.line};
    }

    a {
      color: ${(p) => p.theme.colors.primary};
      font-size: 0.78rem;
      margin-left: 0.4rem;
      text-decoration: none;
      &:hover { text-decoration: underline; }
    }
  }
`;

const ResourcesSection = styled.section`
  background: ${(p) => p.theme.colors.card};
  border: 1px solid ${(p) => p.theme.colors.line};
  border-radius: 6px;
  padding: 0.85rem 1.1rem;
  margin-bottom: 1.6rem;

  .heading {
    font-family: ${(p) => p.theme.fonts.sans};
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: ${(p) => p.theme.colors.inkSoft};
    font-weight: 600;
    margin-bottom: 0.45rem;
  }

  ul {
    margin: 0;
    padding-left: 1.1rem;
  }

  li {
    font-family: ${(p) => p.theme.fonts.body};
    font-size: 0.85rem;
    color: ${(p) => p.theme.colors.ink};
    margin-bottom: 0.35rem;
    line-height: 1.45;

    a {
      color: ${(p) => p.theme.colors.primary};
      text-decoration: none;
      font-weight: 500;
      &:hover { text-decoration: underline; }
    }

    .pub {
      font-size: 0.78rem;
      color: ${(p) => p.theme.colors.inkSoft};
      margin-left: 0.3rem;
    }
  }
`;

const SectionField = styled.div`
  margin-bottom: 1.5rem;

  .label-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 0.35rem;
  }

  label {
    font-family: ${(p) => p.theme.fonts.sans};
    font-size: 0.92rem;
    font-weight: 600;
    color: ${(p) => p.theme.colors.ink};

    .req {
      color: #a03612;
      margin-left: 0.25rem;
      font-weight: 700;
    }
  }

  .filled-pill {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.7rem;
    color: ${(p) => p.theme.colors.inkFaded};
    text-transform: uppercase;
    letter-spacing: 0.06em;

    &.is-filled { color: #2d6a31; }
    &.is-empty-required { color: #a03612; }
  }

  .prompt {
    font-family: ${(p) => p.theme.fonts.body};
    font-size: 0.85rem;
    color: ${(p) => p.theme.colors.inkSoft};
    margin-bottom: 0.5rem;
    line-height: 1.5;
    font-style: italic;
  }

  textarea, input, select {
    width: 100%;
    padding: 0.65rem 0.85rem;
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

  textarea {
    min-height: 110px;
    resize: vertical;
    font-family: ${(p) => p.theme.fonts.body};
  }
`;

const Footer = styled.div`
  border-top: 1px solid ${(p) => p.theme.colors.line};
  padding: 1rem 1.75rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;

  .progress {
    font-family: ${(p) => p.theme.fonts.sans};
    font-size: 0.82rem;
    color: ${(p) => p.theme.colors.inkSoft};

    strong {
      color: ${(p) => (p.$ready ? '#2d6a31' : '#a03612')};
    }
  }

  .actions {
    display: flex;
    gap: 0.6rem;
    align-items: center;
  }
`;

const PrimaryButton = styled.button`
  background: ${(p) => p.theme.colors.primary};
  color: white;
  border: none;
  padding: 0.65rem 1.25rem;
  border-radius: 5px;
  font-family: ${(p) => p.theme.fonts.sans};
  font-weight: 600;
  font-size: 0.9rem;
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
  padding: 0.6rem 1rem;
  border-radius: 5px;
  font-family: ${(p) => p.theme.fonts.sans};
  font-weight: 500;
  font-size: 0.88rem;
  cursor: pointer;
  &:hover { border-color: ${(p) => p.theme.colors.primary}; color: ${(p) => p.theme.colors.primary}; }
`;

const StatusBanner = styled.div`
  background: ${(p) =>
    p.$status === 'faerdig'
      ? 'rgba(45, 106, 49, 0.08)'
      : p.$status === 'i_gang'
      ? 'rgba(176, 138, 74, 0.1)'
      : 'rgba(160, 54, 18, 0.06)'};
  border-left: 3px solid
    ${(p) =>
      p.$status === 'faerdig'
        ? '#2d6a31'
        : p.$status === 'i_gang'
        ? '#b08a4a'
        : '#a03612'};
  border-radius: 0 4px 4px 0;
  padding: 0.6rem 0.9rem;
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.85rem;
  color: ${(p) => p.theme.colors.ink};
  margin-bottom: 1.2rem;
`;

const Spinner = styled(FaSpinner)`
  animation: spin 1s linear infinite;
  @keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }
`;

const ReviewPanel = styled.section`
  background: ${(p) => p.theme.colors.paperSoft || 'rgba(13,46,84,0.04)'};
  border: 1px solid ${(p) => p.theme.colors.line};
  border-left: 4px solid ${(p) => {
    const s = p.$score || 3;
    if (s >= 4) return '#2d6a31';
    if (s >= 3) return '#b08a4a';
    return '#a03612';
  }};
  border-radius: 6px;
  padding: 1rem 1.15rem;
  margin-bottom: 1.6rem;

  .header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 0.6rem;
    flex-wrap: wrap;
  }

  .title {
    font-family: ${(p) => p.theme.fonts.sans};
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-weight: 700;
    color: ${(p) => p.theme.colors.bronze};
    display: flex;
    align-items: center;
    gap: 0.45rem;
  }

  .score {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 1.1rem;
    font-weight: 700;
    color: ${(p) => {
      const s = p.$score || 3;
      if (s >= 4) return '#2d6a31';
      if (s >= 3) return '#6e5527';
      return '#a03612';
    }};
    background: ${(p) => p.theme.colors.paper};
    border: 1px solid ${(p) => p.theme.colors.line};
    border-radius: 4px;
    padding: 0.2rem 0.55rem;
    display: inline-flex;
    align-items: baseline;
    gap: 0.2rem;

    .max {
      font-size: 0.75rem;
      color: ${(p) => p.theme.colors.inkFaded};
      font-weight: 400;
    }
  }

  .summary {
    font-family: ${(p) => p.theme.fonts.body};
    font-size: 0.9rem;
    color: ${(p) => p.theme.colors.ink};
    line-height: 1.55;
    margin-bottom: 0.85rem;
  }

  .section-block {
    margin-top: 0.7rem;

    h4 {
      font-family: ${(p) => p.theme.fonts.sans};
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: ${(p) => p.theme.colors.inkSoft};
      font-weight: 600;
      margin: 0 0 0.35rem;
    }

    ul {
      margin: 0;
      padding-left: 0;
      list-style: none;
    }

    li {
      font-family: ${(p) => p.theme.fonts.body};
      font-size: 0.86rem;
      color: ${(p) => p.theme.colors.ink};
      line-height: 1.5;
      padding: 0.35rem 0.5rem;
      margin-bottom: 0.3rem;
      border-radius: 4px;
      display: flex;
      align-items: flex-start;
      gap: 0.45rem;
      background: ${(p) => p.theme.colors.paper};

      &.sev-blocker {
        border-left: 3px solid #a03612;
        color: ${(p) => p.theme.colors.ink};
      }
      &.sev-warning {
        border-left: 3px solid #b08a4a;
      }
      &.sev-tip {
        border-left: 3px solid #6c8ab3;
      }

      .icon {
        flex-shrink: 0;
        margin-top: 0.15rem;
        font-size: 0.85rem;
      }

      .sev-blocker .icon { color: #a03612; }

      .section-tag {
        font-family: ${(p) => p.theme.fonts.mono};
        font-size: 0.72rem;
        color: ${(p) => p.theme.colors.inkFaded};
        margin-right: 0.4rem;
      }
    }
  }

  .dismiss {
    background: transparent;
    border: none;
    color: ${(p) => p.theme.colors.inkFaded};
    cursor: pointer;
    padding: 0.2rem 0.4rem;
    font-size: 0.85rem;
    &:hover { color: ${(p) => p.theme.colors.ink}; }
  }
`;

// ---- Component -----------------------------------------------------------

const STATUS_LABEL = {
  mangler: 'Mangler',
  i_gang: 'Undervejs',
  faerdig: 'Færdig',
  godkendt: 'Godkendt',
};

const EvidenceEditor = ({
  open,
  artifactId,
  caseId,
  user,
  onClose,
  onSaved,
}) => {
  const [template, setTemplate] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [content, setContent] = useState({});
  const [saving, setSaving] = useState(false);
  const [savedStatus, setSavedStatus] = useState(null);
  const [generatingDraft, setGeneratingDraft] = useState(false);
  const [aiDraftedKeys, setAiDraftedKeys] = useState(new Set());
  const [qualityReview, setQualityReview] = useState(null);
  const [reviewing, setReviewing] = useState(false);
  const [reviewError, setReviewError] = useState(null);
  const [autoReviewedFor, setAutoReviewedFor] = useState(null); // status hvor vi sidst auto-review'ede
  const toast = useToast();

  const runQualityReview = async ({ silent = false } = {}) => {
    if (!caseId || !artifactId) return null;
    setReviewing(true);
    setReviewError(null);
    try {
      const res = await axios.post(
        `/api/v3/cases/${encodeURIComponent(caseId)}/evidence/${encodeURIComponent(artifactId)}/quality-review`,
        { content },
      );
      const rev = res.data?.review || null;
      setQualityReview(rev);
      if (!silent && rev) {
        const score = rev.quality_score;
        if (score >= 4) {
          toast.success(`Kvalitetstjek: ${score}/5 — solid evidens`);
        } else if (score >= 3) {
          toast.info(`Kvalitetstjek: ${score}/5 — se forslag i panelet`);
        } else {
          toast.warning?.(`Kvalitetstjek: ${score}/5 — flere blockers fundet`) || toast.error(`Kvalitetstjek: ${score}/5 — flere blockers fundet`);
        }
      }
      return rev;
    } catch (err) {
      const msg = err?.response?.data?.error?.message || err?.message || 'Review fejlede';
      setReviewError(msg);
      if (!silent) toast.error(`AI-kvalitetstjek fejlede: ${msg}`);
      return null;
    } finally {
      setReviewing(false);
    }
  };

  const handleGenerateDraft = async () => {
    if (!caseId || !artifactId) return;
    setGeneratingDraft(true);
    try {
      const res = await axios.post(
        `/api/v3/cases/${encodeURIComponent(caseId)}/evidence/${encodeURIComponent(artifactId)}/generate-draft`,
        { existing_content: content },
      );
      const drafts = res.data?.drafts || {};
      const filledCount = Object.keys(drafts).length;
      if (filledCount === 0) {
        toast.info('Ingen tomme sektioner at udfylde — alle required er allerede besvaret');
      } else {
        // Merge ind i content (overskriver IKKE — backend filtrerer)
        setContent((prev) => ({ ...prev, ...drafts }));
        setAiDraftedKeys((prev) => {
          const next = new Set(prev);
          Object.keys(drafts).forEach((k) => next.add(k));
          return next;
        });
        toast.success(`${filledCount} sektion${filledCount === 1 ? '' : 'er'} fyldt med AI-udkast — review før gem`);
      }
    } catch (err) {
      toast.error(`AI-udkast fejlede: ${err?.response?.data?.error?.message || err?.message}`);
    } finally {
      setGeneratingDraft(false);
    }
  };

  // Load template + existing content when modal opens
  useEffect(() => {
    if (!open || !artifactId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setQualityReview(null);
    setReviewError(null);
    setAutoReviewedFor(null);
    setAiDraftedKeys(new Set());
    (async () => {
      try {
        const tmplRes = await axios.get(
          `/api/v3/evidence/templates/${encodeURIComponent(artifactId)}`,
        );
        if (cancelled) return;
        setTemplate(tmplRes.data);

        // Try to load existing content
        let existing = null;
        if (caseId) {
          try {
            const evRes = await axios.get(
              `/api/v3/cases/${encodeURIComponent(caseId)}/evidence`,
            );
            const found = (evRes.data?.items || []).find(
              (it) => it.artifact_id === artifactId,
            );
            existing = found?.content || null;
            setSavedStatus(found?.status || null);
          } catch {
            // no existing content; that's fine
          }
        }

        // Initialize editable content from existing or default_text
        const init = {};
        for (const s of tmplRes.data.sections || []) {
          if (existing && Object.prototype.hasOwnProperty.call(existing, s.key)) {
            init[s.key] = existing[s.key];
          } else if (s.default_text != null) {
            init[s.key] = s.default_text;
          } else if (s.field_type === 'boolean') {
            init[s.key] = undefined;
          } else {
            init[s.key] = '';
          }
        }
        setContent(init);
      } catch (err) {
        if (cancelled) return;
        setError(err?.response?.data?.detail || err?.message || 'Kunne ikke hente skabelon');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [open, artifactId, caseId]);

  const requiredKeys = useMemo(
    () => (template?.sections || []).filter((s) => s.required).map((s) => s.key),
    [template],
  );
  const filledRequired = useMemo(
    () => requiredKeys.filter((k) => isFilled(content[k])),
    [requiredKeys, content],
  );
  const allRequiredFilled = requiredKeys.length === filledRequired.length;

  const handleSave = async () => {
    if (!template || !caseId) return;
    setSaving(true);
    setError(null);
    // Optimistic UI: vis straks at vi gemmer (toast udløses ved svar)
    try {
      const res = await axios.put(
        `/api/v3/cases/${encodeURIComponent(caseId)}/evidence/${encodeURIComponent(artifactId)}`,
        { content, user },
      );
      setSavedStatus(res.data.status);
      // Notify parent so checklist can re-fetch
      if (onSaved) onSaved(artifactId, res.data.status);

      // Toast med kontekst-besked baseret på resulterende status
      const title = template?.title || artifactId;
      if (res.data.status === 'faerdig') {
        toast.success(`${title} markeret som færdig`, { link: `/sag/${encodeURIComponent(caseId)}?tab=evidens`, linkLabel: 'Se sag →' });
      } else if (res.data.status === 'godkendt') {
        toast.success(`${title} godkendt`, { link: `/sag/${encodeURIComponent(caseId)}?tab=evidens`, linkLabel: 'Se sag →' });
      } else if (res.data.status === 'i_gang') {
        toast.info(`${title} gemt — fortsæt udfyldelse`);
      } else {
        toast.info(`${title} gemt`);
      }

      // Auto-trigger AI quality review når status netop blev "faerdig"
      // (kun første gang pr. modal-session — bruger kan altid trigge manuelt igen)
      if (
        res.data.status === 'faerdig' &&
        autoReviewedFor !== 'faerdig'
      ) {
        setAutoReviewedFor('faerdig');
        // Fire-and-forget — bruger ser panelet når review er klar
        runQualityReview({ silent: true }).then((rev) => {
          if (rev && rev.quality_score < 4) {
            toast.info(
              `AI-kvalitetstjek (${rev.quality_score}/5): ${rev.issues?.length || 0} issues — se panelet før godkendelse`,
            );
          }
        });
        // BLIV i modal så bruger kan se review-feedback
        return;
      }

      // Close automatically on completion (godkendt or already-reviewed faerdig)
      if (res.data.status === 'godkendt') {
        setTimeout(onClose, 600);
      }
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || 'Kunne ikke gemme';
      setError(msg);
      toast.error(`Gem fejlede: ${msg}`);
    } finally {
      setSaving(false);
    }
  };

  if (!open) return null;

  return (
    <Backdrop onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <Sheet onClick={(e) => e.stopPropagation()}>
        <Header>
          <div style={{ flex: 1 }}>
            <h2>{template?.title || (loading ? 'Indlæser…' : artifactId)}</h2>
            {template && <p className="summary">{template.summary}</p>}
          </div>
          <CloseButton onClick={onClose} aria-label="Luk">
            <FaTimes />
          </CloseButton>
        </Header>

        <Body>
          {loading && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', color: '#666' }}>
              <Spinner /> Henter skabelon og eksisterende svar…
            </div>
          )}

          {error && (
            <div style={{ color: '#a02020', padding: '0.5rem 0', fontFamily: 'monospace', fontSize: '0.86rem' }}>
              {error}
            </div>
          )}

          {savedStatus && (
            <StatusBanner $status={savedStatus}>
              <strong>Status:</strong> {STATUS_LABEL[savedStatus] || savedStatus}
              {savedStatus === 'faerdig' && ' ✓ — alle påkrævede felter udfyldt'}
            </StatusBanner>
          )}

          {reviewing && !qualityReview && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: '0.6rem',
              padding: '0.7rem 0.9rem', marginBottom: '1.2rem',
              background: 'rgba(13,46,84,0.04)', border: '1px solid #e5e7eb',
              borderRadius: '6px', fontSize: '0.88rem', color: '#374151',
              fontFamily: 'inherit',
            }}>
              <Spinner /> AI gennemgår din evidens for blockers, mangler og forbedringsforslag…
            </div>
          )}

          {qualityReview && (
            <ReviewPanel $score={qualityReview.quality_score}>
              <div className="header-row">
                <div className="title">
                  <FaSearch /> AI-kvalitetstjek
                  <span style={{ fontWeight: 400, fontSize: '0.75rem', textTransform: 'none', letterSpacing: 'normal', color: '#666' }}>
                    · vejledende — jurist har det endelige ord
                  </span>
                </div>
                <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
                  <span className="score">
                    {qualityReview.quality_score}<span className="max">/5</span>
                  </span>
                  <button
                    className="dismiss"
                    onClick={() => setQualityReview(null)}
                    title="Skjul panel"
                    type="button"
                  >
                    <FaTimes />
                  </button>
                </div>
              </div>

              {qualityReview.summary && (
                <div className="summary">{qualityReview.summary}</div>
              )}

              {qualityReview.issues?.length > 0 && (
                <div className="section-block">
                  <h4>Issues ({qualityReview.issues.length})</h4>
                  <ul>
                    {qualityReview.issues.map((iss, i) => {
                      const sev = iss.severity === 'blocker' ? 'sev-blocker'
                        : iss.severity === 'warning' ? 'sev-warning'
                        : 'sev-tip';
                      const Icon = iss.severity === 'blocker' ? FaExclamationTriangle
                        : iss.severity === 'warning' ? FaInfoCircle
                        : FaLightbulb;
                      return (
                        <li key={i} className={sev}>
                          <span className="icon"><Icon /></span>
                          <span>
                            {iss.section_key && (
                              <span className="section-tag">[{iss.section_key}]</span>
                            )}
                            {iss.message}
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}

              {qualityReview.suggestions?.length > 0 && (
                <div className="section-block">
                  <h4>Forbedringsforslag</h4>
                  <ul>
                    {qualityReview.suggestions.map((sug, i) => (
                      <li key={i} className="sev-tip">
                        <span className="icon"><FaLightbulb /></span>
                        <span>{sug}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {qualityReview.missing_legal_refs?.length > 0 && (
                <div className="section-block">
                  <h4>Manglende lovreferencer</h4>
                  <ul>
                    {qualityReview.missing_legal_refs.map((ref, i) => (
                      <li key={i} className="sev-warning">
                        <span className="icon"><FaInfoCircle /></span>
                        <span>{ref}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {!qualityReview.issues?.length
                && !qualityReview.suggestions?.length
                && !qualityReview.missing_legal_refs?.length && (
                <div style={{ fontSize: '0.86rem', color: '#2d6a31', fontStyle: 'italic' }}>
                  ✓ Ingen issues fundet — evidens ser solid ud
                </div>
              )}
            </ReviewPanel>
          )}

          {reviewError && !reviewing && (
            <div style={{
              color: '#a02020', padding: '0.5rem 0.8rem', marginBottom: '1rem',
              background: 'rgba(160,32,32,0.06)', borderLeft: '3px solid #a02020',
              borderRadius: '0 4px 4px 0', fontSize: '0.85rem',
            }}>
              AI-kvalitetstjek fejlede: {reviewError}
            </div>
          )}

          {template && caseId && (
            <SkabelonPicker
              artifactId={artifactId}
              caseId={caseId}
              currentContent={content}
              user={user}
              onApplied={(merged) => setContent(merged)}
            />
          )}

          {template?.legal_basis?.length > 0 && (
            <LegalSection>
              <div className="heading">Lovhjemmel</div>
              {template.legal_basis.map((lb, i) => (
                <div key={i} className="ref">
                  <span className="lov">{lb.lov}</span> — {lb.artikel}
                  {lb.url && (
                    <a href={lb.url} target="_blank" rel="noopener noreferrer">
                      <FaExternalLinkAlt size={10} /> kilde
                    </a>
                  )}
                  <span className="citat">"{lb.citat}"</span>
                </div>
              ))}
            </LegalSection>
          )}

          {template?.external_resources?.length > 0 && (
            <ResourcesSection>
              <div className="heading">Eksterne vejledninger</div>
              <ul>
                {template.external_resources.map((er, i) => (
                  <li key={i}>
                    <a href={er.url} target="_blank" rel="noopener noreferrer">
                      {er.title}
                    </a>
                    <span className="pub">— {er.publisher}</span>
                    {er.description && (
                      <span style={{ display: 'block', fontSize: '0.78rem', color: '#777', marginTop: '0.2rem' }}>
                        {er.description}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </ResourcesSection>
          )}

          {(template?.sections || []).map((s) => {
            const value = content[s.key];
            const filled = isFilled(value);
            const filledClass = filled
              ? 'filled-pill is-filled'
              : s.required
              ? 'filled-pill is-empty-required'
              : 'filled-pill';
            return (
              <SectionField key={s.key}>
                <div className="label-row">
                  <label htmlFor={`f-${s.key}`}>
                    {s.heading}
                    {s.required && <span className="req">*</span>}
                  </label>
                  <span className={filledClass}>
                    {filled ? '✓ udfyldt' : s.required ? 'mangler' : 'valgfri'}
                  </span>
                </div>
                {s.prompt && <div className="prompt">{s.prompt}</div>}
                {s.field_type === 'enum' && (
                  <select
                    id={`f-${s.key}`}
                    value={value || ''}
                    onChange={(e) => setContent((p) => ({ ...p, [s.key]: e.target.value }))}
                  >
                    <option value="">— vælg —</option>
                    {(s.enum_values || []).map((ev) => (
                      <option key={ev} value={ev}>{ev.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                )}
                {s.field_type === 'boolean' && (
                  <select
                    id={`f-${s.key}`}
                    value={value === true ? 'true' : value === false ? 'false' : ''}
                    onChange={(e) => {
                      const v = e.target.value;
                      setContent((p) => ({
                        ...p,
                        [s.key]: v === 'true' ? true : v === 'false' ? false : undefined,
                      }));
                    }}
                  >
                    <option value="">— vælg —</option>
                    <option value="true">Ja</option>
                    <option value="false">Nej</option>
                  </select>
                )}
                {s.field_type === 'text' && (
                  <input
                    id={`f-${s.key}`}
                    type="text"
                    placeholder={s.placeholder}
                    value={value || ''}
                    onChange={(e) => setContent((p) => ({ ...p, [s.key]: e.target.value }))}
                  />
                )}
                {s.field_type === 'date' && (
                  <input
                    id={`f-${s.key}`}
                    type="date"
                    value={value || ''}
                    onChange={(e) => setContent((p) => ({ ...p, [s.key]: e.target.value }))}
                  />
                )}
                {(!s.field_type || s.field_type === 'textarea') && (
                  <textarea
                    id={`f-${s.key}`}
                    placeholder={s.placeholder}
                    value={value || ''}
                    onChange={(e) => setContent((p) => ({ ...p, [s.key]: e.target.value }))}
                  />
                )}
                {caseId && (
                  <EvidenceComments
                    caseId={caseId}
                    artifactId={artifactId}
                    sectionKey={s.key}
                    user={user}
                  />
                )}
              </SectionField>
            );
          })}
        </Body>

        <Footer $ready={allRequiredFilled}>
          <div className="progress">
            <strong>{filledRequired.length}/{requiredKeys.length}</strong> påkrævede felter udfyldt
            {template?.estimated_minutes && (
              <span style={{ marginLeft: '0.6rem', opacity: 0.6 }}>
                · est. {template.estimated_minutes} min
              </span>
            )}
          </div>
          <div className="actions">
            <SecondaryButton
              onClick={() => {
                if (!caseId || !artifactId) return;
                const url = `/sag/${encodeURIComponent(caseId)}/evidens/${encodeURIComponent(artifactId)}/print`;
                window.open(url, '_blank', 'noopener,noreferrer');
              }}
              disabled={!template || !caseId}
              title="Åbn print-venlig version i ny tab — brug derefter Cmd+P / Ctrl+P"
              type="button"
            >
              <FaPrint /> Print
            </SecondaryButton>
            <SecondaryButton
              onClick={handleGenerateDraft}
              disabled={generatingDraft || saving || !template || !caseId}
              title="LLM laver udkast for tomme required-sektioner baseret på sagens intake"
              type="button"
              style={{ background: 'rgba(13,46,84,0.04)' }}
            >
              {generatingDraft ? <><Spinner /> Genererer…</> : '✨ Generer udkast'}
            </SecondaryButton>
            <SecondaryButton
              onClick={() => runQualityReview()}
              disabled={reviewing || saving || !template || !caseId || !filledRequired.length}
              title={filledRequired.length
                ? 'AI gennemgår dine svar for blockers, mangler og inkonsistens'
                : 'Udfyld mindst én required-sektion før AI-tjek'}
              type="button"
              style={{ background: 'rgba(13,46,84,0.04)' }}
            >
              {reviewing ? <><Spinner /> Reviewer…</> : <><FaSearch /> AI-kvalitetstjek</>}
            </SecondaryButton>
            <SecondaryButton onClick={onClose} disabled={saving}>
              Annullér
            </SecondaryButton>
            <PrimaryButton onClick={handleSave} disabled={saving || !template || !caseId}>
              {saving ? <><Spinner /> Gemmer…</> : <><FaCheck /> Gem</>}
            </PrimaryButton>
          </div>
        </Footer>
      </Sheet>
    </Backdrop>
  );
};

function isFilled(v) {
  if (v === undefined || v === null) return false;
  if (typeof v === 'string') return v.trim() !== '';
  if (typeof v === 'boolean') return true;
  if (typeof v === 'number') return true;
  return Boolean(v);
}

export default EvidenceEditor;
