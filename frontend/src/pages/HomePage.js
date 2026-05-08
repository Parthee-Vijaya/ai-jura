import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import styled from 'styled-components';

import NewsSection from '../components/NewsSection';
import DataOverview from '../components/data-overview/DataOverview';
import aiActDidYouKnowFacts from '../data/aiActDidYouKnow';

/**
 * Tyr — HomePage (Northern Modern, Design system v2)
 *
 * Helt nyt layout der matcher DESIGN.md. Drop'er den gamle Forseti-hero
 * med rødt-gradient, version-card, system-status-block og 3-kolonne
 * icon-feature-grid (AI-slop). Erstattet af:
 *   1. Hero — wordmark "Tyr ᛏ" + h1 + lede + primær/sekundær CTA
 *   2. Sådan virker Tyr — 4-trins workflow (hairline border, mono-tal)
 *   3. Hvad du bør vide — 3 rotating facts som editorial cards
 *   4. NewsSection (live RSS)
 *   5. DataOverview (drift-overblik nederst — version + system-status)
 */

// ---- Layout primitives -------------------------------------------------

const Page = styled.div`
  max-width: 1240px;
  margin: 0 auto;
  padding: 2.25rem 1.75rem 4rem;
  display: flex;
  flex-direction: column;
  gap: 56px;

  @media (max-width: 720px) {
    padding: 1.5rem 1rem 3rem;
    gap: 40px;
  }
`;

// ---- Hero ---------------------------------------------------------------

const Hero = styled.section`
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 48px;
  padding-bottom: 32px;
  border-bottom: 1px solid ${(p) => p.theme.colors.borderSoft};

  @media (max-width: 920px) {
    grid-template-columns: 1fr;
    gap: 32px;
  }
`;

const HeroPrimary = styled.div`
  display: flex;
  flex-direction: column;
  gap: 18px;
`;

const Wordmark = styled.div`
  display: inline-flex;
  align-items: baseline;
  gap: 10px;
  font-family: ${(p) => p.theme.fonts.display};
  font-weight: 700;
  font-size: 1.05rem;
  letter-spacing: 0.06em;
  color: ${(p) => p.theme.colors.text};

  .rune {
    color: ${(p) => p.theme.colors.bronze};
    font-size: 1.4rem;
    line-height: 1;
  }

  .ver {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.7rem;
    letter-spacing: 0.1em;
    color: ${(p) => p.theme.colors.textMuted};
    margin-left: 6px;
  }
`;

const HeroTitle = styled.h1`
  font-family: ${(p) => p.theme.fonts.display};
  font-weight: 700;
  font-size: clamp(2.4rem, 5vw, 3.6rem);
  letter-spacing: -0.025em;
  line-height: 1.05;
  color: ${(p) => p.theme.colors.text};
  margin: 0;
`;

const HeroLede = styled.p`
  font-family: ${(p) => p.theme.fonts.body};
  font-size: 1.1rem;
  line-height: 1.6;
  color: ${(p) => p.theme.colors.textMuted};
  margin: 0;
  max-width: 540px;
`;

const CTARow = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 8px;
`;

const PrimaryCTA = styled(Link)`
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 12px 22px;
  background: ${(p) => p.theme.colors.primary};
  color: ${(p) => p.theme.colors.white};
  font-family: ${(p) => p.theme.fonts.sans};
  font-weight: 500;
  font-size: 0.95rem;
  letter-spacing: 0.01em;
  text-decoration: none;
  border-radius: ${(p) => p.theme.borderRadius};
  border: 1px solid ${(p) => p.theme.colors.primary};
  transition: ${(p) => p.theme.animations.transitionFast};

  &:hover {
    background: ${(p) => p.theme.colors.primaryDark};
    border-color: ${(p) => p.theme.colors.primaryDark};
  }

  .arrow { font-family: ${(p) => p.theme.fonts.mono}; font-weight: 400; }
