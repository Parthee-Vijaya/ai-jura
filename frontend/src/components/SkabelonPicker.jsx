import React, { useEffect, useState } from 'react';
import styled from 'styled-components';
import axios from 'axios';
import { FaBookmark, FaSave, FaTrash, FaCheck } from 'react-icons/fa';

import { useToast } from './ui';

/**
 * SkabelonPicker — kompakt UI til at:
 *   1. Liste eksisterende skabeloner for et givent artifact_id
 *   2. Indlæse en skabelon (apply til den åbne sag)
 *   3. Gemme det nuværende indhold som en ny skabelon
 *
 * Bygges ind i EvidenceEditor som en lille header-bar over felterne.
 *
 * Props:
 *   artifactId: string
 *   caseId: string
 *   currentContent: dict — det aktuelle udfyldte indhold (til "Gem som skabelon")
 *   onApplied: (mergedContent) => void — kaldes efter apply for at re-loade content i editor
 *   user: string | undefined
 */

const Wrap = styled.div`
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.55rem 0.85rem;
  background: ${(p) => p.theme.colors.surfaceAlt || '#f6f8fb'};
  border: 1px solid ${(p) => p.theme.colors.borderSoft || '#e2e6ec'};
  border-radius: 6px;
  margin-bottom: 0.85rem;
  font-size: 0.82rem;
  flex-wrap: wrap;

  .label {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: ${(p) => p.theme.colors.textMuted};
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
  }

  select {
    flex: 1;
    min-width: 180px;
    padding: 0.35rem 0.5rem;
    border: 1px solid ${(p) => p.theme.colors.border || '#d8dde6'};
    border-radius: 4px;
    background: white;
    font-family: inherit;
    font-size: 0.82rem;
    cursor: pointer;
  }

  button {
    background: transparent;
    border: 1px solid ${(p) => p.theme.colors.border || '#d8dde6'};
    color: ${(p) => p.theme.colors.text};
    padding: 0.35rem 0.7rem;
    border-radius: 4px;
    cursor: pointer;
    font-family: inherit;
    font-size: 0.78rem;
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;

    &:hover { background: white; border-color: ${(p) => p.theme.colors.primary || '#0d2e54'}; color: ${(p) => p.theme.colors.primary || '#0d2e54'}; }
    &:disabled { opacity: 0.45; cursor: not-allowed; }
  }
  button.primary {
    background: ${(p) => p.theme.colors.primary || '#0d2e54'};
    color: white;
    border-color: transparent;

    &:hover { filter: brightness(1.08); background: ${(p) => p.theme.colors.primary || '#0d2e54'}; color: white; }
  }
`;

const SaveDialog = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  width: 100%;
  margin-top: 0.5rem;

  input, textarea {
    padding: 0.45rem 0.55rem;
    border: 1px solid ${(p) => p.theme.colors.border || '#d8dde6'};
    border-radius: 4px;
    font-family: inherit;
    font-size: 0.85rem;
  }
  textarea { min-height: 60px; resize: vertical; }

  .row {
    display: flex;
    gap: 0.4rem;
    justify-content: flex-end;
  }
