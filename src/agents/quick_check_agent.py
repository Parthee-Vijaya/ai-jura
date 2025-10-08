"""LangChain-baseret agent til hurtig compliance-vurdering."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Dict, Optional

from langchain.agents import create_react_agent, AgentExecutor
from langchain.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field

from src.core.models import ProjectInput
from src.compliance.ai_act_checker import AIActComplianceChecker
from src.compliance.gdpr_checker import GDPRComplianceChecker
from src.research.web_searcher import WebSearcher

logger = logging.getLogger(__name__)

_ai_act_checker = AIActComplianceChecker()
_gdpr_checker = GDPRComplianceChecker()


class QuickCheckToolInput(BaseModel):
    """Inputskema for hurtig compliance-vurdering."""

    description: str = Field(..., description="Kort beskrivelse af AI-systemet")
    ai_type: str = Field(..., description="AI-typen (fx generative_ai, nlp)")
    sector: str = Field(..., description="Fagområde/forretningsområde")
    behandler_persondata: bool = Field(False, description="Om systemet behandler persondata")
    automatiserede_beslutninger: bool = Field(False, description="Om systemet træffer automatiserede beslutninger")


@tool(args_schema=QuickCheckToolInput)
def quick_compliance_check(
    description: str,
    ai_type: str,
    sector: str,
    behandler_persondata: bool = False,
    automatiserede_beslutninger: bool = False,
) -> str:
    """Udfør hurtig vurdering af AI Act-risiko og GDPR-relevans.

    Args:
        description: Beskrivelse af AI-systemet
        ai_type: AI-typen (fx generative_ai, nlp)
        sector: Fagområde/forretningsområde
        behandler_persondata: Om systemet behandler persondata
        automatiserede_beslutninger: Om systemet træffer automatiserede beslutninger
    """

    project = ProjectInput(
        name="Hurtig Agent Vurdering",
        description=description,
        ai_type=ai_type,
        sector=sector,
        personal_data=behandler_persondata,
        automated_decision_making=automatiserede_beslutninger,
    )

    risk_level, reasons = _ai_act_checker.assess_risk_level(project)
    gdpr_relevant = behandler_persondata
    gdpr_high_risk = _gdpr_checker._requires_dpia(project) if gdpr_relevant else False

    result = {
        "ai_act": {
            "risk_level": risk_level.value,
            "reasons": reasons,
        },
        "gdpr": {
            "relevant": gdpr_relevant,
            "requires_dpia": gdpr_high_risk,
        },
        "needs_full_assessment": risk_level in {"high", "unacceptable"} or gdpr_high_risk,
        "recommendations": _generate_recommendations(risk_level.value, gdpr_relevant, gdpr_high_risk),
    }
    return json.dumps(result, ensure_ascii=False)


async def _search_precedents(description: str, ai_type: str, sector: str) -> Dict[str, Any]:
    """Søg efter relevante præcedens og afgørelser på nettet."""
    try:
        async with WebSearcher() as searcher:
            # Byg søgequery med AI Act og GDPR fokus
            query = f"AI Act GDPR {ai_type} {sector} afgørelser præcedens compliance"

            # Søg med fokus på autoritative kilder
            search_results = await searcher.search(
                query=query,
                max_results=5,
                focus_domains=['eur-lex.europa.eu', 'datatilsynet.dk', 'edpb.europa.eu', 'retsinformation.dk']
            )

            if not search_results:
                return {"precedents": [], "summary": "Ingen relevante præcedens fundet"}

            # Brug LLM til at opsummere findings
            summary = await searcher.summarize_with_citations(
                query=f"Hvad siger præcedens og afgørelser om {description}?",
                sources=search_results[:3],
                max_length=200
            )

            precedents = [
                {
                    "title": source.title,
                    "url": source.url,
                    "authority": source.authority,
                    "relevance": source.relevance_score
                }
                for source in search_results[:3]
            ]

            return {
                "precedents": precedents,
                "summary": summary
            }
    except Exception as e:
        logger.warning(f"Web search failed: {e}")
        return {"precedents": [], "summary": "Søgning ikke tilgængelig"}


def _generate_recommendations(risk_level: str, gdpr_relevant: bool, gdpr_high_risk: bool) -> list[str]:
    recs: list[str] = []
    if risk_level in {"unacceptable", "high"}:
        recs.append("Planlæg en fuld compliance control for højrisikosystemet.")
        recs.append("Udarbejd teknisk dokumentation og kvalitetsstyring før idriftsættelse.")
    if gdpr_relevant:
        recs.append("Sørg for lovligt behandlingsgrundlag og informationspligt.")
    if gdpr_high_risk:
        recs.append("Gennemfør en DPIA i samarbejde med databeskyttelsesrådgiver.")
    if not recs:
        recs.append("Fortsæt monitorering og dokumentér governance-tiltag.")
    return recs


def _default_chat_model(model_name: Optional[str] = None):
    model_name = model_name or os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("QUICKCHECK_AGENT_TEMPERATURE", "0.1"))

    if "claude" in model_name.lower():
        return ChatAnthropic(
            model=model_name,
            temperature=temperature,
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )

    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=os.getenv("OPENAI_API_KEY"),
    )


def create_quick_check_agent(model_name: Optional[str] = None) -> AgentExecutor:
    """Opret LangChain-agent til hurtig compliance screening."""

    llm = _default_chat_model(model_name)
    tools = [quick_compliance_check]

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Du er en AI-compliance assistent. Brug `quick_compliance_check` til at hente vurdering. "
                'Svar KUN med JSON: {"risk_summary": "...", "ai_act": {...}, "gdpr": {...}, "recommendations": ["..."]}.'
            ),
            ("user", "{input}"),
        ]
    )

    agent = create_react_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=os.getenv("QUICKCHECK_AGENT_DEBUG") == "1")


def run_quick_check_agent(
    description: str,
    ai_type: str,
    sector: str,
    behandler_persondata: bool = False,
    automatiserede_beslutninger: bool = False,
    model_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Kør agenten og returner JSON-output med web research."""

    # 1. Udfør grundlæggende compliance check
    project = ProjectInput(
        name="Hurtig Agent Vurdering",
        description=description,
        ai_type=ai_type,
        sector=sector,
        personal_data=behandler_persondata,
        automated_decision_making=automatiserede_beslutninger,
    )

    risk_level, reasons = _ai_act_checker.assess_risk_level(project)
    gdpr_relevant = behandler_persondata
    gdpr_high_risk = _gdpr_checker._requires_dpia(project) if gdpr_relevant else False

    # 2. Søg efter præcedens og afgørelser (async)
    try:
        precedents_data = asyncio.run(_search_precedents(description, ai_type, sector))
    except Exception as e:
        logger.warning(f"Precedent search failed: {e}")
        precedents_data = {"precedents": [], "summary": "Søgning ikke tilgængelig"}

    # 3. Generer kortfattet svar med LLM
    llm = _default_chat_model(model_name)
    summary_prompt = f"""Baseret på følgende compliance analyse, giv et KORT og PRÆCIST svar (max 3-4 linjer):

AI System: {description}
AI Act Risiko: {risk_level.value}
GDPR Relevant: {gdpr_relevant}
Præcedens: {precedents_data.get('summary', 'Ingen fundet')}

Giv et kortfattet svar der:
1. Angiver risikoniveau
2. Fremhæver vigtigste compliance krav
3. Nævner relevante præcedens hvis fundet

Svar kun med tekst, ingen overskrifter eller formatering."""

    try:
        llm_response = llm.invoke(summary_prompt)
        short_summary = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)
    except Exception as e:
        logger.warning(f"LLM summary failed: {e}")
        short_summary = f"Systemet vurderes som {risk_level.value} risiko under AI Act."

    # 4. Byg komplet response
    result = {
        "ai_act": {
            "risk_level": risk_level.value,
            "reasons": reasons,
        },
        "gdpr": {
            "relevant": gdpr_relevant,
            "requires_dpia": gdpr_high_risk,
        },
        "needs_full_assessment": risk_level in {"high", "unacceptable"} or gdpr_high_risk,
        "recommendations": _generate_recommendations(risk_level.value, gdpr_relevant, gdpr_high_risk),
        "precedents": precedents_data.get("precedents", []),
        "precedents_summary": precedents_data.get("summary", ""),
        "short_summary": short_summary.strip()
    }

    return result


__all__ = ["create_quick_check_agent", "run_quick_check_agent"]
