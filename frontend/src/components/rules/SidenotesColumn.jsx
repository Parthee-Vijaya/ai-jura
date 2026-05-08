import React from 'react';
import styled from 'styled-components';

/**
 * SidenotesColumn — Northern Modern marginalia column.
 *
 * Renders an ordered list of lov-citater (legal citations) numbered with
 * superscript ¹²³ markers. Each sidenote contains:
 *   - the citat (italic Plex Serif pull-quote)
 *   - source attribution + EUR-Lex / retsinformation link
 *   - last verified date in monospace
 *
 * Designed to sit in a sticky right column next to a document of rules.
 * The footnote IDs (#sn1, #sn2, ...) are clickable from inline `.fn` refs
 * in the body text.
 *
 * Props:
 *   notes: Array<{ id, citat, lov, artikel, url, sidst_verificeret }>
 *   eyebrow?: string — column header label (default: "Lov-kilder · marginalia")
 *   sticky?: boolean — make the column sticky on scroll (default: true)
 */

const Aside = styled.aside`
  border-left: 1px solid ${(p) => p.theme.colors.line};
  padding: 3.5rem 0 3.5rem 2.25rem;
  font-family: ${(p) => p.theme.fonts.sans};
  align-self: start;
  ${(p) =>
    p.$sticky &&
    `
    position: sticky;
    top: 96px;
    max-height: calc(100vh - 96px);
    overflow-y: auto;
  `}

  @media (max-width: 980px) {
    border-left: none;
    border-top: 1px solid ${(p) => p.theme.colors.line};
    padding: 2rem 0 0;
    margin-top: 2rem;
    position: static;
    max-height: none;
  }

  &::-webkit-scrollbar { width: 4px; }
  &::-webkit-scrollbar-thumb {
    background: ${(p) => p.theme.colors.line};
    border-radius: 2px;
  }
`;

const Eyebrow = styled.div`
  font-size: 0.69rem;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: ${(p) => p.theme.colors.inkFaded};
  margin-bottom: 1.1rem;
  font-weight: 600;
`;

const Note = styled.div`
  margin-bottom: 1.75rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid ${(p) => p.theme.colors.lineSoft};

  &:last-child {
    border-bottom: none;
    margin-bottom: 0;
    padding-bottom: 0;
  }
`;

const Num = styled.div`
  font-family: ${(p) => p.theme.fonts.display};
  font-size: 0.875rem;
  color: ${(p) => p.theme.colors.primary};
  font-weight: 700;
  margin-bottom: 0.4rem;
  line-height: 1;
`;

const Citat = styled.p`
  font-family: ${(p) => p.theme.fonts.body};
  font-size: 0.875rem;
  font-style: italic;
  color: ${(p) => p.theme.colors.ink};
  margin-bottom: 0.625rem;
  line-height: 1.55;
  border-left: 2px solid ${(p) => p.theme.colors.primarySoft};
  padding-left: 0.75rem;
`;

const Source = styled.div`
  font-size: 0.75rem;
  color: ${(p) => p.theme.colors.inkSoft};
  margin-bottom: 0.4rem;
  line-height: 1.45;

  a {
    color: ${(p) => p.theme.colors.primary};
    text-decoration: none;
    font-weight: 500;

    &:hover { text-decoration: underline; }
  }
`;

const Meta = styled.div`
  font-family: ${(p) => p.theme.fonts.mono};
  font-size: 0.625rem;
  color: ${(p) => p.theme.colors.inkFaded};
  letter-spacing: 0.04em;
`;

// Unicode superscript map for ¹²³⁴⁵⁶⁷⁸⁹⁰
const SUPERSCRIPT = ['⁰', '¹', '²', '³', '⁴', '⁵', '⁶', '⁷', '⁸', '⁹'];
export const toSuperscript = (n) => {
  if (n < 10) return SUPERSCRIPT[n];
  return String(n)
    .split('')
    .map((ch) => SUPERSCRIPT[parseInt(ch, 10)])
    .join('');
};

const SidenotesColumn = ({
  notes = [],
  eyebrow = 'Lov-kilder · marginalia',
  sticky = true,
}) => {
  if (!notes.length) return null;

  return (
    <Aside $sticky={sticky}>
      <Eyebrow>{eyebrow}</Eyebrow>
      {notes.map((note, idx) => {
        const num = idx + 1;
        return (
          <Note key={note.id || num} id={`sn${num}`}>
            <Num>{toSuperscript(num)}</Num>
            {note.citat && <Citat>"{note.citat}"</Citat>}
            <Source>
              {[note.lov, note.artikel].filter(Boolean).join(' · ')}
              {note.url && (
                <>
                  {' · '}
                  <a href={note.url} target="_blank" rel="noreferrer noopener">
                    Læs kilden →
                  </a>
                </>
              )}
            </Source>
            {note.sidst_verificeret && (
              <Meta>sidst_verificeret: {note.sidst_verificeret}</Meta>
            )}
          </Note>
        );
      })}
    </Aside>
  );
};

export default SidenotesColumn;
