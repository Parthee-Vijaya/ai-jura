import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import styled from 'styled-components';
import axios from 'axios';
import { FaSearch, FaArrowRight } from 'react-icons/fa';

/**
 * Bifrost — Global Cmd+K spotlight søgning.
 *
 * Mounted ONCE i App.js. Lyttet på Cmd+K (Mac) / Ctrl+K (Win/Linux)
 * for at åbne modalen. ESC lukker. Arrow-keys + Enter navigerer.
 *
 * Søger i: cases, vurderinger, evidens, regler, videnbase, skabeloner.
 */

const TYPE_LABELS = {
  case: 'Sag',
  vurdering: 'Vurdering',
  evidens: 'Evidens',
  skabelon: 'Skabelon',
  regel: 'Regel',
  videnbase: 'Videnbase',
};

const TYPE_COLORS = {
  case: '#0d2e54',
  vurdering: '#a03612',
  evidens: '#2d6a31',
  skabelon: '#b08a4a',
  regel: '#555a64',
  videnbase: '#0d2e54',
};

const Backdrop = styled.div`
  position: fixed;
  inset: 0;
  background: rgba(20, 24, 31, 0.55);
  z-index: 1500;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 12vh;

  @media (max-width: 720px) {
    padding-top: 4vh;
    align-items: flex-start;
  }
`;

const Sheet = styled.div`
  background: ${(p) => p.theme.colors.surface || '#fff'};
  border: 1px solid ${(p) => p.theme.colors.border};
  border-radius: 10px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
  width: min(640px, calc(100vw - 32px));
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
`;

const InputWrap = styled.div`
  display: flex;
  align-items: center;
  padding: 14px 18px;
  gap: 12px;
  border-bottom: 1px solid ${(p) => p.theme.colors.border};

  svg {
    color: ${(p) => p.theme.colors.textMuted};
    font-size: 0.95rem;
  }

  input {
    flex: 1;
    border: none;
    outline: none;
    background: transparent;
    font-family: ${(p) => p.theme.fonts.body};
    font-size: 1rem;
    color: ${(p) => p.theme.colors.text};

    &::placeholder { color: ${(p) => p.theme.colors.textFaded}; font-style: italic; }
  }

  .kbd {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.7rem;
    background: ${(p) => p.theme.colors.surfaceAlt || 'rgba(0,0,0,0.04)'};
    border: 1px solid ${(p) => p.theme.colors.border};
    padding: 2px 6px;
    border-radius: 4px;
    color: ${(p) => p.theme.colors.textMuted};
  }
`;

const Results = styled.div`
  overflow-y: auto;
  flex: 1;
  padding: 6px 0;
`;

const ResultItem = styled.button`
  width: 100%;
  background: ${(p) => (p.$active ? (p.theme.colors.surfaceAlt || 'rgba(13,46,84,0.04)') : 'transparent')};
  border: none;
  text-align: left;
  padding: 10px 18px;
  display: grid;
  grid-template-columns: 70px 1fr auto;
  gap: 12px;
  align-items: center;
  cursor: pointer;
  font-family: inherit;
  border-left: 3px solid ${(p) => (p.$active ? p.theme.colors.primary : 'transparent')};

  &:hover { background: ${(p) => p.theme.colors.surfaceAlt || 'rgba(13,46,84,0.04)'}; }

  .type {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: ${(p) => TYPE_COLORS[p.$type] || p.theme.colors.textMuted};
    font-weight: 700;
  }
  .body {
    min-width: 0;
  }
  .label {
    font-family: ${(p) => p.theme.fonts.body};
    font-size: 0.95rem;
    color: ${(p) => p.theme.colors.text};
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .sublabel {
    font-family: ${(p) => p.theme.fonts.body};
    font-size: 0.78rem;
    color: ${(p) => p.theme.colors.textMuted};
    margin-top: 2px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .arrow {
    color: ${(p) => (p.$active ? p.theme.colors.primary : 'transparent')};
    font-size: 0.78rem;
  }
`;

