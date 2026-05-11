import React, { useState, useMemo } from 'react';
import styled from 'styled-components';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import DataOverview from '../components/data-overview/DataOverview';
import GettingStarted from '../components/GettingStarted';

/**
 * SagerPage — Step 2 ("workflow state-machine") kanban over /api/v3/cases.
 *
 * One column per CASE_STATUS. Drag-drop moves a case between columns;
 * each move triggers a /transition call that records an entry in the
 * case_transitions audit-trail.
 */

const STATUSES = [
  { id: 'kladde', label: 'Kladde' },
  { id: 'vurderet', label: 'Vurderet' },
  { id: 'remediation', label: 'Remediation' },
  { id: 'godkendt', label: 'Godkendt' },
  { id: 'idriftsat', label: 'Idriftsat' },
  { id: 'arkiveret', label: 'Arkiveret' },
];

// Northern Modern verdict-mapping fra DESIGN.md
const STATUS_ACCENT = {
  kladde: '#5b6573',        // textFaded
  vurderet: '#555a64',      // textMuted
  remediation: '#6e5527',   // bronze (betinget — kræver handling, ikke fejl)
  godkendt: '#2f6b2f',      // success
  idriftsat: '#0d2e54',     // primary (kongelig blå — i drift)
  arkiveret: '#5b6573',     // faded
};

// ---- API ----------------------------------------------------------------

async function fetchCases() {
  const res = await axios.get('/api/v3/cases');
  return res.data;
}

async function createCase(body) {
  const res = await axios.post('/api/v3/cases', body);
  return res.data;
}

async function transitionCase({ id, new_status, note }) {
  const res = await axios.post(`/api/v3/cases/${id}/transition`, {
    new_status,
    note,
  });
  return res.data;
}

// ---- Layout shell -------------------------------------------------------

const Page = styled.div`
  max-width: 1480px;
  margin: 0 auto;
  padding: 3rem 2.5rem 5rem;
`;

const Header = styled.header`
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 2rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
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
  margin: 0 0 0.5rem;
  color: ${(p) => p.theme.colors.ink};
`;

const Lede = styled.p`
  font-family: ${(p) => p.theme.fonts.body};
  margin: 0;
  color: ${(p) => p.theme.colors.inkSoft};
  font-size: 1rem;
  line-height: 1.55;
  max-width: 720px;
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
  align-self: flex-end;

  &:hover { background: ${(p) => p.theme.colors.primaryDark}; }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
`;

// ---- Kanban -------------------------------------------------------------

const KanbanGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(${STATUSES.length}, minmax(200px, 1fr));
  gap: 0.85rem;
  align-items: start;
  overflow-x: auto;

  @media (max-width: 1100px) {
    grid-template-columns: repeat(3, minmax(220px, 1fr));
  }
  @media (max-width: 720px) {
    grid-template-columns: 1fr;
  }
`;

const Column = styled.div`
  background: ${(p) => p.theme.colors.paperSoft};
  border: 1px solid ${(p) => (p.$dragOver ? p.theme.colors.primary : p.theme.colors.line)};
  border-radius: 8px;
  padding: 0.85rem 0.65rem 0.65rem;
  min-height: 200px;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
`;

const ColumnHead = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 0.4rem 0.5rem;
  border-bottom: 2px solid ${(p) => p.$accent || p.theme.colors.line};
  margin-bottom: 0.4rem;
`;

const ColumnTitle = styled.span`
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-weight: 700;
  color: ${(p) => p.$accent};
`;

const ColumnCount = styled.span`
  font-family: ${(p) => p.theme.fonts.mono};
  font-size: 0.78rem;
  color: ${(p) => p.theme.colors.inkFaded};
`;

