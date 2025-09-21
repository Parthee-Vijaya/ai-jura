import React, { useMemo, useState } from 'react';
import styled from 'styled-components';
import { useQuery, useQueryClient } from 'react-query';
import { toast } from 'react-hot-toast';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  FaBalanceScale,
  FaPaperPlane,
  FaClock,
  FaEnvelopeOpenText,
  FaRedo,
  FaCheckCircle,
  FaExternalLinkAlt
} from 'react-icons/fa';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '';

const buildApiUrl = (path) => {
  if (!API_BASE_URL) {
    return path;
  }
  return `${API_BASE_URL.replace(/\/$/, '')}${path}`;
};

const fetchCases = async () => {
  const response = await fetch(buildApiUrl('/api/ai-cases'));
  if (!response.ok) {
    throw new Error('Kunne ikke hente AI sager');
  }
  return response.json();
};

const submitCase = async (payload) => {
  const response = await fetch(buildApiUrl('/api/ai-cases'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    const message = error?.detail || 'Kunne ikke oprette AI sag';
    throw new Error(message);
  }

  return response.json();
};

const PageContainer = styled.div`
  max-width: 960px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 2.5rem;
`;

const Header = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.75rem;

  h1 {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    color: ${props => props.theme.colors.text};
  }

  p {
    color: ${props => props.theme.colors.textMuted};
    font-size: 1.05rem;
    max-width: 680px;
  }
`;

const FormCard = styled.form`
  background: ${props => props.theme.colors.surface};
  border-radius: ${props => props.theme.borderRadiusLarge};
  box-shadow: ${props => props.theme.shadows.lg};
  padding: 2rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  border: 1px solid ${props => props.theme.colors.border};
`;

const FieldGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.65rem;

  label {
    font-weight: 600;
    color: ${props => props.theme.colors.text};
  }

  input,
  textarea {
    width: 100%;
    padding: 0.85rem 1rem;
    border-radius: ${props => props.theme.borderRadius};
    border: 1px solid ${props => props.theme.colors.border};
    background: ${props => props.theme.colors.surfaceAlt};
    color: ${props => props.theme.colors.text};
    font-size: 0.95rem;
    transition: ${props => props.theme.animations.transitionFast};

    &:focus {
      border-color: ${props => props.theme.colors.primary};
      outline: none;
      box-shadow: ${props => props.theme.shadows.focus};
    }
  }

  textarea {
    min-height: 180px;
    resize: vertical;
  }
`;

const ActionsRow = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 1rem;
`;

const HelperText = styled.span`
  color: ${props => props.theme.colors.textMuted};
  font-size: 0.85rem;
`;

const SubmitButton = styled.button`
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.85rem 1.5rem;
  border-radius: 999px;
  border: none;
  background: ${props => props.theme.colors.gradients.primary};
  color: ${props => props.theme.colors.white};
  font-weight: 600;
  cursor: pointer;
  transition: ${props => props.theme.animations.transitionFast};

  &:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: ${props => props.theme.shadows.md};
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
`;

const CasesSection = styled.section`
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
`;

const SectionHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 1rem;

  h2 {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    color: ${props => props.theme.colors.text};
    font-size: 1.25rem;
  }
`;

const RefreshButton = styled.button`
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.6rem 1rem;
  border-radius: ${props => props.theme.borderRadius};
  border: 1px solid ${props => props.theme.colors.border};
  background: ${props => props.theme.colors.surfaceAlt};
  color: ${props => props.theme.colors.text};
  cursor: pointer;
  transition: ${props => props.theme.animations.transitionFast};

  &:hover {
    background: ${props => props.theme.colors.surface};
    transform: translateY(-1px);
  }
`;

const CasesGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 1.25rem;
`;

const CaseCard = styled(motion.article)`
  background: ${props => props.theme.colors.surface};
  border-radius: ${props => props.theme.borderRadiusLarge};
  border: 1px solid ${props => props.theme.colors.border};
  box-shadow: ${props => props.theme.shadows.sm};
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: inherit;
    background: linear-gradient(135deg, rgba(26, 54, 93, 0.08), rgba(26, 54, 93, 0));
    opacity: 0.6;
    pointer-events: none;
  }

  > * {
    position: relative;
    z-index: 1;
  }
