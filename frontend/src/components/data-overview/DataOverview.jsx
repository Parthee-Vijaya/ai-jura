import React, { useEffect, useState } from 'react';
import styled from 'styled-components';
import axios from 'axios';

/**
 * Bifrost — DataOverview
 *
 * Signatur-mønster fra DESIGN.md: hver hovedside får et clean
 * drift-overblik ved bunden af canvas. Tre sektioner:
 *   1. 4-stat grid       (sager / betinget-go / citater / flagget)
 *   2. 2-kol data row    (seneste vurderinger ledger + citat-friskhed)
 *   3. 5-cell status-bar (backend / db / llm / verifier / engine)
 *
 * Komponenten henter sin egen data fra v3-API'erne så den kan
 * dropbares på alle sider uden props-drilling.
 */

// ---- Styled (Northern Modern, kompakt mode) ----------------------------
//
// Kompakt-mode: hele DataOverview holder sig <600px høj så den passer
// "below the fold" på en standard 1080p-skærm uden at slå sig sammen
// med side-content ovenfor. Seneste vurderinger + citat-friskhed
// stables vertikalt så hver får fuld bredde (ingen klemte rule_ids).

const Wrap = styled.section`
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid ${(p) => p.theme.colors.borderSoft};
`;

// Inline header: eyebrow + status-label på samme linje, ingen H2
const SectionHead = styled.div`
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
  flex-wrap: wrap;

  .eyebrow {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: ${(p) => p.theme.colors.bronze};
    font-weight: 600;
  }

  .meta {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.68rem;
    color: ${(p) => p.theme.colors.textMuted};
    letter-spacing: 0.04em;
  }
`;

// 4-stat grid (kompakt — mindre padding + font)
const Stats = styled.div`
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  background: ${(p) => p.theme.colors.surface};
  border: 1px solid ${(p) => p.theme.colors.border};
  border-radius: ${(p) => p.theme.borderRadius};
  margin-bottom: 10px;

  @media (max-width: 720px) {
    grid-template-columns: repeat(2, 1fr);
  }
`;

const Stat = styled.div`
  padding: 8px 14px;
  border-right: 1px solid ${(p) => p.theme.colors.border};
  display: flex;
  flex-direction: column;
  gap: 2px;

  &:last-child { border-right: none; }

  @media (max-width: 720px) {
    &:nth-child(2n) { border-right: none; }
    &:nth-child(-n+2) { border-bottom: 1px solid ${(p) => p.theme.colors.border}; }
  }

  .label {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: ${(p) => p.theme.colors.textFaded};
  }
  .value {
    font-family: ${(p) => p.theme.fonts.display};
    font-weight: 700;
    font-size: 1.3rem;
    letter-spacing: -0.02em;
    color: ${({ $tone, theme }) => {
      if ($tone === 'bronze') return theme.colors.bronze;
      if ($tone === 'success') return theme.colors.success;
      if ($tone === 'danger') return theme.colors.danger;
      return theme.colors.text;
    }};
    line-height: 1;
  }
  .delta {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.62rem;
    color: ${(p) => p.theme.colors.textMuted};
  }
`;

// Vertikal stak — Seneste vurderinger + Citat-friskhed under hinanden,
// hver med fuld bredde så lange rule_ids og sagsnavne ikke klemmes.
const DataRow = styled.div`
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 10px;
`;

const Panel = styled.div`
  background: ${(p) => p.theme.colors.surface};
  border: 1px solid ${(p) => p.theme.colors.border};
  border-radius: ${(p) => p.theme.borderRadius};
  overflow: hidden;
`;

const PanelHead = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 14px;
  border-bottom: 1px solid ${(p) => p.theme.colors.border};
  background: ${(p) => p.theme.colors.background};

  .title {
    font-family: ${(p) => p.theme.fonts.display};
    font-weight: 600;
    font-size: 0.82rem;
    color: ${(p) => p.theme.colors.text};
  }
  .meta {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.64rem;
    letter-spacing: 0.06em;
    color: ${(p) => p.theme.colors.textMuted};
  }
  a {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.64rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: ${(p) => p.theme.colors.primary};
    text-decoration: none;
    &:hover { text-decoration: underline; }
  }
