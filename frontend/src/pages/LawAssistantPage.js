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
import {
  PageShell,
  PageHeader,
  PrimaryButton,
} from '../components/page-chrome/PageChrome';

const SearchCard = styled.div`
  background: ${(p) => p.theme.colors.surface};
  border: 1px solid ${(p) => p.theme.colors.border};
  border-radius: ${(p) => p.theme.borderRadius};
  padding: 1.75rem;
  margin-bottom: 2rem;
`;

const SearchInput = styled.input`
  width: 100%;
  padding: 0.85rem 1rem 0.85rem 2.75rem;
  border: 1px solid ${(p) => p.theme.colors.border};
  border-radius: ${(p) => p.theme.borderRadius};
  font-family: ${(p) => p.theme.fonts.body};
  font-size: 1rem;
  background: ${(p) => p.theme.colors.surface};
  color: ${(p) => p.theme.colors.text};
  transition: ${(p) => p.theme.animations.transitionFast};

  &:focus {
    border-color: ${(p) => p.theme.colors.primary};
    outline: none;
    box-shadow: ${(p) => p.theme.shadows.focus};
  }

  &::placeholder {
    color: ${(p) => p.theme.colors.textFaded};
    font-style: italic;
  }
`;

const SearchInputWrapper = styled.div`
  position: relative;
  margin-bottom: 1.25rem;

  .search-icon {
    position: absolute;
    left: 14px;
    top: 50%;
    transform: translateY(-50%);
    color: ${(p) => p.theme.colors.textMuted};
    font-size: 0.9rem;
  }
`;

const CategorySelect = styled.select`
  padding: 0.7rem 0.9rem;
  border: 1px solid ${(p) => p.theme.colors.border};
  border-radius: ${(p) => p.theme.borderRadius};
  background: ${(p) => p.theme.colors.surface};
  color: ${(p) => p.theme.colors.text};
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.92rem;
  cursor: pointer;
  margin-bottom: 1.25rem;
  width: 100%;

  &:focus {
    border-color: ${(p) => p.theme.colors.primary};
    outline: none;
  }
`;

const SearchButton = styled(PrimaryButton)`
  width: 100%;
  justify-content: center;
  padding: 12px 20px;
`;

const AnswerCard = styled(motion.div)`
  background: ${(p) => p.theme.colors.surface};
  border: 1px solid ${(p) => p.theme.colors.border};
  border-left: 3px solid ${(p) => p.theme.colors.primary};
  border-radius: ${(p) => p.theme.borderRadius};
  padding: 1.75rem;
  margin-bottom: 2rem;

  h3 {
    font-family: ${(p) => p.theme.fonts.display};
    font-size: 1.3rem;
    font-weight: 600;
    color: ${(p) => p.theme.colors.text};
    margin: 0 0 1rem 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;

    .icon {
      color: ${(p) => p.theme.colors.primary};
      font-size: 1rem;
    }
  }
`;

const AnswerText = styled.div`
  font-family: ${(p) => p.theme.fonts.body};
  color: ${(p) => p.theme.colors.text};
  line-height: 1.7;
  font-size: 1.05rem;
  margin-bottom: 1.5rem;

  p { margin-bottom: 1rem; }

  strong {
    color: ${(p) => p.theme.colors.text};
    font-weight: 600;
  }
`;

const ConfidenceBadge = styled.div`
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 4px 12px;
  border-radius: 999px;
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.74rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  background: transparent;
  border: 1px solid;
  ${({ confidence, theme }) => {
    if (confidence >= 0.8)
      return `border-color: ${theme.colors.success}; color: ${theme.colors.success};`;
    if (confidence >= 0.6)
      return `border-color: ${theme.colors.warning}; color: ${theme.colors.warning};`;
    return `border-color: ${theme.colors.danger}; color: ${theme.colors.danger};`;
  }}
`;