const Card = styled.div`
  background: ${(p) => p.theme.colors.card};
  border: 1px solid ${(p) => p.theme.colors.line};
  border-radius: 6px;
  padding: 0.75rem 0.9rem 0.65rem;
  cursor: pointer;
  transition: border-color ${(p) => p.theme.animations.transitionFast},
              box-shadow ${(p) => p.theme.animations.transitionFast},
              transform ${(p) => p.theme.animations.transitionFast};
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  position: relative;

  &:hover {
    border-color: ${(p) => p.theme.colors.primary};
    box-shadow: 0 4px 12px rgba(20, 17, 13, 0.08);
    transform: translateY(-1px);
  }

  &:focus-visible {
    outline: 2px solid ${(p) => p.theme.colors.primary};
    outline-offset: 2px;
  }

  /* Drag-handle indicator — tydeliggør at kortet kan trækkes */
  &::before {
    content: '⋮⋮';
    position: absolute;
    top: 0.65rem;
    right: 0.7rem;
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.78rem;
    color: ${(p) => p.theme.colors.inkFaded};
    letter-spacing: -2px;
    cursor: grab;
    opacity: 0.4;
    transition: opacity 0.15s ease;
  }
  &:hover::before { opacity: 0.9; }
  &:active::before { cursor: grabbing; }
`;

const CardPreview = styled.div`
  font-family: ${(p) => p.theme.fonts.body};
  font-size: 0.82rem;
  color: ${(p) => p.theme.colors.inkSoft};
  line-height: 1.4;
  margin-top: 0.1rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
`;

const CardProgress = styled.div`
  margin-top: 0.4rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-family: ${(p) => p.theme.fonts.mono};
  font-size: 0.7rem;
  color: ${(p) => p.theme.colors.inkFaded};

  .bar {
    flex: 1;
    height: 4px;
    background: ${(p) => p.theme.colors.line};
    border-radius: 999px;
    overflow: hidden;

    .fill {
      height: 100%;
      background: ${(p) => p.theme.colors.primary};
      transition: width 0.3s ease;
    }
  }
`;

const CardCta = styled.div`
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px dashed ${(p) => p.theme.colors.line};
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.78rem;
  color: ${(p) => p.theme.colors.primary};
  font-weight: 600;
  display: flex;
  justify-content: space-between;
  align-items: center;

  .arrow {
    transition: transform 0.15s ease;
  }
`;

const CardCaseId = styled.div`
  font-family: ${(p) => p.theme.fonts.mono};
  font-size: 0.7rem;
  color: ${(p) => p.theme.colors.inkFaded};
  letter-spacing: 0.08em;
  text-transform: uppercase;
`;

const CardTitle = styled.div`
  font-family: ${(p) => p.theme.fonts.display};
  font-size: 0.95rem;
  font-weight: 600;
  line-height: 1.35;
  color: ${(p) => p.theme.colors.ink};
`;

const CardMeta = styled.div`
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.72rem;
  color: ${(p) => p.theme.colors.inkSoft};
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
  margin-top: 0.2rem;

  .pill {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 3px;
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.68rem;
    letter-spacing: 0.05em;
  }
  .pill-go { background: rgba(45,106,49,0.10); color: #2d6a31; }
  .pill-betinget { background: #fdf2eb; color: #a03612; }
  .pill-no-go { background: rgba(160,32,32,0.10); color: #a02020; }
`;

const EmptyHint = styled.div`
  font-family: ${(p) => p.theme.fonts.body};
  font-size: 0.82rem;
  color: ${(p) => p.theme.colors.inkFaded};
  padding: 1rem 0.5rem;
  text-align: center;
  border: 1px dashed ${(p) => p.theme.colors.line};
  border-radius: 6px;
  margin-top: 0.3rem;
`;

const EmptyCta = styled.button`
  background: transparent;
  border: 1px solid ${(p) => p.theme.colors.primary};
  color: ${(p) => p.theme.colors.primary};
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.78rem;
  font-weight: 600;
  padding: 0.4rem 0.85rem;
  border-radius: 5px;
  cursor: pointer;
  margin-top: 0.6rem;

  &:hover {
    background: ${(p) => p.theme.colors.primary};
    color: white;
  }
`;

