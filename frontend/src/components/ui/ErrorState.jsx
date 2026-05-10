import React from 'react';
import styled from 'styled-components';
import { FaExclamationTriangle, FaRedo } from 'react-icons/fa';
import Button from './Button';

/**
 * Bifrost — unified ErrorState
 *
 * Usage:
 *   <ErrorState
 *     title="Kunne ikke hente sager"
 *     error={err}
 *     onRetry={() => refetch()}
 *   />
 */

const Wrap = styled.div`
  background: rgba(160, 32, 32, 0.04);
  border: 1px solid rgba(160, 32, 32, 0.25);
  border-left-width: 3px;
  border-left-color: #a02020;
  border-radius: 0 6px 6px 0;
  padding: 1rem 1.25rem;
  margin: 0 0 1rem;

  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 12px;
  align-items: start;

  .icon {
    color: #a02020;
    font-size: 1.1rem;
    margin-top: 2px;
  }

  .body {
    min-width: 0;
  }

  h3 {
    font-family: ${(p) => p.theme.fonts.display};
    font-size: 0.95rem;
    font-weight: 600;
    margin: 0 0 0.25rem;
    color: #a02020;
  }

  p {
    margin: 0;
    font-family: ${(p) => p.theme.fonts.body};
    font-size: 0.85rem;
    color: ${(p) => p.theme.colors.text};
    line-height: 1.5;
    overflow-wrap: break-word;
  }

  .detail {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.78rem;
    color: ${(p) => p.theme.colors.textMuted};
    margin-top: 0.4rem;
    word-break: break-word;
  }

  @media (max-width: 540px) {
    grid-template-columns: 1fr;
  }
`;

export const ErrorState = ({ title, error, detail, onRetry }) => {
  const errorMessage =
    detail ||
    (error?.response?.data?.detail) ||
    (error?.message) ||
    (typeof error === 'string' ? error : null);

  return (
    <Wrap role="alert" aria-live="assertive">
      <FaExclamationTriangle className="icon" aria-hidden="true" />
      <div className="body">
        <h3>{title || 'Noget gik galt'}</h3>
        <p>Det lykkedes ikke at hente data. Prøv igen — hvis fejlen vedbliver, kontakt IT-sikkerhed@kalundborg.dk.</p>
        {errorMessage && <div className="detail">{errorMessage}</div>}
      </div>
      {onRetry && (
        <Button $variant="secondary" $size="sm" onClick={onRetry}>
          <FaRedo /> Prøv igen
        </Button>
      )}
    </Wrap>
  );
};

export default ErrorState;
