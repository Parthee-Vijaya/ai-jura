import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'react-hot-toast';
import {
  FaSearch,
  FaSpinner,
  FaExternalLinkAlt,
  FaGavel,
  FaChevronDown,
  FaChevronUp,
  FaCheckCircle,
  FaBook
} from 'react-icons/fa';
import axios from 'axios';

// ============ STYLED COMPONENTS (Matching ResearchPage) ============

const LawContainer = styled.div`
  max-width: 1200px;
  margin: 0 auto;
`;

const PageHeader = styled.div`
  margin-bottom: 2rem;
  text-align: center;

  h1 {
    color: ${props => props.theme.isDark ? props.theme.colors.gray[100] : props.theme.colors.gray[800]};
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1rem;

    .icon {
      color: ${props => props.theme.colors.primary};
    }
  }

  p {
    color: ${props => props.theme.isDark ? props.theme.colors.gray[400] : props.theme.colors.gray[600]};
    font-size: 1.1rem;
  }
`;

const SearchCard = styled.div`
  background: ${props => props.theme.isDark
    ? 'rgba(45, 55, 72, 0.95)'
    : 'rgba(255, 255, 255, 0.95)'};
  backdrop-filter: blur(20px);
  border-radius: ${props => props.theme.borderRadiusLarge};
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 8px 32px 0 rgba(201, 68, 22, 0.37);
  border: 1px solid ${props => props.theme.isDark
    ? 'rgba(255, 255, 255, 0.1)'
    : 'rgba(0, 0, 0, 0.05)'};
`;

const SearchInput = styled.input`
  width: 100%;
  padding: 1rem 1rem 1rem 3rem;
  border: 2px solid ${props => props.theme.isDark
    ? props.theme.colors.gray[600]
    : props.theme.colors.gray[300]};
  border-radius: ${props => props.theme.borderRadius};
  font-size: 1rem;
  background: ${props => props.theme.isDark
    ? props.theme.colors.gray[700]
    : 'white'};
  color: ${props => props.theme.isDark
    ? props.theme.colors.gray[100]
    : props.theme.colors.gray[900]};
  transition: all 0.2s ease;

  &:focus {
    border-color: ${props => props.theme.colors.primary};
    outline: none;
    box-shadow: 0 0 0 3px ${props => props.theme.colors.primary}33;
  }

  &::placeholder {
    color: ${props => props.theme.isDark
      ? props.theme.colors.gray[500]
      : props.theme.colors.gray[400]};
  }
`;

const SearchInputWrapper = styled.div`
  position: relative;
  margin-bottom: 1.5rem;

  .search-icon {
    position: absolute;
    left: 1rem;
    top: 50%;
    transform: translateY(-50%);
    color: ${props => props.theme.colors.gray[400]};
  }
`;

const CategorySelect = styled.select`
  padding: 0.75rem;
  border: 2px solid ${props => props.theme.isDark
    ? props.theme.colors.gray[600]
    : props.theme.colors.gray[300]};
  border-radius: ${props => props.theme.borderRadius};
  background: ${props => props.theme.isDark
    ? props.theme.colors.gray[700]
    : 'white'};
  color: ${props => props.theme.isDark
    ? props.theme.colors.gray[100]
    : props.theme.colors.gray[900]};
  font-size: 0.95rem;
  cursor: pointer;
  margin-bottom: 1rem;

  &:focus {
    border-color: ${props => props.theme.colors.primary};
    outline: none;
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
  width: 100%;

  &:hover:not(:disabled) {
    background: ${props => props.theme.colors.primary}dd;
    transform: translateY(-1px);
  }

  &:disabled {
    background: ${props => props.theme.colors.gray[400]};
    cursor: not-allowed;
  }
`;

