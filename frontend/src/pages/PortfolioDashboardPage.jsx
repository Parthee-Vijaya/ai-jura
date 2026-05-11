import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useQuery } from 'react-query';
import styled from 'styled-components';
import axios from 'axios';
import {
  FaChartBar,
  FaExclamationTriangle,
  FaCheckCircle,
  FaClock,
  FaArrowRight,
  FaCommentDots,
} from 'react-icons/fa';

import {
  PageShell,
  PageHeader,
  Eyebrow,
  PageTitle,
  Lede,
  LoadingState,
  ErrorState,
} from '../components/ui';

/**
 * PortfolioDashboardPage — kommune-overblik over hele AI-porteføljen.
 *
 * URL: /portefolje
 *
 * 3 widgets:
 *   1. Stats-strip (total sager, evidens %, åbne kommentarer, verdicts)
 *   2. Heatmap (verdict × evidens-status)
 *   3. Top 5 blockers (hvilke evidens stopper flest sager)
 *   + SLA-liste (forfaldne reviews + næste 7 dage)
 *
 * Data: GET /api/v3/dashboard/portfolio
 */

// ---- Layout primitives --------------------------------------------------

const Grid = styled.div`
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.25rem;
  margin: 1.25rem 0;

  @media (min-width: 900px) {
    grid-template-columns: 1fr 1fr;
  }
`;

const StatRow = styled.section`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1.25rem;
`;

const Stat = styled.div`
  background: ${(p) => p.theme.colors.surface || '#fff'};
  border: 1px solid ${(p) => p.theme.colors.border || '#d8dde6'};
  border-radius: 8px;
  padding: 1rem 1.1rem;

  .label {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: ${(p) => p.theme.colors.textMuted};
    margin: 0 0 0.4rem;
  }
  .value {
    font-family: ${(p) => p.theme.fonts.display};
    font-size: 1.8rem;
    font-weight: 600;
    color: ${(p) => p.theme.colors.text};
    line-height: 1;
  }
  .delta {
    font-size: 0.78rem;
    color: ${(p) => p.theme.colors.textMuted};
    margin-top: 0.4rem;
  }
`;

const Card = styled.section`
  background: ${(p) => p.theme.colors.surface || '#fff'};
  border: 1px solid ${(p) => p.theme.colors.border || '#d8dde6'};
  border-radius: 8px;
  padding: 1.25rem 1.4rem;

  .head {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 0 0 0.85rem;
    color: ${(p) => p.theme.colors.primary || '#0d2e54'};

    h2 {
      font-family: ${(p) => p.theme.fonts.display};
      font-size: 1.05rem;
      font-weight: 600;
      margin: 0;
      color: ${(p) => p.theme.colors.text};
    }
  }
  .lede {
    font-size: 0.82rem;
    color: ${(p) => p.theme.colors.textMuted};
    margin: 0 0 1rem;
    line-height: 1.45;
  }
`;

// ---- Heatmap ------------------------------------------------------------

const HeatmapTable = styled.table`
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;

  th, td {
    text-align: center;
    padding: 0.55rem 0.4rem;
    border: 1px solid ${(p) => p.theme.colors.borderSoft || '#e2e6ec'};
  }
  th {
    background: ${(p) => p.theme.colors.surfaceAlt || '#f6f8fb'};
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: ${(p) => p.theme.colors.textMuted};
  }
  th.row-head {
    text-align: left;
    background: white;
    font-family: ${(p) => p.theme.fonts.display};
    color: ${(p) => p.theme.colors.text};
  }
  td.cell {
    font-family: ${(p) => p.theme.fonts.mono};
    font-weight: 600;
    color: ${(p) => p.theme.colors.text};
  }
  /* Heatmap cell shading via background-opacity */
  td.cell[data-pct] {
    color: ${(p) => p.theme.colors.text};
  }
`;

function shade(value, max, hue = '13, 46, 84') {
  if (max === 0 || !value) return 'transparent';
  const ratio = Math.min(1, value / max);
  const opacity = 0.05 + ratio * 0.45;
  return `rgba(${hue}, ${opacity})`;
}

