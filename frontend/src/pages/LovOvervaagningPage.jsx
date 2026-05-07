import React, { useState } from 'react';
import styled from 'styled-components';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import axios from 'axios';

/**
 * LovOvervaagningPage — Step 3 ("Citation-Verifier") admin-side.
 *
 * Viser hver regels seneste verifikation: Er kilde.citat stadig findes
 * ordret i kilde.url? Det er en fitness-funktion ailex.dk ikke har —
 * bevisbart at vores citater er friske ift. lovteksten.
 */

async function fetchFreshness() {
  const res = await axios.get('/api/v3/law/freshness');
  return res.data;
}

async function runFreshness() {
  const res = await axios.post('/api/v3/law/freshness/run', {}, { timeout: 240000 });
  return res.data;
}

const Page = styled.div`
  max-width: 1100px;
  margin: 0 auto;
  padding: 3rem 2.5rem 5rem;
`;

const Eyebrow = styled.div`
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: ${(p) => p.theme.colors.inkFaded};
  margin-bottom: 0.6rem;
  font-weight: 600;
`;

const Title = styled.h1`
  font-family: ${(p) => p.theme.fonts.display};
  font-size: 2.4rem;
  font-weight: 700;
  letter-spacing: -0.022em;
  line-height: 1.12;
  margin: 0 0 0.6rem;
  color: ${(p) => p.theme.colors.ink};
`;

const Lede = styled.p`
  font-family: ${(p) => p.theme.fonts.body};
  margin: 0 0 1.5rem;
  color: ${(p) => p.theme.colors.inkSoft};
  font-size: 1.02rem;
  line-height: 1.6;
  max-width: 720px;
`;

const Header = styled.header`
  display: flex; justify-content: space-between; align-items: flex-end;
  gap: 1.5rem; margin-bottom: 1.5rem; flex-wrap: wrap;
`;

const Stats = styled.div`
  display: flex; gap: 1.25rem;
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.85rem;
  color: ${(p) => p.theme.colors.inkSoft};

  .num { font-family: ${(p) => p.theme.fonts.display}; font-size: 1.6rem; font-weight: 700; line-height: 1; display: block; }
  .green .num { color: #2d6a31; }
  .red .num { color: ${(p) => p.theme.colors.primary}; }
  .grey .num { color: ${(p) => p.theme.colors.inkFaded}; }
  .lab { font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.12em; color: ${(p) => p.theme.colors.inkFaded}; font-weight: 600; }
`;

const PrimaryButton = styled.button`
  background: ${(p) => p.theme.colors.primary};
  color: white;
  border: none;
  padding: 0.7rem 1.4rem;
  border-radius: 6px;
  font-family: ${(p) => p.theme.fonts.sans};
  font-weight: 600;
  font-size: 0.92rem;
  cursor: pointer;
  &:hover { background: ${(p) => p.theme.colors.primaryDark}; }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
`;

const Table = styled.div`
  background: ${(p) => p.theme.colors.card};
  border: 1px solid ${(p) => p.theme.colors.line};
  border-radius: 10px;
  overflow: hidden;
`;

const Row = styled.div`
  display: grid;
  grid-template-columns: 24px 1fr 130px 130px;
  gap: 1rem;
  padding: 0.95rem 1.2rem;
  border-bottom: 1px solid ${(p) => p.theme.colors.lineSoft};
  align-items: center;

  &:last-child { border-bottom: none; }

  @media (max-width: 720px) {
    grid-template-columns: 24px 1fr;
    .col-status, .col-date { display: none; }
  }
`;

const HeadRow = styled(Row)`
  background: ${(p) => p.theme.colors.paperSoft};
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.66rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: ${(p) => p.theme.colors.inkFaded};
  font-weight: 600;
`;

const Dot = styled.span`
  width: 10px; height: 10px; border-radius: 50%;
  background: ${(p) => {
    if (p.$state === 'green') return '#2d6a31';
    if (p.$state === 'red') return p.theme.colors.primary;
    return p.theme.colors.inkFaded;
  }};
`;

const RuleId = styled.div`
  font-family: ${(p) => p.theme.fonts.mono};
  font-size: 0.78rem;
  color: ${(p) => p.theme.colors.ink};
  letter-spacing: 0.02em;

  .url { font-size: 0.7rem; color: ${(p) => p.theme.colors.inkFaded}; margin-top: 4px; display: block; }
  .err { font-family: ${(p) => p.theme.fonts.body}; color: ${(p) => p.theme.colors.primary}; font-style: italic; margin-top: 4px; font-size: 0.82rem; }
`;

