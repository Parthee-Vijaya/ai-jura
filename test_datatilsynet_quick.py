#!/usr/bin/env python3
"""
Quick test for Datatilsynet scraping functionality
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from news.live_scraper import LiveNewsScraper

logging.basicConfig(level=logging.INFO)

async def quick_test():
    """Quick test of improved Datatilsynet scraping"""
    print("🚀 Quick test af forbedret Datatilsynet scraper...")

    try:
        async with LiveNewsScraper() as scraper:
            print("✅ Scraper klar")

            start_time = datetime.now()
            articles = await scraper._scrape_datatilsynet()
            duration = (datetime.now() - start_time).total_seconds()

            print(f"⏱️  Scraping tog {duration:.2f} sekunder")
            print(f"📊 Fandt {len(articles)} artikler")

            if articles:
                print("\n📋 Top 3 artikler:")
                for i, article in enumerate(articles[:3], 1):
                    print(f"{i}. {article.title}")
                    print(f"   🏷️  Keywords: {', '.join(article.keywords)}")
                    print(f"   ⭐ Vigtighed: {article.importance}")
                    print()

            print("✅ Test gennemført succesfuldt!")

    except Exception as e:
        print(f"❌ Fejl: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(quick_test())