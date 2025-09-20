import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FaHistory,
  FaEye,
  FaDownload,
  FaTrash,
  FaSearch,
  FaCalendarAlt,
  FaFilter,
  FaChevronDown,
  FaChevronUp
} from 'react-icons/fa';
import { format } from 'date-fns';
import { da } from 'date-fns/locale';

const HistoryContainer = styled.div`
  max-width: 1200px;
  margin: 0 auto;
`;

const PageHeader = styled.div`
  margin-bottom: 2rem;

  h1 {
    color: ${props => props.theme.colors.gray[800]};
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  p {
    color: ${props => props.theme.colors.gray[600]};
    font-size: 1.1rem;
  }
`;

const ControlsSection = styled.div`
  background: white;
  padding: 1.5rem;
  border-radius: ${props => props.theme.borderRadius};
  box-shadow: ${props => props.theme.shadows.md};
  margin-bottom: 2rem;
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: center;
`;

const SearchBox = styled.div`
  position: relative;
  flex: 1;
  min-width: 250px;

  input {
    width: 100%;
    padding: 0.75rem 2.5rem 0.75rem 1rem;
    border: 2px solid ${props => props.theme.colors.gray[300]};
    border-radius: ${props => props.theme.borderRadius};
    font-size: 0.875rem;

    &:focus {
      border-color: ${props => props.theme.colors.primary};
      outline: none;
    }
  }

  .search-icon {
    position: absolute;
    right: 0.75rem;
    top: 50%;
    transform: translateY(-50%);
    color: ${props => props.theme.colors.gray[400]};
  }
`;

const FilterDropdown = styled.div`
  position: relative;

  button {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    background: ${props => props.theme.colors.gray[100]};
    border: 2px solid ${props => props.theme.colors.gray[300]};
    border-radius: ${props => props.theme.borderRadius};
    color: ${props => props.theme.colors.gray[700]};
    cursor: pointer;
    transition: all 0.2s ease;

    &:hover {
      background: ${props => props.theme.colors.gray[200]};
    }
  }
`;

const HistoryList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1rem;
`;

const HistoryCard = styled(motion.div)`
  background: white;
  border-radius: ${props => props.theme.borderRadius};
  box-shadow: ${props => props.theme.shadows.md};
  overflow: hidden;
  border-left: 4px solid ${props => {
    switch(props.decision) {
      case 'go': return props.theme.colors.success;
      case 'betinget-go': return props.theme.colors.warning;
      case 'no-go': return props.theme.colors.danger;
      default: return props.theme.colors.gray[300];
    }
  }};
`;

const CardHeader = styled.div`
  padding: 1.5rem;
  border-bottom: 1px solid ${props => props.theme.colors.gray[200]};
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
`;

const CardInfo = styled.div`
  flex: 1;

  h3 {
    color: ${props => props.theme.colors.gray[800]};
    margin-bottom: 0.5rem;
    font-size: 1.1rem;
  }

  .meta {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    color: ${props => props.theme.colors.gray[600]};
    font-size: 0.875rem;

    .meta-item {
      display: flex;
      align-items: center;
      gap: 0.25rem;
    }
  }
`;

const DecisionBadge = styled.span`
  padding: 0.375rem 0.75rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  background: ${props => {
    switch(props.decision) {
      case 'go': return props.theme.colors.success;
      case 'betinget-go': return props.theme.colors.warning;
      case 'no-go': return props.theme.colors.danger;
      default: return props.theme.colors.gray[400];
    }
  }};
  color: white;
`;

const RiskScore = styled.div`
  text-align: center;
  padding: 0.5rem;

  .score {
    font-size: 1.5rem;
    font-weight: 700;
    color: ${props => {
      if (props.score <= 30) return props.theme.colors.success;
      if (props.score <= 70) return props.theme.colors.warning;
      return props.theme.colors.danger;
    }};
  }

  .label {
    font-size: 0.75rem;
    color: ${props => props.theme.colors.gray[600]};
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
`;

const CardActions = styled.div`
  display: flex;
  gap: 0.5rem;
`;

const ActionButton = styled.button`
  padding: 0.5rem;
  background: ${props => props.variant === 'danger' ? props.theme.colors.danger : props.theme.colors.gray[100]};
  color: ${props => props.variant === 'danger' ? 'white' : props.theme.colors.gray[600]};
  border: none;
  border-radius: ${props => props.theme.borderRadius};
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: ${props => props.variant === 'danger' ? '#c53030' : props.theme.colors.gray[200]};
    color: ${props => props.variant === 'danger' ? 'white' : props.theme.colors.gray[800]};
  }
