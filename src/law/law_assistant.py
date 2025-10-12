"""
Law AI Assistant - Generate AI answers with citations using Azure OpenAI
"""

import os
import logging
from typing import List, Dict, Any, Optional
import asyncio
import aiohttp
import json
from dotenv import load_dotenv

from .law_data import search_laws, get_law_by_slug

load_dotenv()
logger = logging.getLogger(__name__)


class LawAssistant:
    """AI assistant for Danish law queries using Azure OpenAI"""

    def __init__(self):
        # Azure OpenAI credentials
        self.azure_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        self.azure_api_key = os.getenv('AZURE_OPENAI_API_KEY')
        self.azure_deployment = os.getenv('AZURE_DEPLOYMENT_NAME', 'gpt-4o-mini')
        self.azure_api_version = os.getenv('OPENAI_API_VERSION', '2024-02-15-preview')

        # Fallback to standard OpenAI
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

        self.use_azure = bool(self.azure_endpoint and self.azure_api_key)

        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def ask(
        self,
        query: str,
        category: Optional[str] = None,
        max_sources: int = 5
    ) -> Dict[str, Any]:
        """
        Generate AI answer for legal query with citations

        Args:
            query: User's legal question
            category: Optional category filter
            max_sources: Max number of source laws to use

        Returns:
            Dict with: answer, confidence, key_points, sources, citations
        """
        # Step 1: Search for relevant laws
        logger.info(f"Searching for laws matching query: {query}")
        search_results = search_laws(query, category=category, limit=max_sources)

        if not search_results:
            return {
                'answer': 'Jeg kunne ikke finde relevante love for dit spørgsmål. Prøv at omformulere eller søge bredere.',
                'confidence': 0.0,
                'key_points': [],
                'sources': [],
                'citations': []
            }

        sources = [result['law'] for result in search_results]

        # Step 2: Generate AI answer with Azure OpenAI
        logger.info(f"Generating AI answer using {len(sources)} sources")
        ai_response = await self._generate_answer_with_llm(query, sources)

        return ai_response

    async def _generate_answer_with_llm(
        self,
        query: str,
        sources: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate answer using Azure OpenAI with RAG pattern"""

        if not self.session:
            raise RuntimeError("LawAssistant must be used as async context manager")

        # Build context from sources
        context_parts = []
        for idx, source in enumerate(sources, start=1):
            title = source.get('title', 'Ukendt lov')
            summary = source.get('summary', '')
            content = source.get('content', '')
            law_number = source.get('lawNumber', '')

            # Use more content - we now have full law texts (but not too much to avoid timeout)
            content_excerpt = content[:2000] if content else summary

            context_parts.append(f"""
[{idx}] {title}
{f"Lovnummer: {law_number}" if law_number else ""}
Resumé: {summary}
Indhold: {content_excerpt}
""")

        context = "\n---\n".join(context_parts)

        # System prompt
        system_prompt = """Du er en dansk juridisk AI-assistent. Din opgave er at besvare juridiske spørgsmål baseret på de love, du får oplyst.

Du har adgang til omfattende lovtekster fra de relevante love. Brug denne information til at give detaljerede og præcise svar.

Retningslinjer:
- Svar på dansk
- Forklar hvilke love der er relevante og hvorfor
- Referer til specifikke love ved navn, lovnummer og paragraf
- Brug citations [1], [2] etc. til at henvise til kilderne
- Citér relevante lovparagraffer når det er passende
- Giv konkrete svar baseret på lovteksten
- Giv 3-5 nøglepunkter om hvad loven siger specifikt om emnet
- Inkluder en konfidensscore (0.8-0.95) baseret på hvor præcist lovteksten besvarer spørgsmålet
- For komplekse juridiske spørgsmål, anbefal at konsultere en advokat

Format dit svar som JSON:
{
  "answer": "Baseret på de relevante love jeg fandt:\n\n[1] **[Lovnavn]** ([Lovnummer]): [Forklaring af lovens relevans med konkrete citater fra lovteksten].\n\n[Fortsæt med flere love hvis relevant]",
  "confidence": 0.85,
  "key_points": [
    "Specifikt punkt fra lovteksten om emnet",
    "Konkret information om hvem/hvad loven dækker",
    "Praktisk information om hvordan loven anvendes"
  ],
  "citations": [
    {"source_index": 1, "text": "Direkte citat fra lovteksten"}
  ]
}
"""

        user_prompt = f"""Spørgsmål: {query}

Relevante love med lovtekst:
{context}

Besvar spørgsmålet ved at:
1. Identificere hvilke love der er mest relevante for spørgsmålet
2. Citere specifikke paragraffer og bestemmelser fra lovteksten
3. Forklare hvordan loven besvarer brugerens spørgsmål
4. Give praktiske nøglepunkter baseret på lovteksten
5. Inkludere citations til specifikke lovparagraffer

Brug den omfattende lovtekst du har adgang til for at give et præcist og detaljeret svar."""

        # Prepare API payload
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 3000,  # Increased for detailed responses with law text
            "response_format": {"type": "json_object"}
        }

        try:
            if self.use_azure:
                # Azure OpenAI
                url = f"{self.azure_endpoint}/openai/deployments/{self.azure_deployment}/chat/completions?api-version={self.azure_api_version}"
                headers = {
                    "api-key": self.azure_api_key,
                    "Content-Type": "application/json"
                }
                payload["model"] = self.azure_deployment
                logger.info(f"Using Azure OpenAI: {self.azure_deployment}")
            else:
                # Standard OpenAI
                url = "https://api.openai.com/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                }
                payload["model"] = self.openai_model
                logger.info(f"Using Standard OpenAI: {self.openai_model}")

            # Add timeout to prevent hanging
            timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout
            async with self.session.post(url, headers=headers, json=payload, timeout=timeout) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"LLM API error: {response.status} - {error_text}")
                    return self._fallback_answer(sources)

                data = await response.json()
                logger.info(f"LLM API response received successfully")

            # Parse LLM response
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)

            # Validate and structure response
            answer = parsed.get('answer', 'Intet svar genereret')
            confidence = float(parsed.get('confidence', 0.5))
            key_points = parsed.get('key_points', [])
            citations = parsed.get('citations', [])

            return {
                'answer': answer,
                'confidence': confidence,
                'key_points': key_points,
                'sources': sources,
                'citations': citations
            }

        except Exception as exc:
            logger.error(f"Failed to generate LLM answer: {exc}")
            return self._fallback_answer(sources)

    def _fallback_answer(self, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback answer when LLM fails"""
        answer_parts = ["Baseret på min søgning fandt jeg følgende relevante love:\n"]

        for idx, source in enumerate(sources, start=1):
            title = source.get('title', 'Ukendt lov')
            summary = source.get('summary', 'Ingen beskrivelse')
            answer_parts.append(f"[{idx}] **{title}**: {summary}")

        return {
            'answer': '\n\n'.join(answer_parts),
            'confidence': 0.6,
            'key_points': [
                'Se de linkede love for detaljeret information',
                'Konsulter en advokat for juridisk rådgivning'
            ],
            'sources': sources,
            'citations': []
        }
