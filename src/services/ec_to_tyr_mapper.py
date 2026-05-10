"""EC compliance-checker flag → Bifrost signal/predicate mapper.

EC's Compliance Checker producerer 45 outcome-flags der klassificerer et
AI-system på højt niveau (er det out-of-scope? højrisiko? hvilken rolle
har du? GPAI?). Bifrosts vurderingsmotor kører på 9 signals + ~75 predikater
fordelt over 21 deklarative regler.

Denne mapper er broen: når brugeren har gennemført EC-wizarden får vi et
sæt rejste flag, og vi vil:

  1. Pre-fylde signals + predicates i Bifrosts RuleInput-tilstand så
     sagsbehandleren ikke skal svare to gange på det samme.
  2. Markere bestemte regler som relevante (`surfaced_rules`) så UI
     kan collapse de øvrige regler bag en "vis alle" toggle.
  3. Markere predikater som påkrævede (`required_predicates`) så
     "Vurdér"-knappen blokerer indtil sagsbehandleren har fuldført dem.
  4. Levere en kort dansk `ec_summary`-tekst der vises i banneret
     øverst på `/vurdering` så sagsbehandleren ved hvad EC konkluderede.

Curation-strategi: vi mapper de mest entydige højrisiko/rolle/scope-flag
direkte; de øvrige 30+ flag er info-only (vises kun som banner-tekst,
påvirker ikke regelsættet). Det dækker de 80% af kommunale use-cases.

Skema for et FlagMapping:
  - set_signals      : signals der altid pre-sættes når flaget er rejst
  - set_predicates   : predikater der pre-fyldes (inkl. enum-værdier)
  - surface_rules    : rule_ids der skal vises som relevante
  - require_predicates: predikater hvis svar SKAL afgives før Vurdér
  - info             : kort dansk forklaring til UI-banneret

Schema for input til map_ec_flags_to_tyr:
  {flag_name: bool|str|number}     hvor strings = enum-svar, bool = sat/ej-sat
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from .eu_ai_act_checker import CACHE_DIR, _safe_read_json

logger = logging.getLogger(__name__)


# ---- Datatyper -------------------------------------------------------------


@dataclass
class FlagMapping:
    """Hvad et EC-flag betyder for Bifrost's regelmotor."""

    set_signals: dict[str, bool] = field(default_factory=dict)
    set_predicates: dict[str, Any] = field(default_factory=dict)
    surface_rules: list[str] = field(default_factory=list)
    require_predicates: list[str] = field(default_factory=list)
    info: str = ""
    category: str = "info"  # one of: scope|risk|role|gpai|transparency|fria|info


@dataclass
class PrefilledAssessment:
    """Resultat af at køre flag-sættet gennem mapperen."""

    signals: dict[str, bool]
    predicates: dict[str, Any]
    surfaced_rules: list[str]
    required_predicates: dict[str, list[str]]  # rule_id → predicate_ids
    ec_summary: str
    matched_flags: list[str]
    info_messages: list[str]
    fallback_to_full_form: bool


# ---- EC_FLAG_MAPPING -------------------------------------------------------
#
# Curated dict — kun flag der entydigt påvirker Bifrost's regelmotor er
# mappet med set_signals/predicates/rules; resten har info-tekst.