`;

const CardDetails = styled(motion.div)`
  padding: 1.5rem;
  background: ${props => props.theme.colors.gray[50]};
  border-top: 1px solid ${props => props.theme.colors.gray[200]};

  .summary {
    margin-bottom: 1rem;

    h4 {
      color: ${props => props.theme.colors.gray[800]};
      margin-bottom: 0.5rem;
    }

    p {
      color: ${props => props.theme.colors.gray[600]};
      line-height: 1.6;
    }
  }

  .evidence-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;

    .evidence-item {
      background: white;
      padding: 0.75rem;
      border-radius: ${props => props.theme.borderRadius};
      border-left: 3px solid ${props => props.theme.colors.primary};

      .evidence-title {
        font-weight: 600;
        color: ${props => props.theme.colors.gray[800]};
        font-size: 0.875rem;
        margin-bottom: 0.25rem;
      }

      .evidence-status {
        font-size: 0.75rem;
        color: ${props => props.theme.colors.gray[600]};
      }
    }
  }
`;

const EmptyState = styled.div`
  text-align: center;
  padding: 3rem;
  background: white;
  border-radius: ${props => props.theme.borderRadius};
  box-shadow: ${props => props.theme.shadows.md};

  .icon {
    font-size: 3rem;
    color: ${props => props.theme.colors.gray[400]};
    margin-bottom: 1rem;
  }

  h3 {
    color: ${props => props.theme.colors.gray[700]};
    margin-bottom: 0.5rem;
  }

  p {
    color: ${props => props.theme.colors.gray[500]};
  }