const AnswerCard = styled(motion.div)`
  background: ${props => props.theme.isDark
    ? 'linear-gradient(135deg, rgba(66, 76, 92, 0.95) 0%, rgba(45, 55, 72, 0.95) 100%)'
    : 'linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(249, 250, 251, 0.95) 100%)'};
  backdrop-filter: blur(30px);
  border-radius: ${props => props.theme.borderRadiusLarge};
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 8px 32px 0 rgba(102, 126, 234, 0.2);
  border: 1px solid ${props => props.theme.isDark
    ? 'rgba(255, 255, 255, 0.1)'
    : 'rgba(0, 0, 0, 0.05)'};

  h3 {
    color: ${props => props.theme.isDark
      ? props.theme.colors.gray[100]
      : props.theme.colors.gray[800]};
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;

    .icon {
      color: ${props => props.theme.colors.primary};
    }
  }
`;

const AnswerText = styled.div`
  color: ${props => props.theme.isDark
    ? props.theme.colors.gray[300]
    : props.theme.colors.gray[700]};
  line-height: 1.8;
  font-size: 1.05rem;
  margin-bottom: 1.5rem;

  p {
    margin-bottom: 1rem;
  }

  strong {
    color: ${props => props.theme.isDark
      ? props.theme.colors.gray[100]
      : props.theme.colors.gray[900]};
  }
`;

const ConfidenceBadge = styled.div`
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.875rem;
  font-weight: 600;
  background: ${props => {
    const conf = props.confidence;
    if (conf >= 0.8) return 'rgba(34, 197, 94, 0.2)';
    if (conf >= 0.6) return 'rgba(234, 179, 8, 0.2)';
    return 'rgba(239, 68, 68, 0.2)';
  }};
  color: ${props => {
    const conf = props.confidence;
    if (conf >= 0.8) return '#22c55e';
    if (conf >= 0.6) return '#eab308';
    return '#ef4444';
  }};
`;

const KeyPointsList = styled.ul`
  list-style: none;
  padding: 0;
  margin-top: 1.5rem;

  li {
    padding: 0.75rem;
    margin-bottom: 0.5rem;
    background: ${props => props.theme.isDark
      ? 'rgba(66, 76, 92, 0.5)'
      : 'rgba(249, 250, 251, 0.8)'};
    border-left: 3px solid ${props => props.theme.colors.primary};
    border-radius: 4px;
    color: ${props => props.theme.isDark
      ? props.theme.colors.gray[300]
      : props.theme.colors.gray[700]};
  }
`;

const SourcesCard = styled.div`
  background: ${props => props.theme.isDark
    ? 'rgba(45, 55, 72, 0.95)'
    : 'rgba(255, 255, 255, 0.95)'};
  backdrop-filter: blur(20px);
  border-radius: ${props => props.theme.borderRadiusLarge};
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 8px 32px 0 rgba(201, 68, 22, 0.37);
  border: 1px solid ${props => props.theme.isDark
    ? 'rgba(255, 255, 255, 0.1)'
    : 'rgba(0, 0, 0, 0.05)'};

  h3 {
    color: ${props => props.theme.isDark
      ? props.theme.colors.gray[100]
      : props.theme.colors.gray[800]};
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
`;

