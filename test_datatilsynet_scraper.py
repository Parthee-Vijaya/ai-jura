#!/usr/bin/env python3
"""
Test script for improved Datatilsynet scraping functionality
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from news.live_scraper import LiveNewsScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_datatilsynet_scraping():
    """Test the improved Datatilsynet scraping functionality"""
    print("🚀 Testing forbedret Datatilsynet scraping funktionalitet...")
    print("=" * 60)

    try:
        async with LiveNewsScraper() as scraper:
            print("✅ Scraper initialiseret")

            # Test Datatilsynet scraping specifically
            print("\n📰 Testing Datatilsynet scraping...")
            start_time = datetime.now()

            datatilsynet_news = await scraper._scrape_datatilsynet()

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            print(f"⏱️  Scraping tog {duration:.2f} sekunder")
            print(f"📊 Fandt {len(datatilsynet_news)} Datatilsynet artikler")

            if datatilsynet_news:
                print("\n📋 Datatilsynet artikler:")
                print("-" * 40)

                for i, article in enumerate(datatilsynet_news, 1):
                    print(f"\n{i}. {article.title}")
                    print(f"   🔗 URL: {article.url}")
                    print(f"   📅 Dato: {article.published_date}")
                    print(f"   🏷️  Keywords: {', '.join(article.keywords)}")
                    print(f"   ⭐ Vigtighed: {article.importance}")
                    print(f"   📝 Sammendrag: {article.summary[:100]}...")
                    print()

                # Test keyword relevance
                print("🔍 Keyword analyse:")
                all_keywords = []
                for article in datatilsynet_news:
                    all_keywords.extend(article.keywords)

                from collections import Counter
                keyword_counts = Counter(all_keywords)
                print(f"   Mest brugte keywords: {dict(keyword_counts.most_common(5))}")

                # Test importance distribution
                importance_counts = Counter([article.importance for article in datatilsynet_news])
                print(f"   Vigtigheds-fordeling: {dict(importance_counts)}")

                # Test date distribution
                recent_articles = [a for a in datatilsynet_news if a.published_date and
                                 (datetime.now() - a.published_date).days <= 30]
                print(f"   Artikler fra sidste 30 dage: {len(recent_articles)}")

            else:
                print("⚠️  Ingen artikler fundet fra Datatilsynet")

            # Test complete news scraping
            print("\n🌍 Testing komplet news scraping...")
            all_news = await scraper.fetch_latest_news()

            print(f"📊 Total artikler fra alle kilder: {len(all_news)}")

            # Show distribution by source
            from collections import Counter
            source_counts = Counter([article.source for article in all_news])
            print("\n📈 Fordeling efter kilde:")
            for source, count in source_counts.items():
                print(f"   {source}: {count} artikler")

            # Show high importance articles
            high_importance = [a for a in all_news if a.importance == 'high']
            print(f"\n⭐ Højt prioriterede artikler: {len(high_importance)}")

            if high_importance:
                print("Top højt prioriterede artikler:")
                for article in high_importance[:3]:
                    print(f"   • {article.title} ({article.source})")

    except Exception as e:
        print(f"❌ Fejl under test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_datatilsynet_scraping())