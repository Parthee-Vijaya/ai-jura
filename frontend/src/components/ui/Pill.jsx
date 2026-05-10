import styled, { css } from 'styled-components';

/**
 * Bifrost — unified Pill component (verdicts + statuses)
 *
 * Usage:
 *   <Pill verdict="GO|BETINGET-GO|NO-GO" />
 *   <Pill status="kladde|vurderet|remediation|godkendt|idriftsat|arkiveret" />
 *   <Pill tone="success|warn|danger|info|neutral">Custom</Pill>
 *
 * Centraliserer pill-styling der tidligere var spredt på 5+ sider.
 */

const verdictTone = {
  GO: 'success',
  'BETINGET-GO': 'warn',
  'NO-GO': 'danger',
};

const statusTone = {
  kladde: 'neutral',
  vurderet: 'info',
  remediation: 'warn',
  godkendt: 'success',
  idriftsat: 'info',
  arkiveret: 'neutral',
};

const statusLabels = {
  kladde: 'Kladde',
  vurderet: 'Vurderet',
  remediation: 'Remediation',
  godkendt: 'Godkendt',
  idriftsat: 'Idriftsat',
  arkiveret: 'Arkiveret',
};

const toneStyles = {
  success: css`
    background: rgba(45, 106, 49, 0.10);
    color: #2d6a31;
  `,
  warn: css`
    background: #fdf2eb;
    color: #a03612;
  `,
  danger: css`
    background: rgba(160, 32, 32, 0.10);
    color: #a02020;
  `,
  info: css`
    background: rgba(13, 46, 84, 0.08);
    color: #0d2e54;
  `,
  neutral: css`
    background: ${(p) => p.theme.colors.surfaceAlt || 'rgba(0,0,0,0.06)'};
    color: ${(p) => p.theme.colors.textMuted};
  `,
};

const PillBase = styled.span`
  display: inline-flex;
  align-items: center;
  font-family: ${(p) => p.theme.fonts.mono};
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: 3px;
  white-space: nowrap;
  ${(p) => toneStyles[p.$tone || 'neutral']}
`;

export const Pill = ({ verdict, status, tone, children, className }) => {
  let resolvedTone = tone;
  let label = children;

  if (verdict) {
    resolvedTone = verdictTone[verdict] || 'neutral';
    label = label || verdict;
  } else if (status) {
    resolvedTone = statusTone[status] || 'neutral';
    label = label || statusLabels[status] || status;
  }

  return (
    <PillBase $tone={resolvedTone} className={className}>
      {label}
    </PillBase>
  );
};

export default Pill;