const KeyPointsList = styled.ul`
  list-style: none;
  padding: 0;
  margin-top: 1.5rem;

  li {
    font-family: ${(p) => p.theme.fonts.body};
    padding: 0.85rem 1rem;
    margin-bottom: 0.5rem;
    background: ${(p) => p.theme.colors.surfaceAlt};
    border-left: 2px solid ${(p) => p.theme.colors.primary};
    border-radius: 4px;
    color: ${(p) => p.theme.colors.text};
    line-height: 1.55;
  }
`;

const SourcesCard = styled.div`
  background: ${(p) => p.theme.colors.surface};
  border: 1px solid ${(p) => p.theme.colors.border};
  border-radius: ${(p) => p.theme.borderRadius};
  padding: 1.75rem;
  margin-bottom: 2rem;

  h3 {
    font-family: ${(p) => p.theme.fonts.display};
    font-size: 1.3rem;
    font-weight: 600;
    color: ${(p) => p.theme.colors.text};
    margin: 0 0 1.25rem 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
`;

const SourceItem = styled.div`
  padding: 1.1rem;
  margin-bottom: 0.8rem;
  background: ${(p) => p.theme.colors.surfaceAlt};
  border-radius: ${(p) => p.theme.borderRadius};
  border: 1px solid ${(p) => p.theme.colors.borderSoft};
  cursor: pointer;
  transition: ${(p) => p.theme.animations.transitionFast};

  &:hover {
    border-color: ${(p) => p.theme.colors.primary};
    background: ${(p) => p.theme.colors.surface};
  }

  .law-header {
    display: flex;
    justify-content: space-between;
    align-items: start;
    gap: 1rem;
  }

  .law-title {
    font-family: ${(p) => p.theme.fonts.display};
    font-weight: 600;
    font-size: 1.05rem;
    color: ${(p) => p.theme.colors.text};
    margin-bottom: 0.4rem;
  }

  .law-summary {
    font-family: ${(p) => p.theme.fonts.body};
    color: ${(p) => p.theme.colors.text};
    font-size: 0.92rem;
    line-height: 1.55;
    margin-top: 0.4rem;
  }

  .law-link {
    font-family: ${(p) => p.theme.fonts.sans};
    color: ${(p) => p.theme.colors.primary};
    text-decoration: none;
    font-size: 0.82rem;
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    margin-top: 0.75rem;

    &:hover { text-decoration: underline; }
  }

  .expand-icon {
    color: ${(p) => p.theme.colors.textMuted};
    transition: transform 0.2s ease;
    transform: ${(p) => (p.expanded ? 'rotate(180deg)' : 'rotate(0deg)')};
  }

  .law-content {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid ${(p) => p.theme.colors.borderSoft};
    font-family: ${(p) => p.theme.fonts.body};
    color: ${(p) => p.theme.colors.text};
    font-size: 0.94rem;
    line-height: 1.7;
  }
`;

const ExampleQueries = styled.div`
  margin-top: 1rem;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;

  .label {
    font-family: ${(p) => p.theme.fonts.sans};
    color: ${(p) => p.theme.colors.textMuted};
    font-size: 0.78rem;
    letter-spacing: 0.04em;
    margin-right: 4px;
  }

  button {
    font-family: ${(p) => p.theme.fonts.sans};
    background: transparent;
    color: ${(p) => p.theme.colors.textMuted};
    border: 1px solid ${(p) => p.theme.colors.border};
    padding: 5px 12px;
    border-radius: 999px;
    font-size: 0.78rem;
    cursor: pointer;
    transition: ${(p) => p.theme.animations.transitionFast};

    &:hover {
      border-color: ${(p) => p.theme.colors.primary};
      color: ${(p) => p.theme.colors.primary};
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
    <PageShell>
      <PageHeader
        eyebrow="Tyr · lov-assistent"
        title="Lov-assistent"
        lede="AI-genererede svar på juridiske spørgsmål forankret i 295 danske love. Kilder fremgår altid eksplicit, så du kan verificere mod regelrytter.dk og Retsinformation."
      />

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
    </PageShell>
  );
};

export default LawAssistantPage;
