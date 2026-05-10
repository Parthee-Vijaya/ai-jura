import React from 'react';
import styled from 'styled-components';
import Button from './Button';

/**
 * Bifrost — unified EmptyState
 *
 * Usage:
 *   <EmptyState
 *     icon={<FaFolderOpen />}
 *     title="Ingen sager endnu"
 *     description="Start med at oprette din første sag."
 *     action={{ label: '+ Ny sag', onClick: () => navigate('/indkoebsproces') }}
 *   />
 *
 * Erstatter de 5+ ad-hoc empty-state-styled-components på tværs af pages.
 */

const Wrap = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: ${(p) => (p.$compact ? '1.25rem 1rem' : '3rem 1.5rem')};
  border: 1px dashed ${(p) => p.theme.colors.border};
  border-radius: 8px;
  background: ${(p) => p.theme.colors.surfaceAlt || 'transparent'};

  .icon {
    font-size: ${(p) => (p.$compact ? '1.4rem' : '2.4rem')};
    color: ${(p) => p.theme.colors.textFaded};
    margin-bottom: ${(p) => (p.$compact ? '0.5rem' : '1rem')};
    opacity: 0.7;
  }

  h3 {
    font-family: ${(p) => p.theme.fonts.display};
    font-size: ${(p) => (p.$compact ? '0.95rem' : '1.15rem')};
    font-weight: 600;
    margin: 0 0 0.4rem;
    color: ${(p) => p.theme.colors.text};
  }

  p {
    font-family: ${(p) => p.theme.fonts.body};
    font-size: ${(p) => (p.$compact ? '0.85rem' : '0.95rem')};
    color: ${(p) => p.theme.colors.textMuted};
    line-height: 1.5;
    margin: 0 0 1rem;
    max-width: 380px;
  }
`;

export const EmptyState = ({
  icon,
  title,
  description,
  action,
  compact = false,
}) => (
  <Wrap $compact={compact}>
    {icon && <div className="icon" aria-hidden="true">{icon}</div>}
    {title && <h3>{title}</h3>}
    {description && <p>{description}</p>}
    {action && (
      <Button
        $variant={action.variant || 'secondary'}
        $size={compact ? 'sm' : 'md'}
        onClick={action.onClick}
      >
        {action.label}
      </Button>
    )}
  </Wrap>
);

export default EmptyState;