EC_FLAG_MAPPING: dict[str, FlagMapping] = {
    # ============ SCOPE (3) ============
    "flag_outofscope": FlagMapping(
        set_signals={"system.uses_ai": False},
        info=(
            "Systemet falder uden for AI-forordningens anvendelsesområde "
            "(jf. Artikel 2). Bifrost's øvrige checks — GDPR og forvaltningsret — "
            "kan stadig gælde, men AI Act-reglerne springes over."
        ),
        category="scope",
    ),
    "flag_outofscope_gpai": FlagMapping(
        set_signals={"system.uses_ai": False},
        info=(
            "GPAI-modellen falder uden for AI-forordningens anvendelsesområde "
            "(forskning, ren videnskabelig brug eller lignende undtagelse). "
            "GDPR og kontraktretlige krav kan stadig gælde."
        ),
        category="scope",
    ),
    "flag_ai_system_outsidescope": FlagMapping(
        set_signals={"system.uses_ai": False},
        info=(
            "AI-systemet er uden for AI-forordningens anvendelsesområde. "
            "Bifrost's øvrige regler om GDPR + forvaltningsret kan dog gælde."
        ),
        category="scope",
    ),
    "flag_aisystem_role_and_obligation_outofscope": FlagMapping(
        info=(
            "AI-systemet ligger uden for forordningens forpligtelseskreds for "
            "denne rolle. Bifrost's øvrige regelsæt evalueres alligevel."
        ),
        category="scope",
    ),
    "flag_notaimodel_result_output": FlagMapping(
        set_signals={"system.uses_ai": False},
        info=(
            "Du har angivet at det IKKE er en AI-model. AI-forordningen er "
            "derfor ikke direkte relevant — men GDPR og dansk forvaltningsret "
            "kan stadig gælde for et almindeligt softwaresystem."
        ),
        category="scope",
    ),

    # ============ RISIKONIVEAU — AI SYSTEM (3) ============
    "flag_obligations_prohibitedsystems_result_output": FlagMapping(
        set_signals={"system.uses_ai": True},
        surface_rules=["ai_act.art5.forbudte_praksisser"],
        require_predicates=["anvendelse", "medicinsk_eller_sikkerheds_undtagelse"],
        info=(
            "EC's wizard har klassificeret systemet som muligvis omfattet af "
            "Artikel 5 (forbudte praksisser). Bekræft hvilken specifik praksis "
            "i Bifrost's art. 5-regel — det afgør om det er et NO-GO."
        ),
        category="risk",
    ),
    "flag_risklevel_aisystem_highrisk_output": FlagMapping(
        set_signals={
            "system.uses_ai": True,
            "system.makes_decisions_about_persons": True,
        },
        surface_rules=[
            "ai_act.art6.hojrisiko_klassifikation",
            "ai_act.art13.transparens_og_brugerinformation",
            "ai_act.art14.menneskelig_overvaagning",
            "gdpr.art35.dpia_pligt",
            "gdpr.art22.automatiseret_individuel_afgorelse",
            "forvaltningsloven.par22.begrundelsespligt",
            "forvaltningsloven.par24.begrundelsens_indhold",
        ],
        # Pre-set er_hojrisiko=true i de regler der har det predikat
        set_predicates={
            "er_hojrisiko": True,
        },
        require_predicates=[
            "anvendelsesomraade",
            "kun_forberedende",
            "profilering",
            "oversight_kapabilitet",
        ],
        info=(
            "EC har klassificeret systemet som højrisiko under Bilag III. "
            "Det udløser Artikel 6 + 9-15 + 27 (FRIA) + 49 (EU-database). "
            "Udfyld de markerede felter i Bifrost så vi kan producere den endelige "
            "vurdering med danske krav (GDPR + forvaltningsret oveni)."
        ),
        category="risk",
    ),
    "flag_risklevel_aisystem_nohighrisk_output": FlagMapping(
        set_signals={"system.uses_ai": True},
        set_predicates={"er_hojrisiko": False},
        surface_rules=[
            "ai_act.art50.transparens",
            "gdpr.art6.retsgrundlag_for_behandling",
            "gdpr.art22.automatiseret_individuel_afgorelse",
        ],
        info=(
            "EC har klassificeret systemet som IKKE-højrisiko. Artikel 6's "
            "tunge højrisiko-krav gælder ikke. Tjek alligevel art. 50 "
            "(transparens), GDPR-retsgrundlaget og forvaltningsretslige krav "
            "ved automatiseret afgørelse."
        ),
        category="risk",
    ),
    "flag_risklevel_aisystem_output": FlagMapping(
        set_signals={"system.uses_ai": True},
        info=(
            "EC's klassificering af AI-systemet er foretaget. Følg de øvrige "
            "flag for konkrete forpligtelser."
        ),
        category="risk",
    ),

    # ============ RISIKONIVEAU — GPAI (4) ============
    "flag_risklevel_output_gpai_with_systemic_risk": FlagMapping(
        set_signals={"system.uses_ai": True},
        info=(
            "GPAI-modellen klassificeres som havende systemisk risiko (Art. 51). "
            "Dette udløser særlige forpligtelser — uden for Bifrost's nuværende "
            "regelsæt. Konsultér Artikel 55 og Code of Practice."
        ),
        category="gpai",
    ),
    "flag_risklevel_output_gpai_without_systemic_risk": FlagMapping(
        set_signals={"system.uses_ai": True},
        info=(
            "GPAI-modellen klassificeres uden systemisk risiko. Artikel 53 "
            "gælder (teknisk dokumentation, copyright, training-summary)."
        ),
        category="gpai",
    ),
    "flag_aimodel_obligations_systemicrisk_result_output": FlagMapping(
        info=(
            "Forpligtelser for GPAI-modeller med systemisk risiko er udløst "
            "(Art. 55). Bifrost's regelsæt dækker ikke specifikke GPAI-krav endnu."
        ),
        category="gpai",
    ),
    "flag_aimodel_obligations_nosystemicrisk_result_output": FlagMapping(
        info=(
            "Forpligtelser for GPAI-modeller uden systemisk risiko er udløst "
            "(Art. 53)."
        ),
        category="gpai",
    ),
    "flag_aimodel_obligations_result_output": FlagMapping(
        info="GPAI-modellens forpligtelser er identificeret af EC.",
        category="gpai",
    ),

    # ============ ROLLE — AI SYSTEM (5) ============
    "flag_ai_system_role_provider": FlagMapping(
        info=(
            "Du er udbyder af AI-systemet. De fulde art. 16-22-forpligtelser "
            "gælder — risikostyring, datasæt, dokumentation, menneskelig "
            "overvågning, EU-database-registrering."
        ),
        category="role",
    ),
    "flag_ai_system_role_deployer": FlagMapping(
        info=(
            "Du er idriftsætter af AI-systemet. Art. 26 + 27 (FRIA) gælder — "
            "menneskelig overvågning, brug iht. brugsanvisning, FRIA inden "
            "ibrugtagning hvis offentlig myndighed."
        ),
        category="role",
    ),
    "flag_ai_system_role_distributor": FlagMapping(
        info=(
            "Du er distributør af AI-systemet. Art. 24 gælder — verificér "
            "CE-mærkning og overensstemmelseserklæring inden videresalg."
        ),
        category="role",
    ),
    "flag_ai_system_role_importer": FlagMapping(
        info=(
            "Du er importør. Art. 23 gælder — sikr at udbyderen har gennemført "
            "overensstemmelsesvurdering, har CE-mærkning og udarbejdet teknisk "
            "dokumentation."
        ),
        category="role",
    ),
    "flag_ai_system_role_authorisedrepre": FlagMapping(
        info=(
            "Du er bemyndiget repræsentant. Art. 22 gælder — du repræsenterer "
            "en udbyder uden for EU og holder dokumentation tilgængelig for "
            "myndigheder."
        ),
        category="role",
    ),
    "flag_ai_system_role_productmanufacturer": FlagMapping(
        info=(
            "Du er produktproducent og AI-systemet er en sikkerhedskomponent "
            "i dit produkt. Art. 25 gælder — du indtager udbyderrollen."
        ),
        category="role",
    ),
    "flag_role_distriimportdeployer_becomeprovider_result": FlagMapping(
        info=(
            "Distributør/importør/idriftsætter overgår til udbyderrolle (Art. 25). "
            "Det sker ved (a) re-branding, (b) substantiel ændring, eller "
            "(c) ny tilsigtet anvendelse. De fulde udbyder-forpligtelser gælder."
        ),
        category="role",
    ),
    "flag_role_manutoprovider_output": FlagMapping(
        info="Produktproducent er at betragte som udbyder af AI-systemet (Art. 25).",
        category="role",
    ),
    "flag_role_provider_gpai_output": FlagMapping(
        info=(
            "Du er udbyder af GPAI-modellen. Art. 53 + (hvis systemisk risiko) "
            "Art. 55 gælder."
        ),
        category="role",
    ),
    "flag_role_authorized_representative_gpai_output": FlagMapping(
        info=(
            "Du er bemyndiget repræsentant for GPAI-udbyder uden for EU. "
            "Art. 54 gælder."
        ),
        category="role",
    ),
    "flag_downstream_modifier": FlagMapping(
        info=(
            "Du er downstream-modifikator (har modificeret GPAI). Art. 53, "
            "stk. 5 gælder — proportionale forpligtelser baseret på modifikationens "
            "omfang."
        ),
        category="role",
    ),

    # ============ FORPLIGTELSER (16) ============
    "flag_obligations_provider_results_high_risk": FlagMapping(
        set_signals={"system.uses_ai": True, "system.makes_decisions_about_persons": True},
        set_predicates={"er_hojrisiko": True},
        surface_rules=[
            "ai_act.art6.hojrisiko_klassifikation",
            "ai_act.art13.transparens_og_brugerinformation",
            "ai_act.art14.menneskelig_overvaagning",
        ],
        require_predicates=[
            "kapabiliteter_og_begraensninger_dokumenteret",
            "brugsanvisning_paa_dansk",
            "oversight_kapabilitet",
        ],
        info=(
            "Som udbyder af et højrisiko-system er du underlagt det fulde "
            "art. 16-22 forpligtelses-batteri. Bifrost surfacer art. 13 + 14 her — "
            "udfyld for endelig kravliste."
        ),
        category="risk",
    ),
    "flag_obligations_provider_section_b_results_high_risk": FlagMapping(
        set_signals={"system.uses_ai": True},
        surface_rules=[
            "ai_act.art13.transparens_og_brugerinformation",
            "ai_act.art14.menneskelig_overvaagning",
        ],
        info=(
            "Som udbyder under section B (Bilag III) er du underlagt højrisiko-"
            "krav. Bifrost har art. 13 + 14 surfaced — udfyld dem for endelig "
            "vurdering."
        ),
        category="risk",
    ),
    "flag_obligations_authorisdrepre_results_high_risk": FlagMapping(
        info=(
            "Bemyndiget repræsentant for udbyder af højrisiko-system. "
            "Art. 22 — sikr at dokumentationen er tilgængelig for myndigheder."
        ),
        category="role",
    ),
    "flag_obligations_authorisedrep": FlagMapping(
        info="Bemyndiget repræsentant — Art. 22.",
        category="role",
    ),
    "flag_obligations_authorisedrep_nosystemicrisk_opensource": FlagMapping(
        info=(
            "Bemyndiget repræsentant for open-source GPAI uden systemisk "
            "risiko — lempede dokumentations-krav."
        ),
        category="gpai",
    ),
    "flag_obligations_importer_output": FlagMapping(
        info=(
            "Importør-forpligtelser udløst (Art. 23). Verificér CE-mærkning, "
            "overensstemmelseserklæring og teknisk dokumentation."
        ),
        category="role",
    ),
    "flag_obligations_distributor_output": FlagMapping(
        info=(
            "Distributør-forpligtelser udløst (Art. 24). Verificér CE-mærkning "
            "før videresalg."
        ),
        category="role",
    ),
    "flag_obligations_deployer_output": FlagMapping(
        set_signals={
            "system.uses_ai": True,
            "system.is_used_by_public_authority": True,
        },
        surface_rules=[
            "forvaltningsloven.par19.partshoring",
            "forvaltningsloven.par22.begrundelsespligt",
            "gdpr.art22.automatiseret_individuel_afgorelse",
        ],
        require_predicates=[
            "traeffer_afgoerelse",
            "har_retsvirkning_eller_betydelig_paavirkning",
        ],
        info=(
            "Idriftsætter-forpligtelser udløst (Art. 26). Som offentlig myndighed "
            "skal Bifrost også vurdere forvaltningsretslige krav (partshøring, "
            "begrundelse) + GDPR art. 22 ved automatiseret afgørelse."
        ),
        category="role",
    ),
    "flag_obligations_provideranddeployer_ailiteracy": FlagMapping(
        info=(
            "AI-kyndighedskrav (Art. 4) gælder — sørg for at personer der "
            "bruger eller udvikler AI-systemet har tilstrækkelig viden om "
            "AI generelt og det konkrete system."
        ),
        category="info",
    ),
    "flag_obligations_aisystem_opensource": FlagMapping(
        info=(
            "Open-source AI-system — visse krav lempes (jf. Art. 2, stk. 12). "
            "Højrisiko og forbudte praksisser gælder dog stadig."
        ),
        category="info",
    ),
    "flag_obligations_aisystem_nohighrisk_output": FlagMapping(
        set_signals={"system.uses_ai": True},
        set_predicates={"er_hojrisiko": False},
        surface_rules=["ai_act.art50.transparens"],
        info=(
            "Ikke-højrisiko AI-system. Tjek art. 50 (transparens ved chatbot, "
            "deepfake, syntetisk indhold) + Bifrost's GDPR/forvaltnings-regler."
        ),
        category="risk",
    ),
    "flag_obligations_opensource_provider": FlagMapping(
        info=(
            "Open-source-udbyder. Lempede krav for ikke-højrisiko AI; "
            "højrisiko og forbudte praksisser gælder dog stadig."
        ),
        category="info",
    ),
    "flag_aisystem_obligations_exclusions_output": FlagMapping(
        info=(
            "Visse AI-system-forpligtelser er undtaget i din situation "
            "(typisk forskning, militær eller national sikkerhed)."
        ),
        category="scope",
    ),
    "flag_obligations_gpai_outofscope_solescientific": FlagMapping(
        set_signals={"system.uses_ai": False},
        info=(
            "GPAI-modellen er udelukkende anvendt til videnskabelig forskning "
            "(Art. 2, stk. 6). Forordningen gælder ikke."
        ),
        category="scope",
    ),
    "flag_obligations_gpai_outofscope_researchtesting": FlagMapping(
        set_signals={"system.uses_ai": False},
        info=(
            "GPAI-modellen er udelukkende anvendt til forskning, afprøvning "
            "eller udvikling (Art. 2, stk. 8). Forordningen gælder ikke i "
            "denne fase."
        ),
        category="scope",
    ),
    "flag_ai_system_obligations_productmanufacturer": FlagMapping(
        info=(
            "Produktproducent-forpligtelser (Art. 25). Du betragtes som "
            "udbyder af AI-sikkerhedskomponenten."
        ),
        category="role",
    ),

    # ============ FRIA (1) ============
    "flag_ai_system_no_highrisk_frimpactassessement_provider_output": FlagMapping(
        info=(
            "Selvom systemet ikke er højrisiko, kan en frivillig konsekvensanalyse "
            "for grundlæggende rettigheder (FRIA) være god praksis hvis det "
            "anvendes af offentlig myndighed."
        ),
        category="fria",
    ),
    "flag_fr_impact_assessment_deployer": FlagMapping(
        set_signals={
            "system.uses_ai": True,
            "system.is_used_by_public_authority": True,
            "system.makes_decisions_about_persons": True,
        },
        surface_rules=[
            "gdpr.art35.dpia_pligt",
            "forvaltningsloven.par19.partshoring",
            "forvaltningsloven.par22.begrundelsespligt",
        ],
        require_predicates=[
            "art35_stk3_litra",
            "dpia_eksisterer",
            "traeffer_afgoerelse",
        ],
        info=(
            "FRIA påkrævet (Art. 27) — som offentlig idriftsætter af et "
            "højrisiko-system skal du gennemføre en konsekvensanalyse for "
            "grundlæggende rettigheder INDEN ibrugtagning. Bifrost surfacer "
            "DPIA-pligten (GDPR art. 35) og forvaltningsretslige krav som de "
            "supplerende krav du også skal opfylde."
        ),
        category="fria",
    ),

    # ============ TRANSPARENS (2) ============
    "flag_obligation_transparency_provider": FlagMapping(
        set_signals={"system.uses_ai": True},
        surface_rules=["ai_act.art50.transparens"],
        require_predicates=["scenarie", "aabenbart_at_det_er_ai"],
        info=(
            "Transparenskrav for udbyder udløst (Art. 50). Personer skal "
            "informeres om AI-interaktion / syntetisk indhold skal mærkes "
            "maskinlæsbart. Udfyld art. 50-regelens predikater."
        ),
        category="transparency",
    ),
    "flag_obligation_transparency_deployer": FlagMapping(
        set_signals={"system.uses_ai": True},
        surface_rules=["ai_act.art50.transparens"],
        require_predicates=["scenarie", "aabenbart_at_det_er_ai"],
        info=(
            "Transparenskrav for idriftsætter udløst (Art. 50, stk. 3 + 4). "
            "Hvis systemet bruger følelsesgenkendelse / biometrisk kategorisering / "
            "deepfakes — informér de personer det vedrører."
        ),
        category="transparency",
    ),
}


