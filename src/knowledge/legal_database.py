"""
Omfattende juridisk database med alle relevante AI & Data Protection kilder
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import json


@dataclass
class LegalSource:
    """Juridisk kilde"""
    id: str
    title: str
    type: str  # 'regulation', 'directive', 'guideline', 'decision', 'opinion', 'recommendation'
    authority: str
    url: str
    pdf_url: Optional[str]
    adoption_date: Optional[datetime]
    effective_date: Optional[datetime]
    status: str  # 'active', 'proposed', 'amended', 'repealed'
    summary: str
    key_provisions: List[str]
    relevant_articles: List[Dict[str, str]]
    keywords: List[str]
    language: str = 'da'
    last_updated: datetime = datetime.now()


class LegalDatabase:
    """
    Omfattende database med alle juridiske kilder relateret til AI og data protection
    """

    def __init__(self):
        self.sources = self._initialize_legal_sources()

    def _initialize_legal_sources(self) -> Dict[str, LegalSource]:
        """Initialiserer alle juridiske kilder"""
        sources = {}

        # EU AI Act
        sources['eu_ai_act'] = LegalSource(
            id='eu_ai_act',
            title='Forordning (EU) 2024/1689 om kunstig intelligens (AI-loven)',
            type='regulation',
            authority='EU',
            url='https://eur-lex.europa.eu/legal-content/DA/TXT/?uri=CELEX:32024R1689',
            pdf_url='https://eur-lex.europa.eu/legal-content/DA/TXT/PDF/?uri=CELEX:32024R1689',
            adoption_date=datetime(2024, 6, 13),
            effective_date=datetime(2024, 8, 1),
            status='active',
            summary='EU-forordning der regulerer udvikling, markedsføring og brug af AI-systemer i EU med fokus på sikkerhed og grundlæggende rettigheder.',
            key_provisions=[
                'Forbud mod uacceptable AI-praksisser (Artikel 5)',
                'Krav til højrisiko AI-systemer (Artikel 6-51)',
                'Gennemsigtighedsforpligtelser for visse AI-systemer (Artikel 52)',
                'Governance og håndhævelse (Artikel 56-91)',
                'Sanktioner og bøder (Artikel 99)'
            ],
            relevant_articles=[
                {'article': 'Artikel 5', 'content': 'Forbudte AI-praksisser'},
                {'article': 'Artikel 6-15', 'content': 'Krav til højrisiko AI-systemer'},
                {'article': 'Artikel 22', 'content': 'Automatiserede beslutninger'},
                {'article': 'Artikel 52', 'content': 'Gennemsigtighedsforpligtelser'},
                {'article': 'Artikel 99', 'content': 'Bøder og sanktioner'}
            ],
            keywords=['ai act', 'kunstig intelligens', 'højrisiko', 'forbudt', 'gennemsigtighed', 'governance']
        )

        # GDPR
        sources['gdpr'] = LegalSource(
            id='gdpr',
            title='Forordning (EU) 2016/679 om beskyttelse af fysiske personer (GDPR)',
            type='regulation',
            authority='EU',
            url='https://eur-lex.europa.eu/legal-content/DA/TXT/?uri=CELEX:32016R0679',
            pdf_url='https://eur-lex.europa.eu/legal-content/DA/TXT/PDF/?uri=CELEX:32016R0679',
            adoption_date=datetime(2016, 4, 27),
            effective_date=datetime(2018, 5, 25),
            status='active',
            summary='Databeskyttelsesforordningen der beskytter fysiske personers grundlæggende ret til beskyttelse af personoplysninger.',
            key_provisions=[
                'Principper for behandling af personoplysninger (Artikel 5)',
                'Retsgrundlag for behandling (Artikel 6)',
                'Automatiseret individuel beslutningstagning (Artikel 22)',
                'Den registreredes rettigheder (Artikel 12-23)',
                'Konsekvensanalyse for databeskyttelse (Artikel 35)'
            ],
            relevant_articles=[
                {'article': 'Artikel 5', 'content': 'Principper for behandling'},
                {'article': 'Artikel 6', 'content': 'Retsgrundlag'},
                {'article': 'Artikel 22', 'content': 'Automatiserede beslutninger'},
                {'article': 'Artikel 35', 'content': 'DPIA krav'},
                {'article': 'Artikel 83', 'content': 'Administrative bøder'}
            ],
            keywords=['gdpr', 'databeskyttelse', 'personoplysninger', 'automatiserede beslutninger', 'dpia']
        )

        # Dansk Databeskyttelseslov
        sources['danish_data_act'] = LegalSource(
            id='danish_data_act',
            title='Lov om supplerende bestemmelser til forordning om beskyttelse af fysiske personer',
            type='law',
            authority='Danmark',
            url='https://www.retsinformation.dk/eli/lta/2018/502',
            pdf_url=None,
            adoption_date=datetime(2018, 5, 23),
            effective_date=datetime(2018, 5, 25),
            status='active',
            summary='Dansk lov der supplerer GDPR med nationale bestemmelser om databeskyttelse.',
            key_provisions=[
                'Datatilsynets beføjelser og opgaver',
                'Nationale undtagelser fra GDPR',
                'Straffebestemmelser',
                'Særlige bestemmelser for offentlige myndigheder'
            ],
            relevant_articles=[
                {'article': '§ 1', 'content': 'Lovens anvendelsesområde'},
                {'article': '§ 24-31', 'content': 'Datatilsynets opgaver'},
                {'article': '§ 41', 'content': 'Straffebestemmelser'}
            ],
            keywords=['databeskyttelsesloven', 'datatilsynet', 'danske regler']
        )

        # EDPB Guidelines
        sources['edpb_ai_guidelines'] = LegalSource(
            id='edpb_ai_guidelines',
            title='EDPB Guidelines on Automated Decision-Making and Profiling',
            type='guideline',
            authority='EDPB',
            url='https://edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-automated-individual-decision-making-and-profiling_en',
            pdf_url='https://edpb.europa.eu/sites/default/files/files/file1/edpb_guidelines_201904_article_22_final.pdf',
            adoption_date=datetime(2017, 10, 3),
            effective_date=datetime(2018, 2, 6),
            status='active',
            summary='EDPB vejledning om automatiserede individuelle beslutninger og profilering under GDPR.',
            key_provisions=[
                'Fortolkning af Artikel 22 GDPR',
                'Krav til automatiserede beslutninger',
                'Menneskeligt indgreb og oversight',
                'Profilering og konsekvenser'
            ],
            relevant_articles=[
                {'article': 'Section 3', 'content': 'Artikel 22 scope'},
                {'article': 'Section 4', 'content': 'Meaningful human review'},
                {'article': 'Section 5', 'content': 'Profiling requirements'}
            ],
            keywords=['edpb', 'automatiserede beslutninger', 'profilering', 'artikel 22']
        )

        # Datatilsynet AI Vejledning
        sources['datatilsynet_ai'] = LegalSource(
            id='datatilsynet_ai',
            title='Vejledning om kunstig intelligens og databeskyttelse',
            type='guideline',
            authority='Datatilsynet',
            url='https://www.datatilsynet.dk/media/dokumenter/vejledning-til-gdpr/kunstig-intelligens-og-databeskyttelse.pdf',
            pdf_url='https://www.datatilsynet.dk/media/dokumenter/vejledning-til-gdpr/kunstig-intelligens-og-databeskyttelse.pdf',
            adoption_date=datetime(2023, 3, 15),
            effective_date=datetime(2023, 3, 15),
            status='active',
            summary='Datatilsynets vejledning om anvendelse af GDPR på kunstig intelligens og AI-systemer.',
            key_provisions=[
                'AI og personoplysninger',
                'Automatiserede beslutninger i AI',
                'DPIA for AI-systemer',
                'Gennemsigtighed og forklarbarhed',
                'AI i ansættelsesprocesser'
            ],
            relevant_articles=[
                {'article': 'Kapitel 3', 'content': 'AI og automatiserede beslutninger'},
                {'article': 'Kapitel 4', 'content': 'DPIA for AI'},
                {'article': 'Kapitel 5', 'content': 'Gennemsigtighed i AI'}
            ],
            keywords=['datatilsynet', 'ai vejledning', 'dansk implementering']
        )

        # EU Commission AI Act Implementation
        sources['ai_act_implementation'] = LegalSource(
            id='ai_act_implementation',
            title='Commission Guidelines on AI Act Implementation',
            type='guideline',
            authority='EU Commission',
            url='https://ec.europa.eu/docsroom/documents/58649',
            pdf_url='https://ec.europa.eu/docsroom/documents/58649/attachments/1/translations/en/renditions/native',
            adoption_date=datetime(2024, 7, 15),
            effective_date=datetime(2024, 7, 15),
            status='active',
            summary='EU-Kommissionens implementeringsvejledning til AI Act med praktiske guidelines.',
            key_provisions=[
                'Klassifikation af AI-systemer',
                'Conformity assessment procedurer',
                'CE-mærkning krav',
                'Notified bodies og akkreditering',
                'Markedsovervågning'
            ],
            relevant_articles=[
                {'article': 'Section 2', 'content': 'Risk classification'},
                {'article': 'Section 4', 'content': 'Conformity assessment'},
                {'article': 'Section 6', 'content': 'Market surveillance'}
            ],
            keywords=['ai act implementation', 'conformity assessment', 'ce marking']
        )

        # Digital Services Act
        sources['dsa'] = LegalSource(
            id='dsa',
            title='Forordning (EU) 2022/2065 om digitale tjenester (Digital Services Act)',
            type='regulation',
            authority='EU',
            url='https://eur-lex.europa.eu/legal-content/DA/TXT/?uri=CELEX:32022R2065',
            pdf_url='https://eur-lex.europa.eu/legal-content/DA/TXT/PDF/?uri=CELEX:32022R2065',
            adoption_date=datetime(2022, 10, 19),
            effective_date=datetime(2024, 2, 17),
            status='active',
            summary='EU-forordning om digitale tjenester med særlige bestemmelser for meget store online platforme.',
            key_provisions=[
                'Risikovurdering og risikominimering',
                'Algoritmiske anbefalingssystemer',
                'Gennemsigtighed i online annoncering',
                'Uafhængig revision og compliance'
            ],
            relevant_articles=[
                {'article': 'Artikel 34', 'content': 'Systemic risk assessment'},
                {'article': 'Artikel 38', 'content': 'Recommender systems'},
                {'article': 'Artikel 42', 'content': 'Independent auditing'}
            ],
            keywords=['dsa', 'digitale tjenester', 'algoritmer', 'platforme']
        )

        # ISO/IEC Standards
        sources['iso_23053'] = LegalSource(
            id='iso_23053',
            title='ISO/IEC 23053:2022 Framework for AI systems using machine learning',
            type='standard',
            authority='ISO/IEC',
            url='https://www.iso.org/standard/74438.html',
            pdf_url=None,
            adoption_date=datetime(2022, 8, 1),
            effective_date=datetime(2022, 8, 1),
            status='active',
            summary='International standard der giver framework for AI-systemer der bruger machine learning.',
            key_provisions=[
                'AI system lifecycle',
                'Risk management for AI',
                'Data quality requirements',
                'Human oversight principles',
                'Continuous monitoring'
            ],
            relevant_articles=[
                {'article': 'Clause 5', 'content': 'AI system concepts'},
                {'article': 'Clause 7', 'content': 'Risk management'},
                {'article': 'Clause 9', 'content': 'Data management'}
            ],
            keywords=['iso standard', 'ai framework', 'machine learning', 'risk management']
        )

        # IEEE Ethics Guidelines
        sources['ieee_ethics'] = LegalSource(
            id='ieee_ethics',
            title='IEEE Ethically Aligned Design for Autonomous and Intelligent Systems',
            type='guideline',
            authority='IEEE',
            url='https://standards.ieee.org/industry-connections/ec/autonomous-systems.html',
            pdf_url='https://standards.ieee.org/content/dam/ieee-standards/standards/web/documents/other/ead_v2.pdf',
            adoption_date=datetime(2019, 3, 15),
            effective_date=datetime(2019, 3, 15),
            status='active',
            summary='IEEE guidelines for etisk design af autonome og intelligente systemer.',
            key_provisions=[
                'Human values in AI design',
                'Algorithmic bias mitigation',
                'Transparency and explainability',
                'Privacy and data agency',
                'Responsibility and accountability'
            ],
            relevant_articles=[
                {'article': 'Chapter 2', 'content': 'Well-being principle'},
                {'article': 'Chapter 3', 'content': 'Human agency principle'},
                {'article': 'Chapter 4', 'content': 'Transparency principle'}
            ],
            keywords=['ieee', 'ai ethics', 'ethically aligned design', 'autonomous systems']
        )

        # Product Liability Directive
        sources['product_liability'] = LegalSource(
            id='product_liability',
            title='Direktiv 85/374/EØF om produktansvar',
            type='directive',
            authority='EU',
            url='https://eur-lex.europa.eu/legal-content/DA/TXT/?uri=CELEX:31985L0374',
            pdf_url='https://eur-lex.europa.eu/legal-content/DA/TXT/PDF/?uri=CELEX:31985L0374',
            adoption_date=datetime(1985, 7, 25),
            effective_date=datetime(1988, 7, 30),
            status='active',
            summary='EU-direktiv om producentens objektive ansvar for skadelige produkter.',
            key_provisions=[
                'Objektivt produktansvar',
                'Bevisbyrdens fordeling',
                'Undtagelser og grænser for ansvar',
                'Erstatningskrav og frister'
            ],
            relevant_articles=[
                {'article': 'Artikel 1', 'content': 'Producentens ansvar'},
                {'article': 'Artikel 4', 'content': 'Bevisbyrde'},
                {'article': 'Artikel 7', 'content': 'Undtagelser'}
            ],
            keywords=['produktansvar', 'objektivt ansvar', 'ai produkter']
        )

        # Danish AI Strategy
        sources['danish_ai_strategy'] = LegalSource(
            id='danish_ai_strategy',
            title='Danmarks Nationale Strategi for Kunstig Intelligens',
            type='policy',
            authority='Erhvervsministeriet',
            url='https://em.dk/publikationer/2019/marts/national-strategi-for-kunstig-intelligens/',
            pdf_url='https://em.dk/media/13078/national-strategi-for-kunstig-intelligens.pdf',
            adoption_date=datetime(2019, 3, 1),
            effective_date=datetime(2019, 3, 1),
            status='active',
            summary='Danmarks nationale strategi for udvikling og anvendelse af kunstig intelligens.',
            key_provisions=[
                'Etiske principper for AI',
                'AI i den offentlige sektor',
                'Forsk­ning og innovation',
                'Kompetenceudvikling',
                'Internationalt samarbejde'
            ],
            relevant_articles=[
                {'article': 'Kapitel 2', 'content': 'Etiske principper'},
                {'article': 'Kapitel 3', 'content': 'Offentlig AI'},
                {'article': 'Kapitel 4', 'content': 'Innovation og forskning'}
            ],
            keywords=['dansk ai strategi', 'nationale principper', 'offentlig ai']
        )

        return sources

    def get_all_sources(self) -> List[Dict[str, Any]]:
        """Hent alle juridiske kilder"""
        return [asdict(source) for source in self.sources.values()]

    def get_sources_by_type(self, source_type: str) -> List[Dict[str, Any]]:
        """Hent kilder efter type"""
        filtered = [source for source in self.sources.values() if source.type == source_type]
        return [asdict(source) for source in filtered]

    def get_sources_by_authority(self, authority: str) -> List[Dict[str, Any]]:
        """Hent kilder efter myndighed"""
        filtered = [source for source in self.sources.values() if source.authority == authority]
        return [asdict(source) for source in filtered]

    def search_sources(self, query: str) -> List[Dict[str, Any]]:
        """Søg i kilder efter nøgleord"""
        query_lower = query.lower()
        matches = []

        for source in self.sources.values():
            # Søg i titel, sammenfatning og nøgleord
            if (query_lower in source.title.lower() or
                query_lower in source.summary.lower() or
                any(query_lower in keyword.lower() for keyword in source.keywords)):
                matches.append(asdict(source))

        return matches

    def get_source_by_id(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Hent specifik kilde efter ID"""
        source = self.sources.get(source_id)
        return asdict(source) if source else None

    def get_eu_sources(self) -> List[Dict[str, Any]]:
        """Hent alle EU-kilder"""
        eu_authorities = ['EU', 'EU Commission', 'EDPB']
        filtered = [source for source in self.sources.values() if source.authority in eu_authorities]
        return [asdict(source) for source in filtered]

    def get_danish_sources(self) -> List[Dict[str, Any]]:
        """Hent alle danske kilder"""
        danish_authorities = ['Danmark', 'Datatilsynet', 'Erhvervsministeriet']
        filtered = [source for source in self.sources.values() if source.authority in danish_authorities]
        return [asdict(source) for source in filtered]

    def get_standards_and_guidelines(self) -> List[Dict[str, Any]]:
        """Hent standarder og vejledninger"""
        types = ['standard', 'guideline']
        filtered = [source for source in self.sources.values() if source.type in types]
        return [asdict(source) for source in filtered]

    def get_active_regulations(self) -> List[Dict[str, Any]]:
        """Hent aktive forordninger og direktiver"""
        types = ['regulation', 'directive', 'law']
        filtered = [source for source in self.sources.values()
                   if source.type in types and source.status == 'active']
        return [asdict(source) for source in filtered]


# Singleton instance
legal_db = LegalDatabase()