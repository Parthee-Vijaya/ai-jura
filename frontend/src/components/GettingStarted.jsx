import React from 'react';
import { useNavigate } from 'react-router-dom';
import styled from 'styled-components';
import {
  FaPlay,
  FaSearch,
  FaClipboardCheck,
  FaArrowRight,
  FaBookOpen,
} from 'react-icons/fa';

/**
 * Bifrost — Getting Started / Onboarding-kort.
 *
 * Vises når en bruger er ny og ikke har data endnu (fx ingen sager på
 * SagerPage). Forklarer 3-trins workflow og giver tydelige CTAs.
 *
 * Kompakt variant: <GettingStarted compact /> — bruges i sidepanel.
 *
 * Designet til at hjælpe sagsbehandlere komme i gang uden at skulle
 * gætte sig til hvor de starter.
 */

const Wrap = styled.section`
  display: grid;
  grid-template-columns: 1fr;
  gap: ${(p) => (p.$compact ? '1rem' : '1.5rem')};
  padding: ${(p) => (p.$compact ? '1.25rem' : '2rem')};
  background: ${(p) => p.theme.colors.surface || '#fff'};
  border: 1px solid ${(p) => p.theme.colors.border || '#d8dde6'};
  border-radius: 10px;
  margin-bottom: 1.5rem;

  @media (min-width: 900px) {
    grid-template-columns: ${(p) => (p.$compact ? '1fr' : '1fr 2fr')};
    align-items: start;
  }

  .intro {
    .eyebrow {
      font-family: ${(p) => p.theme.fonts.mono};
      font-size: 0.7rem;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: ${(p) => p.theme.colors.primary || '#0d2e54'};
      margin: 0 0 0.5rem;
    }
    h2 {
      font-family: ${(p) => p.theme.fonts.display};
      font-size: ${(p) => (p.$compact ? '1.05rem' : '1.4rem')};
      font-weight: 600;
      color: ${(p) => p.theme.colors.text};
      margin: 0 0 0.6rem;
      line-height: 1.25;
    }
    p {
      font-family: ${(p) => p.theme.fonts.body};
      font-size: 0.92rem;
      line-height: 1.55;
      color: ${(p) => p.theme.colors.textMuted};
      margin: 0;
    }
  }

  .steps {
    display: grid;
    grid-template-columns: 1fr;
    gap: 0.75rem;

    @media (min-width: 700px) {
      grid-template-columns: ${(p) => (p.$compact ? '1fr' : 'repeat(3, 1fr)')};
    }
  }
`;

const Step = styled.button`
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  text-align: left;
  background: ${(p) => p.theme.colors.surfaceAlt || '#f6f8fb'};
  border: 1px solid ${(p) => p.theme.colors.borderSoft || '#e2e6ec'};
  border-radius: 8px;
  padding: 1rem;
  cursor: pointer;
  font-family: inherit;
  transition: transform 120ms ease, box-shadow 120ms ease, border-color 120ms ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 18px rgba(13, 46, 84, 0.08);
    border-color: ${(p) => p.theme.colors.primary || '#0d2e54'};
  }
  &:focus-visible {
    outline: none;
    border-color: ${(p) => p.theme.colors.primary || '#0d2e54'};
    box-shadow: 0 0 0 2px ${(p) => p.theme.colors.primary || '#0d2e54'};
  }

  .head {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin-bottom: 0.5rem;
    color: ${(p) => p.theme.colors.primary || '#0d2e54'};

    .num {
      font-family: ${(p) => p.theme.fonts.mono};
      font-size: 0.7rem;
      font-weight: 700;
      letter-spacing: 0.05em;
      background: ${(p) => p.theme.colors.primary || '#0d2e54'};
      color: white;
      padding: 0.15rem 0.45rem;
      border-radius: 3px;
    }
    .icon {
      font-size: 0.95rem;
    }
  }
  .title {
    font-family: ${(p) => p.theme.fonts.display};
    font-size: 0.95rem;
    font-weight: 600;
    color: ${(p) => p.theme.colors.text};
    margin: 0 0 0.3rem;
  }
  .desc {
    font-size: 0.82rem;
    line-height: 1.45;
    color: ${(p) => p.theme.colors.textMuted};
    margin: 0 0 0.8rem;
  }
  .cta {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: ${(p) => p.theme.colors.primary || '#0d2e54'};
    margin-top: auto;
  }
`;

const HelpRow = styled.div`
  margin-top: 0.5rem;
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: center;
  font-size: 0.82rem;
  color: ${(p) => p.theme.colors.textMuted};

  a {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    color: ${(p) => p.theme.colors.primary || '#0d2e54'};
    text-decoration: none;
    border-bottom: 1px dotted currentColor;

    &:hover { border-bottom-style: solid; }
  }
`;

const STEPS = [
  {
    num: '1',
    icon: FaPlay,
    title: 'Start indkøbsprocessen',
    desc: 'Beskriv behov, dobbeltsystem-tjek og om I køber eller udvikler. Gemmes automatisk som kladde.',
    path: '/proces?step=indkoeb',
    cta: 'Start ny sag',
  },
  {
    num: '2',
    icon: FaSearch,
    title: 'EU AI Act-tjek',
    desc: 'Besvar 33 standardspørgsmål — Bifrost klassificerer systemet (forbudt/højrisiko/begrænset/minimal).',
    path: '/proces?step=eu-checker',
    cta: 'Åbn EU-checker',
  },
  {
    num: '3',
    icon: FaClipboardCheck,
    title: 'Bifrost-vurdering',
    desc: 'Kør den deterministiske regelmotor mod 21 lov-regler — får GO / BETINGET-GO / NO-GO med citater.',
    path: '/proces?step=vurdering',
    cta: 'Kør vurdering',
  },
];

const GettingStarted = ({ compact = false, hideTitle = false }) => {
  const navigate = useNavigate();
  return (
    <Wrap $compact={compact} aria-label="Sådan kommer du i gang med Bifrost">
      {!hideTitle && (
        <div className="intro">
          <p className="eyebrow">Sådan kommer du i gang</p>
          <h2>Tre trin fra idé til hjemlet AI-vurdering</h2>
          <p>
            Bifrost guider dig fra første tanke om en AI-løsning til en
            samlet compliance-vurdering med ordret lovcitat. Du kan
            altid hoppe mellem trinene — sagen følger med.
          </p>
        </div>
      )}
      <div>
        <div className="steps">
          {STEPS.map((s) => {
            const Icon = s.icon;
            return (
              <Step
                key={s.num}
                type="button"
                onClick={() => navigate(s.path)}
                aria-label={`Trin ${s.num}: ${s.title}`}
              >
                <span className="head">
                  <span className="num">Trin {s.num}</span>
                  <Icon className="icon" aria-hidden="true" />
                </span>
                <span className="title">{s.title}</span>
                <span className="desc">{s.desc}</span>
                <span className="cta">
                  {s.cta} <FaArrowRight />
                </span>
              </Step>
            );
          })}
        </div>
        <HelpRow>
          <a href="/ressourcer">
            <FaBookOpen aria-hidden="true" /> Lov-bibliotek + skabeloner
          </a>
          <a href="/proces">
            Hele 3-trins-flowet på én side <FaArrowRight aria-hidden="true" />
          </a>
        </HelpRow>
      </div>
    </Wrap>
  );
};

export default GettingStarted;