# Total antal flag i EC's logic.json — bruges af /drift til mapping-stat-card.
EC_TOTAL_FLAGS = 45


# ---- Pure rule-mapping (uafhængigt af YAML, brugt af endpoint) -----------


# Hvilke regler har hvilke predikat-IDs (statisk udledt fra YAML).
# Kunne læses dynamisk via rule_engine.loader, men det her er hurtigt
# nok til mapping-niveauet og holder mapper-koden self-contained.
_RULE_PREDICATES: dict[str, set[str]] = {
    "ai_act.art5.forbudte_praksisser": {"anvendelse", "medicinsk_eller_sikkerheds_undtagelse"},
    "ai_act.art6.hojrisiko_klassifikation": {"anvendelsesomraade", "kun_forberedende", "profilering"},
    "ai_act.art13.transparens_og_brugerinformation": {
        "er_hojrisiko",
        "brugsanvisning_eksisterer",
        "kapabiliteter_og_begraensninger_dokumenteret",
        "brugsanvisning_paa_dansk",
    },
    "ai_act.art14.menneskelig_overvaagning": {
        "er_hojrisiko",
        "oversight_kapabilitet",
        "stop_eller_override_mulighed",
        "kompetent_oversight",
    },
    "ai_act.art50.transparens": {
        "scenarie",
        "aabenbart_at_det_er_ai",
        "kunstnerisk_eller_satirisk_undtagelse",
    },
    "gdpr.art5.principper_for_behandling": {
        "formaal_dokumenteret",
        "dataminimering_vurderet",
        "opbevaringsfrist_fastsat",
        "korrekthedsproces",
        "sikkerhedsforanstaltninger",
    },
    "gdpr.art6.retsgrundlag_for_behandling": {
        "retsgrundlag",
        "behandler_saerlige_kategorier",
        "nationalt_retsgrundlag_dokumenteret",
    },
    "gdpr.art22.automatiseret_individuel_afgorelse": {
        "er_helautomatiseret",
        "har_retsvirkning_eller_betydelig_paavirkning",
        "retsgrundlag_til_undtagelse",
        "omfatter_saerlige_kategorier",
    },
    "gdpr.art32.sikkerhed_ved_behandling": {
        "pseudonymisering_kryptering",
        "integritet_og_fortrolighed",
        "gendannelse_efter_haendelse",
        "regelmaessig_test",
        "behandler_saerlige_kategorier",
        "brud_anmeldelses_proces",
    },
    "gdpr.art35.dpia_pligt": {
        "art35_stk3_litra",
        "paa_datatilsynets_liste",
        "art35_stk1_hoj_risiko",
        "dpia_eksisterer",
    },
    "forvaltningsloven.par3.inhabilitet": {
        "ai_traeffer_eller_paavirker_afgoerelse",
        "udvikler_eller_leverandoer_har_interesse",
        "bias_audit_udfoert",
        "leverandoer_uafhaengighed_dokumenteret",
    },
    "forvaltningsloven.par19.partshoring": {
        "traeffer_afgoerelse",
        "bruger_oplysninger_om_part",
        "parten_kender_oplysningerne",
        "ufordelagtig_for_parten",
    },
    "forvaltningsloven.par22.begrundelsespligt": {
        "traeffer_afgoerelse",
        "meddeles_skriftligt",
        "fuld_medhold",
        "kan_systemet_generere_begrundelse",
    },
    "forvaltningsloven.par24.begrundelsens_indhold": {
        "genererer_begrundelse",
        "indeholder_lovhenvisning",
        "angiver_hovedhensyn_ved_skon",
        "angiver_faktiske_omstaendigheder",
        "lovhenvisninger_verificerbare",
    },
    "offentlighedsloven.par13.dataudtraek_og_sammenstilling": {
        "laver_sammenstillinger",
        "enkle_kommandoer",
        "indeholder_personoplysninger",
        "anonymiseringskapacitet",
    },
}


