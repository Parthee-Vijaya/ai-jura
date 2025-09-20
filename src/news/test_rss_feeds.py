#!/usr/bin/env python3
"""
Test script for RSS feeds functionality
Tests that the live scraper can fetch real RSS feeds
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))

from news.live_scraper import LiveNewsScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_individual_rss_feeds():
    """Test each RSS feed individually"""
    logger.info("Testing individual RSS feeds...")

    async with LiveNewsScraper() as scraper:
        # Test EU Commission RSS
        logger.info("\n=== Testing EU Commission RSS ===")
        try:
            eu_news = await scraper._scrape_eu_commission_rss()
            logger.info(f"EU Commission: Found {len(eu_news)} relevant articles")
            for item in eu_news[:3]:
                logger.info(f"  - {item.title[:80]}... (importance: {item.importance})")
        except Exception as e:
            logger.error(f"EU Commission RSS test failed: {e}")

        # Test EDPB RSS
        logger.info("\n=== Testing EDPB RSS ===")
        try:
            edpb_news = await scraper._scrape_edpb_rss()
            logger.info(f"EDPB: Found {len(edpb_news)} relevant articles")
            for item in edpb_news[:3]:
                logger.info(f"  - {item.title[:80]}... (importance: {item.importance})")
        except Exception as e:
            logger.error(f"EDPB RSS test failed: {e}")

        # Test Council of EU RSS
        logger.info("\n=== Testing Council of EU RSS ===")
        try:
            council_news = await scraper._scrape_council_eu_rss()
            logger.info(f"Council of EU: Found {len(council_news)} relevant articles")
            for item in council_news[:3]:
                logger.info(f"  - {item.title[:80]}... (importance: {item.importance})")
        except Exception as e:
            logger.error(f"Council of EU RSS test failed: {e}")

        # Test KL RSS
        logger.info("\n=== Testing KL RSS ===")
        try:
            kl_news = await scraper._scrape_kl_rss()
            logger.info(f"KL: Found {len(kl_news)} relevant articles")
            for item in kl_news[:3]:
                logger.info(f"  - {item.title[:80]}... (importance: {item.importance})")
        except Exception as e:
            logger.error(f"KL RSS test failed: {e}")


async def test_full_scraping():
    """Test full news scraping with all sources"""
    logger.info("\n=== Testing Full News Scraping ===")

    async with LiveNewsScraper() as scraper:
        try:
            all_news = await scraper.fetch_latest_news()
            logger.info(f"Total articles found: {len(all_news)}")

            # Group by source
            by_source = {}
            for item in all_news:
                if item.source not in by_source:
                    by_source[item.source] = []
                by_source[item.source].append(item)

            logger.info("\nArticles by source:")
            for source, articles in by_source.items():
                logger.info(f"  {source}: {len(articles)} articles")

            # Show high importance articles
            high_importance = [item for item in all_news if item.importance == 'high']
            logger.info(f"\nHigh importance articles: {len(high_importance)}")
            for item in high_importance[:5]:
                logger.info(f"  - {item.title[:80]}...")
                logger.info(f"    Source: {item.source}, Keywords: {', '.join(item.keywords[:3])}")

        except Exception as e:
            logger.error(f"Full scraping test failed: {e}")


async def test_rss_feed_direct():
    """Test RSS feed fetching directly"""
    logger.info("\n=== Testing Direct RSS Feed Fetching ===")

    async with LiveNewsScraper() as scraper:
        # Test feeds
        feeds_to_test = [
            ("EU Commission", "http://europa.eu/rapid/rss.htm"),
            ("EDPB", "https://www.edpb.europa.eu/feed/news_en"),
            ("Council of EU", "https://www.consilium.europa.eu/en/about-site/rss/"),
            ("KL", "https://www.kl.dk/nyheder/feed/")
        ]

        for name, url in feeds_to_test:
            logger.info(f"\nTesting {name} RSS feed: {url}")
            try:
                entries = await scraper._fetch_rss_feed(url)
                logger.info(f"  Success! Found {len(entries)} entries")
                if entries:
                    first_entry = entries[0]
                    title = first_entry.get('title', 'No title')
                    logger.info(f"  First entry: {title[:60]}...")
            except Exception as e:
                logger.error(f"  Failed: {e}")


if __name__ == "__main__":
    async def main():
        logger.info("Starting RSS feeds test...")

        try:
            await test_rss_feed_direct()
            await test_individual_rss_feeds()
            await test_full_scraping()

            logger.info("\nRSS feeds test completed!")

        except Exception as e:
            logger.error(f"Test failed: {e}")
            sys.exit(1)

    asyncio.run(main())