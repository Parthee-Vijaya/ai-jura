# Sektorlove — placeholder + jurist-spec

Status: **BLOKERET PÅ JURIST-INPUT** (per HANDOFF.md Step 5).

## Kontekst

v3-rule_engine dækker pt. tværgående lovgrundlag:

| Område | Lov | Antal regler |
|---|---|---|
| `ai_act/` | EU AI-forordningen 2024/1689 | 5 |
| `gdpr/` | Databeskyttelsesforordningen 2016/679 | 5 |
| `forvaltningsloven/` | Forvaltningsloven (lbk. 433/2014) | 4 |
| `offentlighedsloven/` | Offentlighedsloven (lov 606/2013) | 1 |

Sektorlove er den **kommune-specifikke** lovgrundlag der gælder afhængigt af, hvilken sektor en AI-vurdering rammer (jobcenter, social, sundhed, beskæftigelse, undervisning).

## Hvad mangler

For at kunne tilføje sektorlove til regelmotoren skal en jurist hos Kalundborg Kommune levere følgende per sektor (~5-10 paragraffer i alt):

### 1. Servicelov (LBK nr. 1089/2025)
**Relevant for:** Børn og Familie, Voksenspecialenheden, Sundhed og Myndighed.

**Spørgsmål til jurist:**
- Hvilke 3-5 paragraffer rammer hyppigst i AI-cases (visitation, indstilling, beslutning om foranstaltning)?
- Er § 11 (kommunal forsørgelsespligt), § 50 (børneundersøgelser), § 102 (særlig støtte til voksne) i scope?
- Hvilke afgørelser er klassisk anke-bare og kræver derfor begrundelses-kontrol?

### 2. Lov om aktiv beskæftigelsesindsats (LBK nr. 701/2024)
**Relevant for:** Jobcenter, Borgerservice (kontanthjælp).

**Spørgsmål til jurist:**
- Hvilke paragraffer styrer profilering af ledige (kontaktforløb, jobplan, visitation til indsats)?
- § 11 (ret/pligt til samtaler), § 27 (jobplan), § 30a (digital selvbetjening) — relevante?
- Hvor er grænsen mellem "AI-assist" og "automatisk afgørelse" i beskæftigelseslov?

### 3. Sundhedslov (LBK nr. 248/2024)
**Relevant for:** Sundhed og Myndighed (triagering, hjælpemidler).

**Spørgsmål til jurist:**
- § 23 (information til patient), § 26 (samtykke), § 41 (videregivelse af helbredsoplysninger)?
- Hvilke AI-cases falder under "diagnose-støtte" (medicinsk udstyr efter MDR/IVDR — ikke service) vs "myndighedsbeslutning" (servicelov)?

## Sådan bidrager juristen

For hver ny regel skal følgende felter udfyldes (samme JSON Schema som de eksisterende — se `../_schema.json`):

```yaml
id: servicelov.par11.kommunal_forsorgelsespligt
kilde:
  lov: "Lov om social service (LBK nr. 1089/2025)"
  artikel: "§ 11"
  citat: "Direkte citat fra lovteksten (1-3 sætninger)"
  url: "https://www.retsinformation.dk/eli/lta/2025/1089"
  sidst_verificeret: "2026-05-07"

trigger:
  any_of:
    - signal: system.makes_decisions_about_persons
    # eller mere specifikt
    - predicate:
        field: sektor
        equals: "social"

predikater:
  - id: visiteres_til_foranstaltning
    spørgsmål: "Træffes afgørelsen om en konkret foranstaltning efter § 11?"
    type: boolean

decision:
  if: "visiteres_til_foranstaltning"
  then:
    status: BETINGET-GO
    krav:
      - "Krav 1 baseret på lovens ordlyd"
      - "Krav 2 ..."
    evidens_påkrævet: ["dokumentation_X", "dokumentation_Y"]
  ellers:
    status: GO

metadata:
  forfatter: "[Jurist-navn]"
  version: "1.0.0"
  tags: ["servicelov", "social", "kommunalt"]
```

## Foreslået arbejdsproces

1. **30-min interview** med jurist hos Kalundborg → identificer top 5-10 paragraffer der hyppigst rammer
2. **Workshop** (~1 time) hvor regelforfatteren (efter `docs/RULE_AUTHORING.md`) sammen med juristen skriver YAML-filer
3. **Test mod casebase** — kør hver ny regel mod `tests/regression/cases.yaml` for at verificere afgørelseslogik
4. **Sign-off** — jurist verificerer citater og sidst_verificeret-dato før release

Når sektorlove er på plads, slettes denne README og erstattes med en `INDEX.md` der oplister de leverede regler.

## Aktuel placeholder-struktur

```
rules/sektorlove/
├── README.md          ← denne fil
├── servicelov/        ← tom (afventer jurist)
├── beskaeftigelseslov/ ← tom (afventer jurist)
└── sundhedslov/       ← tom (afventer jurist)
```

Disse mapper er bevidst tomme — `RuleLoader` ignorerer tomme mapper, så regelmotoren kører videre uden disse.
