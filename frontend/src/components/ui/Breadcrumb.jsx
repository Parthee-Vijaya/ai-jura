import React from 'react';
import { Link } from 'react-router-dom';
import styled from 'styled-components';
import { FaChevronRight } from 'react-icons/fa';

/**
 * Bifrost — unified Breadcrumb
 *
 * Usage:
 *   <Breadcrumb items={[
 *     { label: 'Sager', to: '/sager' },
 *     { label: 'K-2026-0184', to: '/sag/K-2026-0184' },
 *     { label: 'Vurdering' },           // current page (no `to`)
 *   ]} />
 *
 * Sidste item er current (ikke et link). Alle andre items skal have `to`.
 */

const Wrap = styled.nav.attrs({ 'aria-label': 'Breadcrumb' })`
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.82rem;
  color: ${(p) => p.theme.colors.textMuted};
  margin-bottom: 1rem;

  ol {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px;
  }

  li {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  a {
    color: ${(p) => p.theme.colors.textMuted};
    text-decoration: none;
    transition: color 0.15s ease;

    &:hover {
      color: ${(p) => p.theme.colors.primary};
      text-decoration: underline;
    }
    &:focus-visible {
      outline: 2px solid ${(p) => p.theme.colors.primary};
      outline-offset: 2px;
      border-radius: 3px;
    }
  }

  .current {
    color: ${(p) => p.theme.colors.text};
    font-weight: 500;
  }

  .sep {
    color: ${(p) => p.theme.colors.textFaded};
    font-size: 0.7rem;
  }
`;

export const Breadcrumb = ({ items }) => {
  if (!items?.length) return null;

  return (
    <Wrap>
      <ol>
        {items.map((item, i) => {
          const isLast = i === items.length - 1;
          return (
            <li key={`${item.label}-${i}`}>
              {item.to && !isLast ? (
                <Link to={item.to}>{item.label}</Link>
              ) : (
                <span className="current" aria-current={isLast ? 'page' : undefined}>
                  {item.label}
                </span>
              )}
              {!isLast && (
                <FaChevronRight className="sep" aria-hidden="true" />
              )}
            </li>
          );
        })}
      </ol>
    </Wrap>
  );
};

export default Breadcrumb;