const SourceItem = styled.div`
  padding: 1rem;
  margin-bottom: 1rem;
  background: ${props => props.theme.isDark
    ? 'rgba(66, 76, 92, 0.5)'
    : 'rgba(249, 250, 251, 0.8)'};
  border-radius: ${props => props.theme.borderRadius};
  border: 1px solid ${props => props.theme.isDark
    ? 'rgba(255, 255, 255, 0.05)'
    : 'rgba(0, 0, 0, 0.05)'};
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: ${props => props.theme.isDark
      ? 'rgba(66, 76, 92, 0.7)'
      : 'rgba(249, 250, 251, 1)'};
    border-color: ${props => props.theme.colors.primary};
  }

  .law-header {
    display: flex;
    justify-content: space-between;
    align-items: start;
    gap: 1rem;
  }

  .law-title {
    font-weight: 600;
    color: ${props => props.theme.isDark
      ? props.theme.colors.gray[100]
      : props.theme.colors.gray[800]};
    margin-bottom: 0.5rem;
  }

  .law-summary {
    color: ${props => props.theme.isDark
      ? props.theme.colors.gray[400]
      : props.theme.colors.gray[600]};
    font-size: 0.9rem;
    line-height: 1.6;
    margin-top: 0.5rem;
  }

  .law-link {
    color: ${props => props.theme.colors.primary};
    text-decoration: none;
    font-size: 0.875rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.75rem;

    &:hover {
      text-decoration: underline;
    }
  }

  .expand-icon {
    color: ${props => props.theme.colors.gray[500]};
    transition: transform 0.2s ease;
    transform: ${props => props.expanded ? 'rotate(180deg)' : 'rotate(0deg)'};
  }

  .law-content {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid ${props => props.theme.isDark
      ? 'rgba(255, 255, 255, 0.1)'
      : 'rgba(0, 0, 0, 0.1)'};
    color: ${props => props.theme.isDark
      ? props.theme.colors.gray[400]
      : props.theme.colors.gray[700]};
    font-size: 0.9rem;
    line-height: 1.7;
  }
`;

const ExampleQueries = styled.div`
  margin-top: 1rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;

  .label {
    color: ${props => props.theme.isDark
      ? props.theme.colors.gray[400]
      : props.theme.colors.gray[600]};
    font-size: 0.875rem;
  }

  button {
    background: ${props => props.theme.isDark
      ? 'rgba(66, 76, 92, 0.5)'
      : 'rgba(249, 250, 251, 0.8)'};
    color: ${props => props.theme.colors.primary};
    border: 1px solid ${props => props.theme.colors.primary}44;
    padding: 0.5rem 1rem;
    border-radius: 20px;
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.2s ease;

    &:hover {
      background: ${props => props.theme.colors.primary}22;
      transform: translateY(-1px);
    }
  }
`;

const LoadingSpinner = styled(FaSpinner)`
  animation: spin 1s linear infinite;

  @keyframes spin {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }
`;

// ============ MAIN COMPONENT ============