`;

const HistoryPage = () => {
  const [assessments, setAssessments] = useState([]);
  const [filteredAssessments, setFilteredAssessments] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedCard, setExpandedCard] = useState(null);
  const [loading, setLoading] = useState(true);

  // Mock data - In real implementation, this would fetch from an API
  useEffect(() => {
    const mockAssessments = [
      {
        id: '1',
        projectName: 'AI Chatbot for Customer Service',
        date: new Date('2025-09-19'),
        decision: 'betinget-go',
        riskScore: 65,
        aiSystem: 'Conversational AI',
        summary: 'AI-chatbot system til kundebetjening med moderate risici. Kræver yderligere dokumentation af bias-test og menneskeligt oversight.',
        evidence: [
          { title: 'Data Protection Impact Assessment', status: 'Mangler' },
          { title: 'AI System Documentation', status: 'Delvist' },
          { title: 'Risk Management System', status: 'Til stede' },
          { title: 'Human Oversight Procedures', status: 'Mangler' }
        ]
      },
      {
        id: '2',
        projectName: 'Document Classification System',
        date: new Date('2025-09-18'),
        decision: 'go',
        riskScore: 25,
        aiSystem: 'Document Processing',
        summary: 'Lavrisiko dokumentklassificeringssystem med komplet compliance dokumentation. Ingen yderligere tiltag påkrævet.',
        evidence: [
          { title: 'Data Protection Impact Assessment', status: 'Til stede' },
          { title: 'AI System Documentation', status: 'Til stede' },
          { title: 'Risk Management System', status: 'Til stede' },
          { title: 'Quality Management System', status: 'Til stede' }
        ]
      },
      {
        id: '3',
        projectName: 'Automated Hiring System',
        date: new Date('2025-09-17'),
        decision: 'no-go',
        riskScore: 85,
        aiSystem: 'HR Decision Support',
        summary: 'Højrisiko AI-system til rekruttering med kritiske compliance mangler. Betydelig risiko for diskrimination og GDPR overtrædelser.',
        evidence: [
          { title: 'Fundamental Rights Impact Assessment', status: 'Mangler' },
          { title: 'Bias Testing Documentation', status: 'Mangler' },
          { title: 'Transparency Documentation', status: 'Mangler' },
          { title: 'Appeal Process Documentation', status: 'Mangler' }
        ]
      }
    ];

    setTimeout(() => {
      setAssessments(mockAssessments);
      setFilteredAssessments(mockAssessments);
      setLoading(false);
    }, 1000);
  }, []);

  // Filter assessments based on search term
  useEffect(() => {
    if (!searchTerm) {
      setFilteredAssessments(assessments);
    } else {
      const filtered = assessments.filter(assessment =>
        assessment.projectName.toLowerCase().includes(searchTerm.toLowerCase()) ||
        assessment.aiSystem.toLowerCase().includes(searchTerm.toLowerCase())
      );
      setFilteredAssessments(filtered);
    }
  }, [searchTerm, assessments]);

  const toggleCardExpansion = (cardId) => {
    setExpandedCard(expandedCard === cardId ? null : cardId);
  };

  const handleDeleteAssessment = (id) => {
    if (window.confirm('Er du sikker på, at du vil slette denne analyse?')) {
      const updated = assessments.filter(assessment => assessment.id !== id);
      setAssessments(updated);
      setFilteredAssessments(updated);
    }
  };

  const getDecisionText = (decision) => {
    switch(decision) {
      case 'go': return 'GO';
      case 'betinget-go': return 'Betinget GO';
      case 'no-go': return 'NO-GO';
      default: return 'Ukendt';
    }
  };

  if (loading) {
    return (
      <HistoryContainer>
        <PageHeader>
          <h1><FaHistory /> Assessment Historik</h1>
          <p>Indlæser dine tidligere compliance analyser...</p>
        </PageHeader>
      </HistoryContainer>
    );
  }

  return (
    <HistoryContainer>
      <PageHeader>
        <h1><FaHistory /> Assessment Historik</h1>
        <p>Gennemse og administrer dine tidligere AI compliance analyser</p>
      </PageHeader>

      <ControlsSection>
        <SearchBox>
          <input
            type="text"
            placeholder="Søg efter projektnavn eller AI-system type..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <FaSearch className="search-icon" />
        </SearchBox>

        <FilterDropdown>
          <button>
            <FaFilter />
            Filter
            <FaChevronDown />
          </button>
        </FilterDropdown>
      </ControlsSection>

      {filteredAssessments.length === 0 ? (
        <EmptyState>
          <FaHistory className="icon" />
          <h3>Ingen assessments fundet</h3>
          <p>
            {searchTerm
              ? 'Prøv at justere dine søgekriterier eller clear søgefeltet.'
              : 'Du har endnu ikke gennemført nogen compliance analyser.'
            }
          </p>
        </EmptyState>
      ) : (
        <HistoryList>
          {filteredAssessments.map((assessment) => (
            <HistoryCard
              key={assessment.id}
              decision={assessment.decision}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              <CardHeader>
                <CardInfo>
                  <h3>{assessment.projectName}</h3>
                  <div className="meta">
                    <div className="meta-item">
                      <FaCalendarAlt />
                      {format(assessment.date, 'dd MMM yyyy', { locale: da })}
                    </div>
                    <div className="meta-item">
                      AI System: {assessment.aiSystem}
                    </div>
                  </div>
                </CardInfo>

                <RiskScore score={assessment.riskScore}>
                  <div className="score">{assessment.riskScore}</div>
                  <div className="label">Risiko</div>
                </RiskScore>

                <DecisionBadge decision={assessment.decision}>
                  {getDecisionText(assessment.decision)}
                </DecisionBadge>

                <CardActions>
                  <ActionButton
                    onClick={() => toggleCardExpansion(assessment.id)}
                    title="Se detaljer"
                  >
                    {expandedCard === assessment.id ? <FaChevronUp /> : <FaEye />}
                  </ActionButton>
                  <ActionButton title="Download rapport">
                    <FaDownload />
                  </ActionButton>
                  <ActionButton
                    variant="danger"
                    onClick={() => handleDeleteAssessment(assessment.id)}
                    title="Slet analyse"
                  >
                    <FaTrash />
                  </ActionButton>
                </CardActions>
              </CardHeader>

              <AnimatePresence>
                {expandedCard === assessment.id && (
                  <CardDetails
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    <div className="summary">
                      <h4>Sammenfatning</h4>
                      <p>{assessment.summary}</p>
                    </div>

                    <div className="evidence-grid">
                      {assessment.evidence.map((item, index) => (
                        <div key={index} className="evidence-item">
                          <div className="evidence-title">{item.title}</div>
                          <div className="evidence-status">{item.status}</div>
                        </div>
                      ))}
                    </div>
                  </CardDetails>
                )}
              </AnimatePresence>
            </HistoryCard>
          ))}
        </HistoryList>
      )}
    </HistoryContainer>
  );
};

export default HistoryPage;