const STATUS_COLS = [
  { key: 'mangler', label: 'Mangler' },
  { key: 'i_gang', label: 'I gang' },
  { key: 'faerdig', label: 'Færdig' },
];

const VERDICT_ORDER = ['NO-GO', 'BETINGET-GO', 'GO', 'ukendt'];

const Heatmap = ({ data }) => {
  if (!data || Object.keys(data).length === 0) {
    return <p style={{ color: '#5f6b7a', fontStyle: 'italic' }}>Ingen evidens-data endnu.</p>;
  }

  const verdicts = VERDICT_ORDER.filter((v) => v in data);
  // Find max-værdi for at skala farve
  let max = 0;
  for (const v of verdicts) {
    for (const col of STATUS_COLS) {
      max = Math.max(max, data[v]?.[col.key] || 0);
    }
  }

  return (
    <HeatmapTable role="table" aria-label="Heatmap: verdict × evidens-status">
      <thead>
        <tr>
          <th />
          {STATUS_COLS.map((c) => (
            <th key={c.key}>{c.label}</th>
          ))}
          <th>I alt</th>
        </tr>
      </thead>
      <tbody>
        {verdicts.map((v) => {
          const row = data[v];
          const total = STATUS_COLS.reduce((s, c) => s + (row[c.key] || 0), 0);
          return (
            <tr key={v}>
              <th className="row-head" scope="row">
                {v}
              </th>
              {STATUS_COLS.map((c) => {
                const val = row[c.key] || 0;
                const hue =
                  c.key === 'faerdig'
                    ? '45, 106, 49'
                    : c.key === 'mangler'
                    ? '160, 32, 32'
                    : '176, 138, 74';
                return (
                  <td
                    key={c.key}
                    className="cell"
                    data-pct={total > 0 ? Math.round((val / total) * 100) : 0}
                    style={{ background: shade(val, max, hue) }}
                    title={`${v} × ${c.label}: ${val} evidens-rækker`}
                  >
                    {val}
                  </td>
                );
              })}
              <td className="cell">{total}</td>
            </tr>
          );
        })}
      </tbody>
    </HeatmapTable>
  );
};

// ---- Top 5 blockers -----------------------------------------------------

const BlockerList = styled.ol`
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  counter-reset: blocker;
`;

const BlockerItem = styled.li`
  counter-increment: blocker;
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 0.7rem;
  padding: 0.55rem 0.75rem;
  background: ${(p) => p.theme.colors.surfaceAlt || '#f6f8fb'};
  border: 1px solid ${(p) => p.theme.colors.borderSoft || '#e2e6ec'};
  border-radius: 6px;

  &::before {
    content: counter(blocker);
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.78rem;
    font-weight: 700;
    color: white;
    background: ${(p) => p.theme.colors.primary || '#0d2e54'};
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  .label {
    font-family: ${(p) => p.theme.fonts.body};
    font-size: 0.88rem;
    color: ${(p) => p.theme.colors.text};
    text-transform: capitalize;
  }
  .count {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.78rem;
    font-weight: 600;
    color: #a02020;
    white-space: nowrap;
  }
`;

// ---- SLA list -----------------------------------------------------------

const SlaList = styled.ul`
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
`;

const SlaItem = styled.li`
  padding: 0.5rem 0.75rem;
  background: ${(p) =>
    p.$tone === 'overdue' ? 'rgba(160, 32, 32, 0.08)' : 'rgba(176, 138, 74, 0.08)'};
  border-left: 3px solid
    ${(p) => (p.$tone === 'overdue' ? '#a02020' : '#b08a4a')};
  border-radius: 0 4px 4px 0;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;

  a {
    color: ${(p) => p.theme.colors.primary || '#0d2e54'};
    text-decoration: none;
    font-weight: 500;
    &:hover { text-decoration: underline; }
  }
  .meta {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.72rem;
    color: ${(p) => p.theme.colors.textMuted};
  }
`;

// ---- Page ---------------------------------------------------------------

