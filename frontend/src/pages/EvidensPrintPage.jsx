import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import styled, { createGlobalStyle } from 'styled-components';
import axios from 'axios';
import { FaPrint } from 'react-icons/fa';

/**
 * EvidensPrintPage — print-venlig visning af én evidens-artefakt.
 *
 * URL: /sag/:caseId/evidens/:artifactId/print
 *
 * Henter:
 *   - GET /api/v3/evidence/templates/{artifact_id}  → skabelon + lov + sektioner
 *   - GET /api/v3/cases/{case_id}/evidence          → faktiske svar
 *
 * Designet til at:
 *   - Åbnes i ny browser-tab fra EvidenceEditor
 *   - Trykkes direkte (Cmd+P / Ctrl+P) eller "Gem som PDF" via browser-print-dialog
 *   - Vise alt: status, lovhjemler, eksterne ressourcer, hver sektions svar
 *
 * Tilbyder også en "Print"-knap der trigger window.print() — den skjules
 * automatisk i print-output via @media print { display: none }.
 */

// Print-CSS injiceres globalt mens denne page er mounted
const PrintGlobal = createGlobalStyle`
  @media print {
    body { background: white !important; }
    .no-print { display: none !important; }
    @page {
      margin: 1.6cm 1.6cm 2cm;
      size: A4;
    }
  }
`;

const Page = styled.main`
  background: ${(p) => p.theme.colors.surface || '#fff'};
  color: ${(p) => p.theme.colors.text || '#15243a'};
  max-width: 780px;
  margin: 2.5rem auto;
  padding: 2.5rem 3rem;
  font-family: ${(p) => p.theme.fonts?.body || 'Georgia, serif'};
  line-height: 1.5;
  font-size: 0.95rem;
  border: 1px solid ${(p) => p.theme.colors.border || '#d8dde6'};
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.06);

  @media print {
    margin: 0;
    padding: 0;
    border: none;
    box-shadow: none;
    max-width: 100%;
  }

  header.doc-header {
    border-bottom: 2px solid ${(p) => p.theme.colors.primary || '#0d2e54'};
    padding-bottom: 1rem;
    margin-bottom: 1.5rem;

    .eyebrow {
      font-family: ${(p) => p.theme.fonts?.mono || 'monospace'};
      font-size: 0.7rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: ${(p) => p.theme.colors.primary || '#0d2e54'};
      margin: 0 0 0.4rem;
    }
    h1 {
      font-family: ${(p) => p.theme.fonts?.display || 'serif'};
      font-size: 1.6rem;
      font-weight: 600;
      margin: 0 0 0.4rem;
      color: ${(p) => p.theme.colors.text};
    }
    .case-meta {
      font-family: ${(p) => p.theme.fonts?.mono || 'monospace'};
      font-size: 0.75rem;
      color: ${(p) => p.theme.colors.textMuted || '#5f6b7a'};

      .sep { margin: 0 0.4rem; opacity: 0.5; }
    }
  }

  section.summary {
    background: ${(p) => p.theme.colors.surfaceAlt || '#f6f8fb'};
    border-left: 3px solid ${(p) => p.theme.colors.primary || '#0d2e54'};
    padding: 0.85rem 1.1rem;
    margin: 0 0 1.6rem;
    border-radius: 0 4px 4px 0;
    font-size: 0.92rem;

    @media print {
      background: white;
      border-left-width: 2px;
    }
  }

  h2 {
    font-family: ${(p) => p.theme.fonts?.display || 'serif'};
    font-size: 1.05rem;
    font-weight: 600;
    color: ${(p) => p.theme.colors.text};
    margin: 1.6rem 0 0.4rem;
    padding-bottom: 0.2rem;
    border-bottom: 1px solid ${(p) => p.theme.colors.borderSoft || '#e2e6ec'};
    page-break-after: avoid;
  }

  h3 {
    font-family: ${(p) => p.theme.fonts?.display || 'serif'};
    font-size: 0.95rem;
    font-weight: 600;
    color: ${(p) => p.theme.colors.text};
    margin: 1rem 0 0.3rem;
    page-break-after: avoid;
  }

  .legal {
    margin: 0 0 0.8rem;
    padding: 0.6rem 0.9rem;
    background: ${(p) => p.theme.colors.surfaceAlt || '#f6f8fb'};
    border-radius: 4px;
    font-size: 0.84rem;
    page-break-inside: avoid;

    .head {
      font-family: ${(p) => p.theme.fonts?.mono || 'monospace'};
      font-weight: 600;
      color: ${(p) => p.theme.colors.primary || '#0d2e54'};
      margin: 0 0 0.25rem;
    }
    .citat {
      margin: 0 0 0.3rem;
      font-style: italic;
      color: ${(p) => p.theme.colors.text};
    }
    .url {
      font-family: ${(p) => p.theme.fonts?.mono || 'monospace'};
      font-size: 0.7rem;
      color: ${(p) => p.theme.colors.textMuted};
      word-break: break-all;
    }
  }

  .external-list {
    margin: 0;
    padding-left: 1.2rem;
    font-size: 0.85rem;

    li {
      margin: 0.25rem 0;
      .pub {
        font-family: ${(p) => p.theme.fonts?.mono || 'monospace'};
        font-size: 0.72rem;
        color: ${(p) => p.theme.colors.textMuted};
        margin-left: 0.4rem;
      }
    }
  }

  .section-block {
    margin-bottom: 1.2rem;
    page-break-inside: avoid;

    .section-prompt {
      font-size: 0.78rem;
      color: ${(p) => p.theme.colors.textMuted};
      margin: 0 0 0.4rem;
      font-style: italic;
    }
    .section-answer {
      background: ${(p) => p.theme.colors.surfaceAlt || '#f6f8fb'};
      border: 1px solid ${(p) => p.theme.colors.borderSoft || '#e2e6ec'};
      border-radius: 4px;
      padding: 0.6rem 0.85rem;
      font-size: 0.92rem;
      white-space: pre-wrap;
      word-wrap: break-word;

      @media print {
        background: white;
      }
    }
    .section-empty {
      color: ${(p) => p.theme.colors.textFaded || '#9aa3b1'};
      font-style: italic;
      font-size: 0.85rem;
    }
    .required-badge {
      display: inline-block;
      background: ${(p) => p.theme.colors.primary || '#0d2e54'};
      color: white;
      font-family: ${(p) => p.theme.fonts?.mono || 'monospace'};
      font-size: 0.62rem;
      padding: 0.1rem 0.4rem;
      border-radius: 3px;
      margin-left: 0.5rem;
      vertical-align: middle;
    }
  }

  footer.doc-footer {
    margin-top: 2.5rem;
    padding-top: 1rem;
    border-top: 1px solid ${(p) => p.theme.colors.borderSoft || '#e2e6ec'};
    font-family: ${(p) => p.theme.fonts?.mono || 'monospace'};
    font-size: 0.7rem;
    color: ${(p) => p.theme.colors.textMuted};
    text-align: center;

    .gen { display: block; margin-bottom: 0.2rem; }
  }
`;