const HelpHint = styled.div`
  background: ${(p) => p.theme.colors.paperSoft || 'rgba(13,46,84,0.04)'};
  border-left: 3px solid ${(p) => p.theme.colors.bronze};
  padding: 0.6rem 0.95rem;
  border-radius: 0 4px 4px 0;
  margin: 0 0 1rem;
  font-family: ${(p) => p.theme.fonts.body};
  font-size: 0.85rem;
  color: ${(p) => p.theme.colors.inkSoft};
  line-height: 1.5;

  strong { color: ${(p) => p.theme.colors.ink}; }

  kbd {
    background: ${(p) => p.theme.colors.paper};
    border: 1px solid ${(p) => p.theme.colors.line};
    border-radius: 3px;
    padding: 1px 5px;
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.78rem;
  }
`;

// ---- Modal --------------------------------------------------------------

const ModalOverlay = styled.div`
  position: fixed; inset: 0;
  background: rgba(20, 17, 13, 0.4);
  z-index: 1000;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding-top: 14vh;
`;

const ModalPanel = styled.form`
  width: min(540px, 92vw);
  background: ${(p) => p.theme.colors.card};
  border: 1px solid ${(p) => p.theme.colors.line};
  border-radius: 10px;
  padding: 1.6rem 1.75rem;
  display: flex; flex-direction: column;
  gap: 0.85rem;
`;

const ModalTitle = styled.h2`
  font-family: ${(p) => p.theme.fonts.display};
  font-size: 1.4rem;
  margin: 0 0 0.25rem;
`;

const Field = styled.div`
  display: flex; flex-direction: column;
  gap: 0.35rem;

  label {
    font-family: ${(p) => p.theme.fonts.sans};
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: ${(p) => p.theme.colors.inkSoft};
    font-weight: 500;
  }
  input, textarea {
    border: 1px solid ${(p) => p.theme.colors.line};
    border-radius: 6px;
    padding: 0.55rem 0.75rem;
    font-family: ${(p) => p.theme.fonts.body};
    font-size: 0.95rem;
    background: ${(p) => p.theme.colors.paper};
    color: ${(p) => p.theme.colors.ink};
  }
  textarea { min-height: 80px; resize: vertical; }
`;

const ModalActions = styled.div`
  display: flex; gap: 0.7rem; justify-content: flex-end;
  margin-top: 0.4rem;
`;

const SecondaryButton = styled.button`
  background: transparent;
  color: ${(p) => p.theme.colors.ink};
  border: 1px solid ${(p) => p.theme.colors.line};
  padding: 0.55rem 1rem;
  border-radius: 6px;
  font-family: ${(p) => p.theme.fonts.sans};
  font-weight: 500;
  font-size: 0.88rem;
  cursor: pointer;
`;

const ErrorBox = styled.div`
  background: ${(p) => p.theme.colors.dangerSoft};
  border: 1px solid ${(p) => p.theme.colors.danger};
  color: ${(p) => p.theme.colors.danger};
  padding: 0.85rem 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.88rem;
`;

// ---- Page ---------------------------------------------------------------

const aggregatePill = (status) => {
  if (status === 'GO') return 'pill-go';
  if (status === 'BETINGET-GO') return 'pill-betinget';
  if (status === 'NO-GO') return 'pill-no-go';
  return '';
};

// Routing: ALLE sager åbner /sag/{case_id} (sag-detalje-side med 5 tabs).
// Den side har quick-actions der dybt-linker til indkoebsproces/vurdering/
// historik baseret på status. Det giver én pålidelig indgang per sag.
const cardClickPath = (c) => `/sag/${encodeURIComponent(c.case_id)}`;

