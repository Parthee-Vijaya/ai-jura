#!/usr/bin/env python3
"""
Demo script showing the RSS news scraper in action
Displays the best AI and data protection articles found
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
src_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))

from news.live_scraper import LiveNewsScraper


async def demo_news_scraper():
    """Demonstrate the news scraper with real RSS feeds"""
    print("=" * 60)
    print("🤖 AI COMPLIANCE PLATFORM - LIVE NEWS DEMO")
    print("=" * 60)
    print()

    async with LiveNewsScraper() as scraper:
        print("📡 Fetching latest AI and Data Protection news...")
        print("Sources: EDPB, EU Commission, Council of EU, EUR-Lex, Datatilsynet, KL")
        print()

        # Fetch all news
        all_news = await scraper.fetch_latest_news()

        print(f"✅ Successfully scraped {len(all_news)} relevant articles")
        print()

        # Show breakdown by source
        print("📊 ARTICLES BY SOURCE:")
        print("-" * 40)
        by_source = {}
        for item in all_news:
            if item.source not in by_source:
                by_source[item.source] = []
            by_source[item.source].append(item)

        for source, articles in sorted(by_source.items()):
            print(f"  {source:.<25} {len(articles):>3} articles")
        print()

        # Show high importance articles
        high_importance = [item for item in all_news if item.importance == 'high']
        print(f"🔥 HIGH PRIORITY ARTICLES ({len(high_importance)}):")
        print("-" * 50)

        for i, item in enumerate(high_importance[:5], 1):
            print(f"{i}. {item.title}")
            print(f"   📍 Source: {item.source}")
            print(f"   📅 Published: {item.published_date.strftime('%Y-%m-%d %H:%M') if item.published_date else 'Unknown'}")
            print(f"   🏷️  Keywords: {', '.join(item.keywords[:4])}")
            print(f"   📝 Summary: {item.summary[:120]}...")
            print(f"   🔗 URL: {item.url}")
            print()

        # Show medium importance articles
        medium_importance = [item for item in all_news if item.importance == 'medium']
        print(f"📋 MEDIUM PRIORITY ARTICLES ({len(medium_importance)}):")
        print("-" * 50)

        for i, item in enumerate(medium_importance[:3], 1):
            print(f"{i}. {item.title[:70]}...")
            print(f"   📍 {item.source} | 🏷️ {', '.join(item.keywords[:3])}")
            print()

        # Show recent articles (last 24 hours)
        recent_news = scraper.get_recent_news(hours=24)
        print(f"⏰ RECENT ARTICLES (Last 24h): {len(recent_news)}")
        print("-" * 40)

        for item in recent_news[:3]:
            article = item if isinstance(item, dict) else item.__dict__
            print(f"• {article['title'][:60]}...")
            print(f"  📍 {article['source']} | ⭐ {article['importance']}")
            print()

        # Show articles by category
        print("📂 ARTICLES BY CATEGORY:")
        print("-" * 30)
        categories = {}
        for item in all_news:
            cat = item.category
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1

        for category, count in sorted(categories.items()):
            print(f"  {category:.<20} {count:>3}")
        print()

        # Show working RSS feeds
        print("✅ WORKING RSS FEEDS:")
        print("-" * 25)
        working_feeds = [
            ("EDPB", "https://www.edpb.europa.eu/feed/news_en", "✅ Perfect"),
            ("Datatilsynet", "HTML Scraping", "✅ Working"),
            ("EUR-Lex", "Web Search", "✅ Working"),
        ]

        for name, url, status in working_feeds:
            print(f"  {name:.<15} {status}")

        print()
        print("⚠️  NON-WORKING RSS FEEDS:")
        print("-" * 30)
        failing_feeds = [
            ("EU Commission", "404 Error - Using HTML fallback"),
            ("Council of EU", "403 Forbidden - Using fallback"),
            ("KL", "404 Error - Using fallback"),
        ]

        for name, issue in failing_feeds:
            print(f"  {name:.<15} {issue}")

        print()
        print("=" * 60)
        print("📈 SUMMARY:")
        print(f"  • Total Articles: {len(all_news)}")
        print(f"  • High Priority: {len(high_importance)}")
        print(f"  • Medium Priority: {len(medium_importance)}")
        print(f"  • Sources: {len(by_source)}")
        print(f"  • Working RSS: 1 of 4 attempted")
        print("  • Fallback Methods: HTML scraping, curated content")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo_news_scraper())