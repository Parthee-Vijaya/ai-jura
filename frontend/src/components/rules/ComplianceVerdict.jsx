import React from 'react';
import styled, { css } from 'styled-components';

/**
 * ComplianceVerdict — status pill for a v3 rule_engine decision.
 *
 * Maps rule_engine Status values to themed colors:
 *   GO            -> success (green)
 *   BETINGET-GO   -> teglrød (primary brand)
 *   NO-GO         -> danger
 *   needs_input   -> muted gray (rule applies but predicates missing)
 *
 * Usage:
 *   <ComplianceVerdict status="BETINGET-GO" />
 *   <ComplianceVerdict status="NO-GO" size="lg" label="Forbudt under art. 5" />
 */

const statusStyles = {
  GO: css`
    background: ${(p) => p.theme.colors.success}1a;
    color: ${(p) => p.theme.colors.success};
    border-color: ${(p) => p.theme.colors.success};
  `,
  'BETINGET-GO': css`
    background: ${(p) => p.theme.colors.primary}1a;
    color: ${(p) => p.theme.colors.primaryDark};
    border-color: ${(p) => p.theme.colors.primary};
  `,
  'NO-GO': css`
    background: ${(p) => p.theme.colors.danger}1a;
    color: ${(p) => p.theme.colors.danger};
    border-color: ${(p) => p.theme.colors.danger};
  `,
  NEEDS_INPUT: css`
    background: ${(p) => p.theme.colors.gray[100]};
    color: ${(p) => p.theme.colors.gray[600]};
    border-color: ${(p) => p.theme.colors.gray[300]};
  `,
};

const sizeStyles = {
  sm: css`
    padding: 3px 8px;
    font-size: 0.7rem;
  `,
  md: css`
    padding: 5px 12px;
    font-size: 0.75rem;
  `,
  lg: css`
    padding: 8px 16px;
    font-size: 0.85rem;
  `,
};

const Pill = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 0.4em;
  border: 1px solid;
  border-radius: 999px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  white-space: nowrap;
  font-family: ${(p) => p.theme.fonts.main};
  ${(p) => sizeStyles[p.$size] || sizeStyles.md}
  ${(p) => statusStyles[p.$statusKey] || statusStyles.NEEDS_INPUT}
`;

const Dot = styled.span`
  width: 0.45em;
  height: 0.45em;
  border-radius: 50%;
  background: currentColor;
  display: inline-block;
`;

const STATUS_LABELS = {
  GO: 'GO',
  'BETINGET-GO': 'Betinget GO',
  'NO-GO': 'NO-GO',
  NEEDS_INPUT: 'Mangler input',
};

const ComplianceVerdict = ({ status, label, size = 'md', withDot = true, className }) => {
  const key = status || 'NEEDS_INPUT';
  const text = label || STATUS_LABELS[key] || key;
  return (
    <Pill $statusKey={key} $size={size} className={className} role="status">
      {withDot && <Dot aria-hidden="true" />}
      {text}
    </Pill>
  );
};

export default ComplianceVerdict;