const PortfolioDashboardPage = () => {
  const navigate = useNavigate();

  const { data, isLoading, isError, error, refetch } = useQuery(
    'portfolio-dashboard',
    async () => {
      const r = await axios.get('/api/v3/dashboard/portfolio');
      return r.data;
    },
    { refetchInterval: 60_000, staleTime: 30_000 },
  );

  if (isLoading) {
    return (
      <PageShell>
        <PageHeader>
          <Eyebrow>Bifrost · portefølje</Eyebrow>
          <PageTitle>Kommune-overblik</PageTitle>
          <Lede>Henter aggregat over alle sager, evidens og kommentarer…</Lede>
        </PageHeader>
        <LoadingState />
      </PageShell>
    );
  }

  if (isError) {
    return (
      <PageShell>
        <PageHeader>
          <Eyebrow>Bifrost · portefølje</Eyebrow>
          <PageTitle>Kommune-overblik</PageTitle>
        </PageHeader>
        <ErrorState
          title="Kunne ikke hente portefølje-data"
          error={error}
          onRetry={refetch}
        />
      </PageShell>
    );
  }

  const stats = data?.stats || {};
  const heatmap = data?.heatmap || {};
  const blockers = data?.top_blockers || [];
  const sla = data?.sla || { overdue: [], upcoming_within_7_days: [] };

  return (
    <PageShell>
      <PageHeader>
        <Eyebrow>Bifrost · portefølje</Eyebrow>
        <PageTitle>Kommune-overblik</PageTitle>
        <Lede>
          Aggregeret status over Kalundborg Kommunes AI-portefølje. Heatmap
          viser hvor evidens-arbejdet hænger; top 5 blockers peger på de
          skabeloner der stopper flest sager. Auto-opdateres hvert minut.
        </Lede>
      </PageHeader>

      <StatRow>
        <Stat>
          <p className="label">Sager i alt</p>
          <p className="value">{stats.total_cases || 0}</p>
          <p className="delta">
            {Object.entries(stats.by_status || {})
              .map(([s, n]) => `${n} ${s}`)
              .join(' · ') || '—'}
          </p>
        </Stat>
        <Stat>
          <p className="label">Evidens-fremdrift</p>
          <p className="value">{stats.evidens_pct || 0}%</p>
          <p className="delta">
            {stats.evidens_done || 0} af {stats.evidens_total || 0} udfyldt
          </p>
        </Stat>
        <Stat>
          <p className="label">Åbne kommentarer</p>
          <p className="value">{stats.open_comment_count || 0}</p>
          <p className="delta">
            {stats.comment_count_total || 0} i alt (inkl. løste)
          </p>
        </Stat>
        <Stat>
          <p className="label">Verdicts</p>
          <p className="value">
            {(stats.verdict_counts?.['GO'] || 0) +
              (stats.verdict_counts?.['BETINGET-GO'] || 0)}
          </p>
          <p className="delta">
            {stats.verdict_counts?.['NO-GO'] || 0} NO-GO ·{' '}
            {stats.verdict_counts?.['BETINGET-GO'] || 0} betinget ·{' '}
            {stats.verdict_counts?.['GO'] || 0} godkendt
          </p>
        </Stat>
      </StatRow>

      <Grid>
        <Card>
          <div className="head">
            <FaChartBar aria-hidden="true" />
            <h2>Heatmap — verdict × evidens-status</h2>
          </div>
          <p className="lede">
            Hvor er evidens-arbejdet bagud? NO-GO + mange "mangler" = sager
            der trænger til opmærksomhed.
          </p>
          <Heatmap data={heatmap} />
        </Card>

        <Card>
          <div className="head">
            <FaExclamationTriangle aria-hidden="true" />
            <h2>Top 5 blockers</h2>
          </div>
          <p className="lede">
            Evidens-skabeloner der mangler eller er i gang på flest sager.
            Fokusér her for hurtigst at flytte sager fra BETINGET-GO til GO.
          </p>
          {blockers.length === 0 ? (
            <p style={{ color: '#5f6b7a', fontStyle: 'italic' }}>
              Ingen blockers — flot!
            </p>
          ) : (
            <BlockerList>
              {blockers.map((b) => (
                <BlockerItem key={b.artifact_id}>
                  <span className="label">{b.label}</span>
                  <span className="count">{b.blocked_cases} sager</span>
                </BlockerItem>
              ))}
            </BlockerList>
          )}
        </Card>

        <Card>
          <div className="head">
            <FaClock aria-hidden="true" />
            <h2>SLA — forfaldne reviews</h2>
          </div>
          <p className="lede">
            Sager hvis næste review ligger i fortiden. Bør prioriteres straks.
          </p>
          {sla.overdue.length === 0 ? (
            <p style={{ color: '#5f6b7a', fontStyle: 'italic' }}>
              Ingen forfaldne sager — godt!
            </p>
          ) : (
            <SlaList>
              {sla.overdue.map((c) => (
                <SlaItem key={c.case_id} $tone="overdue">
                  <Link to={`/sag/${c.case_id}`}>{c.title || c.case_id}</Link>
                  <span className="meta">{c.days_overdue} dage forsinket</span>
                </SlaItem>
              ))}
            </SlaList>
          )}
        </Card>

        <Card>
          <div className="head">
            <FaCheckCircle aria-hidden="true" />
            <h2>SLA — næste 7 dage</h2>
          </div>
          <p className="lede">
            Sager med review-deadline inden for ugen. Planlæg disse nu.
          </p>
          {sla.upcoming_within_7_days.length === 0 ? (
            <p style={{ color: '#5f6b7a', fontStyle: 'italic' }}>
              Ingen review-deadlines de næste 7 dage.
            </p>
          ) : (
            <SlaList>
              {sla.upcoming_within_7_days.map((c) => (
                <SlaItem key={c.case_id} $tone="upcoming">
                  <Link to={`/sag/${c.case_id}`}>{c.title || c.case_id}</Link>
                  <span className="meta">om {c.days_until} dage</span>
                </SlaItem>
              ))}
            </SlaList>
          )}
        </Card>
      </Grid>

      <Card>
        <div className="head">
          <FaCommentDots aria-hidden="true" />
          <h2>Hurtige genveje</h2>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.6rem' }}>
          <button
            type="button"
            onClick={() => navigate('/sager')}
            style={{
              background: '#0d2e54',
              color: 'white',
              border: 'none',
              borderRadius: 4,
              padding: '0.55rem 1rem',
              cursor: 'pointer',
              fontFamily: 'inherit',
              fontSize: '0.85rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.4rem',
            }}
          >
            Alle sager <FaArrowRight />
          </button>
          <button
            type="button"
            onClick={() => navigate('/proces')}
            style={{
              background: 'transparent',
              color: '#0d2e54',
              border: '1px solid #d8dde6',
              borderRadius: 4,
              padding: '0.55rem 1rem',
              cursor: 'pointer',
              fontFamily: 'inherit',
              fontSize: '0.85rem',
            }}
          >
            Start ny sag
          </button>
          <button
            type="button"
            onClick={() => {
              const a = document.createElement('a');
              a.href = '/api/v3/dashboard/portfolio.csv';
              a.download = '';
              document.body.appendChild(a);
              a.click();
              document.body.removeChild(a);
            }}
            title="Download dette dashboard som CSV (Excel-kompatibel)"
            style={{
              background: 'transparent',
              color: '#0d2e54',
              border: '1px solid #d8dde6',
              borderRadius: 4,
              padding: '0.55rem 1rem',
              cursor: 'pointer',
              fontFamily: 'inherit',
              fontSize: '0.85rem',
              marginRight: '0.6rem',
            }}
          >
            ↓ Eksportér CSV
          </button>
          <button
            type="button"
            onClick={() => navigate('/ressourcer')}
            style={{
              background: 'transparent',
              color: '#0d2e54',
              border: '1px solid #d8dde6',
              borderRadius: 4,
              padding: '0.55rem 1rem',
              cursor: 'pointer',
              fontFamily: 'inherit',
              fontSize: '0.85rem',
            }}
          >
            Lov-bibliotek
          </button>
        </div>
      </Card>
    </PageShell>
  );
};

export default PortfolioDashboardPage;