const Toolbar = styled.div`
  position: fixed;
  top: 16px;
  right: 16px;
  display: flex;
  gap: 8px;
  z-index: 100;

  button {
    background: ${(p) => p.theme.colors.primary || '#0d2e54'};
    color: white;
    border: none;
    border-radius: 4px;
    padding: 0.55rem 0.9rem;
    cursor: pointer;
    font-family: ${(p) => p.theme.fonts?.mono || 'monospace'};
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;

    &:hover { filter: brightness(1.08); }
  }
`;

const STATUS_LABEL = {
  mangler: 'Mangler udfyldelse',
  i_gang: 'Under arbejde',
  faerdig: 'Færdig',
  godkendt: 'Godkendt af jurist',
};

const EvidensPrintPage = () => {
  const { caseId, artifactId } = useParams();

  const [template, setTemplate] = useState(null);
  const [content, setContent] = useState({});
  const [status, setStatus] = useState(null);
  const [updatedAt, setUpdatedAt] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    document.title = `Evidens · ${artifactId} · ${caseId}`;
  }, [caseId, artifactId]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [tmplRes, evidenceRes] = await Promise.all([
          axios.get(
            `/api/v3/evidence/templates/${encodeURIComponent(artifactId)}`,
          ),
          axios.get(`/api/v3/cases/${encodeURIComponent(caseId)}/evidence`),
        ]);
        if (cancelled) return;
        setTemplate(tmplRes.data);
        const found = (evidenceRes.data?.items || []).find(
          (it) => it.artifact_id === artifactId,
        );
        if (found) {
          setContent(found.content_json || {});
          setStatus(found.status);
          setUpdatedAt(found.updated_at || found.completed_at);
        }
      } catch (err) {
        if (cancelled) return;
        setError(
          err?.response?.data?.detail ||
            err?.message ||
            'Kunne ikke hente data',
        );
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [caseId, artifactId]);

  if (loading) {
    return (
      <Page>
        <p>Henter…</p>
      </Page>
    );
  }
  if (error) {
    return (
      <Page>
        <h1>Fejl</h1>
        <p>{error}</p>
      </Page>
    );
  }

  if (!template) return null;

  const generated = new Date().toLocaleString('da-DK', {
    dateStyle: 'long',
    timeStyle: 'short',
  });

  return (
    <>
      <PrintGlobal />
      <Toolbar className="no-print">
        <button type="button" onClick={() => window.print()}>
          <FaPrint aria-hidden="true" /> Print / Gem som PDF
        </button>
      </Toolbar>

      <Page>
        <header className="doc-header">
          <p className="eyebrow">Bifrost · Evidens-artefakt</p>
          <h1>{template.title}</h1>
          <div className="case-meta">
            <span>Sag: {caseId}</span>
            <span className="sep">·</span>
            <span>Status: {STATUS_LABEL[status] || 'Ikke påbegyndt'}</span>
            {updatedAt && (
              <>
                <span className="sep">·</span>
                <span>Sidst opdateret: {new Date(updatedAt).toLocaleString('da-DK')}</span>
              </>
            )}
          </div>
        </header>

        <section className="summary">{template.summary}</section>

        {template.legal_basis && template.legal_basis.length > 0 && (
          <>
            <h2>Lovhjemmel</h2>
            {template.legal_basis.map((ref, idx) => (
              <div className="legal" key={idx}>
                <p className="head">
                  {ref.lov} — {ref.artikel}
                </p>
                {ref.citat && <p className="citat">"{ref.citat}"</p>}
                <p className="url">{ref.url}</p>
              </div>
            ))}
          </>
        )}

        {template.external_resources &&
          template.external_resources.length > 0 && (
            <>
              <h2>Eksterne ressourcer</h2>
              <ul className="external-list">
                {template.external_resources.map((res, idx) => (
                  <li key={idx}>
                    {res.title}
                    <span className="pub">— {res.publisher}</span>
                    {res.description && (
                      <div style={{ marginTop: '0.2rem', fontSize: '0.8rem', color: '#5f6b7a' }}>
                        {res.description}
                      </div>
                    )}
                    <div style={{ fontFamily: 'monospace', fontSize: '0.7rem', color: '#5f6b7a', wordBreak: 'break-all' }}>
                      {res.url}
                    </div>
                  </li>
                ))}
              </ul>
            </>
          )}

        <h2>Udfyldte sektioner</h2>
        {template.sections && template.sections.length > 0 ? (
          template.sections.map((sec) => {
            const value = content[sec.key];
            const isFilled =
              value !== undefined &&
              value !== null &&
              value !== '' &&
              !(Array.isArray(value) && value.length === 0);
            return (
              <div className="section-block" key={sec.key}>
                <h3>
                  {sec.heading}
                  {sec.required && (
                    <span className="required-badge">PÅKRÆVET</span>
                  )}
                </h3>
                <p className="section-prompt">{sec.prompt}</p>
                {isFilled ? (
                  <div className="section-answer">
                    {typeof value === 'boolean'
                      ? value
                        ? 'Ja'
                        : 'Nej'
                      : Array.isArray(value)
                      ? value.join(', ')
                      : String(value)}
                  </div>
                ) : (
                  <div className="section-empty">— ikke udfyldt —</div>
                )}
              </div>
            );
          })
        ) : (
          <p>Ingen sektioner.</p>
        )}

        <footer className="doc-footer">
          <span className="gen">
            Genereret af Bifrost · {generated} · case={caseId} · artifact=
            {artifactId}
          </span>
          <span>
            Bifrost — Kalundborg Kommunes AI-compliance-platform
          </span>
        </footer>
      </Page>
    </>
  );
};

export default EvidensPrintPage;
