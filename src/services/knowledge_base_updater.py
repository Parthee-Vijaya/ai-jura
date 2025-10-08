"""Automatisk vidensbase opdatering service.

Denne service:
1. Henter nye termer fra research queries
2. Bruger LLM til at generere definitioner
3. Opdaterer vidensbasen automatisk
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from src.research.web_searcher import WebSearcher

logger = logging.getLogger(__name__)

# Path til vidensbase fil
KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent.parent / "data" / "knowledge_base.json"


def _default_chat_model(model_name: Optional[str] = None):
    """Opret LLM model til term generation."""
    model_name = model_name or os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("KB_UPDATER_TEMPERATURE", "0.3"))

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


def load_knowledge_base() -> List[Dict[str, Any]]:
    """Indlæs eksisterende vidensbase."""
    if not KNOWLEDGE_BASE_PATH.exists():
        KNOWLEDGE_BASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        return []

    try:
        with open(KNOWLEDGE_BASE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.warning(f"Failed to load knowledge base: {e}")
        return []


def save_knowledge_base(items: List[Dict[str, Any]]) -> None:
    """Gem vidensbase til fil."""
    KNOWLEDGE_BASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(KNOWLEDGE_BASE_PATH, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    logger.info(f"Saved {len(items)} items to knowledge base")


async def search_for_new_terms(topics: List[str]) -> List[Dict[str, Any]]:
    """Søg efter nye termer og definitioner på nettet.

    Args:
        topics: Liste af emner at søge efter (fx ["AI Act", "GDPR", "DPIA"])

    Returns:
        Liste af nye termer med definitioner og kilder
    """
    new_terms = []

    try:
        async with WebSearcher() as searcher:
            for topic in topics:
                # Søg efter definitioner og forklaringer
                query = f"{topic} definition compliance meaning explanation"

                search_results = await searcher.search(
                    query=query,
                    max_results=3,
                    focus_domains=['eur-lex.europa.eu', 'datatilsynet.dk', 'edpb.europa.eu', 'retsinformation.dk']
                )

                if not search_results:
                    continue

                # Brug LLM til at generere definition
                llm = _default_chat_model()

                # Byg kontekst fra søgeresultater
                context = "\n\n".join([
                    f"Kilde: {source.title}\n{source.content[:500]}..."
                    for source in search_results[:2]
                ])

                prompt = f"""Baseret på følgende information, giv en KORT og PRÆCIS definition af "{topic}" (max 2-3 sætninger):

{context}

Svar kun med selve definitionen, ingen overskrifter eller formatering.
Definitionen skal være på dansk og juridisk præcis."""

                try:
                    response = llm.invoke(prompt)
                    definition = response.content if hasattr(response, 'content') else str(response)

                    new_terms.append({
                        "term": topic,
                        "definition": definition.strip(),
                        "category": "legal",  # Default kategori
                        "sources": [
                            {
                                "title": source.title,
                                "url": source.url,
                                "authority": source.authority
                            }
                            for source in search_results[:2]
                        ],
                        "added_date": datetime.now().isoformat(),
                        "auto_generated": True
                    })

                    logger.info(f"Generated definition for term: {topic}")

                except Exception as e:
                    logger.warning(f"Failed to generate definition for {topic}: {e}")
                    continue

    except Exception as e:
        logger.error(f"Failed to search for new terms: {e}")

    return new_terms


async def extract_terms_from_queries(queries: List[str]) -> List[str]:
    """Ekstraher relevante termer fra brugerforespørgsler ved hjælp af LLM.

    Args:
        queries: Liste af brugerforespørgsler fra research

    Returns:
        Liste af ekstraherede termer der kunne være relevante for vidensbasen
    """
    if not queries:
        return []

    llm = _default_chat_model()

    # Sammensæt queries til LLM prompt
    queries_text = "\n".join([f"- {q}" for q in queries[:20]])  # Begræns til 20 seneste

    prompt = f"""Analyser følgende brugerforespørgsler om AI compliance og GDPR:

{queries_text}

Identificer 5-10 vigtige juridiske eller tekniske termer der ofte nævnes eller som kunne være relevante at tilføje til en vidensbase om AI Act og GDPR compliance.

Returner KUN termerne, én per linje, ingen numre eller forklaring.
Termer skal være på dansk eller engelsk (original terminologi).
Fokuser på termer der ikke er helt almindelige (fx ikke "computer" eller "data", men specifikt "DPIA", "risikovurdering", "højrisiko AI-systemer" osv.)."""

    try:
        response = llm.invoke(prompt)
        terms_text = response.content if hasattr(response, 'content') else str(response)

        # Parse termer fra response
        terms = [
            line.strip().lstrip('-•*').strip()
            for line in terms_text.split('\n')
            if line.strip() and not line.strip().startswith('#')
        ]

        # Filtrer tomme linjer og for korte termer
        terms = [t for t in terms if len(t) > 3]

        logger.info(f"Extracted {len(terms)} terms from {len(queries)} queries")
        return terms[:10]  # Max 10 termer

    except Exception as e:
        logger.error(f"Failed to extract terms from queries: {e}")
        return []


async def update_knowledge_base(recent_queries: Optional[List[str]] = None) -> Dict[str, Any]:
    """Opdater vidensbasen automatisk.

    Args:
        recent_queries: Liste af seneste brugerforespørgsler (valgfrit)

    Returns:
        Dict med stats om opdateringen
    """
    logger.info("Starting automatic knowledge base update")

    # Load eksisterende vidensbase
    current_items = load_knowledge_base()
    existing_terms = {item['term'].lower() for item in current_items}

    # Hvis vi har recent queries, ekstraher termer derfra
    if recent_queries:
        extracted_terms = await extract_terms_from_queries(recent_queries)
    else:
        # Default termer hvis ingen queries
        extracted_terms = [
            "AI Act", "DPIA", "Højrisiko AI-system", "Gennemsigtighed",
            "Risikovurdering", "Conformity assessment", "EU AI Office",
            "Fundamental rights impact assessment", "Data minimering"
        ]

    # Filtrer termer der allerede findes
    new_terms_to_search = [
        term for term in extracted_terms
        if term.lower() not in existing_terms
    ]

    if not new_terms_to_search:
        logger.info("No new terms to add")
        return {
            "success": True,
            "new_terms_count": 0,
            "total_terms_count": len(current_items),
            "message": "Ingen nye termer fundet"
        }

    logger.info(f"Searching for definitions for {len(new_terms_to_search)} new terms")

    # Søg efter definitioner
    new_items = await search_for_new_terms(new_terms_to_search[:5])  # Max 5 nye termer per opdatering

    # Tilføj nye items til vidensbase
    updated_items = current_items + new_items

    # Gem opdateret vidensbase
    if new_items:
        save_knowledge_base(updated_items)

    return {
        "success": True,
        "new_terms_count": len(new_items),
        "total_terms_count": len(updated_items),
        "new_terms": [item['term'] for item in new_items],
        "message": f"Tilføjet {len(new_items)} nye termer til vidensbasen"
    }


def run_knowledge_base_update(recent_queries: Optional[List[str]] = None) -> Dict[str, Any]:
    """Synkron wrapper til at køre knowledge base opdatering."""
    return asyncio.run(update_knowledge_base(recent_queries))


__all__ = [
    "update_knowledge_base",
    "run_knowledge_base_update",
    "load_knowledge_base",
    "save_knowledge_base"
]
