/**
 * Bifrost — Glossary / fagudtryk-ordbog
 *
 * Centralt katalog over juridiske og tekniske fagudtryk der bruges i
 * Bifrost. Hver term har:
 *   - definition: 1-2 sætningers forklaring i hverdagssprog
 *   - source: hvor termen stammer fra (fx "AI Act Art. 6")
 *   - link (valgfri): URL til myndighedsside / lov
 *
 * Termer slås op case-insensitively. Aliases peger på en kanonisk term.
 *
 * Bruges af <Term>-komponenten:
 *
 *   import { Term } from '../components/ui';
 *   <Term>DPIA</Term>      → dotted underline + tooltip ved hover
 *   <Term term="dpia">konsekvensanalyse</Term>  → custom tekst, samme tooltip
 *
 * Hvis en term ikke er i kataloget, rendres børnene som almindelig tekst
 * uden tooltip (silent fallback).
 */

// Kanoniske termer
export const TERMS = {
  // ---- AI Act -------------------------------------------------------------
  ai_act: {
    label: 'AI Act',
    definition:
      "EU's AI-forordning (Forordning 2024/1689) — den centrale lovgivning " +
      'for AI i EU. Indfases gradvist 2025-2027.',
    source: 'Forordning (EU) 2024/1689',
    link: 'https://eur-lex.europa.eu/eli/reg/2024/1689/oj/dan',
  },
  hojrisiko: {
    label: 'Højrisiko-AI',
    definition:
      'AI-system der ifølge AI Act Art. 6 + Bilag III udgør en betydelig ' +
      'risiko for sundhed, sikkerhed eller grundlæggende rettigheder. ' +
      'Kræver konformitetsvurdering, CE-mærkning og EU-database-registrering.',
    source: 'AI Act Art. 6',
  },
  bilag_iii: {
    label: 'Bilag III',
    definition:
      'AI Act\'s Bilag III lister 8 områder hvor AI-systemer betragtes som ' +
      'højrisiko: biometri, kritisk infrastruktur, uddannelse, beskæftigelse, ' +
      'væsentlige offentlige tjenester, retshåndhævelse, migration, retspleje.',
    source: 'AI Act Bilag III',
  },
  gpai: {
    label: 'GPAI',
    definition:
      'General Purpose AI — AI-modeller med bred anvendelighed (fx LLMs som ' +
      'GPT-4, Claude, Gemini). Reguleret særskilt under AI Act Art. 51-55.',
    source: 'AI Act Art. 3 + Art. 51',
  },
  provider: {
    label: 'Provider (udbyder)',
    definition:
      'Den der udvikler eller får udviklet et AI-system og bringer det på ' +
      'EU-markedet under eget navn. Bærer hovedansvaret for compliance.',
    source: 'AI Act Art. 3, nr. 3',
  },
  deployer: {
    label: 'Deployer (idriftsætter)',
    definition:
      'Den der bruger et AI-system under egen myndighed — fx en kommune der ' +
      'bruger en leverandørs AI-løsning. Skal udføre FRIA og sikre korrekt brug.',
    source: 'AI Act Art. 3, nr. 4',
  },
  fria: {
    label: 'FRIA',
    definition:
      'Fundamental Rights Impact Assessment — konsekvensvurdering af et ' +
      'højrisiko-AI-systems påvirkning af grundlæggende rettigheder. Pligt ' +
      'for offentlige myndigheder INDEN ibrugtagning.',
    source: 'AI Act Art. 27',
  },
  konformitetsvurdering: {
    label: 'Konformitetsvurdering',
    definition:
      'Procedure der dokumenterer at et højrisiko-AI-system opfylder AI Act\'s ' +
      'krav. Kan være intern (Bilag VI) eller ekstern via bemyndiget organ (Bilag VII).',
    source: 'AI Act Art. 43',
  },
  ce_maerkning: {
    label: 'CE-mærkning',
    definition:
      'Synligt mærke på højrisiko-AI-systemer der bekræfter compliance med ' +
      'AI Act. Skal påføres INDEN ibrugtagning.',
    source: 'AI Act Art. 48',
  },
  bemyndiget_organ: {
    label: 'Bemyndiget organ',
    definition:
      'Privat eller offentlig organisation udpeget til at udføre eksterne ' +
      'konformitetsvurderinger. Slå op i NANDO-databasen.',
    source: 'AI Act Art. 31',
    link: 'https://ec.europa.eu/growth/tools-databases/nando/',
  },
  ai_literacy: {
    label: 'AI-færdigheder (Art. 4)',
    definition:
      'Pligt fra 2. feb 2025: udbydere og idriftsættere skal sikre at ' +
      'personale der drifter eller bruger AI har et tilstrækkeligt ' +
      'kompetenceniveau. Gælder ALLE AI-systemer, ikke kun højrisiko.',
    source: 'AI Act Art. 4',
  },
  art_73: {
    label: 'Art. 73 (incident reporting)',
    definition:
      'Indberetningspligt ved alvorlige hændelser fra højrisiko-AI til ' +
      'markedsovervågningsmyndigheden (i DK: Digitaliseringsstyrelsen). ' +
      'Frist: 2 dage (kritisk infrastruktur), 10 dage (dødsfald), 15 dage (øvrige).',
    source: 'AI Act Art. 73',
  },

  // ---- Forvaltningsret + GDPR --------------------------------------------
  fvl: {
    label: 'FVL',
    definition:
      'Forvaltningsloven — den danske lov der regulerer offentlig ' +
      'forvaltning. Centrale paragraffer: § 19 (partshøring), § 22 (begrundelse), § 24 (begrundelseskrav).',
    source: 'Forvaltningsloven',
    link: 'https://www.retsinformation.dk/eli/lta/2014/433',
  },
  gdpr: {
    label: 'GDPR',
    definition:
      'Databeskyttelsesforordningen (Forordning 2016/679) — EU\'s lov om ' +
      'persondatabehandling. Kendt som DSGVO på tysk.',
    source: 'Forordning (EU) 2016/679',
    link: 'https://eur-lex.europa.eu/eli/reg/2016/679/oj/dan',
  },
  dpia: {
    label: 'DPIA',
    definition:
      'Data Protection Impact Assessment — konsekvensanalyse vedrørende ' +
      'databeskyttelse. Pligt jf. GDPR Art. 35 når en behandling ' +
      'sandsynligvis indebærer høj risiko for personers rettigheder.',
    source: 'GDPR Art. 35',
    link: 'https://www.datatilsynet.dk/Media/637657725432210000/Vejledning-om-konsekvensanalyse.pdf',
  },
  dpo: {
    label: 'DPO',
    definition:
      'Data Protection Officer (databeskyttelsesrådgiver) — uafhængig ' +
      'rådgiver der overvåger en organisations GDPR-compliance. Pligt ' +
      'for offentlige myndigheder.',
    source: 'GDPR Art. 37',
  },
  dbs: {
    label: 'DBS',
    definition:
      'Databehandleraftalen — kontrakt mellem dataansvarlig og databehandler. ' +
      'I kommunal sammenhæng ofte baseret på Datatilsynets standardkontrakt ' +
      '(DBS-skabelonen).',
    source: 'GDPR Art. 28',
    link: 'https://www.datatilsynet.dk/Media/637657742019930000/Vejledning_om_databehandleraftaler.pdf',
  },
  profilering: {
    label: 'Profilering',
    definition:
      'Enhver form for automatisk behandling der vurderer personlige ' +
      'aspekter — fx kreditværdighed, arbejdspræstation, helbredstilstand. ' +
      'Profilering = altid højrisiko under AI Act Art. 6, stk. 3.',
    source: 'GDPR Art. 4, nr. 4',
  },
  persondata: {
    label: 'Persondata',
    definition:
      'Enhver oplysning der kan identificere en fysisk person — direkte ' +
      '(navn, CPR) eller indirekte (lokation, online-id, adfærdsmønstre).',
    source: 'GDPR Art. 4, nr. 1',
  },

  // ---- Bifrost / vurderings-output ---------------------------------------
  go: {
    label: 'GO',
    definition:
      'Bifrost-vurdering: AI-systemet kan tages i brug uden yderligere ' +
      'compliance-foranstaltninger.',
    source: 'Bifrost regelmotor',
  },
  betinget_go: {
    label: 'BETINGET-GO',
    definition:
      'Bifrost-vurdering: AI-systemet kan tages i brug PÅ BETINGELSE af at ' +
      'nævnte krav opfyldes (fx DPIA gennemført, konformitetsvurdering, ' +
      'EU-database-registrering).',
    source: 'Bifrost regelmotor',
  },
  no_go: {
    label: 'NO-GO',
    definition:
      'Bifrost-vurdering: AI-systemet kan IKKE tages i brug i sin nuværende ' +
      'form. Typisk pga. forbudte praksisser (Art. 5) eller manglende lovhjemmel.',
    source: 'Bifrost regelmotor',
  },

  // ---- Standarder + organisationer ---------------------------------------
  altai: {
    label: 'ALTAI',
    definition:
      'Assessment List for Trustworthy AI — EU HLEG\'s officielle ' +
      'selvvurderings-tjekliste mod 7 principper for pålidelig AI.',
    source: 'EU HLEG',
    link: 'https://digital-strategy.ec.europa.eu/en/library/assessment-list-trustworthy-artificial-intelligence-altai-self-assessment',
  },
  hleg: {
    label: 'HLEG',
    definition:
      'High-Level Expert Group on AI — EU-Kommissionens ekspertgruppe der ' +
      'i 2019 udsendte de 7 principper for Trustworthy AI.',
    source: 'EU-Kommissionen',
  },
  iso_42001: {
    label: 'ISO/IEC 42001',
    definition:
      'International ledelsesstandard for AI management systems (2023). ' +
      'Den første standard af sin art — leverandører med ISO 42001-' +
      'certificering har dokumenteret modne AI-styringsprocesser.',
    source: 'ISO',
  },
  iso_23894: {
    label: 'ISO/IEC 23894',
    definition:
      'International standard for AI risk management (2023). Bygger på ' +
      'ISO 31000 og er direkte anvendelig som rygrad i AI Act Art. 9-' +
      'risikostyringsplaner.',
    source: 'ISO',
  },
  digst: {
    label: 'Digitaliseringsstyrelsen',
    definition:
      'Dansk markedsovervågningsmyndighed for AI Act. Modtager Art. 73-' +
      'indberetninger og fører tilsyn med højrisiko-AI i DK.',
    source: 'AI Act Art. 70 + 79',
    link: 'https://digst.dk/tilsyn/ai-forordningen/',
  },
  datatilsynet: {
    label: 'Datatilsynet',
    definition:
      'Dansk myndighed for GDPR-tilsyn. Modtager anmeldelser om brud på ' +
      'persondatasikkerheden inden 72 timer.',
    source: 'GDPR Art. 51 + 33',
    link: 'https://www.datatilsynet.dk',
  },
  kl: {
    label: 'KL',
    definition:
      'Kommunernes Landsforening — interesseorganisation for danske kommuner. ' +
      'Udsender vejledninger og inspirationskataloger om kommunal digitalisering.',
    source: 'KL',
    link: 'https://videncenter.kl.dk',
  },
  wp248: {
    label: 'WP248',
    definition:
      'Article 29 Working Party Guidelines on DPIA (WP248 rev.01) — ' +
      'EU-vejledning om hvornår DPIA er obligatorisk. 9 kriterier; ≥2 = pligt.',
    source: 'EDPB / Art. 29 WP',
  },

  // ---- Sektorlove --------------------------------------------------------
  servicelov: {
    label: 'Serviceloven',
    definition:
      'Dansk lov om social service. Centrale paragraffer for AI: § 50 ' +
      '(børnefaglig undersøgelse), § 102 (voksenstøtte), § 11 (rådgivning).',
    source: 'Serviceloven',
  },
  sundhedslov: {
    label: 'Sundhedsloven',
    definition:
      'Dansk lov om sundhedsvæsenet. Strenge krav til AI der bruges i ' +
      'sundhedsfaglig vurdering.',
    source: 'Sundhedsloven',
  },
  beskaeftigelseslov: {
    label: 'Beskæftigelsesloven',
    definition:
      'Dansk lov om aktiv beskæftigelsesindsats. AI Act Bilag III højrisiko-' +
      'område når AI bruges i jobplaner eller kontaktforløb.',
    source: 'Beskæftigelsesloven',
  },
};

