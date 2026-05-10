import React, { useState, useMemo } from 'react';
import styled from 'styled-components';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import DataOverview from '../components/data-overview/DataOverview';

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
  kladde: '#8a8f96',        // textFaded
  vurderet: '#555a64',      // textMuted
  remediation: '#b08a4a',   // bronze (betinget — kræver handling, ikke fejl)
  godkendt: '#2f6b2f',      // success
  idriftsat: '#0d2e54',     // primary (kongelig blå — i drift)
  arkiveret: '#8a8f96',     // faded
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
  padding: 0.85rem 0.95rem;
  cursor: grab;
  transition: border-color ${(p) => p.theme.animations.transitionFast},
              box-shadow ${(p) => p.theme.animations.transitionFast};
  display: flex;
  flex-direction: column;
  gap: 0.35rem;

  &:hover {
    border-color: ${(p) => p.theme.colors.primary};
    box-shadow: 0 2px 6px rgba(20, 17, 13, 0.06);
  }

  &:active { cursor: grabbing; }
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
  font-style: italic;
  padding: 1rem 0.4rem;
  text-align: center;
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

const SagerPage = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data, isLoading, isError, error } = useQuery('v3-cases', fetchCases);
  const cases = data?.items || [];

  const [showCreate, setShowCreate] = useState(false);
  const [draftCase, setDraftCase] = useState({ case_id: '', title: '', notes: '' });
  const [dragOverColumn, setDragOverColumn] = useState(null);
  const [draggingId, setDraggingId] = useState(null);

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
    cases.forEach((c) => {
      if (out[c.status]) out[c.status].push(c);
    });
    return out;
  }, [cases]);

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
        <PrimaryButton type="button" onClick={() => setShowCreate(true)}>
          + Ny sag
        </PrimaryButton>
      </Header>

      {isError && (
        <ErrorBox>
          Kunne ikke hente sager: {String(error?.message || error)}
        </ErrorBox>
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
                <EmptyHint>Ingen sager</EmptyHint>
              )}
              {items.map((c) => (
                <Card
                  key={c.id}
                  draggable
                  onDragStart={(e) => handleDragStart(e, c.id)}
                  onClick={() => {
                    if (c.last_assessment_log_id) {
                      navigate(`/historik/${c.last_assessment_log_id}`);
                    }
                  }}
                  title={c.last_assessment_log_id ? 'Klik for at åbne seneste vurdering' : undefined}
                >
                  <CardCaseId>{c.case_id}</CardCaseId>
                  <CardTitle>{c.title}</CardTitle>
                  <CardMeta>
                    {c.last_aggregate_status && (
                      <span className={`pill ${aggregatePill(c.last_aggregate_status)}`}>
                        {c.last_aggregate_status}
                      </span>
                    )}
                    {c.next_review_at && (
                      <span>review · {new Date(c.next_review_at).toLocaleDateString('da-DK')}</span>
                    )}
                  </CardMeta>
                </Card>
              ))}
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