const cardCtaLabel = (c) => {
  if (c.status === 'kladde') return 'Åbn sagen';
  if (c.status === 'remediation') return 'Åbn (ret krav)';
  if (c.status === 'vurderet') return 'Åbn sag';
  if (c.status === 'godkendt') return 'Se godkendelse';
  if (c.status === 'idriftsat') return 'Se i drift';
  if (c.status === 'arkiveret') return 'Vis arkiv';
  return 'Åbn';
};

// Beregn progress for kladder baseret på udfyldte felter i intake_state
const intakeProgress = (intake) => {
  if (!intake || typeof intake !== 'object') return null;
  const fields = ['behov', 'dobbeltsystem_tjekket', 'sagsnummer', 'serviceportal_dato',
                  'indkoeb_eller_udvikling', 'system_description'];
  const filled = fields.filter((k) => {
    const v = intake[k];
    if (typeof v === 'boolean') return v;
    return typeof v === 'string' && v.trim() !== '';
  }).length;
  return { filled, total: fields.length, pct: Math.round((filled / fields.length) * 100), step: intake.current_step || 1 };
};

const SagerPage = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data, isLoading, isError, error } = useQuery('v3-cases', fetchCases);
  const cases = data?.items || [];

  const [showCreate, setShowCreate] = useState(false);
  const [draftCase, setDraftCase] = useState({ case_id: '', title: '', notes: '' });
  const [dragOverColumn, setDragOverColumn] = useState(null);
  const [draggingId, setDraggingId] = useState(null);

  // Filtre — alle gemmes i query-string så filtrering er delbar via link
  // Bulk-selection — Set af case.id (db-id, ikke case_id) der er valgt
  const [selectedIds, setSelectedIds] = useState(() => new Set());
  const [bulkTargetStatus, setBulkTargetStatus] = useState('');

  const toggleSelected = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const bulkTransition = async () => {
    if (!bulkTargetStatus || selectedIds.size === 0) return;
    const targets = Array.from(selectedIds);
    const note = `Bulk-flyt til ${bulkTargetStatus} (${targets.length} sager)`;
    // Kør sekventielt for at undgå at hammere backend rate-limit
    let ok = 0;
    let fail = 0;
    for (const id of targets) {
      try {
        await transitionCase({ id, new_status: bulkTargetStatus, note });
        ok += 1;
      } catch (err) {
        fail += 1;
        console.warn('bulk transition failed', id, err);
      }
    }
    setSelectedIds(new Set());
    setBulkTargetStatus('');
    queryClient.invalidateQueries('v3-cases');
    if (fail > 0) {
      alert(`Flyttede ${ok} sager. ${fail} fejlede — se konsol.`);
    }
  };

  const [searchText, setSearchText] = useState('');
  const [filterVerdict, setFilterVerdict] = useState('');     // GO|BETINGET-GO|NO-GO|''
  const [filterIndkoeb, setFilterIndkoeb] = useState('');     // indkoeb|udvikling|hybrid|''
  const [filterAssignee, setFilterAssignee] = useState('');   // text-prefix-match

  // Hent unikke assignees fra cases for autocomplete-listen
  const assigneeOptions = useMemo(() => {
    const set = new Set();
    cases.forEach((c) => { if (c.assigned_to) set.add(c.assigned_to); });
    return Array.from(set).sort();
  }, [cases]);

  // Aplikér filtre BEFORE grouping så kanban-tællere matcher
  const filteredCases = useMemo(() => {
    const q = searchText.trim().toLowerCase();
    return cases.filter((c) => {
      if (q) {
        const haystack = [
          c.case_id, c.title, c.notes,
          c.intake_state?.behov, c.intake_state?.sagsnummer,
        ].filter(Boolean).join(' ').toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      if (filterVerdict && c.last_aggregate_status !== filterVerdict) return false;
      if (filterIndkoeb && c.intake_state?.indkoeb_eller_udvikling !== filterIndkoeb) return false;
      if (filterAssignee && (c.assigned_to || '').toLowerCase().indexOf(filterAssignee.toLowerCase()) === -1) return false;
      return true;
    });
  }, [cases, searchText, filterVerdict, filterIndkoeb, filterAssignee]);

  const hasActiveFilter = !!(searchText || filterVerdict || filterIndkoeb || filterAssignee);

  const createMutation = useMutation(createCase, {
    onSuccess: () => {
      queryClient.invalidateQueries('v3-cases');
      setShowCreate(false);
      setDraftCase({ case_id: '', title: '', notes: '' });
    },
  });

  const transitionMutation = useMutation(transitionCase, {
    onSuccess: () => {
      queryClient.invalidateQueries('v3-cases');
    },
  });

  const grouped = useMemo(() => {
    const out = {};
    STATUSES.forEach((s) => { out[s.id] = []; });
    filteredCases.forEach((c) => {
      if (out[c.status]) out[c.status].push(c);
    });
    return out;
  }, [filteredCases]);

  const handleDragStart = (e, caseId) => {
    setDraggingId(caseId);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', caseId);
  };

  const handleDragOver = (e, columnId) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverColumn(columnId);
  };

  const handleDrop = (e, columnId) => {
    e.preventDefault();
    setDragOverColumn(null);
    setDraggingId(null);
    const caseId = e.dataTransfer.getData('text/plain');
    const moving = cases.find((c) => c.id === caseId);
    if (!moving || moving.status === columnId) return;
    transitionMutation.mutate({
      id: caseId,
      new_status: columnId,
      note: `Flyttet til ${STATUSES.find((s) => s.id === columnId)?.label} via kanban`,
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!draftCase.case_id.trim() || !draftCase.title.trim()) return;
    createMutation.mutate({
      case_id: draftCase.case_id.trim(),
      title: draftCase.title.trim(),
      notes: draftCase.notes.trim() || undefined,
      status: 'kladde',
    });
  };

  return (
    <Page>
      <Header>
        <div>
          <Eyebrow>Bifrost · sager</Eyebrow>
          <Title>Sager</Title>
          <Lede>
            Hver sag aggregerer én eller flere v3-vurderinger og lever igennem
            workflow-stadierne. Træk kort mellem kolonner for at registrere en
            statusovergang — hvert skift gemmes i sagens audit-trail.
          </Lede>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button
            type="button"
            onClick={() => {
              const a = document.createElement('a');
              a.href = '/api/v3/cases/export.csv';
              a.download = '';
              document.body.appendChild(a);
              a.click();
              document.body.removeChild(a);
            }}
            title="Download alle sager som CSV (Excel-kompatibel)"
            style={{
              background: 'transparent',
              color: '#0d2e54',
              border: '1px solid #d8d3c5',
              padding: '0.55rem 0.9rem',
              borderRadius: 4,
              cursor: 'pointer',
              fontFamily: 'inherit',
              fontSize: '0.85rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.35rem',
            }}
          >
            ↓ CSV
          </button>
          <PrimaryButton type="button" onClick={() => setShowCreate(true)}>
            + Ny sag
          </PrimaryButton>
        </div>
      </Header>

      {isError && (
        <ErrorBox>
          Kunne ikke hente sager: {String(error?.message || error)}
        </ErrorBox>
      )}

      {!isLoading && cases.length === 0 ? (
        <GettingStarted />
      ) : (
        <>
          <div style={{
            display: 'flex',
            gap: 8,
            flexWrap: 'wrap',
            alignItems: 'center',
            padding: '0.65rem 0.9rem',
            background: '#f5f4ef',
            border: '1px solid #d8d3c5',
            borderRadius: 6,
            marginBottom: '1rem',
          }}>
            <input
              type="search"
              placeholder="Søg sager (id, titel, behov, sagsnummer…)"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              style={{
                flex: '1 1 240px',
                minWidth: 200,
                padding: '0.4rem 0.65rem',
                border: '1px solid #d8d3c5',
                borderRadius: 4,
                fontFamily: 'inherit',
                fontSize: '0.85rem',
              }}
              aria-label="Søg sager"
            />
            <select
              value={filterVerdict}
              onChange={(e) => setFilterVerdict(e.target.value)}
              aria-label="Filter på verdict"
              style={{
                padding: '0.4rem 0.55rem',
                border: '1px solid #d8d3c5',
                borderRadius: 4,
                background: 'white',
                fontFamily: 'inherit',
                fontSize: '0.85rem',
              }}
            >
              <option value="">Alle verdicts</option>
              <option value="GO">GO</option>
              <option value="BETINGET-GO">BETINGET-GO</option>
              <option value="NO-GO">NO-GO</option>
            </select>
            <select
              value={filterIndkoeb}
              onChange={(e) => setFilterIndkoeb(e.target.value)}
              aria-label="Filter på indkøb/udvikling"
              style={{
                padding: '0.4rem 0.55rem',
                border: '1px solid #d8d3c5',
                borderRadius: 4,
                background: 'white',
                fontFamily: 'inherit',
                fontSize: '0.85rem',
              }}
            >
              <option value="">Indkøb og udvikling</option>
              <option value="indkoeb_faerdig_loesning">Indkøb (færdig)</option>
              <option value="skraeddersyet_udvikling">Skræddersyet udvikling</option>
              <option value="hybrid">Hybrid</option>
            </select>
            <input
              type="text"
              list="assignee-options"
              placeholder="Ansvarlig…"
              value={filterAssignee}
              onChange={(e) => setFilterAssignee(e.target.value)}
              style={{
                flex: '0 1 160px',
                padding: '0.4rem 0.55rem',
                border: '1px solid #d8d3c5',
                borderRadius: 4,
                fontFamily: 'inherit',
                fontSize: '0.85rem',
              }}
              aria-label="Filter på ansvarlig"
            />
            <datalist id="assignee-options">
              {assigneeOptions.map((a) => <option key={a} value={a} />)}
            </datalist>
            {hasActiveFilter && (
              <button
                type="button"
                onClick={() => {
                  setSearchText('');
                  setFilterVerdict('');
                  setFilterIndkoeb('');
                  setFilterAssignee('');
                }}
                title="Ryd alle filtre"
                style={{
                  background: 'transparent',
                  color: '#a02020',
                  border: '1px solid #d8d3c5',
                  borderRadius: 4,
                  padding: '0.4rem 0.7rem',
                  fontSize: '0.78rem',
                  cursor: 'pointer',
                }}
              >
                ✕ Ryd
              </button>
            )}
            <span style={{
              marginLeft: 'auto',
              fontFamily: 'monospace',
              fontSize: '0.75rem',
              color: '#5b6573',
            }}>
              {hasActiveFilter
                ? `${filteredCases.length}/${cases.length} sager`
                : `${cases.length} sager i alt`}
            </span>
          </div>

          {selectedIds.size > 0 && (
            <div style={{
              display: 'flex',
              gap: 8,
              alignItems: 'center',
              padding: '0.65rem 0.9rem',
              background: '#0d2e54',
              color: 'white',
              borderRadius: 6,
              marginBottom: '1rem',
              flexWrap: 'wrap',
            }}>
              <strong style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                {selectedIds.size} sag{selectedIds.size === 1 ? '' : 'er'} valgt
              </strong>
              <span style={{ opacity: 0.6 }}>·</span>
              <span style={{ fontSize: '0.82rem' }}>Flyt til status:</span>
              <select
                value={bulkTargetStatus}
                onChange={(e) => setBulkTargetStatus(e.target.value)}
                style={{
                  padding: '0.35rem 0.5rem',
                  border: '1px solid white',
                  borderRadius: 4,
                  fontFamily: 'inherit',
                  fontSize: '0.82rem',
                  background: 'white',
                  color: '#0d2e54',
                }}
                aria-label="Vælg ny status"
              >
                <option value="">— vælg —</option>
                {STATUSES.map((s) => (
                  <option key={s.id} value={s.id}>{s.label}</option>
                ))}
              </select>
              <button
                type="button"
                onClick={bulkTransition}
                disabled={!bulkTargetStatus}
                style={{
                  background: '#6e5527',
                  color: 'white',
                  border: 'none',
                  borderRadius: 4,
                  padding: '0.4rem 0.85rem',
                  cursor: bulkTargetStatus ? 'pointer' : 'not-allowed',
                  opacity: bulkTargetStatus ? 1 : 0.5,
                  fontFamily: 'inherit',
                  fontSize: '0.82rem',
                  fontWeight: 600,
                }}
              >
                Anvend
              </button>
              <button
                type="button"
                onClick={() => setSelectedIds(new Set(filteredCases.map((c) => c.id)))}
                style={{
                  background: 'transparent',
                  color: 'white',
                  border: '1px solid rgba(255,255,255,0.4)',
                  borderRadius: 4,
                  padding: '0.4rem 0.65rem',
                  cursor: 'pointer',
                  fontSize: '0.78rem',
                }}
              >
                Vælg alle synlige
              </button>
              <button
                type="button"
                onClick={() => setSelectedIds(new Set())}
                style={{
                  background: 'transparent',
                  color: 'white',
                  border: '1px solid rgba(255,255,255,0.4)',
                  borderRadius: 4,
                  padding: '0.4rem 0.65rem',
                  cursor: 'pointer',
                  fontSize: '0.78rem',
                  marginLeft: 'auto',
                }}
              >
                ✕ Ryd valg
              </button>
            </div>
          )}

          <HelpHint>
            <strong>Klik et kort</strong> for at åbne sagen — kladder fortsætter
            i indkøbsprocessen, vurderede åbner historikken, remediation åbner
            vurderingsmotoren. <strong>Træk i prikkerne</strong> <kbd>⋮⋮</kbd> i
            øverste højre hjørne for at flytte sagen til en anden kolonne.
            <br />
            <strong>Vælg flere</strong> via checkbox øverst på hvert kort for at
            flytte/arkivere bulk.
          </HelpHint>
        </>
      )}

      <KanbanGrid>
        {STATUSES.map((s) => {
          const items = grouped[s.id] || [];
          return (
            <Column
              key={s.id}
              $dragOver={dragOverColumn === s.id}
              onDragOver={(e) => handleDragOver(e, s.id)}
              onDragLeave={() => setDragOverColumn(null)}
              onDrop={(e) => handleDrop(e, s.id)}
            >
              <ColumnHead $accent={STATUS_ACCENT[s.id]}>
                <ColumnTitle $accent={STATUS_ACCENT[s.id]}>{s.label}</ColumnTitle>
                <ColumnCount>{items.length}</ColumnCount>
              </ColumnHead>
              {items.length === 0 && !isLoading && (
                <EmptyHint>
                  {s.id === 'kladde' ? (
                    <>
                      Ingen kladder endnu
                      <br />
                      <EmptyCta type="button" onClick={() => navigate('/indkoebsproces')}>
                        + Start ny sag
                      </EmptyCta>
                    </>
                  ) : (
                    <>Ingen sager i {s.label.toLowerCase()}</>
                  )}
                </EmptyHint>
              )}
              {items.map((c) => {
                const intake = c.intake_state || null;
                const progress = c.status === 'kladde' ? intakeProgress(intake) : null;
                const previewText = (intake?.behov || intake?.system_description || c.notes || '').trim();
                const targetPath = cardClickPath(c);
                return (
                  <Card
                    key={c.id}
                    draggable
                    role="link"
                    tabIndex={0}
                    onDragStart={(e) => handleDragStart(e, c.id)}
                    onClick={(e) => {
                      // Ignorer click hvis checkbox blev klikket
                      if (e.target.closest('.bulk-checkbox')) return;
                      navigate(targetPath);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        navigate(targetPath);
                      }
                    }}
                    title={`${cardCtaLabel(c)} — ${c.case_id}`}
                    style={selectedIds.has(c.id) ? { boxShadow: '0 0 0 2px #0d2e54' } : undefined}
                  >
                    <label
                      className="bulk-checkbox"
                      onClick={(e) => e.stopPropagation()}
                      style={{
                        position: 'absolute',
                        top: 8,
                        left: 8,
                        cursor: 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        padding: 2,
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={selectedIds.has(c.id)}
                        onChange={() => toggleSelected(c.id)}
                        aria-label={`Vælg sag ${c.case_id}`}
                        style={{ cursor: 'pointer', width: 14, height: 14 }}
                      />
                    </label>
                    <CardCaseId style={{ paddingLeft: 22 }}>
                      {c.case_id}
                      {progress && ` · trin ${progress.step}/4`}
                    </CardCaseId>
                    <CardTitle>{c.title}</CardTitle>
                    {previewText && (
                      <CardPreview>{previewText}</CardPreview>
                    )}
                    {progress && (
                      <CardProgress>
                        <span>{progress.pct}%</span>
                        <div className="bar">
                          <div className="fill" style={{ width: `${progress.pct}%` }} />
                        </div>
                        <span>{progress.filled}/{progress.total}</span>
                      </CardProgress>
                    )}
                    <CardMeta>
                      {c.last_aggregate_status && (
                        <span className={`pill ${aggregatePill(c.last_aggregate_status)}`}>
                          {c.last_aggregate_status}
                        </span>
                      )}
                      {c.next_review_at && (
                        <span>review · {new Date(c.next_review_at).toLocaleDateString('da-DK')}</span>
                      )}
                      {c.updated_at && (
                        <span>opdateret {new Date(c.updated_at).toLocaleDateString('da-DK')}</span>
                      )}
                    </CardMeta>
                    <CardCta>
                      <span>{cardCtaLabel(c)}</span>
                      <span className="arrow">→</span>
                    </CardCta>
                  </Card>
                );
              })}
            </Column>
          );
        })}
      </KanbanGrid>

      {showCreate && (
        <ModalOverlay onClick={() => setShowCreate(false)}>
          <ModalPanel onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
            <ModalTitle>Ny sag</ModalTitle>
            <Field>
              <label>Sags-ID</label>
              <input
                placeholder="K-2026-…"
                value={draftCase.case_id}
                onChange={(e) => setDraftCase({ ...draftCase, case_id: e.target.value })}
                required
              />
            </Field>
            <Field>
              <label>Titel</label>
              <input
                placeholder="Fx Borgerassistent — pension"
                value={draftCase.title}
                onChange={(e) => setDraftCase({ ...draftCase, title: e.target.value })}
                required
              />
            </Field>
            <Field>
              <label>Note (valgfri)</label>
              <textarea
                placeholder="Kort beskrivelse af sagen…"
                value={draftCase.notes}
                onChange={(e) => setDraftCase({ ...draftCase, notes: e.target.value })}
              />
            </Field>
            {createMutation.isError && (
              <ErrorBox>
                {String(createMutation.error?.response?.data?.detail || createMutation.error?.message)}
              </ErrorBox>
            )}
            <ModalActions>
              <SecondaryButton type="button" onClick={() => setShowCreate(false)}>
                Annullér
              </SecondaryButton>
              <PrimaryButton type="submit" disabled={createMutation.isLoading}>
                {createMutation.isLoading ? 'Opretter…' : 'Opret sag'}
              </PrimaryButton>
            </ModalActions>
          </ModalPanel>
        </ModalOverlay>
      )}
      <DataOverview scope="sager" />
    </Page>
  );
};

export default SagerPage;