// Aliases — alle keys her peger på en kanonisk term i TERMS
export const ALIASES = {
  'ai-act': 'ai_act',
  'ai forordning': 'ai_act',
  'ai-forordning': 'ai_act',
  forordning: 'ai_act',
  hojrisiko: 'hojrisiko',
  'høj-risiko': 'hojrisiko',
  højrisiko: 'hojrisiko',
  'bilag iii': 'bilag_iii',
  'bilag-iii': 'bilag_iii',
  'general purpose ai': 'gpai',
  udbyder: 'provider',
  idriftsætter: 'deployer',
  idriftsaetter: 'deployer',
  'fundamental rights impact assessment': 'fria',
  'konsekvensvurdering om grundlæggende rettigheder': 'fria',
  'ce mærkning': 'ce_maerkning',
  'ce-mærkning': 'ce_maerkning',
  cemærkning: 'ce_maerkning',
  'notified body': 'bemyndiget_organ',
  'art. 4': 'ai_literacy',
  'artikel 4': 'ai_literacy',
  literacy: 'ai_literacy',
  færdigheder: 'ai_literacy',
  faerdigheder: 'ai_literacy',
  'art. 73': 'art_73',
  'artikel 73': 'art_73',
  forvaltningsloven: 'fvl',
  'data protection impact assessment': 'dpia',
  konsekvensanalyse: 'dpia',
  databeskyttelsesrådgiver: 'dpo',
  databeskyttelsesraadgiver: 'dpo',
  databehandleraftale: 'dbs',
  databehandleraftalen: 'dbs',
  'go ': 'go',
  'betinget go': 'betinget_go',
  'betinget-go': 'betinget_go',
  'no go': 'no_go',
  'no-go': 'no_go',
  'high-level expert group': 'hleg',
  'iso 42001': 'iso_42001',
  'iso/iec 42001': 'iso_42001',
  'iso 23894': 'iso_23894',
  'iso/iec 23894': 'iso_23894',
  digitaliseringsstyrelsen: 'digst',
  'kommunernes landsforening': 'kl',
  serviceloven: 'servicelov',
  sundhedsloven: 'sundhedslov',
  beskæftigelsesloven: 'beskaeftigelseslov',
  beskaeftigelsesloven: 'beskaeftigelseslov',
};

/**
 * Slå en term op case-insensitively. Returnér termObject eller null.
 */
export function lookupTerm(text) {
  if (!text || typeof text !== 'string') return null;
  const key = text.trim().toLowerCase();
  if (TERMS[key]) return TERMS[key];
  const aliased = ALIASES[key];
  if (aliased && TERMS[aliased]) return TERMS[aliased];
  return null;
}

export default { TERMS, ALIASES, lookupTerm };
