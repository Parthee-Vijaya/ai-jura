import React, { useState, useEffect, useMemo, useCallback } from 'react';
import styled from 'styled-components';
import { FaSync } from 'react-icons/fa';
import { NewsSkeletonLoader } from './SkeletonLoader';
import { availableCategories, resolveSourceMeta } from '../utils/newsSourceMap';

const NewsContainer = styled.div`
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  margin-bottom: 24px;
`;

const NewsHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
`;

const NewsTitle = styled.h2`
  color: #1a365d;
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
`;

const HeaderInfo = styled.div`
  display: flex;
  align-items: center;
  gap: 1rem;
`;

const LastUpdated = styled.span`
  color: #666;
  font-size: 0.9rem;
`;

const RefreshButton = styled.button`
  background: #1a365d;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 0.5rem 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.2s ease;

  &:hover {
    background: #2c5282;
    transform: translateY(-1px);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
  }

  .refresh-icon {
    animation: ${props => props.spinning ? 'spin 1s linear infinite' : 'none'};
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
`;

const CategoryButton = styled.button`
  padding: 6px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  background: ${props => props.active ? '#3182ce' : 'white'};
  color: ${props => props.active ? 'white' : '#4a5568'};
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: ${props => props.active ? '#2c5aa0' : '#f7fafc'};
  }
`;

const NewsItem = styled.div`
  border-bottom: 1px solid #e2e8f0;
  padding: 16px 0;

  &:last-child {
    border-bottom: none;
  }
`;

const NewsItemHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
`;

const NewsItemTitle = styled.h3`
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #2d3748;
  line-height: 1.4;
  flex: 1;
`;

const ImportanceBadge = styled.span`
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  margin-left: 12px;
  background: ${props => {
    switch(props.importance) {
      case 'high': return '#fed7d7';
      case 'medium': return '#feebc8';
      case 'low': return '#c6f6d5';
      default: return '#e2e8f0';
    }
  }};
  color: ${props => {
    switch(props.importance) {
      case 'high': return '#c53030';
      case 'medium': return '#dd6b20';
      case 'low': return '#38a169';
      default: return '#4a5568';
    }
  }};
`;

const NewsSource = styled.div`
  font-size: 0.875rem;
  color: #666;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
`;

const SourceLogo = styled.img`
  width: 32px;
  height: 32px;
  border-radius: 8px;
  object-fit: cover;
  border: 1px solid rgba(0, 0, 0, 0.05);
`;

const SourceMeta = styled.span`
  display: flex;
  flex-direction: column;
  line-height: 1.2;
`;

const SourceName = styled.span`
  font-weight: 600;
  color: #1a365d;
`;

const SourceExtra = styled.span`
  color: #718096;
  font-size: 0.75rem;
`;

const SectionHeader = styled.div`
  display: flex;
  flex-direction: column;
  gap: 12px;
`;

const CategoryFilter = styled.div`
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
`;

const NewsSummary = styled.p`
  margin: 0;
  color: #4a5568;
  line-height: 1.5;
  font-size: 0.95rem;
`;

const NewsLink = styled.a`
  color: #3182ce;
  text-decoration: none;
  font-size: 0.875rem;
  margin-top: 8px;
  display: inline-block;

  &:hover {
    text-decoration: underline;
  }
`;

const Keywords = styled.div`
  margin-top: 8px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
`;

const Keyword = styled.span`
  background: #f7fafc;
  border: 1px solid #e2e8f0;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.75rem;
  color: #4a5568;
`;

const LoadingMessage = styled.div`
  text-align: center;
  padding: 40px;
  color: #666;
`;

const ErrorMessage = styled.div`
  text-align: center;
  padding: 40px;
  color: #e53e3e;
  background: #fed7d7;
  border-radius: 8px;
`;

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '';
const POLLING_INTERVAL_MS = 15 * 60 * 1000;

