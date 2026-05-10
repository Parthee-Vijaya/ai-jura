import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from 'react-query';
import axios from 'axios';
import styled from 'styled-components';
import { FaBell, FaCheck, FaCheckDouble } from 'react-icons/fa';

/**
 * Bifrost — NotificationsBell + dropdown panel.
 *
 * Mounted i Sidebar header (eller hvor som helst i appen).
 * Auto-poll hvert 60 sekund for nye unread.
 */

const Wrap = styled.div`
  position: relative;
  display: inline-block;
`;

const BellButton = styled.button`
  background: transparent;
  border: 1px solid transparent;
  color: ${(p) => p.theme.colors.textMuted};
  cursor: pointer;
  font-size: 1.05rem;
  padding: 6px;
  border-radius: 6px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;

  &:hover {
    background: ${(p) => p.theme.colors.surfaceAlt || 'rgba(0,0,0,0.04)'};
    color: ${(p) => p.theme.colors.text};
  }
  &:focus-visible {
    outline: 2px solid ${(p) => p.theme.colors.primary};
    outline-offset: 2px;
  }

  .badge {
    position: absolute;
    top: 0;
    right: 0;
    background: #a02020;
    color: white;
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.6rem;
    font-weight: 700;
    padding: 0 4px;
    min-width: 16px;
    height: 16px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    line-height: 1;
  }
`;

const Panel = styled.div`
  position: absolute;
  top: calc(100% + 6px);
  /* Bell sidder i venstre sidebar — panel skal poppe ud TIL HØJRE
     ind i main-content-area, ikke til venstre off-screen. */
  left: 0;
  width: 360px;
  max-height: 480px;
  background: ${(p) => p.theme.colors.surface || '#fff'};
  border: 1px solid ${(p) => p.theme.colors.border};
  border-radius: 8px;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.12);
  z-index: 1200;
  display: flex;
  flex-direction: column;
  overflow: hidden;

  @media (max-width: 720px) {
    /* På mobile er bell'en evt. flyttet — fallback: fixed centreret
       så panelet altid passer i viewport. */
    position: fixed;
    top: 56px;
    left: 12px;
    right: 12px;
    width: auto;
    max-height: calc(100vh - 80px);
  }
`;

const PanelHead = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid ${(p) => p.theme.colors.border};

  h3 {
    font-family: ${(p) => p.theme.fonts.display};
    font-size: 0.92rem;
    font-weight: 600;
    margin: 0;
    color: ${(p) => p.theme.colors.text};
  }
  button {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.66rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    background: transparent;
    border: none;
    color: ${(p) => p.theme.colors.primary};
    cursor: pointer;
    padding: 4px 8px;
    display: inline-flex;
    align-items: center;
    gap: 5px;

    &:hover { text-decoration: underline; }
    &:disabled { opacity: 0.4; cursor: not-allowed; }
  }
`;

const List = styled.div`
  overflow-y: auto;
  flex: 1;
`;

const Item = styled.button`
  width: 100%;
  background: ${(p) => (p.$unread ? (p.theme.colors.primarySoft || 'rgba(13,46,84,0.04)') : 'transparent')};
  border: none;
  border-bottom: 1px solid ${(p) => p.theme.colors.borderSoft};
  text-align: left;
  padding: 10px 14px;
  cursor: pointer;
  font-family: inherit;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 10px;
  align-items: start;

  &:hover { background: ${(p) => p.theme.colors.surfaceAlt || 'rgba(0,0,0,0.04)'}; }
  &:last-child { border-bottom: none; }

  .marker {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-top: 6px;
    background: ${({ $severity }) =>
      $severity === 'success' ? '#2d6a31' :
      $severity === 'danger' ? '#a02020' :
      $severity === 'warn' ? '#b08a4a' : '#0d2e54'};
    flex-shrink: 0;
  }

  .title {
    font-family: ${(p) => p.theme.fonts.body};
    font-size: 0.88rem;
    font-weight: ${(p) => (p.$unread ? 600 : 500)};
    color: ${(p) => p.theme.colors.text};
    line-height: 1.35;
  }

  .meta {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.7rem;
    color: ${(p) => p.theme.colors.textMuted};
    margin-top: 3px;
  }

  .message {
    font-size: 0.78rem;
    color: ${(p) => p.theme.colors.textMuted};
    margin-top: 3px;
    line-height: 1.4;
    overflow: hidden;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }
`;

const EmptyHint = styled.div`
  padding: 30px 14px;
  text-align: center;
  font-family: ${(p) => p.theme.fonts.body};
  font-size: 0.85rem;
  color: ${(p) => p.theme.colors.textMuted};
`;

const formatRelative = (iso) => {
  if (!iso) return '—';
  const d = new Date(iso);
  const diffMs = Date.now() - d.getTime();
  const min = Math.floor(diffMs / 60000);
  if (min < 1) return 'lige nu';
  if (min < 60) return `${min} min siden`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h} t siden`;
  const days = Math.floor(h / 24);
  if (days < 7) return `${days} d siden`;
  return d.toLocaleDateString('da-DK', { day: 'numeric', month: 'short' });
};

export const NotificationsBell = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const wrapRef = useRef(null);

  const { data } = useQuery(
    'notifications',
    async () => {
      const r = await axios.get('/api/v3/notifications?limit=15');
      return r.data;
    },
    { refetchInterval: 60_000, staleTime: 30_000 },
  );

  const unread = data?.unread || 0;
  const items = data?.items || [];

  // Close on outside click
  useEffect(() => {
    const handler = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    if (open) {
      document.addEventListener('mousedown', handler);
      return () => document.removeEventListener('mousedown', handler);
    }
  }, [open]);

  const handleClick = async (item) => {
    setOpen(false);
    if (!item.is_read) {
      try {
        await axios.post(`/api/v3/notifications/${item.id}/read`);
        queryClient.invalidateQueries('notifications');
      } catch (err) {
        console.warn('mark-read failed', err);
      }
    }
    if (item.link_url) {
      navigate(item.link_url);
    }
  };

  const handleMarkAll = async () => {
    try {
      await axios.post('/api/v3/notifications/read-all');
      queryClient.invalidateQueries('notifications');
    } catch (err) {
      console.warn('mark-all failed', err);
    }
  };

  return (
    <Wrap ref={wrapRef}>
      <BellButton
        onClick={() => setOpen((v) => !v)}
        aria-label={`Notifikationer${unread > 0 ? ` (${unread} ulæste)` : ''}`}
        aria-expanded={open}
      >
        <FaBell />
        {unread > 0 && <span className="badge">{unread > 99 ? '99+' : unread}</span>}
      </BellButton>

      {open && (
        <Panel role="region" aria-label="Notifikations-panel">
          <PanelHead>
            <h3>Notifikationer</h3>
            <button onClick={handleMarkAll} disabled={unread === 0}>
              <FaCheckDouble /> Markér alle
            </button>
          </PanelHead>
          <List>
            {items.length === 0 ? (
              <EmptyHint>Ingen notifikationer</EmptyHint>
            ) : (
              items.map((it) => (
                <Item
                  key={it.id}
                  $unread={!it.is_read}
                  $severity={it.severity}
                  onClick={() => handleClick(it)}
                >
                  <span className="marker" aria-hidden="true" />
                  <div>
                    <div className="title">{it.title}</div>
                    {it.message && <div className="message">{it.message}</div>}
                    <div className="meta">
                      {formatRelative(it.created_at)}
                      {it.case_id && ` · sag ${it.case_id}`}
                      {it.is_read && <> · <FaCheck style={{ opacity: 0.5 }} /></>}
                    </div>
                  </div>
                </Item>
              ))
            )}
          </List>
        </Panel>
      )}
    </Wrap>
  );
};

export default NotificationsBell;
