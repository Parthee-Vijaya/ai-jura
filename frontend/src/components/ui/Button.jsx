import styled, { css } from 'styled-components';

/**
 * Bifrost — unified Button component
 *
 * Variants: primary | secondary | ghost | danger | link
 * Sizes:    sm | md (default) | lg
 *
 * Usage:
 *   <Button variant="primary" size="md" onClick={...}>Tekst</Button>
 *   <Button variant="ghost">← Tilbage</Button>
 *
 * Erstatter PrimaryButton/SecondaryButton/GhostButton der tidligere var
 * redefineret i 8+ filer. Samme visuelle signatur overalt.
 */

const sizeStyles = {
  sm: css`
    padding: 6px 12px;
    font-size: 0.82rem;
    border-radius: 5px;
  `,
  md: css`
    padding: 9px 18px;
    font-size: 0.92rem;
    border-radius: 6px;
  `,
  lg: css`
    padding: 12px 22px;
    font-size: 1rem;
    border-radius: 7px;
  `,
};

const variantStyles = {
  primary: css`
    background: ${(p) => p.theme.colors.primary};
    color: white;
    border-color: ${(p) => p.theme.colors.primary};
    &:hover:not(:disabled) {
      background: ${(p) => p.theme.colors.primaryDark};
      border-color: ${(p) => p.theme.colors.primaryDark};
    }
  `,
  secondary: css`
    background: transparent;
    color: ${(p) => p.theme.colors.text};
    border-color: ${(p) => p.theme.colors.border};
    &:hover:not(:disabled) {
      border-color: ${(p) => p.theme.colors.primary};
      color: ${(p) => p.theme.colors.primary};
    }
  `,
  ghost: css`
    background: transparent;
    color: ${(p) => p.theme.colors.primary};
    border-color: transparent;
    &:hover:not(:disabled) {
      background: ${(p) => p.theme.colors.primarySoft || 'rgba(13,46,84,0.06)'};
    }
  `,
  danger: css`
    background: ${(p) => p.theme.colors.danger};
    color: white;
    border-color: ${(p) => p.theme.colors.danger};
    &:hover:not(:disabled) {
      filter: brightness(0.92);
    }
  `,
  link: css`
    background: transparent;
    color: ${(p) => p.theme.colors.primary};
    border-color: transparent;
    padding-left: 0;
    padding-right: 0;
    text-decoration: underline;
    &:hover:not(:disabled) {
      text-decoration: none;
    }
  `,
};

export const Button = styled.button.attrs((p) => ({
  type: p.type || 'button',
}))`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  font-family: ${(p) => p.theme.fonts.sans};
  font-weight: 600;
  letter-spacing: 0.01em;
  border-style: solid;
  border-width: 1px;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;

  /* WCAG: minimum 44px tap-target on mobile */
  min-height: 36px;
  @media (max-width: 720px) {
    min-height: 44px;
  }

  ${(p) => sizeStyles[p.$size || 'md']}
  ${(p) => variantStyles[p.$variant || 'primary']}

  &:focus-visible {
    outline: 2px solid ${(p) => p.theme.colors.primary};
    outline-offset: 2px;
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &.full-width {
    width: 100%;
  }
`;

export default Button;