`;

const CaseTitle = styled.h3`
  margin: 0;
  font-size: 1.05rem;
  color: ${props => props.theme.colors.text};
`;

const CaseDescription = styled.p`
  margin: 0;
  color: ${props => props.theme.colors.textMuted};
  font-size: 0.9rem;
  line-height: 1.45;
`;

const CaseMeta = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
  color: ${props => props.theme.colors.textMuted};
`;

const StatusBadge = styled.span`
  align-self: flex-start;
  padding: 0.25rem 0.55rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  background: ${props => {
    switch (props.status) {
      case 'sent':
        return 'rgba(16, 185, 129, 0.15)';
      case 'failed':
        return 'rgba(239, 68, 68, 0.15)';
      case 'skipped':
        return 'rgba(79, 70, 229, 0.15)';
      default:
        return 'rgba(234, 179, 8, 0.18)';
    }
  }};
  color: ${props => {
    switch (props.status) {
      case 'sent':
        return '#047857';
      case 'failed':
        return '#b91c1c';
      case 'skipped':
        return '#4338ca';
      default:
        return '#92400e';
    }
  }};
`;

const EmptyState = styled.div`
  background: ${props => props.theme.colors.surface};
  border-radius: ${props => props.theme.borderRadiusLarge};
  border: 1px dashed ${props => props.theme.colors.border};
  padding: 2.5rem;
  text-align: center;
  color: ${props => props.theme.colors.textMuted};
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  align-items: center;

  svg {
    font-size: 2rem;
    opacity: 0.7;
  }

  h3 {
    margin: 0;
    color: ${props => props.theme.colors.text};
  }
`;

const SuccessBanner = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  background: ${props => props.theme.mode === 'dark' ? 'rgba(34, 197, 94, 0.12)' : 'rgba(34, 197, 94, 0.15)'};
  border: 1px solid ${props => props.theme.mode === 'dark' ? 'rgba(34, 197, 94, 0.35)' : 'rgba(34, 197, 94, 0.45)'};
  border-radius: ${props => props.theme.borderRadius};
  padding: 1rem 1.25rem;
  color: ${props => props.theme.colors.text};
`;

const HistoryLinkButton = styled.button`
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.6rem 1.1rem;
  border-radius: 999px;
  border: none;
  background: ${props => props.theme.colors.primary};
  color: ${props => props.theme.colors.white};
  cursor: pointer;
  font-weight: 600;
  transition: ${props => props.theme.animations.transitionFast};

  &:hover {
    transform: translateY(-1px);
    box-shadow: ${props => props.theme.shadows.sm};
  }
