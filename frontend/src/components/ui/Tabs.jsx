import React from 'react';
import styled from 'styled-components';

/**
 * Bifrost — unified Tabs (keyboard-navigerbar)
 *
 * Usage:
 *   <Tabs
 *     tabs={[
 *       { id: 'oversigt', label: 'Oversigt', icon: <FaHome /> },
 *       { id: 'evidens', label: 'Evidens', count: 3 },
 *     ]}
 *     activeTab={tab}
 *     onChange={setTab}
 *   />
 *   {tab === 'oversigt' && <Oversigt />}
 *   {tab === 'evidens' && <Evidens />}
 */

const TabList = styled.div.attrs({ role: 'tablist' })`
  display: flex;
  border-bottom: 1px solid ${(p) => p.theme.colors.border};
  gap: 0;
  overflow-x: auto;
  scrollbar-width: thin;

  @media (max-width: 720px) {
    /* Snap-scroll på mobile så tabs føles native */
    scroll-snap-type: x mandatory;
    -webkit-overflow-scrolling: touch;
  }
`;

const TabButton = styled.button.attrs({ role: 'tab' })`
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.92rem;
  font-weight: ${(p) => (p.$active ? 600 : 500)};
  color: ${(p) => (p.$active ? p.theme.colors.primary : p.theme.colors.textMuted)};
  background: transparent;
  border: none;
  padding: 12px 18px;
  cursor: pointer;
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
  min-height: 44px;
  scroll-snap-align: start;

  &::after {
    content: '';
    position: absolute;
    bottom: -1px;
    left: 0;
    right: 0;
    height: 2px;
    background: ${(p) => (p.$active ? p.theme.colors.primary : 'transparent')};
    transition: background 0.15s ease;
  }

  &:hover:not(:disabled) {
    color: ${(p) => p.theme.colors.text};
  }
  &:focus-visible {
    outline: 2px solid ${(p) => p.theme.colors.primary};
    outline-offset: -2px;
  }
  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .count {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.7rem;
    background: ${(p) => (p.$active ? p.theme.colors.primary : p.theme.colors.surfaceAlt)};
    color: ${(p) => (p.$active ? 'white' : p.theme.colors.textMuted)};
    padding: 1px 6px;
    border-radius: 999px;
    min-width: 18px;
    text-align: center;
  }

  .icon {
    font-size: 0.92rem;
  }
`;

export const Tabs = ({ tabs, activeTab, onChange }) => {
  const handleKey = (e, idx) => {
    if (!tabs?.length) return;
    let nextIdx = idx;
    if (e.key === 'ArrowRight') nextIdx = (idx + 1) % tabs.length;
    else if (e.key === 'ArrowLeft') nextIdx = (idx - 1 + tabs.length) % tabs.length;
    else if (e.key === 'Home') nextIdx = 0;
    else if (e.key === 'End') nextIdx = tabs.length - 1;
    else return;
    e.preventDefault();
    onChange(tabs[nextIdx].id);
  };

  return (
    <TabList>
      {tabs.map((t, idx) => {
        const active = t.id === activeTab;
        return (
          <TabButton
            key={t.id}
            $active={active}
            aria-selected={active}
            tabIndex={active ? 0 : -1}
            onClick={() => onChange(t.id)}
            onKeyDown={(e) => handleKey(e, idx)}
            disabled={t.disabled}
          >
            {t.icon && <span className="icon" aria-hidden="true">{t.icon}</span>}
            <span>{t.label}</span>
            {t.count !== undefined && t.count !== null && (
              <span className="count">{t.count}</span>
            )}
          </TabButton>
        );
      })}
    </TabList>
  );
};

export default Tabs;