const LawAssistantPage = () => {
  const [query, setQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [categories, setCategories] = useState([]);
  const [expandedSources, setExpandedSources] = useState(new Set());

  // Load categories on mount
  useEffect(() => {
    loadCategories();
  }, []);

  const loadCategories = async () => {
    try {
      const response = await axios.get('/api/law/categories');
      if (response.data.success) {
        setCategories(response.data.categories);
      }
    } catch (error) {
      console.error('Failed to load categories:', error);
    }
  };

  const handleSearch = async (e) => {
    e?.preventDefault();

    if (!query.trim() || query.trim().length < 3) {
      toast.error('Indtast venligst mindst 3 tegn');
      return;
    }

    setIsLoading(true);
    setResult(null);

    try {
      // Call AI assistant endpoint
      const response = await axios.post('/api/law/ask', {
        query: query.trim(),
        category: selectedCategory || null
      });

      if (response.data.success) {
        setResult(response.data);
        toast.success('Svar genereret!');
      } else {
        toast.error('Kunne ikke generere svar');
      }
    } catch (error) {
      console.error('Law assistant error:', error);
      toast.error(error.response?.data?.detail || 'Der opstod en fejl');
    } finally {
      setIsLoading(false);
    }
  };

  const toggleSourceExpansion = (slug) => {
    const newExpanded = new Set(expandedSources);
    if (newExpanded.has(slug)) {
      newExpanded.delete(slug);
    } else {
      newExpanded.add(slug);
    }
    setExpandedSources(newExpanded);
  };

  const exampleQueries = [
    'Hvad siger ferieloven om feriepenge?',
    'Hvornår må en arbejdsgiver opsige en medarbejder?',
    'Hvad er reglerne for GDPR og persondata?',
    'Hvad står der i grundloven om ytringsfrihed?'
  ];

  return (
    <LawContainer>
      <PageHeader>
        <h1>
          <FaGavel className="icon" size={32} />
          Lov Assistent
        </h1>
        <p>Få AI-genererede svar på juridiske spørgsmål baseret på 295 danske love</p>
      </PageHeader>

      {/* Search Card */}
      <SearchCard>
        <form onSubmit={handleSearch}>
          <SearchInputWrapper>
            <FaSearch className="search-icon" />
            <SearchInput
              type="text"
              placeholder="Stil et juridisk spørgsmål, fx 'Hvad siger ferieloven om feriepenge?'"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={isLoading}
            />
          </SearchInputWrapper>

          <CategorySelect
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            disabled={isLoading}
          >
            <option value="">Alle kategorier</option>
            {categories.map(cat => (
              <option key={cat.slug} value={cat.slug}>
                {cat.name.replace('Se alle love i', '')}
              </option>
            ))}
          </CategorySelect>

          <SearchButton type="submit" disabled={isLoading}>
            {isLoading ? (
              <>
                <LoadingSpinner />
                Genererer svar...
              </>
            ) : (
              <>
                <FaSearch />
                Søg svar
              </>
            )}
          </SearchButton>
        </form>

        {!result && (
          <ExampleQueries>
            <span className="label">Eksempler:</span>
            {exampleQueries.map((example, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setQuery(example);
                }}
                type="button"
              >
                {example}
              </button>
            ))}
          </ExampleQueries>
        )}
      </SearchCard>

      {/* AI Answer Section */}
      <AnimatePresence>
        {result && (
          <AnswerCard
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            <h3>
              <FaCheckCircle className="icon" />
              AI-Genereret Svar
            </h3>

            <ConfidenceBadge confidence={result.confidence}>
              <FaCheckCircle />
              {Math.round(result.confidence * 100)}% konfidensgrad
            </ConfidenceBadge>

            <AnswerText dangerouslySetInnerHTML={{ __html: result.answer.replace(/\n/g, '<br/>') }} />

            {result.key_points && result.key_points.length > 0 && (
              <>
                <h4>Vigtige punkter:</h4>
                <KeyPointsList>
                  {result.key_points.map((point, idx) => (
                    <li key={idx}>{point}</li>
                  ))}
                </KeyPointsList>
              </>
            )}
          </AnswerCard>
        )}
      </AnimatePresence>

      {/* Sources Section */}
      <AnimatePresence>
        {result && result.sources && result.sources.length > 0 && (
          <SourcesCard
            as={motion.div}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            <h3>
              <FaBook />
              Kilder ({result.sources.length})
            </h3>

            {result.sources.map((source) => {
              const isExpanded = expandedSources.has(source.slug);
              return (
                <SourceItem
                  key={source.slug}
                  expanded={isExpanded}
                  onClick={() => toggleSourceExpansion(source.slug)}
                >
                  <div className="law-header">
                    <div style={{ flex: 1 }}>
                      <div className="law-title">{source.title}</div>
                      {source.lawNumber && (
                        <div style={{ fontSize: '0.85rem', color: 'gray', marginBottom: '0.5rem' }}>
                          {source.lawNumber}
                        </div>
                      )}
                      {source.summary && (
                        <div className="law-summary">{source.summary}</div>
                      )}
                    </div>
                    <div className="expand-icon">
                      {isExpanded ? <FaChevronUp /> : <FaChevronDown />}
                    </div>
                  </div>

                  {isExpanded && source.content && (
                    <div className="law-content">
                      {source.content}
                    </div>
                  )}

                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="law-link"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <FaExternalLinkAlt />
                    Åbn på regelrytter.dk
                  </a>
                </SourceItem>
              );
            })}
          </SourcesCard>
        )}
      </AnimatePresence>
    </LawContainer>
  );
};

export default LawAssistantPage;
