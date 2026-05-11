import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import styled from 'styled-components';
import { FaClock, FaCheckCircle } from 'react-icons/fa';

/**
 * Bifrost — EvidenceProgressRadial: SVG-baseret radial-progress med:
 *   - Done / Total + procent
 *   - Required-progress (færdige af påkrævede)
 *   - Estimat for resterende tid (sum af `estimated_minutes` på templates der mangler)
 *
 * Henter:
 *   - GET /api/v3/evidence/templates  → for at finde estimated_minutes pr. ID
 *
 * Props:
 *   evidenceItems: list of { id, status: 'pending'|'in_progress'|'done' }
 *   compact: bool — mindre version til sidebar/inline
 */

const Wrap = styled.div`
  display: flex;
  align-items: center;
  gap: ${(p) => (p.$compact ? '0.85rem' : '1.5rem')};
  padding: ${(p) => (p.$compact ? '0.75rem 0.9rem' : '1.1rem 1.4rem')};
  background: ${(p) => p.theme.colors.surface || '#fff'};
  border: 1px solid ${(p) => p.theme.colors.border || '#d8dde6'};
  border-radius: 8px;

  .ring-wrap {
    position: relative;
    width: ${(p) => (p.$compact ? '72px' : '96px')};
    height: ${(p) => (p.$compact ? '72px' : '96px')};
    flex-shrink: 0;

    .label {
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      pointer-events: none;
      font-family: ${(p) => p.theme.fonts.display};

      .pct {
        font-size: ${(p) => (p.$compact ? '1.05rem' : '1.4rem')};
        font-weight: 700;
        color: ${(p) => p.theme.colors.text};
        line-height: 1;
      }
      .of {
        font-family: ${(p) => p.theme.fonts.mono};
        font-size: 0.65rem;
        color: ${(p) => p.theme.colors.textMuted};
        margin-top: 2px;
      }
    }
  }

  .meta {
    flex: 1;
    min-width: 0;

    .head {
      font-family: ${(p) => p.theme.fonts.display};
      font-weight: 600;
      font-size: ${(p) => (p.$compact ? '0.85rem' : '0.95rem')};
      color: ${(p) => p.theme.colors.text};
      margin: 0 0 0.2rem;
    }
    .row {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      font-size: 0.8rem;
      color: ${(p) => p.theme.colors.textMuted};
      margin: 0.15rem 0;

      svg { font-size: 0.8rem; opacity: 0.7; }
      .num {
        font-family: ${(p) => p.theme.fonts.mono};
        font-weight: 600;
        color: ${(p) => p.theme.colors.text};
      }
    }
  }
`;

const RING_THICKNESS = 8;

const Ring = ({ pct, size, color }) => {
  const r = (size - RING_THICKNESS) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const circumference = 2 * Math.PI * r;
  const offset = circumference * (1 - Math.max(0, Math.min(1, pct / 100)));

  return (
    <svg width={size} height={size} aria-hidden="true">
      <circle
        cx={cx}
        cy={cy}
        r={r}
        fill="none"
        stroke="rgba(13, 46, 84, 0.10)"
        strokeWidth={RING_THICKNESS}
      />
      <circle
        cx={cx}
        cy={cy}
        r={r}
        fill="none"
        stroke={color}
        strokeWidth={RING_THICKNESS}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        transform={`rotate(-90 ${cx} ${cy})`}
        style={{ transition: 'stroke-dashoffset 400ms ease-out' }}
      />
    </svg>
  );
};

function formatMinutes(min) {
  if (min == null || min === 0) return '0 min';
  if (min < 60) return `${min} min`;
  const h = Math.floor(min / 60);
  const rem = min % 60;
  return rem > 0 ? `${h} t ${rem} min` : `${h} t`;
}

const EvidenceProgressRadial = ({ evidenceItems = [], compact = false }) => {
  const [estimatesByid, setEstimatesById] = useState({});

  // Hent estimerede minutter pr. template-ID — én fetch én gang
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await axios.get('/api/v3/evidence/templates');
        if (cancelled) return;
        const map = {};
        for (const t of res.data?.templates || res.data || []) {
          if (t?.id != null) {
            map[t.id] = t.estimated_minutes ?? null;
          }
        }
        setEstimatesById(map);
      } catch (err) {
        // Ikke kritisk — viser bare ingen estimater
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const stats = useMemo(() => {
    const total = evidenceItems.length;
    const done = evidenceItems.filter((it) => it.status === 'done').length;
    const inProgress = evidenceItems.filter((it) => it.status === 'in_progress').length;
    const pending = evidenceItems.filter((it) => it.status === 'pending').length;

    let estimatedRemainingMin = 0;
    let knownEstimateCount = 0;
    for (const it of evidenceItems) {
      if (it.status === 'done') continue;
      const est = estimatesByid[it.id];
      if (typeof est === 'number') {
        estimatedRemainingMin += est;
        knownEstimateCount += 1;
      }
    }

    const pct = total > 0 ? Math.round((done / total) * 100) : 0;

    return {
      total,
      done,
      inProgress,
      pending,
      pct,
      estimatedRemainingMin,
      knownEstimateCount,
    };
  }, [evidenceItems, estimatesByid]);

  const size = compact ? 72 : 96;
  const ringColor =
    stats.pct >= 100 ? '#2d6a31' : stats.pct >= 50 ? '#0d2e54' : '#6e5527';

  if (stats.total === 0) {
    return (
      <Wrap $compact={compact}>
        <div className="ring-wrap">
          <Ring pct={0} size={size} color="#9aa3b1" />
          <div className="label">
            <span className="pct">—</span>
          </div>
        </div>
        <div className="meta">
          <p className="head">Ingen evidens-skabeloner endnu</p>
          <p className="row">Kør en vurdering for at se hvilke artefakter sagen kræver.</p>
        </div>
      </Wrap>
    );
  }

  return (
    <Wrap $compact={compact} role="status" aria-label="Evidens-fremdrift">
      <div className="ring-wrap">
        <Ring pct={stats.pct} size={size} color={ringColor} />
        <div className="label">
          <span className="pct">{stats.pct}%</span>
          <span className="of">
            {stats.done}/{stats.total}
          </span>
        </div>
      </div>
      <div className="meta">
        <p className="head">Evidens-fremdrift</p>
        <p className="row">
          <FaCheckCircle aria-hidden="true" />
          <span>
            <span className="num">{stats.done}</span> færdige ·{' '}
            <span className="num">{stats.inProgress}</span> i gang ·{' '}
            <span className="num">{stats.pending}</span> mangler
          </span>
        </p>
        {stats.estimatedRemainingMin > 0 && (
          <p className="row">
            <FaClock aria-hidden="true" />
            <span>
              Est. resterende: <span className="num">{formatMinutes(stats.estimatedRemainingMin)}</span>
              {stats.knownEstimateCount < stats.total - stats.done && (
                <span style={{ opacity: 0.6, marginLeft: 4 }}>
                  ({stats.knownEstimateCount} af {stats.total - stats.done} med estimat)
                </span>
              )}
            </span>
          </p>
        )}
      </div>
    </Wrap>
  );
};

export default EvidenceProgressRadial;
