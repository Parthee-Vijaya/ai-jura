import {
  applyFlagOps,
  cleanTranslatedText,
  normalizeRaisedFlags,
  resolveAutomaticNodes,
} from './euCheckerEngine';

describe('EU checker engine', () => {
  test('follows invisible hub nodes to END and applies their flags', () => {
    const result = resolveAutomaticNodes({
      qid: 'hub-a',
      flags: { role: 'deployer' },
      questionsLogic: {
        'hub-a': {
          type: 'hub',
          routing: [{
            conditions: [],
            go_to: 'hub-b',
            set_flags: [{ flag_name: 'classified', value: true }],
          }],
        },
        'hub-b': {
          type: 'hub',
          routing: [{ conditions: [], go_to: 'END' }],
        },
      },
      questionsContent: {},
    });

    expect(result).toEqual({
      qid: 'END',
      flags: { role: 'deployer', classified: true },
      error: null,
    });
  });

  test('only applies conditional flag operations when their condition matches', () => {
    const operations = [
      {
        condition: [{ flag_equals: { flag_name: 'role', value: 'provider' } }],
        flag_name: 'provider_obligation',
        value: true,
      },
      {
        condition: [{ flag_equals: { flag_name: 'role', value: 'deployer' } }],
        flag_name: 'deployer_obligation',
        value: true,
      },
    ];

    expect(applyFlagOps({ role: 'deployer' }, operations)).toEqual({
      role: 'deployer',
      deployer_obligation: true,
    });
  });

  test('removes translation placeholders and keeps the readable fallback', () => {
    expect(cleanTranslatedText('[Kontekst: questions.QAIS 1.answers.0.label] Ja'))
      .toBe('Ja');
  });

  test('normalizes string flag content as readable copy and keeps internal flags technical', () => {
    expect(normalizeRaisedFlags(
      { public_flag: true, role_flag: 'deployer' },
      { public_flag: 'Artikel 4: Sørg for tilstrækkelige AI-færdigheder.' },
    )).toEqual([
      {
        name: 'public_flag',
        value: true,
        description: 'Artikel 4: Sørg for tilstrækkelige AI-færdigheder.',
        hasPublicCopy: true,
      },
      { name: 'role_flag', value: 'deployer', hasPublicCopy: false },
    ]);
  });
});