const Hint = styled.div`
  padding: 10px 18px;
  border-top: 1px solid ${(p) => p.theme.colors.border};
  font-family: ${(p) => p.theme.fonts.mono};
  font-size: 0.7rem;
  color: ${(p) => p.theme.colors.textMuted};
  display: flex;
  gap: 14px;
  flex-wrap: wrap;

  kbd {
    background: ${(p) => p.theme.colors.surfaceAlt || 'rgba(0,0,0,0.04)'};
    border: 1px solid ${(p) => p.theme.colors.border};
    padding: 1px 5px;
    border-radius: 3px;
    margin-right: 3px;
  }
`;

const EmptyHint = styled.div`
  padding: 30px 18px;
  text-align: center;
  font-family: ${(p) => p.theme.fonts.body};
  font-size: 0.92rem;
  color: ${(p) => p.theme.colors.textMuted};

  .kbd {
    font-family: ${(p) => p.theme.fonts.mono};
    background: ${(p) => p.theme.colors.surfaceAlt || 'rgba(0,0,0,0.04)'};
    border: 1px solid ${(p) => p.theme.colors.border};
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 0.78rem;
  }
`;

export const GlobalSearch = () => {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState('');
  const [results, setResults] = useState([]);
  const [active, setActive] = useState(0);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);
  const debounceRef = useRef(null);

  // Cmd+K / Ctrl+K to open
  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setOpen(true);
      }
      if (e.key === 'Escape' && open) {
        setOpen(false);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open]);

  // Auto-focus input on open
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQ('');
      setResults([]);
      setActive(0);
    }
  }, [open]);

  // Debounced search
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!q || q.trim().length < 2) {
      setResults([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    debounceRef.current = setTimeout(async () => {
      try {
        const r = await axios.get(`/api/v3/search?q=${encodeURIComponent(q)}&limit=15`);
        setResults(r.data?.results || []);
        setActive(0);
      } catch (err) {
        console.error('search failed', err);
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 250);
    return () => debounceRef.current && clearTimeout(debounceRef.current);
  }, [q]);

  const handleKey = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, Math.max(0, results.length - 1)));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((a) => Math.max(0, a - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (results[active]) handleSelect(results[active]);
    }
  };

  const handleSelect = (item) => {
    // Skabelon-results er API-paths — vi kan ikke navigere direkte
    const url = item.type === 'skabelon' ? '/sager' : item.url;
    setOpen(false);
    if (url?.startsWith('http')) {
      window.open(url, '_blank', 'noopener');
    } else {
      navigate(url);
    }
  };

  if (!open) return null;

  return (
    <Backdrop onClick={(e) => { if (e.target === e.currentTarget) setOpen(false); }}>
      <Sheet onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-label="Søg">
        <InputWrap>
          <FaSearch />
          <input
            ref={inputRef}
            type="search"
            placeholder="Søg sager, vurderinger, regler, evidens, videnbase…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={handleKey}
            autoComplete="off"
            spellCheck={false}
          />
          <span className="kbd">ESC</span>
        </InputWrap>

        <Results>
          {q.length < 2 && (
            <EmptyHint>
              Skriv mindst 2 tegn for at søge. Prøv <span className="kbd">K-2026</span>,{' '}
              <span className="kbd">DPIA</span> eller <span className="kbd">artikel 6</span>.
            </EmptyHint>
          )}
          {q.length >= 2 && loading && results.length === 0 && (
            <EmptyHint>Søger…</EmptyHint>
          )}
          {q.length >= 2 && !loading && results.length === 0 && (
            <EmptyHint>Ingen resultater for "{q}".</EmptyHint>
          )}
          {results.map((item, i) => (
            <ResultItem
              key={`${item.type}-${item.url}-${i}`}
              $active={i === active}
              $type={item.type}
              onClick={() => handleSelect(item)}
              onMouseEnter={() => setActive(i)}
            >
              <span className="type">{TYPE_LABELS[item.type] || item.type}</span>
              <div className="body">
                <div className="label">{item.label}</div>
                {item.sublabel && <div className="sublabel">{item.sublabel}</div>}
              </div>
              <FaArrowRight className="arrow" />
            </ResultItem>
          ))}
        </Results>

        <Hint>
          <span><kbd>↑</kbd><kbd>↓</kbd> navigér</span>
          <span><kbd>↵</kbd> åbn</span>
          <span><kbd>ESC</kbd> luk</span>
          <span style={{ marginLeft: 'auto' }}>Cmd+K / Ctrl+K hvor som helst</span>
        </Hint>
      </Sheet>
    </Backdrop>
  );
};

export default GlobalSearch;