`;

const GhostCTA = styled(Link)`
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 12px 22px;
  background: transparent;
  color: ${(p) => p.theme.colors.primary};
  font-family: ${(p) => p.theme.fonts.sans};
  font-weight: 500;
  font-size: 0.95rem;
  letter-spacing: 0.01em;
  text-decoration: none;
  border-radius: ${(p) => p.theme.borderRadius};
  border: 1px solid ${(p) => p.theme.colors.border};
  transition: ${(p) => p.theme.animations.transitionFast};

  &:hover {
    border-color: ${(p) => p.theme.colors.primary};
    background: ${(p) => p.theme.colors.primarySoft};
  }
`;

// Hero-sidekort — quick-stats om aktive regler + sagsmasse
const HeroAside = styled.aside`
  background: ${(p) => p.theme.colors.surface};
  border: 1px solid ${(p) => p.theme.colors.border};
  border-radius: ${(p) => p.theme.borderRadius};
  padding: 24px 26px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  align-self: start;
`;

const AsideEyebrow = styled.div`
  font-family: ${(p) => p.theme.fonts.mono};
  font-size: 0.68rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: ${(p) => p.theme.colors.bronze};
`;

const AsideStat = styled.div`
  padding-bottom: 14px;
  border-bottom: 1px solid ${(p) => p.theme.colors.borderSoft};

  &:last-child { border-bottom: none; padding-bottom: 0; }

  .label {
    font-family: ${(p) => p.theme.fonts.sans};
    font-size: 0.78rem;
    letter-spacing: 0.04em;
    color: ${(p) => p.theme.colors.textMuted};
    margin-bottom: 4px;
  }
  .value {
    font-family: ${(p) => p.theme.fonts.display};
    font-weight: 700;
    font-size: 1.3rem;
    color: ${(p) => p.theme.colors.text};
    letter-spacing: -0.01em;
  }
  .value .accent { color: ${(p) => p.theme.colors.primary}; }
  .meta {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.72rem;
    color: ${(p) => p.theme.colors.textFaded};
    margin-top: 4px;
  }
`;

// ---- Workflow -----------------------------------------------------------

const Section = styled.section`
  display: flex;
  flex-direction: column;
  gap: 24px;
`;

const SectionHeader = styled.header`
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-width: 720px;
`;

const SectionEyebrow = styled.span`
  font-family: ${(p) => p.theme.fonts.mono};
  font-size: 0.7rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: ${(p) => p.theme.colors.bronze};
`;

const SectionTitle = styled.h2`
  font-family: ${(p) => p.theme.fonts.display};
  font-weight: 700;
  font-size: 1.65rem;
  letter-spacing: -0.015em;
  margin: 0;
  color: ${(p) => p.theme.colors.text};
`;

const SectionLede = styled.p`
  font-family: ${(p) => p.theme.fonts.body};
  font-size: 1rem;
  line-height: 1.55;
  color: ${(p) => p.theme.colors.textMuted};
  margin: 0;
`;

const Steps = styled.ol`
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  counter-reset: step;

  @media (max-width: 920px) {
    grid-template-columns: repeat(2, 1fr);
  }
  @media (max-width: 540px) {
    grid-template-columns: 1fr;
  }
`;

const Step = styled.li`
  background: ${(p) => p.theme.colors.surface};
  border: 1px solid ${(p) => p.theme.colors.border};
  border-radius: ${(p) => p.theme.borderRadius};
  padding: 22px 22px 24px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  position: relative;

  .num {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.74rem;
    letter-spacing: 0.06em;
    color: ${(p) => p.theme.colors.bronze};
    margin-bottom: 4px;
  }
  .title {
    font-family: ${(p) => p.theme.fonts.display};
    font-weight: 600;
    font-size: 1.05rem;
    color: ${(p) => p.theme.colors.text};
    letter-spacing: -0.005em;
  }
  .body {
    font-family: ${(p) => p.theme.fonts.body};
    font-size: 0.92rem;
    line-height: 1.5;
    color: ${(p) => p.theme.colors.textMuted};
  }
`;

// ---- Editorial fact cards ----------------------------------------------

const FactsRow = styled.div`
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;

  @media (max-width: 920px) {
    grid-template-columns: 1fr;
  }
