import React from 'react';
import styled, { keyframes } from 'styled-components';

/**
 * Bifrost — unified LoadingState (skeleton + spinner)
 *
 * Skeleton bruges som default fordi det er mindre forstyrrende end spinner.
 * Spinner kun når der ikke er en kendt layout-form (fx async action).
 *
 * Usage:
 *   <LoadingState rows={4} />              — skeleton-tabel
 *   <LoadingState type="spinner" />        — centreret spinner
 *   <SkeletonLine width="60%" />           — lavt-niveau primitiv
 */

const shimmer = keyframes`
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
`;

export const SkeletonLine = styled.div`
  height: ${(p) => p.height || '14px'};
  width: ${(p) => p.width || '100%'};
  border-radius: 3px;
  background: linear-gradient(
    90deg,
    ${(p) => p.theme.colors.surfaceAlt || 'rgba(0,0,0,0.06)'} 0%,
    ${(p) => p.theme.colors.borderSoft || 'rgba(0,0,0,0.10)'} 50%,
    ${(p) => p.theme.colors.surfaceAlt || 'rgba(0,0,0,0.06)'} 100%
  );
  background-size: 200% 100%;
  animation: ${shimmer} 1.4s ease-in-out infinite;

  @media (prefers-reduced-motion: reduce) {
    animation: none;
    background: ${(p) => p.theme.colors.surfaceAlt || 'rgba(0,0,0,0.08)'};
  }
`;

const SkeletonStack = styled.div`
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px 0;
`;

const spin = keyframes`
  to { transform: rotate(360deg); }
`;

const Spinner = styled.div`
  width: ${(p) => p.size || '24px'};
  height: ${(p) => p.size || '24px'};
  border: 3px solid ${(p) => p.theme.colors.border};
  border-top-color: ${(p) => p.theme.colors.primary};
  border-radius: 50%;
  animation: ${spin} 0.8s linear infinite;

  @media (prefers-reduced-motion: reduce) {
    animation: ${spin} 2.5s linear infinite;
  }
`;

const SpinnerWrap = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: ${(p) => (p.$compact ? '0.75rem' : '2rem')};
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.88rem;
  color: ${(p) => p.theme.colors.textMuted};
`;

export const LoadingState = ({
  type = 'skeleton',
  rows = 3,
  label,
  compact = false,
}) => {
  if (type === 'spinner') {
    return (
      <SpinnerWrap $compact={compact} role="status" aria-live="polite">
        <Spinner aria-hidden="true" />
        <span>{label || 'Henter…'}</span>
      </SpinnerWrap>
    );
  }
  return (
    <SkeletonStack role="status" aria-busy="true" aria-label={label || 'Henter indhold'}>
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonLine
          key={i}
          width={`${85 - (i % 3) * 12}%`}
          height={i === 0 ? '20px' : '14px'}
        />
      ))}
    </SkeletonStack>
  );
};

export default LoadingState;
