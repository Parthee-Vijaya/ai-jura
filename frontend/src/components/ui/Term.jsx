import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import styled from 'styled-components';
import { lookupTerm } from '../../data/glossary';

/**
 * Bifrost — <Term>: inline glossary-term med dotted underline + popover.
 *
 * Wrapper et fagudtryk (DPIA, FRIA, Art. 73, ...) og viser en lille forklaring
 * ved hover/focus. Hvis termen ikke findes i glossary'en, rendres børnene som
 * almindelig tekst (silent fallback) — så det aldrig "knækker" en page.
 *
 * Brug:
 *   <Term>DPIA</Term>                     → slår "DPIA" op
 *   <Term term="dpia">konsekvensanalyse</Term>   → slår "dpia" op, viser anden tekst
 *   <Term term="ce_maerkning">CE</Term>   → custom term-key + visning
 *
 * Popover-positionering: portal til document.body, dynamisk via getBoundingClientRect,
 * undgår clipping fra parent overflow / transform.
 */

const Trigger = styled.span`
  border-bottom: 1px dotted ${(p) => p.theme.colors.primary || '#0d2e54'};
  cursor: help;
  text-decoration: none;
  background: transparent;

  &:hover,
  &:focus-visible {
    background: ${(p) => p.theme.colors.primarySoft || 'rgba(13,46,84,0.08)'};
    outline: none;
  }

  &:focus-visible {
    border-radius: 2px;
    box-shadow: 0 0 0 2px ${(p) => p.theme.colors.primary || '#0d2e54'};
  }
`;

const Popover = styled.div`
  position: fixed;
  top: ${(p) => p.$top}px;
  left: ${(p) => p.$left}px;
  width: 320px;
  max-width: calc(100vw - 24px);
  background: ${(p) => p.theme.colors.surface || '#fff'};
  color: ${(p) => p.theme.colors.text || '#15243a'};
  border: 1px solid ${(p) => p.theme.colors.border || '#d8dde6'};
  border-radius: 6px;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.18);
  padding: 12px 14px;
  z-index: 9999;
  font-family: ${(p) => p.theme.fonts?.body || 'inherit'};
  font-size: 0.85rem;
  line-height: 1.45;
  pointer-events: auto;

  .label {
    font-family: ${(p) => p.theme.fonts?.display || 'inherit'};
    font-weight: 600;
    font-size: 0.92rem;
    color: ${(p) => p.theme.colors.primary || '#0d2e54'};
    margin: 0 0 4px;
  }
  .definition {
    margin: 0 0 8px;
    color: ${(p) => p.theme.colors.text || '#15243a'};
  }
  .source {
    font-family: ${(p) => p.theme.fonts?.mono || 'monospace'};
    font-size: 0.7rem;
    color: ${(p) => p.theme.colors.textMuted || '#5f6b7a'};
    margin: 0;
  }
  .source a {
    color: ${(p) => p.theme.colors.primary || '#0d2e54'};
    text-decoration: underline;
    text-decoration-style: dotted;
    margin-left: 6px;
  }
`;

const Term = ({ children, term }) => {
  const lookupKey =
    term ?? (typeof children === 'string' ? children : null);
  const def = lookupKey ? lookupTerm(lookupKey) : null;

  const triggerRef = useRef(null);
  const popoverRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState({ top: 0, left: 0 });

  // Position popover når open skifter
  useEffect(() => {
    if (!open || !triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    const POPOVER_WIDTH = 320;
    const PAD = 12;
    let left = rect.left;
    if (left + POPOVER_WIDTH > window.innerWidth - PAD) {
      left = Math.max(PAD, window.innerWidth - POPOVER_WIDTH - PAD);
    }
    let top = rect.bottom + 6;
    // Hvis popover ville gå under viewport-bunden, læg over trigger
    if (top + 180 > window.innerHeight) {
      top = Math.max(PAD, rect.top - 180 - 6);
    }
    setPos({ top, left });
  }, [open]);

  // Close on outside click eller Escape
  useEffect(() => {
    if (!open) return;
    const onClick = (e) => {
      if (
        !triggerRef.current?.contains(e.target) &&
        !popoverRef.current?.contains(e.target)
      ) {
        setOpen(false);
      }
    };
    const onKey = (e) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  // Silent fallback: hvis ingen definition findes, render children plain
  if (!def) {
    return <>{children}</>;
  }

  const popoverEl = open
    ? createPortal(
        <Popover
          ref={popoverRef}
          $top={pos.top}
          $left={pos.left}
          role="tooltip"
          aria-live="polite"
        >
          <p className="label">{def.label}</p>
          <p className="definition">{def.definition}</p>
          {def.source && (
            <p className="source">
              {def.source}
              {def.link && (
                <a
                  href={def.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                >
                  Læs mere →
                </a>
              )}
            </p>
          )}
        </Popover>,
        document.body,
      )
    : null;

  return (
    <>
      <Trigger
        ref={triggerRef}
        tabIndex={0}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => {
          // Lille delay så bruger kan flytte musen ind i popover
          setTimeout(() => {
            if (
              !popoverRef.current?.matches(':hover') &&
              !triggerRef.current?.matches(':hover')
            ) {
              setOpen(false);
            }
          }, 120);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={(e) => {
          // Click toggles — særligt for touch
          e.preventDefault();
          setOpen((v) => !v);
        }}
        aria-describedby={open ? `term-popover-${def.label}` : undefined}
      >
        {children}
      </Trigger>
      {popoverEl}
    </>
  );
};

export default Term;
