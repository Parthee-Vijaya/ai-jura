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

// ---- Styled (Northern Modern) ------------------------------------------

const Wrap = styled.section`
  margin-top: 40px;
  padding-top: 32px;
  border-top: 1px solid ${(p) => p.theme.colors.borderSoft};
`;

const Eyebrow = styled.div`
  font-family: ${(p) => p.theme.fonts.mono};
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: ${(p) => p.theme.colors.bronze};
  margin: 0 0 8px;
`;

const Heading = styled.h2`
  font-family: ${(p) => p.theme.fonts.display};
  font-weight: 600;
  font-size: 1.4rem;
  letter-spacing: -0.01em;
  color: ${(p) => p.theme.colors.text};
  margin: 0 0 24px;
`;

// 4-stat grid
const Stats = styled.div`
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  background: ${(p) => p.theme.colors.surface};
  border: 1px solid ${(p) => p.theme.colors.border};
  border-radius: ${(p) => p.theme.borderRadius};
  margin-bottom: 28px;

  @media (max-width: 720px) {
    grid-template-columns: repeat(2, 1fr);
  }
`;

const Stat = styled.div`
  padding: 22px 24px;
  border-right: 1px solid ${(p) => p.theme.colors.border};

  &:last-child { border-right: none; }

  @media (max-width: 720px) {
    &:nth-child(2n) { border-right: none; }
    &:nth-child(-n+2) { border-bottom: 1px solid ${(p) => p.theme.colors.border}; }
  }

  .label {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.66rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: ${(p) => p.theme.colors.textFaded};
    margin-bottom: 8px;
  }
  .value {
    font-family: ${(p) => p.theme.fonts.display};
    font-weight: 700;
    font-size: 2rem;
    letter-spacing: -0.02em;
    color: ${({ $tone, theme }) => {
      if ($tone === 'bronze') return theme.colors.bronze;
      if ($tone === 'success') return theme.colors.success;
      if ($tone === 'danger') return theme.colors.danger;
      return theme.colors.text;
    }};
    line-height: 1;
    margin-bottom: 6px;
  }
  .delta {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.72rem;
    color: ${(p) => p.theme.colors.textMuted};
  }
`;

// 2-kol data row
const DataRow = styled.div`
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
  margin-bottom: 24px;

  @media (max-width: 920px) {
    grid-template-columns: 1fr;
  }
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
  padding: 14px 22px;
  border-bottom: 1px solid ${(p) => p.theme.colors.border};
  background: ${(p) => p.theme.colors.background};

  .title {
    font-family: ${(p) => p.theme.fonts.display};
    font-weight: 600;
    font-size: 0.96rem;
    color: ${(p) => p.theme.colors.text};
  }
  .meta {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.7rem;
    letter-spacing: 0.06em;
    color: ${(p) => p.theme.colors.textMuted};
  }
  a {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: ${(p) => p.theme.colors.primary};
    text-decoration: none;
    &:hover { text-decoration: underline; }
  }
`;

// Ledger table
const LedgerRow = styled.div`
  display: grid;
  grid-template-columns: 130px 1fr 90px 110px 80px;
  align-items: center;
  padding: 12px 22px;
  border-bottom: 1px solid ${(p) => p.theme.colors.borderSoft};
  font-size: 0.92rem;

  &:last-child { border-bottom: none; }

  &.hdr {
    background: ${(p) => p.theme.colors.background};
    color: ${(p) => p.theme.colors.textFaded};
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.66rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    padding: 9px 22px;
  }

  .cid {
    font-family: ${(p) => p.theme.fonts.mono};
    color: ${(p) => p.theme.colors.primary};
    font-size: 0.82rem;
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
    font-size: 0.78rem;
    color: ${(p) => p.theme.colors.textMuted};
  }
  .who {
    font-size: 0.82rem;
    color: ${(p) => p.theme.colors.textMuted};
  }

  @media (max-width: 720px) {
    grid-template-columns: 1fr 90px;
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

// Citation panel
const CitationRow = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 22px;
  border-bottom: 1px solid ${(p) => p.theme.colors.borderSoft};
  font-family: ${(p) => p.theme.fonts.mono};
  font-size: 0.78rem;

  &:last-child { border-bottom: none; }

  .left { display: flex; align-items: center; gap: 8px; }
  .marker {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: ${({ $status, theme }) =>
      $status === 'flagged' ? theme.colors.danger :
      $status === 'verified' ? theme.colors.success :
      theme.colors.textFaded};
    display: inline-block;
  }
  .name { color: ${(p) => p.theme.colors.text}; }
  .when { color: ${(p) => p.theme.colors.textMuted}; font-size: 0.72rem; }
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
  padding: 14px 18px;
  border-right: 1px solid ${(p) => p.theme.colors.border};
  font-family: ${(p) => p.theme.fonts.mono};
  font-size: 0.74rem;

  &:last-child { border-right: none; }

  .label {
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: ${(p) => p.theme.colors.textFaded};
    margin-bottom: 4px;
  }
  .value {
    color: ${({ $tone, theme }) =>
      $tone === 'ok' ? theme.colors.success :
      $tone === 'warn' ? theme.colors.bronze :
      $tone === 'danger' ? theme.colors.danger :
      theme.colors.text};
    font-weight: 500;
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
      <Eyebrow>Drift-overblik</Eyebrow>
      <Heading>Aktuel status på tværs af alle sager og regler</Heading>

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
          {(audit.items || []).slice(0, 5).map((entry) => (
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
          {(freshness.items || []).slice(0, 8).map((item) => (
            <CitationRow key={item.rule_id} $status={item.flagged_for_review ? 'flagged' : item.citation_found ? 'verified' : 'unknown'}>
              <div className="left">
                <span className="marker" />
                <span className="name">{item.rule_id}</span>
              </div>
              <span className="when">{item.flagged_for_review ? 'flagget' : formatHHmm(item.last_checked_at)}</span>
            </CitationRow>
          ))}
          {(freshness.items || []).length === 0 && !loading && (
            <CitationRow>
              <div className="left"><span className="name" style={{ opacity: 0.6 }}>Ingen friskheds-data endnu</span></div>
            </CitationRow>
          )}
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
