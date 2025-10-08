"""LangChain-baseret agent til juridisk research."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from langchain.agents import create_react_agent, AgentExecutor
from langchain.tools import tool
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain import hub
from pydantic import BaseModel, Field

from src.research.web_searcher import WebSearcher


class ResearchToolInput(BaseModel):
    """Inputskema for web_research værktøjet."""

    query: str = Field(..., description="Research-spørgsmålet der skal undersøges")
    focus_areas: Optional[List[str]] = Field(
        default=None,
        description="Liste over temaer der skal prioriteres (fx 'GDPR', 'Højrisiko AI')",
    )


@tool(args_schema=ResearchToolInput)
async def web_research(query: str, focus_areas: Optional[List[str]] = None) -> str:
    """Udfør juridisk research i autoritative kilder og returnér struktureret JSON.

    Args:
        query: Research-spørgsmålet der skal undersøges
        focus_areas: Liste over temaer der skal prioriteres (fx 'GDPR', 'Højrisiko AI')
    """
    async with WebSearcher() as searcher:
        result = await searcher.research_topic(query=query, focus_areas=focus_areas)
    return json.dumps(result, ensure_ascii=False)


def _default_chat_model(model_name: Optional[str] = None):
    """Returner en ChatOpenAI/ChatAnthropic instans baseret på konfiguration."""

    model_name = model_name or os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("RESEARCH_AGENT_TEMPERATURE", "0.2"))

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


def create_research_agent(model_name: Optional[str] = None) -> AgentExecutor:
    """Opret en LangChain-agent til juridisk research."""

    llm = _default_chat_model(model_name)
    tools = [web_research]

    # Brug standard ReAct prompt template
    prompt_template = """Du er en juridisk forsker med fokus på AI-compliance.
Brug værktøjet `web_research` til at indsamle kilder.
Analyser resultaterne, og svar KUN med JSON i følgende format:
{{"summary": "kort dansk sammenfatning", "key_findings": ["punkt"...], "recommended_actions": ["punkt"...], "sources": [{{"title": "...", "url": "...", "authority": "..."}}], "cross_references": [{{"statement": "...", "citations": [{{"title": "...", "url": "..."}}]}}]}}

Du har adgang til følgende værktøjer:

{tools}

Brug følgende format:

Question: input spørgsmålet
Thought: overvej hvad du skal gøre
Action: værktøjets navn fra [{tool_names}]
Action Input: input til værktøjet
Observation: værktøjets output
... (gentag Thought/Action/Observation N gange)
Thought: Jeg har nu nok information
Final Answer: dit endelige svar i JSON format

Question: {input}
Thought:{agent_scratchpad}"""

    prompt = PromptTemplate.from_template(prompt_template)

    agent = create_react_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=os.getenv("RESEARCH_AGENT_DEBUG") == "1")


async def run_research_agent(
    query: str,
    focus_areas: Optional[List[str]] = None,
    model_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Kør research-agenten og returner resultat som dict."""

    agent = create_research_agent(model_name)
    focus_text = f"Fokusområder: {', '.join(focus_areas)}" if focus_areas else ""
    payload = {
        "input": f"Research-spørgsmål: {query}. {focus_text}".strip(),
    }
    response = await agent.ainvoke(payload)
    output = response.get("output", "{}")
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {"summary": output}


__all__ = ["create_research_agent", "run_research_agent"]
