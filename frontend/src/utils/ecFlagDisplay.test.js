import { summarizeEcFlags } from './ecFlagDisplay';

describe('EC flag display', () => {
  test('deduplicates role state and exposes readable classification points', () => {
    expect(summarizeEcFlags({
      flag_ai_system_role: 'deployer',
      flag_ai_initial_system_role: 'deployer',
      flag_risklevel_aisystem_nohighrisk_output: true,
      ignored_false_flag: false,
    })).toEqual([
      { key: 'flag_ai_system_role', label: 'Rolle: Idriftsætter', tone: 'info' },
      {
        key: 'flag_risklevel_aisystem_nohighrisk_output',
        label: 'Ikke-højrisiko AI-system',
        tone: 'success',
      },
    ]);
  });
});