`;

const STATUS_LABELS = {
  sent: 'Email sendt',
  skipped: 'Email ikke konfigureret',
  failed: 'Email fejl',
  pending: 'Afventer email'
};

const AICasesPage = () => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [lastCase, setLastCase] = useState(null);
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const { data: casesData = [], isLoading, isError, refetch } = useQuery(['ai-cases'], fetchCases, {
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });

  const handleSubmit = async (event) => {
    event.preventDefault();

    const trimmedTitle = title.trim();
    const trimmedDescription = description.trim();

    if (!trimmedTitle || !trimmedDescription) {
      toast.error('Udfyld både titel og beskrivelse');
      return;
    }

    setSubmitting(true);
    try {
      const created = await submitCase({ title: trimmedTitle, description: trimmedDescription });
      toast.success('AI sag sendt til behandling');
      setTitle('');
      setDescription('');
      setLastCase(created);
      queryClient.invalidateQueries(['ai-cases']);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleViewHistory = () => {
    if (lastCase) {
      navigate('/historik', { state: { highlightCaseId: lastCase.id } });
    } else {
      navigate('/historik');
    }
  };

  const cases = useMemo(() => {
    return (casesData || []).map((item) => ({
      ...item,
      createdAt: item.created_at ? new Date(item.created_at) : null,
    }));
  }, [casesData]);

  return (
    <PageContainer>
      <Header>
        <h1>
          <FaBalanceScale />
          AI Sager
        </h1>
        <p>
          Opret AI-relaterede sager direkte til compliance-teamet. Beskriv udfordringen eller casen, så bliver den sendt videre til ServicePortalen@kalundborg.dk og registreret i historikken.
        </p>
      </Header>

      {lastCase && (
        <SuccessBanner>
          <div>
            <strong>
              <FaCheckCircle /> Sagen er registreret
            </strong>
            <div>
              "{lastCase.title}" blev gemt {lastCase.created_at ? new Date(lastCase.created_at).toLocaleString('da-DK') : 'lige nu'}.
            </div>
          </div>
          <HistoryLinkButton onClick={handleViewHistory}>
            Se i historik
            <FaExternalLinkAlt size={12} />
          </HistoryLinkButton>
        </SuccessBanner>
      )}

      <FormCard onSubmit={handleSubmit}>
        <FieldGroup>
          <label htmlFor="case-title">Overskrift</label>
          <input
            id="case-title"
            type="text"
            placeholder='F.eks. "AI chatbot for borgerservice"'
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            disabled={submitting}
            maxLength={150}
          />
        </FieldGroup>

        <FieldGroup>
          <label htmlFor="case-description">Beskrivelse</label>
          <textarea
            id="case-description"
            placeholder="Beskriv sagen, udfordringer og relevante detaljer..."
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            disabled={submitting}
            maxLength={5000}
          />
        </FieldGroup>

        <ActionsRow>
          <HelperText>
            Alle sager logges og sendes til ServicePortalen@kalundborg.dk
          </HelperText>
          <SubmitButton type="submit" disabled={submitting}>
            <FaPaperPlane />
            {submitting ? 'Sender...' : 'Send AI sag'}
          </SubmitButton>
        </ActionsRow>
      </FormCard>

      <CasesSection>
        <SectionHeader>
          <h2>
            <FaEnvelopeOpenText /> Registrerede sager
          </h2>
          <RefreshButton type="button" onClick={() => refetch()}>
            <FaRedo /> Opdater
          </RefreshButton>
        </SectionHeader>

        {isLoading ? (
          <EmptyState>
            <FaClock />
            <h3>Henter AI sager...</h3>
            <p>Vent venligst et øjeblik.</p>
          </EmptyState>
        ) : isError ? (
          <EmptyState>
            <FaEnvelopeOpenText />
            <h3>Kunne ikke hente AI sager</h3>
            <p>Prøv igen senere eller kontakt support.</p>
          </EmptyState>
        ) : cases.length === 0 ? (
          <EmptyState>
            <FaEnvelopeOpenText />
            <h3>Ingen AI sager endnu</h3>
            <p>Opret din første sag via formularen ovenfor.</p>
          </EmptyState>
        ) : (
          <CasesGrid>
            {cases.map((item) => (
              <CaseCard
                key={item.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
              >
                <StatusBadge status={item.email_status}>
                  {STATUS_LABELS[item.email_status] || item.email_status}
                </StatusBadge>
                <CaseTitle>{item.title}</CaseTitle>
                {item.createdAt && (
                  <CaseMeta>
                    <FaClock />
                    {item.createdAt.toLocaleString('da-DK')}
                  </CaseMeta>
                )}
                <CaseDescription>{item.description}</CaseDescription>
              </CaseCard>
            ))}
          </CasesGrid>
        )}
      </CasesSection>
    </PageContainer>
  );
};

export default AICasesPage;
