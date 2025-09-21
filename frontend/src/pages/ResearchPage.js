import React, { useState } from 'react';
import styled from 'styled-components';
import { motion, AnimatePresence } from 'framer-motion';
import { useForm } from 'react-hook-form';
import { toast } from 'react-hot-toast';
import {
  FaSearch,
  FaSpinner,
  FaExternalLinkAlt,
  FaQuoteLeft,
  FaCalendarAlt,
  FaGlobeEurope,
  FaFileAlt,
  FaUniversity,
  FaBookOpen
} from 'react-icons/fa';
import axios from 'axios';

const ResearchContainer = styled.div`
  max-width: 1200px;
  margin: 0 auto;
`;

const PageHeader = styled.div`
  margin-bottom: 2rem;

  h1 {
    color: ${props => props.theme.colors.gray[800]};
    margin-bottom: 0.5rem;
  }

  p {
    color: ${props => props.theme.colors.gray[600]};
    font-size: 1.1rem;
  }
`;

const SearchSection = styled.section`
  background: white;
  padding: 2rem;
  border-radius: ${props => props.theme.borderRadius};
  box-shadow: ${props => props.theme.shadows.md};
  margin-bottom: 2rem;
`;

const SearchForm = styled.form`
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
`;

const FormGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.5rem;

  label {
    font-weight: 600;
    color: ${props => props.theme.colors.gray[700]};
  }
`;

const SearchInput = styled.input`
  padding: 1rem;
  border: 2px solid ${props => props.theme.colors.gray[300]};
  border-radius: ${props => props.theme.borderRadius};
  font-size: 1rem;
  transition: border-color 0.2s ease;

  &:focus {
    border-color: ${props => props.theme.colors.primary};
    outline: none;
  }

  &::placeholder {
    color: ${props => props.theme.colors.gray[400]};
  }
`;

const FocusAreasContainer = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
`;

const FocusAreaTag = styled.button`
  background: ${props => props.selected ? props.theme.colors.primary : props.theme.colors.gray[100]};
  color: ${props => props.selected ? 'white' : props.theme.colors.gray[700]};
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: ${props => props.selected ? props.theme.colors.primary : props.theme.colors.gray[200]};
  }
`;

const SearchButton = styled.button`
  background: ${props => props.theme.colors.primary};
  color: white;
  border: none;
  padding: 1rem 2rem;
  border-radius: ${props => props.theme.borderRadius};
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  transition: all 0.2s ease;
  align-self: flex-start;

  &:hover {
    background: ${props => props.theme.colors.primary}dd;
    transform: translateY(-1px);
  }

  &:disabled {
    background: ${props => props.theme.colors.gray[400]};
    cursor: not-allowed;
    transform: none;
  }
`;

const ResultsSection = styled.section`
  display: ${props => props.show ? 'block' : 'none'};
`;

const ResultsHeader = styled.div`
  background: white;
  padding: 1.5rem 2rem;
  border-radius: ${props => props.theme.borderRadius};
  box-shadow: ${props => props.theme.shadows.md};
  margin-bottom: 1.5rem;

  h2 {
    color: ${props => props.theme.colors.gray[800]};
    margin-bottom: 0.5rem;
  }

  .summary {
    color: ${props => props.theme.colors.gray[600]};
    line-height: 1.6;
  }
`;

const AnswerCard = styled.div`
  background: white;
  border-radius: ${props => props.theme.borderRadius};
  box-shadow: ${props => props.theme.shadows.md};
  padding: 1.75rem 2rem;
  margin-bottom: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.2rem;

  h3 {
    margin: 0;
    color: ${props => props.theme.colors.gray[800]};
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  p {
    margin: 0;
    color: ${props => props.theme.colors.gray[700]};
    line-height: 1.7;
  }
`;

const CitationList = styled.ul`
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;

  li {
    background: ${props => props.theme.colors.gray[100]};
    border-radius: 999px;
    padding: 0.4rem 0.75rem;
    font-size: 0.85rem;
    color: ${props => props.theme.colors.gray[700]};
  }
`;

const SourcesGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
`;

const CrossReferenceList = styled.ul`
  list-style: none;
  padding: 0;
  margin: 0 0 2rem;
  display: flex;
  flex-direction: column;
  gap: 1.2rem;
`;

const CrossReferenceItem = styled.li`
  background: white;
  border-radius: ${props => props.theme.borderRadius};
  border: 1px solid ${props => props.theme.colors.gray[200]};
  padding: 1.25rem 1.5rem;
  box-shadow: ${props => props.theme.shadows.sm};
  line-height: 1.6;

  p {
    margin: 0 0 0.75rem;
    color: ${props => props.theme.colors.gray[800]};
  }

  ul {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  li {
    background: ${props => props.theme.colors.gray[100]};
    border-radius: 999px;
    padding: 0.35rem 0.75rem;
    font-size: 0.85rem;
    color: ${props => props.theme.colors.gray[700]};
  }
`;

const SourceCard = styled(motion.div)`
  background: white;
  border-radius: ${props => props.theme.borderRadius};
  box-shadow: ${props => props.theme.shadows.md};
  overflow: hidden;
  transition: all 0.3s ease;

  &:hover {
    box-shadow: ${props => props.theme.shadows.lg};
    transform: translateY(-2px);
  }
`;

const SourceHeader = styled.div`
  padding: 1.5rem;
  border-bottom: 1px solid ${props => props.theme.colors.gray[200]};

  .authority {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: ${props => props.theme.colors.primary};
    color: white;
    padding: 0.25rem 0.75rem;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-bottom: 1rem;
  }

  .title {
    font-size: 1.125rem;
    font-weight: 600;
    color: ${props => props.theme.colors.gray[800]};
    margin-bottom: 0.5rem;
    line-height: 1.4;
  }

  .meta {
    display: flex;
    align-items: center;
    gap: 1rem;
    font-size: 0.875rem;
    color: ${props => props.theme.colors.gray[500]};

    .domain {
      display: flex;
      align-items: center;
      gap: 0.25rem;
    }

    .date {
      display: flex;
      align-items: center;
      gap: 0.25rem;
    }
  }
`;

const SourceContent = styled.div`
  padding: 1.5rem;

  .relevance-score {
    display: inline-block;
    background: ${props => props.score > 0.8 ? props.theme.colors.success :
                         props.score > 0.6 ? props.theme.colors.warning :
                         props.theme.colors.danger};
    color: white;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-bottom: 1rem;
  }
`;

const SourceLink = styled.a`
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  color: ${props => props.theme.colors.primary};
  text-decoration: none;
  font-weight: 500;
  margin-top: 1rem;

  &:hover {
    text-decoration: underline;
  }
`;

const CitationsSection = styled.div`
  background: white;
  border-radius: ${props => props.theme.borderRadius};
  box-shadow: ${props => props.theme.shadows.md};
  overflow: hidden;
`;

const CitationsHeader = styled.div`
  background: ${props => props.theme.colors.gray[50]};
  padding: 1.5rem 2rem;
  border-bottom: 1px solid ${props => props.theme.colors.gray[200]};

  h3 {
    color: ${props => props.theme.colors.gray[800]};
    margin: 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
`;

const CitationsList = styled.div`
  padding: 1.5rem 2rem;
`;

const CitationItem = styled.div`
  border-left: 4px solid ${props => props.theme.colors.primary};
  padding-left: 1rem;
  margin-bottom: 1.5rem;

  &:last-child {
    margin-bottom: 0;
  }

  .quote {
    font-style: italic;
    color: ${props => props.theme.colors.gray[700]};
    margin-bottom: 0.5rem;
    line-height: 1.6;
  }

  .citation-source {
    font-size: 0.875rem;
    color: ${props => props.theme.colors.gray[500]};
    font-weight: 500;
  }

  .confidence {
    display: inline-block;
    background: ${props => props.confidence > 0.8 ? props.theme.colors.success + '20' : props.theme.colors.warning + '20'};
    color: ${props => props.confidence > 0.8 ? props.theme.colors.success : props.theme.colors.warning};
    padding: 0.125rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-left: 0.5rem;
  }
`;

const LoadingSpinner = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: ${props => props.theme.colors.primary};

  .spinner {
    animation: spin 1s linear infinite;
  }

  .text {
    margin-left: 1rem;
    font-weight: 500;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
`;

const ResearchPage = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [selectedFocusAreas, setSelectedFocusAreas] = useState(['EU AI Act', 'GDPR']);

  const { register, handleSubmit, watch } = useForm();

  const focusAreas = [
    'EU AI Act',
    'GDPR',
    'Dansk lovgivning',
    'Automatiserede beslutninger',
    'Højrisiko AI systemer',
    'Biometrisk identifikation',
    'Databeskyttelse',
    'Datatilsynets vejledninger'
  ];

  const toggleFocusArea = (area) => {
    setSelectedFocusAreas(prev =>
      prev.includes(area)
        ? prev.filter(item => item !== area)
        : [...prev, area]
    );
  };

  const onSubmit = async (data) => {
    if (!data.emne.trim()) {
      toast.error('Indtast venligst et research emne');
      return;
    }

    setIsLoading(true);

    try {
      const response = await axios.post('/api/research/juridisk', {
        emne: data.emne,
        fokusområder: selectedFocusAreas
      });

      setResults(response.data.resultat);
      toast.success(`Research afsluttet - ${response.data.resultat.sources.length} kilder fundet`);
    } catch (error) {
      console.error('Research fejl:', error);
      toast.error('Der opstod en fejl under research. Prøv igen.');
    } finally {
      setIsLoading(false);
    }
  };

  const getAuthorityIcon = (authority) => {
    switch (authority) {
      case 'EU-Kommissionen':
      case 'EU':
        return FaUniversity;
      case 'Datatilsynet':
        return FaGlobeEurope;
      case 'EDPB':
        return FaBookOpen;
      default:
        return FaFileAlt;
    }
  };

  return (
    <ResearchContainer>
      <PageHeader>
        <h1>Juridisk Research</h1>
        <p>
          Udfør dyb research i relevant lovgivning med præcise kildehenvisninger.
          Søg i autoritative kilder som EUR-Lex, Datatilsynet og EDPB guidelines.
        </p>
      </PageHeader>

      <SearchSection>
        <h2 style={{ marginBottom: '1.5rem', color: '#1e293b' }}>Start Research</h2>

        <SearchForm onSubmit={handleSubmit(onSubmit)}>
          <FormGroup>
            <label htmlFor="emne">Research Emne</label>
            <SearchInput
              {...register('emne', { required: true })}
              placeholder="F.eks. 'højrisiko AI systemer i sundhedssektoren' eller 'automatiserede beslutninger GDPR'"
            />
          </FormGroup>

          <FormGroup>
            <label>Fokusområder</label>
            <FocusAreasContainer>
              {focusAreas.map((area) => (
                <FocusAreaTag
                  key={area}
                  type="button"
                  selected={selectedFocusAreas.includes(area)}
                  onClick={() => toggleFocusArea(area)}
                >
                  {area}
                </FocusAreaTag>
              ))}
            </FocusAreasContainer>
          </FormGroup>

          <SearchButton type="submit" disabled={isLoading}>
            {isLoading ? (
              <>
                <FaSpinner className="spinner" />
                Researcher...
              </>
            ) : (
              <>
                <FaSearch />
                Start Research
              </>
            )}
          </SearchButton>
        </SearchForm>
      </SearchSection>

      <AnimatePresence>
        {isLoading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <LoadingSpinner>
              <FaSpinner className="spinner" size={24} />
              <span className="text">Søger i juridiske databaser...</span>
            </LoadingSpinner>
          </motion.div>
        )}
      </AnimatePresence>

      <ResultsSection show={results && !isLoading}>
        {results && (
          <>
            <ResultsHeader>
              <h2>Research Resultater: "{results.query}"</h2>
              <div className="summary">
                {results.summary}
              </div>
            </ResultsHeader>

            {results.llm_answer && (
              <AnswerCard>
                <h3>
                  <FaBookOpen /> Samlet svar
                </h3>
                <p>{results.llm_answer}</p>
                {results.llm_answer_citations && results.llm_answer_citations.length > 0 && (
                  <CitationList>
                    {results.llm_answer_citations.map((citation, index) => (
                      <li key={`answer-citation-${index}`}>
                        <a
                          href={citation.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ color: '#1d4ed8', textDecoration: 'none' }}
                        >
                          {citation.authority || citation.title}
                        </a>
                      </li>
                    ))}
                  </CitationList>
                )}
              </AnswerCard>
            )}

            {results.sources.length > 0 && (
              <>
                <h3 style={{ marginBottom: '1rem', color: '#1e293b' }}>
                  Kilder ({results.sources.length})
                </h3>
                {results.cross_references && results.cross_references.length > 0 && (
                  <>
                    <h4 style={{ marginBottom: '0.75rem', color: '#334155' }}>Krydshenvisninger</h4>
                    <CrossReferenceList>
                      {results.cross_references.map((item, index) => (
                        <CrossReferenceItem key={`cross-ref-${index}`}>
                          <p>{item.statement}</p>
                          <ul>
                            {item.citations.map((citation, citationIndex) => (
                              <li key={`citation-${citationIndex}`}>
                                <a
                                  href={citation.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  style={{ color: '#2563eb', textDecoration: 'none' }}
                                >
                                  {citation.authority || citation.title}
                                </a>
                              </li>
                            ))}
                          </ul>
                        </CrossReferenceItem>
                      ))}
                    </CrossReferenceList>
                  </>
                )}
                <SourcesGrid>
                  {results.sources.map((source, index) => {
                    const AuthorityIcon = getAuthorityIcon(source.authority);
                    return (
                      <SourceCard
                        key={index}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.1 }}
                      >
                        <SourceHeader>
                          {source.authority && (
                            <div className="authority">
                              <AuthorityIcon size={12} />
                              {source.authority}
                            </div>
                          )}
                          <div className="title">{source.title}</div>
                          <div className="meta">
                            <div className="domain">
                              <FaGlobeEurope size={12} />
                              {source.domain}
                            </div>
                            <div className="date">
                              <FaCalendarAlt size={12} />
                              {new Date(source.date_accessed).toLocaleDateString('da-DK')}
                            </div>
                          </div>
                        </SourceHeader>
                        <SourceContent>
                          <div className="relevance-score" score={source.relevance_score}>
                            Relevans: {Math.round(source.relevance_score * 100)}%
                          </div>
                          <SourceLink href={source.url} target="_blank" rel="noopener noreferrer">
                            Læs kilde <FaExternalLinkAlt size={12} />
                          </SourceLink>
                        </SourceContent>
                      </SourceCard>
                    );
                  })}
                </SourcesGrid>
              </>
            )}

            {results.citations.length > 0 && (
              <CitationsSection>
                <CitationsHeader>
                  <h3>
                    <FaQuoteLeft />
                    Citationer ({results.citations.length})
                  </h3>
                </CitationsHeader>
                <CitationsList>
                  {results.citations.map((citation, index) => (
                    <CitationItem
                      key={index}
                      confidence={citation.confidence}
                    >
                      <div className="quote">"{citation.text}"</div>
                      <div className="citation-source">
                        — {citation.source.title} ({citation.source.authority || citation.source.domain})
                        <span className="confidence">
                          {Math.round(citation.confidence * 100)}% sikkerhed
                        </span>
                      </div>
                    </CitationItem>
                  ))}
                </CitationsList>
              </CitationsSection>
            )}
          </>
        )}
      </ResultsSection>
    </ResearchContainer>
  );
};

export default ResearchPage;