`;

// Ledger table — meget kompakt række
const LedgerRow = styled.div`
  display: grid;
  grid-template-columns: 110px 1fr 85px 70px 44px;
  align-items: center;
  padding: 5px 14px;
  border-bottom: 1px solid ${(p) => p.theme.colors.borderSoft};
  font-size: 0.82rem;

  &:last-child { border-bottom: none; }

  &.hdr {
    background: ${(p) => p.theme.colors.background};
    color: ${(p) => p.theme.colors.textFaded};
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    padding: 4px 14px;
  }

  .cid {
    font-family: ${(p) => p.theme.fonts.mono};
    color: ${(p) => p.theme.colors.primary};
    font-size: 0.74rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .cname {
    color: ${(p) => p.theme.colors.text};
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    padding-right: 8px;
  }
  .ts {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.72rem;
    color: ${(p) => p.theme.colors.textMuted};
  }
  .who {
    font-size: 0.74rem;
    color: ${(p) => p.theme.colors.textMuted};
  }

  @media (max-width: 720px) {
    grid-template-columns: 1fr 80px;
    .cid, .ts, .who { display: none; }
  }
`;

const Pill = styled.span`
  font-family: ${(p) => p.theme.fonts.mono};
  font-size: 0.66rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 2px 9px;
  border-radius: 2px;
  text-align: center;
  display: inline-block;

  ${({ $verdict, theme }) => {
    if ($verdict === 'GO') return `background: ${theme.colors.successSoft}; color: ${theme.colors.success};`;
    if ($verdict === 'BETINGET-GO') return `background: ${theme.colors.bronzeSoft}; color: ${theme.colors.bronze};`;
    if ($verdict === 'NO-GO') return `background: ${theme.colors.dangerSoft}; color: ${theme.colors.danger};`;
    return `background: ${theme.colors.surfaceAlt}; color: ${theme.colors.textMuted};`;
  }}
`;

// Citation panel — to-kolonne grid INDEN for panelet så 6 citater fylder
// 3 rækker × 2 kolonner. Panelet selv har nu fuld side-bredde (efter
// vertikal stak), så vi kan udnytte plads horisontalt.
const CitationGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;

  @media (max-width: 720px) {
    grid-template-columns: 1fr;
  }
`;

const CitationRow = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 14px;
  border-bottom: 1px solid ${(p) => p.theme.colors.borderSoft};
  border-right: 1px solid ${(p) => p.theme.colors.borderSoft};
  font-family: ${(p) => p.theme.fonts.mono};
  font-size: 0.72rem;
  gap: 8px;

  &:nth-child(2n) { border-right: none; }

  /* Sidste 2 rækker (sidste 2 items) får ikke bottom-border når vi har 6 items */
  &:nth-last-child(-n+2) { border-bottom: none; }

  .left { display: flex; align-items: center; gap: 7px; min-width: 0; flex: 1; }
  .marker {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: ${({ $status, theme }) =>
      $status === 'flagged' ? theme.colors.danger :
      $status === 'verified' ? theme.colors.success :
      theme.colors.textFaded};
    display: inline-block;
    flex-shrink: 0;
  }
  .name {
    color: ${(p) => p.theme.colors.text};
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
  }
  .when {
    color: ${(p) => p.theme.colors.textMuted};
    font-size: 0.7rem;
    flex-shrink: 0;
  }

  @media (max-width: 720px) {
    border-right: none;
    &:not(:last-child) { border-bottom: 1px solid ${(p) => p.theme.colors.borderSoft}; }
  }
`;

// Status-bar (5-cell footer)
const StatusBar = styled.div`
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  background: ${(p) => p.theme.colors.surface};
  border: 1px solid ${(p) => p.theme.colors.border};
  border-radius: ${(p) => p.theme.borderRadius};
  overflow: hidden;

  @media (max-width: 720px) {
    grid-template-columns: repeat(2, 1fr);
  }
`;

const StatusCell = styled.div`
  padding: 6px 12px;
  border-right: 1px solid ${(p) => p.theme.colors.border};
  font-family: ${(p) => p.theme.fonts.mono};
  font-size: 0.7rem;
  display: flex;
  flex-direction: column;
  gap: 1px;

  &:last-child { border-right: none; }

  .label {
    font-size: 0.56rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: ${(p) => p.theme.colors.textFaded};
  }
  .value {
    color: ${({ $tone, theme }) =>
      $tone === 'ok' ? theme.colors.success :
      $tone === 'warn' ? theme.colors.bronze :
      $tone === 'danger' ? theme.colors.danger :
      theme.colors.text};
    font-weight: 500;
    font-size: 0.72rem;
  }

  @media (max-width: 720px) {
    &:nth-child(2n) { border-right: none; }
    &:nth-child(-n+4) { border-bottom: 1px solid ${(p) => p.theme.colors.border}; }
  }
`;

// ---- Helpers -----------------------------------------------------------

const initialsOf = (name) => {
  if (!name) return '—';
  return name.split(/[ @.]/).filter(Boolean).slice(0, 2).map((p) => p[0]).join('').toUpperCase();
};

const formatHHmm = (iso) => {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  const today = new Date();
  if (d.toDateString() === today.toDateString()) {
    return d.toLocaleTimeString('da-DK', { hour: '2-digit', minute: '2-digit' });
  }
  const yesterday = new Date(today.getTime() - 86400000);
  if (d.toDateString() === yesterday.toDateString()) return 'igår';
  return d.toLocaleDateString('da-DK', { day: '2-digit', month: '2-digit' });
};

const truncateName = (s, n = 38) => {
  if (!s) return '';
  return s.length <= n ? s : `${s.slice(0, n - 1)}…`;
};

// ---- Component ---------------------------------------------------------

const DataOverview = ({ scope = 'global' }) => {
  const [audit, setAudit] = useState({ items: [], total: 0 });
  const [cases, setCases] = useState({ items: [] });
  const [freshness, setFreshness] = useState({ items: [], counts: { verified: 0, flagged: 0, total: 0 } });
  const [version, setVersion] = useState(null);
  const [llm, setLlm] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const [auditRes, casesRes, freshRes, versionRes] = await Promise.allSettled([
          axios.get('/api/v3/audit?limit=5'),
          axios.get('/api/v3/cases?limit=50'),
          axios.get('/api/v3/law/freshness'),
          axios.get('/api/version'),
        ]);

        if (cancelled) return;

        if (auditRes.status === 'fulfilled') setAudit(auditRes.value.data);
        if (casesRes.status === 'fulfilled') setCases(casesRes.value.data);
        if (freshRes.status === 'fulfilled') {
          const items = freshRes.value.data.items || [];
          const verified = items.filter((i) => i.citation_found).length;
          const flagged = items.filter((i) => i.flagged_for_review).length;
          setFreshness({ items, counts: { verified, flagged, total: items.length } });
        }
        if (versionRes.status === 'fulfilled') setVersion(versionRes.value.data);

        // Background LLM probe — non-blocking
        try {
          const llmRes = await axios.post('/api/compliance/test-llm', { prompt: 'ok' }, { timeout: 6000 });
          if (!cancelled) setLlm(llmRes.data);
        } catch {
          if (!cancelled) setLlm({ success: false });
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Derive stats
  const inWorkflow = (cases.items || []).filter(
    (c) => !['arkiveret', 'godkendt'].includes(c.status),
  ).length;

  const conditionalOpen = (cases.items || []).filter(
    (c) => c.last_aggregate_status === 'BETINGET-GO' && c.status !== 'arkiveret',
  ).length;

  return (
    <Wrap>
      <SectionHead>
        <span className="eyebrow">Drift-overblik</span>
        <span className="meta">{loading ? 'henter…' : `${cases.items?.length || 0} sager · ${freshness.counts.total} regler`}</span>
      </SectionHead>

      {/* 4-stat grid */}
      <Stats>
        <Stat>
          <div className="label">Sager i workflow</div>
          <div className="value">{loading ? '…' : inWorkflow}</div>
          <div className="delta">{cases.items?.length || 0} totalt</div>
        </Stat>
        <Stat $tone="bronze">
          <div className="label">Betinget-GO åbne</div>
          <div className="value">{loading ? '…' : conditionalOpen}</div>
          <div className="delta">remediation-spor</div>
        </Stat>
        <Stat $tone="success">
          <div className="label">Citater verificeret</div>
          <div className="value">{loading ? '…' : `${freshness.counts.verified}/${freshness.counts.total}`}</div>
          <div className="delta">friske kl. 04:00</div>
        </Stat>
        <Stat $tone={freshness.counts.flagged > 0 ? 'danger' : 'success'}>
          <div className="label">Flagget til jurist-review</div>
          <div className="value">{loading ? '…' : freshness.counts.flagged}</div>
          <div className="delta">{freshness.counts.flagged > 0 ? 'kræver review' : 'alt verificeret'}</div>
        </Stat>
      </Stats>

      {/* Ledger + citations */}
      <DataRow>
        <Panel>
          <PanelHead>
            <span className="title">Seneste vurderinger</span>
            <a href="/historik">Se hele historikken →</a>
          </PanelHead>
          <LedgerRow className="hdr">
            <div>sags-id</div>
            <div>sag</div>
            <div>verdict</div>
            <div>vurderet</div>
            <div>af</div>
          </LedgerRow>
          {(audit.items || []).slice(0, 4).map((entry) => (
            <LedgerRow key={entry.id}>
              <div className="cid">{entry.case_id || '—'}</div>
              <div className="cname">{truncateName(entry.note || entry.case_id || 'Ukendt sag')}</div>
              <div><Pill $verdict={entry.aggregate_status}>{entry.aggregate_status || '—'}</Pill></div>
              <div className="ts">{formatHHmm(entry.created_at)}</div>
              <div className="who">{initialsOf(entry.user_id)}</div>
            </LedgerRow>
          ))}
          {(audit.items || []).length === 0 && !loading && (
            <LedgerRow>
              <div className="cname" style={{ gridColumn: '1 / -1', textAlign: 'center', color: 'inherit', opacity: 0.6 }}>
                Ingen vurderinger endnu — start på <a href="/vurdering">/vurdering</a>
              </div>
            </LedgerRow>
          )}
        </Panel>

        <Panel>
          <PanelHead>
            <span className="title">Citat-friskhed</span>
            <span className="meta">04:00 / dag</span>
          </PanelHead>
          {/* 6 citater i 3×2 grid — panelet er fuld bredde (vertikal stak) */}
          <CitationGrid>
            {(freshness.items || []).slice(0, 6).map((item) => (
              <CitationRow key={item.rule_id} $status={item.flagged_for_review ? 'flagged' : item.citation_found ? 'verified' : 'unknown'}>
                <div className="left">
                  <span className="marker" />
                  <span className="name" title={item.rule_id}>{item.rule_id}</span>
                </div>
                <span className="when">{item.flagged_for_review ? 'flagget' : formatHHmm(item.last_checked_at)}</span>
              </CitationRow>
            ))}
            {(freshness.items || []).length === 0 && !loading && (
              <CitationRow style={{ gridColumn: '1 / -1', borderRight: 'none' }}>
                <div className="left"><span className="name" style={{ opacity: 0.6 }}>Ingen friskheds-data endnu</span></div>
              </CitationRow>
            )}
          </CitationGrid>
        </Panel>
      </DataRow>

      {/* 5-cell status bar */}
      <StatusBar>
        <StatusCell $tone="ok">
          <div className="label">Backend</div>
          <div className="value">8001 · ok</div>
        </StatusCell>
        <StatusCell $tone="ok">
          <div className="label">Database</div>
          <div className="value">SQLite</div>
        </StatusCell>
        <StatusCell $tone={llm?.success ? 'ok' : 'warn'}>
          <div className="label">LLM</div>
          <div className="value">{llm?.success ? (llm.model || 'aktiv') : 'offline'}</div>
        </StatusCell>
        <StatusCell $tone={freshness.counts.flagged > 0 ? 'warn' : 'ok'}>
          <div className="label">Citat-verifier</div>
          <div className="value">
            {freshness.counts.verified}/{freshness.counts.total} friske
            {freshness.counts.flagged > 0 ? ` · ${freshness.counts.flagged} flagget` : ''}
          </div>
        </StatusCell>
        <StatusCell $tone="ok">
          <div className="label">Rule engine</div>
          <div className="value">{version?.version ? `v${version.version}` : '—'}</div>
        </StatusCell>
      </StatusBar>
    </Wrap>
  );
};

export default DataOverview;