const NewsSection = () => {
  const [rawItems, setRawItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [lastUpdated, setLastUpdated] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const categories = useMemo(() => availableCategories(), []);

  const fetchNews = useCallback(async ({ forceRefresh = false } = {}) => {
    try {
      if (forceRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      const params = new URLSearchParams({ limit: '24' });
      if (forceRefresh) {
        params.append('force_refresh', 'true');
      }

      const response = await fetch(`${API_BASE_URL}/api/news/latest?${params.toString()}`);
      if (!response.ok) {
        throw new Error('Kunne ikke hente nyheder');
      }

      const data = await response.json();
      setRawItems(data.items || []);
      setLastUpdated(data.last_updated ? new Date(data.last_updated) : new Date());
      setError(null);
    } catch (err) {
      setError(err.message || 'Uventet fejl');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchNews();

    const interval = setInterval(() => {
      fetchNews();
    }, POLLING_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [fetchNews]);

  const handleCategoryChange = (category) => {
    setSelectedCategory(category);
  };

  const handleManualRefresh = () => {
    fetchNews({ forceRefresh: true });
  };

  const news = useMemo(() => {
    if (selectedCategory === 'all') {
      return rawItems;
    }
    return rawItems.filter((item) => resolveSourceMeta(item.source).id === selectedCategory);
  }, [rawItems, selectedCategory]);

  const formatDate = (dateString, fallbackString) => {
    const date = dateString ? new Date(dateString) : fallbackString ? new Date(fallbackString) : null;
    if (!date || Number.isNaN(date.getTime())) {
      return 'Ukendt tidspunkt';
    }
    return date.toLocaleDateString('da-DK', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <NewsContainer>
      <SectionHeader>
        <NewsHeader>
          <NewsTitle>Seneste AI- og juranews</NewsTitle>
          <HeaderInfo>
            {lastUpdated && (
              <LastUpdated>
                Opdateret {lastUpdated.toLocaleDateString('da-DK', {
                  day: '2-digit',
                  month: '2-digit',
                  year: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </LastUpdated>
            )}
            <RefreshButton
              onClick={handleManualRefresh}
              disabled={refreshing || loading}
              spinning={refreshing}
            >
              <FaSync className="refresh-icon" />
              {refreshing ? 'Opdaterer...' : 'Opdater nu'}
            </RefreshButton>
          </HeaderInfo>
        </NewsHeader>

        <CategoryFilter>
          {categories.map((category) => (
            <CategoryButton
              key={category.key}
              active={selectedCategory === category.key}
              onClick={() => handleCategoryChange(category.key)}
            >
              {category.label}
            </CategoryButton>
          ))}
        </CategoryFilter>
      </SectionHeader>

      {error && (
        <ErrorMessage>Fejl ved indlæsning af nyheder: {error}</ErrorMessage>
      )}

      {loading && rawItems.length === 0 ? (
        <NewsSkeletonLoader />
      ) : news.length === 0 ? (
        <LoadingMessage>Ingen relevante nyheder fundet lige nu.</LoadingMessage>
      ) : (
        news.map((item, index) => {
          const sourceMeta = resolveSourceMeta(item.source);
          return (
            <NewsItem key={`${item.url}-${index}`}>
              <NewsItemHeader>
                <NewsItemTitle>{item.title}</NewsItemTitle>
                <ImportanceBadge importance={item.importance}>
                  {item.importance === 'high'
                    ? 'Høj vigtighed'
                    : item.importance === 'medium'
                    ? 'Middel vigtighed'
                    : 'Lav vigtighed'}
                </ImportanceBadge>
              </NewsItemHeader>

              <NewsSource>
                <SourceLogo src={sourceMeta.logo} alt={`${sourceMeta.name} logo`} />
                <SourceMeta>
                  <SourceName>{item.source}</SourceName>
                  <SourceExtra>
                    {sourceMeta.region} • {formatDate(item.published_at, item.scraped_at)}
                  </SourceExtra>
                </SourceMeta>
              </NewsSource>

              <NewsSummary>{item.summary}</NewsSummary>

              {item.keywords && item.keywords.length > 0 && (
                <Keywords>
                  {item.keywords.map((keyword, kidx) => (
                    <Keyword key={kidx}>{keyword}</Keyword>
                  ))}
                </Keywords>
              )}

              <NewsLink href={item.url} target="_blank" rel="noopener noreferrer">
                Læs mere →
              </NewsLink>
            </NewsItem>
          );
        })
      )}
    </NewsContainer>
  );
};

export default NewsSection;
