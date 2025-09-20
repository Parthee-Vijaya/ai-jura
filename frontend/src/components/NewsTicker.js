import React, { useMemo } from 'react';
import styled, { keyframes } from 'styled-components';
import { FaGlobeEurope } from 'react-icons/fa';
import { useQuery } from 'react-query';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '';
const POLL_INTERVAL_MS = 5 * 60 * 1000; // 5 minutter

const scroll = keyframes`
  0% { transform: translateX(100%); }
  100% { transform: translateX(-100%); }
`;

const TickerWrapper = styled.div`
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: #1f2937;
  display: flex;
  align-items: center;
  overflow: hidden;
  padding: 0.75rem 1rem;
  border-radius: 14px;
  margin-bottom: 1.5rem;
  box-shadow: 0 10px 25px -10px rgba(217, 119, 6, 0.6);
`;

const TickerLabel = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  font-size: 0.95rem;
  margin-right: 1rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
`;

const TickerTrack = styled.div`
  flex: 1;
  overflow: hidden;
`;

const TickerContent = styled.div`
  display: inline-flex;
  align-items: center;
  gap: 3rem;
  white-space: nowrap;
  animation: ${scroll} ${props => props.duration}s linear infinite;
`;

const TickerItem = styled.a`
  display: inline-flex;
  align-items: center;
  gap: 0.75rem;
  color: inherit;
  text-decoration: none;
  font-size: 0.95rem;
  opacity: 0.9;
  transition: opacity 0.2s ease;

  &:hover {
    opacity: 1;
  }
`;

const SourceTag = styled.span`
  font-weight: 600;
  font-size: 0.75rem;
  text-transform: uppercase;
  background: rgba(31, 41, 55, 0.12);
  color: #1f2937;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  letter-spacing: 0.05em;
`;

const HeadlineText = styled.span`
  font-size: 0.95rem;
  color: #1f2937;
  font-weight: 500;
`;

const NewsTicker = () => {
  const { data } = useQuery(
    ['news', 'ticker'],
    async () => {
      const res = await fetch(`${API_BASE_URL}/api/news/ticker`);
      if (!res.ok) {
        throw new Error('Kunne ikke hente ticker');
      }
      return res.json();
    },
    {
      refetchInterval: POLL_INTERVAL_MS,
      refetchOnWindowFocus: false,
      staleTime: POLL_INTERVAL_MS,
    }
  );

  const items = data?.items || [];

  const tickerItems = useMemo(() => {
    if (!items.length) {
      return [
        {
          title: 'Live AI-nyheder indlæses…',
          url: '#',
          source: 'System',
        },
      ];
    }
    return items;
  }, [items]);

  const duration = useMemo(() => {
    const base = 45;
    return Math.max(30, Math.min(base + tickerItems.length * 6, 90));
  }, [tickerItems.length]);

  const displayItems = useMemo(() => {
    if (tickerItems.length <= 1) {
      return [...tickerItems, ...tickerItems];
    }
    return [...tickerItems, ...tickerItems];
  }, [tickerItems]);

  return (
    <TickerWrapper>
      <TickerLabel>
        <FaGlobeEurope />
        <span>Seneste AI- og juranyheder</span>
      </TickerLabel>
      <TickerTrack>
        <TickerContent duration={duration}>
          {displayItems.map((item, index) => (
            <TickerItem key={`${item.url}-${index}`} href={item.url} target="_blank" rel="noopener noreferrer">
              <SourceTag>{item.source}</SourceTag>
              <HeadlineText>{item.title}</HeadlineText>
            </TickerItem>
          ))}
        </TickerContent>
      </TickerTrack>
    </TickerWrapper>
  );
};

export default NewsTicker;
