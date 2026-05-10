import styled, { css } from 'styled-components';

/**
 * Bifrost — unified Card primitive
 *
 * Variants:
 *   default       — standard editorial card med bronze top-accent option
 *   muted         — paperSoft baggrund, ingen accent
 *   interactive   — hover-elevation + cursor-pointer
 *
 * Usage:
 *   <Card>...</Card>
 *   <Card variant="interactive" onClick={...}>...</Card>
 */

const variantStyles = {
  default: css`
    background: ${(p) => p.theme.colors.surface};
    border: 1px solid ${(p) => p.theme.colors.border};
  `,
  muted: css`
    background: ${(p) => p.theme.colors.paperSoft || p.theme.colors.surfaceAlt};
    border: 1px solid ${(p) => p.theme.colors.borderSoft || p.theme.colors.border};
  `,
  interactive: css`
    background: ${(p) => p.theme.colors.surface};
    border: 1px solid ${(p) => p.theme.colors.border};
    cursor: pointer;
    transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;

    &:hover {
      border-color: ${(p) => p.theme.colors.primary};
      box-shadow: 0 4px 12px rgba(20, 17, 13, 0.08);
      transform: translateY(-1px);
    }

    &:focus-visible {
      outline: 2px solid ${(p) => p.theme.colors.primary};
      outline-offset: 2px;
    }
  `,
};

export const Card = styled.div`
  border-radius: 8px;
  padding: ${(p) => (p.$padding === 'sm' ? '0.85rem 1rem' : p.$padding === 'lg' ? '1.5rem 1.75rem' : '1.1rem 1.25rem')};
  position: relative;

  ${(p) => variantStyles[p.$variant || 'default']}

  /* Bronze top-accent (Northern Modern signature) — kun hvis $accent */
  ${(p) => p.$accent && css`
    &::before {
      content: '';
      position: absolute;
      top: -1px;
      left: 1.5rem;
      right: 1.5rem;
      height: 2px;
      background: linear-gradient(
        to right,
        transparent,
        ${(p) => p.theme.colors.bronze} 50%,
        transparent
      );
      opacity: 0.4;
    }
  `}
`;

export default Card;