# ---- Public API ------------------------------------------------------------


def map_ec_flags_to_tyr(flags: dict[str, Any]) -> PrefilledAssessment:
    """Hovedfunktion. Tag rejste flag fra EC-wizarden → producér en
    pre-fyldt RuleInput-tilstand til Bifrost's regelmotor.

    Vi behandler et flag som "rejst" hvis værdien er truthy (true, en
    ikke-tom string, eller et tal != 0). EC's flag_logic kan også sætte
    flag til false eksplicit — det betragter vi her som ikke-rejst.
    """
    raised = {k for k, v in (flags or {}).items() if _is_truthy(v)}

    signals: dict[str, bool] = {}
    predicates: dict[str, Any] = {}
    surfaced: set[str] = set()
    required_per_rule: dict[str, set[str]] = {}
    info_messages: list[str] = []
    matched: list[str] = []

    for flag in raised:
        mapping = EC_FLAG_MAPPING.get(flag)
        if mapping is None:
            # Ikke-mappet flag — stille spring over. /drift's stat-card
            # rapporterer hvor mange flag der ligger i denne kategori.
            continue
        matched.append(flag)
        for sig, val in mapping.set_signals.items():
            signals[sig] = val
        for pid, val in mapping.set_predicates.items():
            predicates[pid] = val
        for rid in mapping.surface_rules:
            surfaced.add(rid)
        for pid in mapping.require_predicates:
            # Find hvilke regler der ejer denne predikat-ID
            for rid, pids in _RULE_PREDICATES.items():
                if pid in pids and rid in surfaced:
                    required_per_rule.setdefault(rid, set()).add(pid)
        if mapping.info:
            info_messages.append(mapping.info)

    # Hvis intet flag matchede mapping → fald tilbage til fuld form
    fallback = len(matched) == 0

    summary = _build_summary(matched)

    return PrefilledAssessment(
        signals=dict(signals),
        predicates=dict(predicates),
        surfaced_rules=sorted(surfaced),
        required_predicates={rid: sorted(pids) for rid, pids in required_per_rule.items()},
        ec_summary=summary,
        matched_flags=matched,
        info_messages=info_messages,
        fallback_to_full_form=fallback,
    )


