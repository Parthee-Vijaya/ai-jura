import styled, { css } from 'styled-components';

/**
 * Bifrost — unified Banner (info/warning/danger/success)
 *
 * Usage:
 *   <Banner tone="info">Maskinel oversættelse — under jurist-review.</Banner>
 *   <Banner tone="warn" title="DPIA påkrævet">2 kriterier opfyldt</Banner>
 *
 * Erstatter ad-hoc InfoBox / EcBanner / FlaggedBanner der findes i 6+ filer.
 */

const toneStyles = {
  info: css`
    background: rgba(13, 46, 84, 0.04);
    border-left-color: ${(p) => p.theme.colors.primary || '#0d2e54'};
    --accent: ${(p) => p.theme.colors.primary || '#0d2e54'};
  `,
  warn: css`
    background: rgba(176, 138, 74, 0.10);
    border-left-color: ${(p) => p.theme.colors.bronze || '#b08a4a'};
    --accent: ${(p) => p.theme.colors.bronze || '#b08a4a'};
  `,
  danger: css`
    background: rgba(160, 32, 32, 0.06);
    border-left-color: #a02020;
    --accent: #a02020;
  `,
  success: css`
    background: rgba(45, 106, 49, 0.06);
    border-left-color: #2d6a31;
    --accent: #2d6a31;
  `,
};

export const Banner = styled.div`
  border-left: 3px solid;
  border-radius: 0 6px 6px 0;
  padding: 10px 14px;
  margin: 0 0 12px;
  font-family: ${(p) => p.theme.fonts.body};
  font-size: 0.88rem;
  line-height: 1.55;
  color: ${(p) => p.theme.colors.ink || p.theme.colors.text};

  ${(p) => toneStyles[p.$tone || 'info']}

  strong, b {
    color: var(--accent);
    font-weight: 700;
  }
  a {
    color: var(--accent);
    font-weight: 500;
  }
  code, kbd {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.85em;
    padding: 1px 4px;
    background: rgba(0, 0, 0, 0.04);
    border-radius: 3px;
  }
`;

export default Banner;
