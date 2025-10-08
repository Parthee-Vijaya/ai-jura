"""LangChain-baseret agent til hurtig compliance-vurdering."""

from __future__ import annotations

import json
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
    """Kør agenten og returner JSON-output."""

    agent = create_quick_check_agent(model_name)
    payload = {
        "input": (
            "Udfør en hurtig compliance screening for følgende system. "
            f"Beskrivelse: {description}. AI-type: {ai_type}. Fagområde: {sector}. "
            f"Behandler persondata: {behandler_persondata}. Automatiserede beslutninger: {automatiserede_beslutninger}."
        )
    }
    response = agent.invoke(payload)
    output = response.get("output", "{}")
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {"risk_summary": output}


__all__ = ["create_quick_check_agent", "run_quick_check_agent"]