`;

const FactCard = styled.article`
  background: ${(p) => p.theme.colors.surface};
  border: 1px solid ${(p) => p.theme.colors.border};
  border-left: 3px solid ${(p) => p.theme.colors.bronze};
  border-radius: ${(p) => p.theme.borderRadius};
  padding: 22px 24px;
  display: flex;
  flex-direction: column;
  gap: 10px;

  .topic {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.7rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: ${(p) => p.theme.colors.bronze};
  }
  h3 {
    font-family: ${(p) => p.theme.fonts.display};
    font-weight: 600;
    font-size: 1.1rem;
    letter-spacing: -0.005em;
    margin: 0;
    color: ${(p) => p.theme.colors.text};
  }
  p {
    font-family: ${(p) => p.theme.fonts.body};
    font-size: 0.94rem;
    line-height: 1.6;
    color: ${(p) => p.theme.colors.text};
    margin: 0;
    display: -webkit-box;
    -webkit-line-clamp: 6;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  a {
    font-family: ${(p) => p.theme.fonts.sans};
    font-size: 0.82rem;
    letter-spacing: 0.02em;
    color: ${(p) => p.theme.colors.primary};
    text-decoration: none;
    margin-top: 4px;

    &:hover { text-decoration: underline; }
  }
`;

const FactsRotateCue = styled.div`
  font-family: ${(p) => p.theme.fonts.mono};
  font-size: 0.7rem;
  letter-spacing: 0.06em;
  color: ${(p) => p.theme.colors.textFaded};
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-top: -8px;
`;

// ---- Footer ribbon ------------------------------------------------------

const Footer = styled.footer`
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 14px;
  padding-top: 24px;
  border-top: 1px solid ${(p) => p.theme.colors.borderSoft};
  font-family: ${(p) => p.theme.fonts.mono};
  font-size: 0.72rem;
  letter-spacing: 0.04em;
  color: ${(p) => p.theme.colors.textFaded};
`;

// ---- Static content -----------------------------------------------------

const STEPS = [
  {
    num: '01',
    title: 'Beskriv',
    body: 'Beskriv et AI-system i fri tekst eller upload kontrakt/DPIA. LLM extraherer signaler — den må aldrig ændre afgørelsen.',
  },
  {
    num: '02',
    title: 'Vurder',
    body: 'Deterministisk regelmotor evaluerer 15 lovartikler (EU AI Act, GDPR, forvaltningslov, offentlighedslov) mod input.',
  },
  {
    num: '03',
    title: 'Hjemling',
    body: 'Hver triggered regel får ordret lov-citat med direkte link til EUR-Lex eller Retsinformation.',
  },
  {
    num: '04',
    title: 'Verifikation',
    body: 'Citat-verifier kører dagligt kl. 04:00 og flagger hvis et citat ikke længere findes ordret i kilden.',
  },
];

const TOPIC_LABELS = {
  'ai-': 'AI-teknologi',
  'aiact-': 'EU AI Act',
  'gdpr-': 'GDPR',
  'compliance-': 'Compliance',
  'fvl-': 'Forvaltningslov',
  'kommunal-': 'Kommunal praksis',
};

const topicForFact = (fact) => {
  const id = String(fact.id || '');
  for (const [prefix, label] of Object.entries(TOPIC_LABELS)) {
    if (id.startsWith(prefix)) return label;
  }
  return 'Faglig viden';
};

// ---- Component ---------------------------------------------------------

const HomePage = () => {
  const facts = aiActDidYouKnowFacts || [];
  const [factOffset, setFactOffset] = useState(() => {
    if (facts.length === 0) return 0;
    return Math.floor(Math.random() * facts.length);
  });

  useEffect(() => {
    if (facts.length <= 3) return undefined;
    const id = window.setInterval(() => {
      setFactOffset((prev) => (prev + 3) % facts.length);
    }, 120_000);
    return () => window.clearInterval(id);
  }, [facts.length]);

  const visibleFacts = useMemo(() => {
    if (facts.length === 0) return [];
    return Array.from({ length: 3 }, (_, idx) => facts[(factOffset + idx) % facts.length]);
  }, [factOffset, facts]);

  return (
    <Page>
      {/* ============ HERO ============ */}
      <Hero>
        <HeroPrimary>
          <Wordmark>
            <span>Tyr</span>
            <span className="rune" aria-hidden="true">ᛏ</span>
            <span className="ver">v3 · Kalundborg</span>
          </Wordmark>
          <HeroTitle>Hver vurdering peger på den ordret-verificerede lovartikel.</HeroTitle>
          <HeroLede>
            Tyr er Kalundborg Kommunes interne AI-compliance-platform. Beskriv et AI-system,
            upload kontrakt eller DPIA — og få en hjemlet GO / BETINGET-GO / NO-GO med
            ordret citat fra EU AI Act, GDPR, forvaltningslov og offentlighedslov.
          </HeroLede>
          <CTARow>
            <PrimaryCTA to="/vurdering">Start vurdering <span className="arrow">→</span></PrimaryCTA>
            <GhostCTA to="/sager">Sag-overblik</GhostCTA>
          </CTARow>
        </HeroPrimary>

        <HeroAside>
          <AsideEyebrow>I drift lige nu</AsideEyebrow>
          <AsideStat>
            <div className="label">Aktive lovregler</div>
            <div className="value"><span className="accent">15</span> regler</div>
            <div className="meta">EU AI Act · GDPR · Forvaltningslov · Offentlighedslov</div>
          </AsideStat>
          <AsideStat>
            <div className="label">Kilde-verifikation</div>
            <div className="value">Dagligt kl. <span className="accent">04:00</span></div>
            <div className="meta">EUR-Lex + Retsinformation · automatisk flagging</div>
          </AsideStat>
          <AsideStat>
            <div className="label">LLM</div>
            <div className="value">Lokal eller Azure</div>
            <div className="meta">må aldrig ændre afgørelsen — kun ekstrahere signaler</div>
          </AsideStat>
        </HeroAside>
      </Hero>

      {/* ============ WORKFLOW ============ */}
      <Section>
        <SectionHeader>
          <SectionEyebrow>Sådan virker Tyr</SectionEyebrow>
          <SectionTitle>Fire trin fra fri tekst til hjemlet vurdering</SectionTitle>
          <SectionLede>
            Fra sagsbehandlerens beskrivelse til en deterministisk afgørelse med live-verificerede
            lov-citater. LLM må aldrig ændre afgørelsen — kun extrahere signaler.
          </SectionLede>
        </SectionHeader>
        <Steps>
          {STEPS.map((s) => (
            <Step key={s.num}>
              <div className="num">{s.num}</div>
              <div className="title">{s.title}</div>
              <div className="body">{s.body}</div>
            </Step>
          ))}
        </Steps>
      </Section>

      {/* ============ EDITORIAL FACTS ============ */}
      {visibleFacts.length > 0 && (
        <Section>
          <SectionHeader>
            <SectionEyebrow>Hvad du bør vide</SectionEyebrow>
            <SectionTitle>Faglig baggrund — kuration der roterer</SectionTitle>
            <SectionLede>
              Korte essays om de teknologier og lovrammer Tyr bygger på.
              {facts.length > 3 ? ` Roterer hvert andet minut · ${factOffset + 1}–${factOffset + 3} af ${facts.length}.` : ''}
            </SectionLede>
          </SectionHeader>
          <FactsRow>
            {visibleFacts.map((fact) => (
              <FactCard key={fact.id}>
                <span className="topic">{topicForFact(fact)}</span>
                <h3>{fact.title}</h3>
                <p>{fact.text}</p>
                {fact.source && (
                  <a href={fact.source} target="_blank" rel="noopener noreferrer">
                    Læs kilden →
                  </a>
                )}
              </FactCard>
            ))}
          </FactsRow>
          <FactsRotateCue>
            <span>↻</span>
            <span>{facts.length > 3 ? 'Næste rotation om ~2 min · klik på et kort for at åbne kilden' : 'Alle entries vises'}</span>
          </FactsRotateCue>
        </Section>
      )}

      {/* ============ NEWS ============ */}
      <Section>
        <NewsSection />
      </Section>

      {/* ============ DRIFT-OVERBLIK (data-overview pattern) ============ */}
      <DataOverview scope="home" />

      {/* ============ FOOTER ribbon ============ */}
      <Footer>
        <span>Tyr · kommunal AI-compliance · Kalundborg Kommune</span>
        <span>Kun til internt brug · Digitalisering og IT</span>
      </Footer>
    </Page>
  );
};

export default HomePage;
