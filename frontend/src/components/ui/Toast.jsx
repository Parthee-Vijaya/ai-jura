import React, { createContext, useCallback, useContext, useState } from 'react';
import styled, { keyframes } from 'styled-components';
import { FaCheck, FaTimes, FaExclamationTriangle, FaInfoCircle } from 'react-icons/fa';

/**
 * Bifrost — Toast-system (a11y aria-live)
 *
 * Usage in App:
 *   <ToastProvider><App /></ToastProvider>
 *
 * In components:
 *   const toast = useToast();
 *   toast.success('Gemt på sag K-2026-0184', { link: '/sag/K-2026-0184' });
 *   toast.error('Kunne ikke gemme');
 */

const ToastContext = createContext(null);

const slideIn = keyframes`
  from { transform: translateX(120%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
`;

const Region = styled.div.attrs({
  role: 'status',
  'aria-live': 'polite',
  'aria-atomic': 'true',
})`
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 2000;
  display: flex;
  flex-direction: column;
  gap: 10px;
  pointer-events: none;
  max-width: min(420px, calc(100vw - 32px));

  @media (max-width: 720px) {
    bottom: 80px; /* over bottom-nav */
    right: 12px;
    left: 12px;
    max-width: none;
  }
`;

const toneColors = {
  success: { bg: '#2d6a31', accent: '#1f4d22' },
  error: { bg: '#a02020', accent: '#7a1818' },
  warn: { bg: '#6e5527', accent: '#8a6c38' },
  info: { bg: '#0d2e54', accent: '#0a2440' },
};

const Item = styled.div`
  pointer-events: auto;
  background: ${(p) => p.theme.colors.surface || '#fff'};
  border: 1px solid ${(p) => p.theme.colors.border};
  border-left: 3px solid ${(p) => toneColors[p.$tone]?.bg || '#666'};
  border-radius: 6px;
  padding: 0.7rem 0.85rem;
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 10px;
  align-items: center;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.15);
  font-family: ${(p) => p.theme.fonts.body};
  animation: ${slideIn} 0.25s ease-out;

  @media (prefers-reduced-motion: reduce) {
    animation: none;
  }

  .icon {
    color: ${(p) => toneColors[p.$tone]?.bg || '#666'};
    font-size: 0.95rem;
  }
  .body {
    font-size: 0.88rem;
    color: ${(p) => p.theme.colors.text};
    line-height: 1.4;
    min-width: 0;

    a {
      color: ${(p) => toneColors[p.$tone]?.bg || p.theme.colors.primary};
      font-weight: 500;
      margin-left: 6px;
    }
  }
  .close {
    background: transparent;
    border: none;
    color: ${(p) => p.theme.colors.textFaded};
    cursor: pointer;
    padding: 4px;
    font-size: 0.85rem;
    border-radius: 3px;
    min-width: 28px;
    min-height: 28px;
    &:hover { color: ${(p) => p.theme.colors.text}; }
  }
`;

const ICONS = {
  success: FaCheck,
  error: FaExclamationTriangle,
  warn: FaExclamationTriangle,
  info: FaInfoCircle,
};

let nextId = 1;

export const ToastProvider = ({ children, defaultDuration = 4500 }) => {
  const [toasts, setToasts] = useState([]);

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const push = useCallback((tone, message, opts = {}) => {
    const id = nextId++;
    const duration = opts.duration ?? defaultDuration;
    setToasts((prev) => [...prev, { id, tone, message, link: opts.link, linkLabel: opts.linkLabel }]);
    if (duration > 0) {
      setTimeout(() => dismiss(id), duration);
    }
    return id;
  }, [defaultDuration, dismiss]);

  const api = {
    success: (msg, opts) => push('success', msg, opts),
    error: (msg, opts) => push('error', msg, { ...opts, duration: opts?.duration ?? 7000 }),
    warn: (msg, opts) => push('warn', msg, opts),
    info: (msg, opts) => push('info', msg, opts),
    dismiss,
  };

  return (
    <ToastContext.Provider value={api}>
      {children}
      <Region>
        {toasts.map((t) => {
          const Icon = ICONS[t.tone] || FaInfoCircle;
          return (
            <Item key={t.id} $tone={t.tone}>
              <Icon className="icon" aria-hidden="true" />
              <div className="body">
                {t.message}
                {t.link && (
                  <a href={t.link}>{t.linkLabel || 'Åbn →'}</a>
                )}
              </div>
              <button
                className="close"
                onClick={() => dismiss(t.id)}
                aria-label="Luk besked"
              >
                <FaTimes />
              </button>
            </Item>
          );
        })}
      </Region>
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    // Soft fallback: ingen ToastProvider — log til console
    return {
      success: (m) => console.log('[toast.success]', m),
      error: (m) => console.error('[toast.error]', m),
      warn: (m) => console.warn('[toast.warn]', m),
      info: (m) => console.info('[toast.info]', m),
      dismiss: () => {},
    };
  }
  return ctx;
};

export default useToast;