def _is_truthy(v: Any) -> bool:
    if v is None or v is False:
        return False
    if v is True:
        return True
    if isinstance(v, str):
        return v.strip().lower() not in ("", "false", "no", "0")
    if isinstance(v, (int, float)):
        return v != 0
    return bool(v)


def _build_summary(matched_flags: list[str]) -> str:
    """Producér 1-2 sætnings dansk resumé baseret på matched flag."""
    if not matched_flags:
        return (
            "EC's wizard udløste ingen flag der direkte styrer Bifrost's regelmotor. "
            "Udfyld vurderingsformen for fuld dansk vurdering."
        )

    parts: list[str] = []
    has_outofscope = any(
        f in {"flag_outofscope", "flag_outofscope_gpai", "flag_ai_system_outsidescope"}
        for f in matched_flags
    )
    has_prohibited = "flag_obligations_prohibitedsystems_result_output" in matched_flags
    has_highrisk = any(
        f in {
            "flag_risklevel_aisystem_highrisk_output",
            "flag_obligations_provider_results_high_risk",
            "flag_obligations_provider_section_b_results_high_risk",
        }
        for f in matched_flags
    )
    has_nohighrisk = "flag_risklevel_aisystem_nohighrisk_output" in matched_flags
    has_fria = "flag_fr_impact_assessment_deployer" in matched_flags
    has_transparency = any(
        f in {"flag_obligation_transparency_provider", "flag_obligation_transparency_deployer"}
        for f in matched_flags
    )

    role: str | None = None
    role_map = {
        "flag_ai_system_role_provider": "udbyder",
        "flag_ai_system_role_deployer": "idriftsætter",
        "flag_ai_system_role_distributor": "distributør",
        "flag_ai_system_role_importer": "importør",
        "flag_ai_system_role_authorisedrepre": "bemyndiget repræsentant",
        "flag_ai_system_role_productmanufacturer": "produktproducent",
        "flag_role_provider_gpai_output": "GPAI-udbyder",
    }
    for fid, label in role_map.items():
        if fid in matched_flags:
            role = label
            break

    if has_outofscope:
        parts.append("Systemet falder uden for AI-forordningens anvendelsesområde.")
    elif has_prohibited:
        parts.append("Mulig forbudt praksis (Artikel 5) — kræver bekræftelse i Bifrost.")
    elif has_highrisk:
        bits = ["højrisiko AI-system"]
        if role:
            bits.append(f"rolle: {role}")
        parts.append(f"Klassificeret som {' — '.join(bits)}.")
    elif has_nohighrisk:
        bit = "ikke-højrisiko AI-system"
        if role:
            bit += f" — rolle: {role}"
        parts.append(bit + ".")
    elif role:
        parts.append(f"Rolle identificeret: {role}.")

    if has_fria:
        parts.append("FRIA påkrævet inden idriftsættelse.")
    if has_transparency:
        parts.append("Artikel 50-transparenskrav udløst.")

    if not parts:
        parts.append("EC's wizard har klassificeret AI-systemet — se info-bokse for detaljer.")

    return " ".join(parts)


