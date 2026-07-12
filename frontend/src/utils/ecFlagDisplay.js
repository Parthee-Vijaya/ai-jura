const ROLE_LABELS = {
  provider: 'Udbyder',
  deployer: 'Idriftsætter',
  distributor: 'Distributør',
  importer: 'Importør',
  authorised_representative: 'Bemyndiget repræsentant',
  product_manufacturer: 'Produktproducent',
};

export const EC_FLAG_DISPLAY = {
  flag_risklevel_aisystem_output: { label: 'Omfattet af EU AI Act', tone: 'info' },
  flag_risklevel_aisystem_highrisk_output: { label: 'Højrisiko AI-system (Bilag III)', tone: 'danger' },
  flag_risklevel_aisystem_nohighrisk_output: { label: 'Ikke-højrisiko AI-system', tone: 'success' },
  flag_obligations_aisystem_nohighrisk_output: { label: 'Ingen særlige højrisikokrav i kapitel III', tone: 'success' },
  flag_obligations_prohibitedsystems_result_output: { label: 'Mulig forbudt praksis (art. 5)', tone: 'danger' },
  flag_outofscope: { label: 'Uden for AI Act-anvendelsesområdet', tone: 'info' },
  flag_fr_impact_assessment_deployer: { label: 'FRIA påkrævet', tone: 'warn' },
  flag_obligation_transparency_provider: { label: 'Transparenskrav for udbyder', tone: 'warn' },
  flag_obligation_transparency_deployer: { label: 'Transparenskrav for idriftsætter', tone: 'warn' },
  flag_obligations_provideranddeployer_ailiteracy: { label: 'AI-færdigheder påkrævet (art. 4)', tone: 'warn' },
};

const readableFallback = (flag) => flag
  .replace(/^flag_/, '')
  .replace(/_/g, ' ')
  .replace(/\baisystem\b/gi, 'AI-system')
  .replace(/\boutput\b/gi, '')
  .replace(/\s+/g, ' ')
  .trim();

/** Return one concise, user-facing row per meaningful EC result. */
export function summarizeEcFlags(flags = {}) {
  const rows = [];
  const role = flags.flag_ai_system_role || flags.flag_ai_initial_system_role;
  if (role) {
    rows.push({
      key: 'flag_ai_system_role',
      label: `Rolle: ${ROLE_LABELS[role] || role}`,
      tone: 'info',
    });
  }

  Object.entries(flags).forEach(([flag, value]) => {
    if (flag === 'flag_ai_system_role' || flag === 'flag_ai_initial_system_role') return;
    if (value !== true) return;
    const display = EC_FLAG_DISPLAY[flag] || {
      label: readableFallback(flag),
      tone: 'info',
    };
    rows.push({ key: flag, ...display });
  });
  return rows;
}