const Status = styled.div`
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: ${(p) => {
    if (p.$state === 'green') return '#2d6a31';
    if (p.$state === 'red') return p.theme.colors.primary;
    return p.theme.colors.inkFaded;
  }};
`;

const DateCol = styled.div`
  font-family: ${(p) => p.theme.fonts.mono};
  font-size: 0.72rem;
  color: ${(p) => p.theme.colors.inkFaded};
  letter-spacing: 0.04em;
`;

const Empty = styled.div`
  background: ${(p) => p.theme.colors.paperSoft};
  border: 1px dashed ${(p) => p.theme.colors.line};
  border-radius: 8px;
  padding: 2.5rem;
  text-align: center;
  font-family: ${(p) => p.theme.fonts.body};
  color: ${(p) => p.theme.colors.inkSoft};
  font-style: italic;
`;

const fmtDate = (iso) => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('da-DK', {
      day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  } catch { return '—'; }
};

const stateOf = (item) => {
  if (item.citation_found && !item.flagged_for_review) return 'green';
  if (item.flagged_for_review) return 'red';
  return 'grey';
};

const LovOvervaagningPage = () => {
  const queryClient = useQueryClient();
  const { data, isLoading, isError, error } = useQuery('v3-freshness', fetchFreshness);
  const items = data?.items || [];

  const runMutation = useMutation(runFreshness, {
    onSuccess: () => queryClient.invalidateQueries('v3-freshness'),
  });

  const counts = {
    green: items.filter((i) => stateOf(i) === 'green').length,
    red: items.filter((i) => stateOf(i) === 'red').length,
    grey: items.filter((i) => stateOf(i) === 'grey').length,
  };

  return (
    <Page>
      <Eyebrow>Forseti · lov-overvågning</Eyebrow>
      <Title>Lov-overvågning</Title>
      <Lede>
        Daglig automatisk verifikation af hver regels lov-citat: Findes citatet
        stadig ordret i kilden? Hvis ikke, flagges reglen til juridisk review.
        Det er en fitness-funktion der gør Forseti bevisbart frisk overfor
        EUR-Lex og Retsinformation — ikke bare ved sidst-verificeret-stempel.
      </Lede>

      <Header>
        <Stats>
          <div className="green"><span className="num">{counts.green}</span><span className="lab">Verificeret</span></div>
          <div className="red"><span className="num">{counts.red}</span><span className="lab">Flagget</span></div>
          <div className="grey"><span className="num">{counts.grey}</span><span className="lab">Ukendt</span></div>
        </Stats>
        <PrimaryButton
          type="button"
          disabled={runMutation.isLoading}
          onClick={() => runMutation.mutate()}
        >
          {runMutation.isLoading ? 'Kører…' : 'Kør verifikation nu'}
        </PrimaryButton>
      </Header>

      {isError && <Empty>Kunne ikke hente status: {String(error?.message || error)}</Empty>}

      {!isError && items.length === 0 && (
        <Empty>
          {isLoading ? 'Indlæser…' : 'Verifikation er aldrig kørt. Klik "Kør verifikation nu".'}
        </Empty>
      )}

      {items.length > 0 && (
        <Table>
          <HeadRow>
            <div></div>
            <div>Regel · kilde</div>
            <div className="col-status">Status</div>
            <div className="col-date">Sidst tjekket</div>
          </HeadRow>
          {items.map((item) => {
            const state = stateOf(item);
            return (
              <Row key={item.rule_id}>
                <Dot $state={state} />
                <RuleId>
                  {item.rule_id}
                  {item.source_url && (
                    <a className="url" href={item.source_url} target="_blank" rel="noreferrer noopener">
                      {item.source_url}
                    </a>
                  )}
                  {item.error_message && state === 'red' && (
                    <span className="err">{item.error_message}</span>
                  )}
                </RuleId>
                <Status $state={state} className="col-status">
                  {state === 'green' ? '✓ Verificeret' : state === 'red' ? '⚠ Flagget' : '— Ukendt'}
                </Status>
                <DateCol className="col-date">{fmtDate(item.last_checked_at)}</DateCol>
              </Row>
            );
          })}
        </Table>
      )}
    </Page>
  );
};

export default LovOvervaagningPage;