# ---- Stats til /drift ------------------------------------------------------


def mapping_stats() -> dict:
    """Statistik over EC-flag-mappingen — bruges af /drift's stat-card."""
    total_known_flags = EC_TOTAL_FLAGS
    mapped = len(EC_FLAG_MAPPING)
    active = sum(
        1
        for m in EC_FLAG_MAPPING.values()
        if m.set_signals or m.set_predicates or m.surface_rules
    )
    info_only = mapped - active
    by_category: dict[str, int] = {}
    for m in EC_FLAG_MAPPING.values():
        by_category[m.category] = by_category.get(m.category, 0) + 1

    # Sammenlign med faktiske flag i logic.json så vi opdager hvis EC har
    # tilføjet/fjernet flag siden mapperen blev curated.
    logic_path = CACHE_DIR / "logic.json"
    actual_flags: list[str] = []
    logic = _safe_read_json(logic_path) or {}
    if isinstance(logic.get("flags_logic"), dict):
        actual_flags = list(logic["flags_logic"].keys())

    actual_set = set(actual_flags)
    mapped_set = set(EC_FLAG_MAPPING.keys())
    unmapped_in_ec = sorted(actual_set - mapped_set)
    in_mapper_but_not_ec = sorted(mapped_set - actual_set)

    return {
        "total_known_flags": total_known_flags,
        "actual_flags_in_ec_logic": len(actual_flags),
        "mapped_flags": mapped,
        "active_mappings": active,
        "info_only_mappings": info_only,
        "by_category": by_category,
        "unmapped_in_ec": unmapped_in_ec,
        "in_mapper_but_not_ec": in_mapper_but_not_ec,
        "checked_at": datetime.now(UTC).isoformat(),
    }