`;

const SkabelonPicker = ({
  artifactId,
  caseId,
  currentContent,
  onApplied,
  user,
}) => {
  const toast = useToast();
  const [skabeloner, setSkabeloner] = useState([]);
  const [selectedId, setSelectedId] = useState('');
  const [loading, setLoading] = useState(false);
  const [saveOpen, setSaveOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [savingTemplate, setSavingTemplate] = useState(false);

  const fetchList = async () => {
    if (!artifactId) return;
    setLoading(true);
    try {
      const res = await axios.get(
        `/api/v3/skabelon-bibliotek?artifact_id=${encodeURIComponent(artifactId)}`,
      );
      setSkabeloner(res.data?.items || []);
    } catch (err) {
      // Stille — skabelon-bibliotek er nice-to-have
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchList();
    setSelectedId('');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [artifactId]);

  const handleApply = async () => {
    if (!selectedId || !caseId) return;
    setLoading(true);
    try {
      const res = await axios.post(
        `/api/v3/skabelon-bibliotek/${selectedId}/apply?case_id=${encodeURIComponent(caseId)}`,
        { user: user || null },
      );
      const merged = res.data?.content || {};
      const name = res.data?.applied_skabelon_name || 'skabelon';
      toast.success(`Indlæste: ${name} — eksisterende svar bevaret`);
      if (onApplied) onApplied(merged);
      // Refresh listen for at se opdateret times_used
      fetchList();
    } catch (err) {
      toast.error(`Kunne ikke indlæse skabelon: ${err?.response?.data?.detail || err?.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!newName.trim() || !artifactId) return;
    setSavingTemplate(true);
    try {
      await axios.post('/api/v3/skabelon-bibliotek', {
        artifact_id: artifactId,
        name: newName.trim(),
        description: newDesc.trim() || null,
        content: currentContent || {},
        source_case_id: caseId || null,
        user: user || null,
      });
      toast.success(`Skabelon "${newName.trim()}" gemt — kan nu bruges på andre sager`);
      setNewName('');
      setNewDesc('');
      setSaveOpen(false);
      fetchList();
    } catch (err) {
      toast.error(`Kunne ikke gemme skabelon: ${err?.response?.data?.detail || err?.message}`);
    } finally {
      setSavingTemplate(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Slet denne skabelon? Kan ikke fortrydes.')) return;
    try {
      await axios.delete(`/api/v3/skabelon-bibliotek/${id}`);
      toast.info('Skabelon slettet');
      if (String(id) === String(selectedId)) setSelectedId('');
      fetchList();
    } catch (err) {
      toast.error(`Kunne ikke slette: ${err?.response?.data?.detail || err?.message}`);
    }
  };

  if (!artifactId) return null;

  return (
    <Wrap aria-label="Skabelon-bibliotek">
      <span className="label" title="Skabelon-bibliotek for denne evidens-type">
        <FaBookmark /> Skabelon
      </span>
      {skabeloner.length > 0 ? (
        <>
          <select
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            disabled={loading}
            aria-label="Vælg skabelon"
          >
            <option value="">— Vælg en skabelon —</option>
            {skabeloner.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}{s.times_used > 0 ? ` (brugt ${s.times_used}×)` : ''}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="primary"
            onClick={handleApply}
            disabled={!selectedId || loading}
            title="Indlæs valgte skabelon — eksisterende svar bevares"
          >
            <FaCheck /> Indlæs
          </button>
          {selectedId && (
            <button
              type="button"
              onClick={() => handleDelete(selectedId)}
              title="Slet valgte skabelon"
              aria-label="Slet skabelon"
            >
              <FaTrash />
            </button>
          )}
        </>
      ) : (
        <span style={{ color: '#5f6b7a', fontSize: '0.78rem', fontStyle: 'italic' }}>
          Ingen gemte skabeloner endnu
        </span>
      )}
      <button
        type="button"
        onClick={() => setSaveOpen((v) => !v)}
        title="Gem nuværende indhold som genbrugbar skabelon"
      >
        <FaSave /> {saveOpen ? 'Fortryd' : 'Gem som skabelon'}
      </button>

      {saveOpen && (
        <SaveDialog>
          <input
            type="text"
            placeholder="Navn — fx 'Standard literacy-program for Borgerservice'"
            value={newName}
            maxLength={160}
            onChange={(e) => setNewName(e.target.value)}
            aria-label="Skabelon-navn"
          />
          <textarea
            placeholder="Beskrivelse (valgfri) — hvornår bruges denne skabelon?"
            value={newDesc}
            maxLength={2000}
            onChange={(e) => setNewDesc(e.target.value)}
            aria-label="Skabelon-beskrivelse"
          />
          <div className="row">
            <button type="button" onClick={() => setSaveOpen(false)}>
              Annullér
            </button>
            <button
              type="button"
              className="primary"
              onClick={handleSave}
              disabled={!newName.trim() || savingTemplate}
            >
              {savingTemplate ? 'Gemmer…' : 'Gem skabelon'}
            </button>
          </div>
        </SaveDialog>
      )}
    </Wrap>
  );
};

export default SkabelonPicker;
