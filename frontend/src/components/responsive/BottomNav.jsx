import React, { useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import styled from 'styled-components';
import {
  FaHome,
  FaShoppingCart,
  FaClipboardList,
  FaBalanceScale,
  FaEllipsisH,
  FaTimes,
  FaSearch,
  FaBell,
  FaHistory,
  FaBook,
  FaGavel,
  FaCog,
} from 'react-icons/fa';

/**
 * Bifrost — BottomNav for <720px viewports.
 *
 * Erstatter sidebar på mobile. 5 fixed items: Forside, Indkøb, Vurdering,
 * Sager, Mere (åbner sheet med resten).
 *
 * Mounted i App.js. Skjules på desktop via CSS-media-query.
 */

const Bar = styled.nav`
  display: none;

  @media (max-width: 720px) {
    display: grid;
  }

  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 60px;
  /* iOS safe-area */
  padding-bottom: env(safe-area-inset-bottom);
  background: ${(p) => p.theme.colors.surface || '#fff'};
  border-top: 1px solid ${(p) => p.theme.colors.border};
  grid-template-columns: repeat(5, 1fr);
  z-index: 900;
`;

const Item = styled(NavLink)`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  padding: 6px 0;
  text-decoration: none;
  color: ${(p) => p.theme.colors.textMuted};
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.62rem;
  text-align: center;
  /* WCAG touch target */
  min-height: 44px;

  svg {
    font-size: 1.05rem;
  }

  &.active {
    color: ${(p) => p.theme.colors.primary};
  }
  &:focus-visible {
    outline: 2px solid ${(p) => p.theme.colors.primary};
    outline-offset: -2px;
  }
`;

const MoreButton = styled.button`
  background: transparent;
  border: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  padding: 6px 0;
  cursor: pointer;
  color: ${(p) => p.theme.colors.textMuted};
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.62rem;
  min-height: 44px;

  svg { font-size: 1.05rem; }
  &:focus-visible {
    outline: 2px solid ${(p) => p.theme.colors.primary};
    outline-offset: -2px;
  }
`;

const Sheet = styled.div`
  position: fixed;
  inset: 0;
  background: rgba(20, 24, 31, 0.5);
  z-index: 1100;
  display: flex;
  align-items: flex-end;
  justify-content: center;
`;

const SheetContent = styled.div`
  width: 100%;
  background: ${(p) => p.theme.colors.surface || '#fff'};
  border-radius: 16px 16px 0 0;
  padding: 14px 18px calc(20px + env(safe-area-inset-bottom));
  max-height: 80vh;
  overflow-y: auto;

  .head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 14px;
  }
  h3 {
    font-family: ${(p) => p.theme.fonts.display};
    font-size: 1rem;
    margin: 0;
    color: ${(p) => p.theme.colors.text};
  }
  button.close {
    background: transparent;
    border: none;
    font-size: 1.1rem;
    color: ${(p) => p.theme.colors.textMuted};
    cursor: pointer;
    padding: 4px;
    min-width: 36px;
    min-height: 36px;
  }
`;

const SheetGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
`;

const SheetItem = styled(NavLink)`
  background: ${(p) => p.theme.colors.surfaceAlt || 'rgba(0,0,0,0.04)'};
  border: 1px solid ${(p) => p.theme.colors.border};
  border-radius: 10px;
  padding: 12px 10px;
  text-decoration: none;
  color: ${(p) => p.theme.colors.text};
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.78rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  text-align: center;
  min-height: 70px;

  svg { font-size: 1.1rem; color: ${(p) => p.theme.colors.primary}; }
  &.active { background: ${(p) => p.theme.colors.primarySoft || 'rgba(13,46,84,0.1)'}; }
`;

const PRIMARY_ITEMS = [
  { path: '/', icon: FaHome, label: 'Forside' },
  { path: '/indkoebsproces', icon: FaShoppingCart, label: 'Indkøb' },
  { path: '/vurdering', icon: FaClipboardList, label: 'Vurdér' },
  { path: '/sager', icon: FaBalanceScale, label: 'Sager' },
];

const MORE_ITEMS = [
  { path: '/historik', icon: FaHistory, label: 'Historik' },
  { path: '/eu-checker', icon: FaBalanceScale, label: 'EU AI Act' },
  { path: '/videnbase', icon: FaBook, label: 'Videnbase' },
  { path: '/lov-assistent', icon: FaGavel, label: 'Lov-assistent' },
  { path: '/lov-overvaagning', icon: FaGavel, label: 'Lov-overvågning' },
  { path: '/drift', icon: FaCog, label: 'Drift' },
  { path: '/indstillinger', icon: FaCog, label: 'Indstillinger' },
];

export const BottomNav = () => {
  const [more, setMore] = useState(false);
  const navigate = useNavigate();

  return (
    <>
      <Bar role="navigation" aria-label="Primær mobil-navigation">
        {PRIMARY_ITEMS.map((it) => (
          <Item key={it.path} to={it.path} end={it.path === '/'}>
            <it.icon aria-hidden="true" />
            <span>{it.label}</span>
          </Item>
        ))}
        <MoreButton
          type="button"
          onClick={() => setMore(true)}
          aria-label="Flere navigations-muligheder"
          aria-expanded={more}
        >
          <FaEllipsisH aria-hidden="true" />
          <span>Mere</span>
        </MoreButton>
      </Bar>

      {more && (
        <Sheet onClick={(e) => { if (e.target === e.currentTarget) setMore(false); }}>
          <SheetContent role="dialog" aria-modal="true" aria-label="Flere navigations-muligheder">
            <div className="head">
              <h3>Mere</h3>
              <button className="close" onClick={() => setMore(false)} aria-label="Luk">
                <FaTimes />
              </button>
            </div>
            <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
              <button
                type="button"
                onClick={() => {
                  setMore(false);
                  window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true, bubbles: true }));
                }}
                style={{
                  flex: 1, padding: '10px 12px',
                  background: 'rgba(13,46,84,0.04)',
                  border: '1px solid rgba(13,46,84,0.15)',
                  borderRadius: 8,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                  fontFamily: 'inherit', fontSize: '0.85rem', cursor: 'pointer',
                  color: 'inherit',
                }}
              >
                <FaSearch /> Søg
              </button>
            </div>
            <SheetGrid>
              {MORE_ITEMS.map((it) => (
                <SheetItem
                  key={it.path}
                  to={it.path}
                  onClick={() => setMore(false)}
                >
                  <it.icon aria-hidden="true" />
                  <span>{it.label}</span>
                </SheetItem>
              ))}
            </SheetGrid>
          </SheetContent>
        </Sheet>
      )}
    </>
  );
};

export default BottomNav;
