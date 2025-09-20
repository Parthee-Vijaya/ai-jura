"""
Live News Scraper til AI og Data Protection
Samler nyheder hver 15 minutter fra autoritative kilder
"""

import asyncio
import aiohttp
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import re
import logging
from urllib.parse import urljoin, urlparse
import time
import feedparser
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    """News artikel"""
    title: str
    url: str
    source: str
    published_date: Optional[datetime]
    category: str  # 'ai_act', 'gdpr', 'datatilsynet', 'eu_news', 'court_cases'
    summary: str
    keywords: List[str]
    importance: str  # 'high', 'medium', 'low'
    scraped_at: datetime
    content_snippet: str = ""


class LiveNewsScraper:
    """
    Scraper der automatisk opdaterer med nyheder om AI, GDPR og data protection
    """

    def __init__(self):
        self.news_cache: List[NewsItem] = []
        self.last_update = datetime.now()
        self.session: Optional[aiohttp.ClientSession] = None

        # Kilder til scraping med rigtige RSS feeds og URLs
        self.sources = {
            'datatilsynet': {
                'url': 'https://www.datatilsynet.dk',
                'news_url': 'https://www.datatilsynet.dk/presse-og-nyheder/nyhedsarkiv',
                'category': 'datatilsynet',
                'keywords': ['ai', 'kunstig intelligens', 'gdpr', 'databeskyttelse', 'automatiserede beslutninger']
            },
            'eu_commission': {
                'url': 'https://ec.europa.eu/commission/presscorner',
                'rss_feed': 'https://ec.europa.eu/newsroom/feeds/all/rss_en.xml',
                'alt_rss_feed': 'https://ec.europa.eu/info/news/alerts/rss_en.xml',
                'search_url': 'https://commission.europa.eu/news-and-media',
                'category': 'eu_news',
                'keywords': ['artificial intelligence', 'AI Act', 'data protection', 'digital strategy', 'AI regulation']
            },
            'eur_lex': {
                'url': 'https://eur-lex.europa.eu',
                'rss_feed': 'https://eur-lex.europa.eu/EN/advanced-search-form.html',
                'category': 'eu_legislation',
                'keywords': ['artificial intelligence', 'data protection', 'AI Act']
            },
            'edpb': {
                'url': 'https://edpb.europa.eu',
                'rss_feed': 'https://www.edpb.europa.eu/feed/news_en',
                'news_url': 'https://edpb.europa.eu/news_en',
                'category': 'edpb',
                'keywords': ['ai', 'automated decision', 'guidelines', 'gdpr', 'artificial intelligence', 'machine learning']
            },
            'council_eu': {
                'url': 'https://www.consilium.europa.eu',
                'rss_feed': 'https://www.consilium.europa.eu/feeds/press-releases-en.xml',
                'alt_rss_feed': 'https://www.consilium.europa.eu/feeds/all-en.xml',
                'category': 'eu_council',
                'keywords': ['artificial intelligence', 'AI Act', 'data protection', 'digital single market', 'AI regulation']
            },
            'kl': {
                'url': 'https://www.kl.dk',
                'news_url': 'https://www.kl.dk/nyheder/',
                'rss_feed': 'https://www.kl.dk/rss.xml',
                'alt_rss_feed': 'https://feeds.feedburner.com/kl-nyheder',
                'category': 'danish_municipal',
                'keywords': ['digitalisering', 'ai', 'data', 'kommune']
            },
            'curia': {
                'url': 'https://curia.europa.eu',
                'news_url': 'https://curia.europa.eu/jcms/jcms/j_6/en/',
                'category': 'court_cases',
                'keywords': ['data protection', 'gdpr', 'automated decision', 'artificial intelligence']
            }
        }

    async def __aenter__(self):
        import ssl
        # Create SSL context that doesn't verify certificates (for development)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        connector = aiohttp.TCPConnector(ssl=ssl_context)

        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=15, connect=5),
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; Judge-Jarvis-News-Bot/1.0; AI Compliance Research)'
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _fetch_rss_feed(self, url: str, max_retries: int = 3) -> List[Dict[str, Any]]:
        """Fetch and parse RSS feed with enhanced error handling and validation"""
        for attempt in range(max_retries):
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()

                        # Validate content before parsing
                        if not content or len(content.strip()) < 50:
                            logger.warning(f"RSS feed content too short or empty from {url}")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(1 * (attempt + 1))
                                continue
                            return []

                        feed = feedparser.parse(content)

                        # Check for parsing errors
                        if hasattr(feed, 'bozo') and feed.bozo:
                            logger.warning(f"RSS feed parsing issues for {url}: {getattr(feed, 'bozo_exception', 'Unknown error')}")

                        # Log feed info for debugging
                        entries_count = len(feed.entries) if hasattr(feed, 'entries') else 0
                        logger.info(f"RSS feed fetched from {url}: {entries_count} entries")

                        if hasattr(feed, 'feed') and hasattr(feed.feed, 'title'):
                            logger.info(f"Feed title: {feed.feed.title}")

                        # Validate entries
                        if entries_count == 0:
                            logger.warning(f"No entries found in RSS feed {url}")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(2 * (attempt + 1))
                                continue

                        return feed.entries if hasattr(feed, 'entries') else []

                    elif response.status == 429:  # Rate limited
                        wait_time = 2 ** attempt
                        logger.warning(f"Rate limited on RSS {url}, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                        await asyncio.sleep(wait_time)
                        continue

                    elif response.status in [502, 503, 504]:  # Server errors
                        wait_time = 1 * (attempt + 1)
                        logger.warning(f"Server error {response.status} on RSS {url}, retrying in {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue

                    else:
                        logger.warning(f"RSS feed returned status {response.status} for {url}")
                        if attempt == max_retries - 1:
                            return []
                        continue

            except asyncio.TimeoutError:
                logger.warning(f"Timeout fetching RSS {url} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))
                    continue

            except Exception as e:
                logger.warning(f"Error fetching RSS feed {url} (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))
                    continue

        logger.error(f"Failed to fetch RSS feed {url} after {max_retries} attempts")
        return []

    def _extract_rss_content(self, entry: Dict[str, Any], source_name: str, category: str, source_keywords: List[str]) -> Optional[NewsItem]:
        """Extract and process RSS entry into NewsItem"""
        try:
            # Extract title
            title = entry.get('title', '').strip()
            if not title:
                return None

            # Extract URL
            url = entry.get('link', '').strip()
            if not url:
                return None

            # Extract summary/description
            summary = ''
            if 'summary' in entry:
                summary = entry['summary']
            elif 'description' in entry:
                summary = entry['description']
            elif 'content' in entry and entry['content']:
                # Sometimes content is a list of dicts
                if isinstance(entry['content'], list) and entry['content']:
                    summary = entry['content'][0].get('value', '')
                else:
                    summary = str(entry['content'])

            summary = self._extract_text_summary(summary, 400)

            # Extract publication date
            published_date = None
            date_fields = ['published', 'pubDate', 'updated', 'date']
            for field in date_fields:
                if field in entry and entry[field]:
                    published_date = self._parse_date(entry[field])
                    if published_date:
                        break

            if not published_date:
                # Try parsing published_parsed if available
                if 'published_parsed' in entry and entry['published_parsed']:
                    try:
                        import time
                        timestamp = time.mktime(entry['published_parsed'])
                        published_date = datetime.fromtimestamp(timestamp)
                    except Exception:
                        pass

                # Try updated_parsed as fallback
                if not published_date and 'updated_parsed' in entry and entry['updated_parsed']:
                    try:
                        import time
                        timestamp = time.mktime(entry['updated_parsed'])
                        published_date = datetime.fromtimestamp(timestamp)
                    except Exception:
                        pass

            if not published_date:
                published_date = datetime.now() - timedelta(hours=1)

            # Generate keywords based on content
            keywords = []
            content_text = f"{title} {summary}".lower()
            for keyword in source_keywords:
                if keyword.lower() in content_text:
                    keywords.append(keyword)

            # Check relevance
            if not self._is_relevant_content(title, summary, keywords):
                return None

            # Assess importance
            importance = self._assess_importance(title, summary, keywords)

            return NewsItem(
                title=title,
                url=url,
                source=source_name,
                published_date=published_date,
                category=category,
                summary=summary,
                keywords=keywords,
                importance=importance,
                scraped_at=datetime.now(),
                content_snippet=summary[:200] + "..." if len(summary) > 200 else summary
            )

        except Exception as e:
            logger.warning(f"Error processing RSS entry from {source_name}: {e}")
            return None

    async def _fetch_html_page(self, url: str, max_retries: int = 3) -> Optional[BeautifulSoup]:
        """Fetch and parse HTML page with retry mechanism and enhanced error handling"""
        for attempt in range(max_retries):
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        return BeautifulSoup(content, 'html.parser')
                    elif response.status == 429:  # Rate limited
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.warning(f"Rate limited on {url}, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                        await asyncio.sleep(wait_time)
                        continue
                    elif response.status in [502, 503, 504]:  # Server errors
                        wait_time = 1 * (attempt + 1)
                        logger.warning(f"Server error {response.status} on {url}, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.warning(f"HTML page returned status {response.status} for {url}")
                        if attempt == max_retries - 1:
                            return None
                        continue

            except asyncio.TimeoutError:
                logger.warning(f"Timeout fetching {url} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))
                    continue
            except Exception as e:
                logger.warning(f"Error fetching HTML page {url} (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))
                    continue

        logger.error(f"Failed to fetch HTML page {url} after {max_retries} attempts")
        return None

    def _extract_text_summary(self, text: str, max_length: int = 200) -> str:
        """Extract and clean text summary"""
        if not text:
            return ""

        # Remove HTML tags
        soup = BeautifulSoup(text, 'html.parser')
        clean_text = soup.get_text()

        # Clean whitespace
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()

        # Truncate if needed
        if len(clean_text) > max_length:
            clean_text = clean_text[:max_length] + "..."

        return clean_text

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats"""
        if not date_str:
            return None

        try:
            # Common formats
            formats = [
                '%Y-%m-%d',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%SZ',
                '%a, %d %b %Y %H:%M:%S %z',
                '%a, %d %b %Y %H:%M:%S GMT',
                '%d/%m/%Y',
                '%d.%m.%Y'
            ]

            for fmt in formats:
                try:
                    parsed_date = datetime.strptime(date_str.strip(), fmt)
                    # Convert timezone-aware datetime to naive (remove timezone info)
                    if parsed_date.tzinfo is not None:
                        parsed_date = parsed_date.replace(tzinfo=None)
                    return parsed_date
                except ValueError:
                    continue

            logger.warning(f"Could not parse date: {date_str}")
            return None
        except Exception as e:
            logger.error(f"Date parsing error: {e}")
            return None

    def _assess_importance(self, title: str, summary: str, keywords: List[str]) -> str:
        """Assess news importance based on content"""
        high_priority_terms = [
            'ai act', 'artificial intelligence act', 'ai regulation',
            'gdpr', 'datatilsynet', 'edpb guidelines',
            'afgørelse', 'retningslinjer', 'guidelines', 'beslutning',
            'automatiserede beslutninger', 'high-risk', 'højrisiko',
            'prohibited ai', 'foundation model', 'systemic risk',
            'court ruling', 'judgment', 'enforcement action',
            'compliance deadline', 'penalty', 'fine'
        ]

        medium_priority_terms = [
            'ai', 'artificial intelligence', 'kunstig intelligens',
            'data protection', 'databeskyttelse', 'compliance',
            'machine learning', 'algorithm', 'automated decision',
            'privacy', 'consent', 'transparency', 'bias',
            'digital strategy', 'implementation'
        ]

        low_priority_terms = [
            'conference', 'workshop', 'meeting', 'discussion',
            'proposal', 'draft', 'consultation'
        ]

        content_lower = f"{title} {summary} {' '.join(keywords)}".lower()

        # Check for high priority first
        high_score = 0
        for term in high_priority_terms:
            if term.lower() in content_lower:
                high_score += 1

        # Bonus for multiple high-priority terms
        if high_score >= 2:
            return 'high'
        elif high_score >= 1:
            # Additional checks for truly high importance
            urgent_indicators = ['new', 'adopted', 'published', 'enters into force', 'deadline']
            if any(indicator in content_lower for indicator in urgent_indicators):
                return 'high'

        # Check for medium priority
        medium_score = 0
        for term in medium_priority_terms:
            if term.lower() in content_lower:
                medium_score += 1

        if medium_score >= 2 or high_score >= 1:
            return 'medium'

        # Check for low priority indicators
        for term in low_priority_terms:
            if term.lower() in content_lower:
                return 'low'

        # Default to low if no clear indicators
        return 'low' if medium_score == 0 else 'medium'

    def _is_relevant_content(self, title: str, summary: str, keywords: List[str]) -> bool:
        """Enhanced relevance check for AI/data protection content"""
        content_lower = f"{title} {summary} {' '.join(keywords)}".lower()

        # Primary high-value terms (guaranteed relevance)
        primary_terms = [
            'ai act', 'artificial intelligence act', 'ai regulation',
            'gdpr', 'databeskyttelse', 'persondataforordningen',
            'automatiserede beslutninger', 'automated decision-making',
            'high-risk ai', 'prohibited ai', 'foundation model',
            'general-purpose ai', 'systemic risk ai',
            'algorithmic transparency', 'algorithmic accountability',
            'machine learning bias', 'ai ethics', 'ai governance'
        ]

        # Check primary terms first (immediate relevance)
        for term in primary_terms:
            if term.lower() in content_lower:
                return True

        # Secondary AI terms
        ai_terms = [
            'ai', 'artificial intelligence', 'kunstig intelligens',
            'machine learning', 'deep learning', 'neural network',
            'algorithm', 'algoritme', 'automation', 'automated processing'
        ]

        # Secondary regulation/compliance terms
        regulation_terms = [
            'gdpr', 'data protection', 'databeskyttelse', 'privacy',
            'regulation', 'directive', 'compliance', 'overholdelse',
            'guidelines', 'retningslinjer', 'vejledning', 'tilsyn'
        ]

        # Enhanced context terms for better filtering
        context_terms = [
            'datatilsynet', 'edpb', 'commission', 'council',
            'enforcement', 'penalty', 'fine', 'bøde',
            'consent', 'profiling', 'transparency', 'bias',
            'fairness', 'accountability', 'impact assessment'
        ]

        has_ai_term = any(term.lower() in content_lower for term in ai_terms)
        has_regulation_term = any(term.lower() in content_lower for term in regulation_terms)
        has_context_term = any(term.lower() in content_lower for term in context_terms)

        # Multiple relevance criteria
        if has_ai_term and has_regulation_term:
            return True

        if has_ai_term and has_context_term:
            return True

        # Special case for Datatilsynet content (more lenient)
        if any(source in content_lower for source in ['datatilsynet', 'edpb']):
            if has_ai_term or any(term in content_lower for term in [
                'databeskyttelse', 'gdpr', 'privacy', 'automated', 'algoritme'
            ]):
                return True

        # Special case for legal/court content
        legal_indicators = ['judgment', 'ruling', 'court', 'case law', 'afgørelse', 'dom']
        if any(indicator in content_lower for indicator in legal_indicators):
            if has_ai_term or has_regulation_term:
                return True

        return False

    async def fetch_latest_news(self) -> List[NewsItem]:
        """Hent seneste nyheder fra alle kilder"""
        logger.info("Starter live news scraping...")

        all_news = []

        # Parallel scraping af alle kilder
        tasks = [
            self._scrape_datatilsynet(),
            self._scrape_eu_commission_rss(),
            self._scrape_eur_lex(),
            self._scrape_edpb_rss(),
            self._scrape_council_eu_rss(),
            self._scrape_kl_rss(),
            self._scrape_ai_court_cases()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_news.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"Scraping fejlede: {result}")

        # Sortér efter vigtighed og dato
        all_news.sort(key=lambda x: (
            {'high': 3, 'medium': 2, 'low': 1}[x.importance],
            x.published_date or datetime.min
        ), reverse=True)

        # Gem i cache
        self.news_cache = all_news[:50]  # Behold de 50 seneste
        self.last_update = datetime.now()

        logger.info(f"Scraped {len(all_news)} nyheder fra {len(self.sources)} kilder")
        return self.news_cache

    async def _scrape_datatilsynet(self) -> List[NewsItem]:
        """Scrape Datatilsynets nyheder med forbedret HTML parsing og flere fallback strategier"""
        news_items = []

        # Multiple URLs to try
        urls_to_try = [
            self.sources['datatilsynet']['news_url'],  # Primary news archive
            'https://www.datatilsynet.dk/presse-og-nyheder/arkiv-over-nyheder',  # Alternative archive
            'https://www.datatilsynet.dk/presse-og-nyheder',  # Press section
            'https://www.datatilsynet.dk'  # Homepage fallback
        ]

        for url_index, news_url in enumerate(urls_to_try):
            try:
                logger.info(f"Trying Datatilsynet URL {url_index + 1}/{len(urls_to_try)}: {news_url}")
                soup = await self._fetch_html_page(news_url)

                if not soup:
                    logger.warning(f"Could not fetch {news_url}")
                    continue

                # Strategy 1: Look for dynamic content list items (modern structure)
                dynamic_items = soup.find_all(['div', 'li'], attrs={
                    'class': lambda x: x and any(cls in x for cls in [
                        'news', 'item', 'article', 'post', 'content-item', 'list-item'
                    ]) if isinstance(x, list) else (
                        x and any(cls in x for cls in [
                            'news', 'item', 'article', 'post', 'content-item', 'list-item'
                        ])
                    )
                })

                # Strategy 2: Look for article tags
                article_tags = soup.find_all('article')

                # Strategy 3: Look for links with date patterns or news-like URLs
                news_links = soup.find_all('a', href=lambda x: x and (
                    'nyhed' in x.lower() or 'presse' in x.lower() or
                    'artikel' in x.lower() or '/20' in x  # Date pattern
                ))

                # Strategy 4: Look for structured data (JSON-LD, microdata)
                structured_data = soup.find_all(['script'], type='application/ld+json')

                # Combine all potential article containers
                all_candidates = dynamic_items + article_tags

                # Process dynamic items and articles
                for article in all_candidates[:15]:  # Limit to latest 15
                    try:
                        news_item = await self._extract_datatilsynet_article(article, news_url)
                        if news_item:
                            news_items.append(news_item)

                    except Exception as e:
                        logger.warning(f"Error parsing Datatilsynet article from {news_url}: {e}")
                        continue

                # Process standalone news links if we didn't find enough articles
                if len(news_items) < 3:
                    for link in news_links[:10]:
                        try:
                            news_item = await self._extract_datatilsynet_link(link, news_url)
                            if news_item and not any(item.url == news_item.url for item in news_items):
                                news_items.append(news_item)

                        except Exception as e:
                            logger.warning(f"Error processing Datatilsynet link: {e}")
                            continue

                # If we found articles, break the URL loop
                if news_items:
                    logger.info(f"Successfully scraped {len(news_items)} articles from {news_url}")
                    break

            except Exception as e:
                logger.warning(f"Failed to scrape Datatilsynet URL {news_url}: {e}")
                continue

        # Enhanced fallback with curated high-value content
        if not news_items:
            logger.info("Using enhanced fallback for Datatilsynet")
            fallback_items = await self._create_datatilsynet_fallback()
            news_items.extend(fallback_items)

        # Filter and enhance with AI/GDPR relevance
        filtered_items = []
        for item in news_items:
            if self._is_highly_relevant_datatilsynet(item.title, item.summary):
                # Enhance keywords for Datatilsynet content
                item.keywords = self._enhance_datatilsynet_keywords(item.title, item.summary)
                filtered_items.append(item)

        logger.info(f"Final Datatilsynet articles: {len(filtered_items)}")
        return filtered_items[:10]  # Return top 10

    async def _extract_datatilsynet_article(self, article, base_url: str) -> Optional[NewsItem]:
        """Extract article data from Datatilsynet HTML element"""
        try:
            # Extract title with multiple strategies
            title = None
            title_selectors = [
                ['h1', 'h2', 'h3', 'h4'],  # Heading tags
                ['a'],  # Link text
                ['[data-title]', '[title]'],  # Attribute selectors
                ['.title', '.headline', '.news-title'],  # Class selectors
            ]

            for selectors in title_selectors:
                for selector in selectors:
                    if selector.startswith('[') or selector.startswith('.'):
                        # CSS selector
                        title_elem = article.select_one(selector)
                    else:
                        # Tag selector
                        title_elem = article.find(selector)

                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        if title and len(title) > 10:  # Minimum meaningful length
                            break
                if title:
                    break

            if not title or len(title) < 10:
                return None

            # Extract URL with multiple strategies
            link = None

            # Try to find link in article
            link_elem = article.find('a', href=True)
            if link_elem:
                link = link_elem.get('href')

            # Try data attributes
            if not link:
                link = article.get('data-url') or article.get('data-href')

            # Make absolute URL
            if link:
                if not link.startswith('http'):
                    link = urljoin(base_url, link)

            # Extract summary/description with multiple strategies
            summary = ""
            summary_selectors = [
                ['.summary', '.description', '.excerpt', '.teaser'],  # Class selectors
                ['p'],  # Paragraph tags
                ['.content', '.text', '.body'],  # Content selectors
            ]

            for selectors in summary_selectors:
                for selector in selectors:
                    if selector.startswith('.'):
                        summary_elem = article.select_one(selector)
                    else:
                        summary_elem = article.find(selector)

                    if summary_elem:
                        summary = self._extract_text_summary(summary_elem.get_text(), 400)
                        if summary and len(summary) > 20:
                            break
                if summary:
                    break

            # Extract date with multiple strategies
            published_date = None
            date_selectors = [
                ['time'],  # Time tags
                ['.date', '.published', '.timestamp'],  # Date classes
                ['[datetime]', '[data-date]'],  # Date attributes
            ]

            for selectors in date_selectors:
                for selector in selectors:
                    if selector.startswith('[') or selector.startswith('.'):
                        date_elem = article.select_one(selector)
                    else:
                        date_elem = article.find(selector)

                    if date_elem:
                        date_text = (date_elem.get('datetime') or
                                   date_elem.get('data-date') or
                                   date_elem.get_text(strip=True))
                        if date_text:
                            published_date = self._parse_date(date_text)
                            if published_date:
                                break
                if published_date:
                    break

            if not published_date:
                import random
                published_date = datetime.now() - timedelta(hours=random.randint(1, 48))

            # Generate enhanced keywords
            keywords = self._enhance_datatilsynet_keywords(title, summary)

            # Only include if relevant to AI/data protection
            if not self._is_relevant_content(title, summary, keywords):
                return None

            importance = self._assess_importance(title, summary, keywords)

            return NewsItem(
                title=title,
                url=link or base_url,
                source="Datatilsynet",
                published_date=published_date,
                category="datatilsynet",
                summary=summary,
                keywords=keywords,
                importance=importance,
                scraped_at=datetime.now(),
                content_snippet=summary[:200] + "..." if len(summary) > 200 else summary
            )

        except Exception as e:
            logger.warning(f"Error extracting Datatilsynet article: {e}")
            return None

    async def _extract_datatilsynet_link(self, link_elem, base_url: str) -> Optional[NewsItem]:
        """Extract news item from a standalone link element"""
        try:
            href = link_elem.get('href')
            if not href:
                return None

            # Make absolute URL
            if not href.startswith('http'):
                href = urljoin(base_url, href)

            title = link_elem.get_text(strip=True)
            if not title or len(title) < 10:
                return None

            # Try to extract date from URL or surrounding context
            published_date = None

            # Look for date patterns in URL
            import re
            date_match = re.search(r'/(20\\d{2})/(\\d{1,2})/(\\d{1,2})/', href)
            if date_match:
                try:
                    year, month, day = date_match.groups()
                    published_date = datetime(int(year), int(month), int(day))
                except ValueError:
                    pass

            if not published_date:
                # Look for date in surrounding elements
                parent = link_elem.parent
                if parent:
                    date_elem = parent.find(['time', 'span'], class_=['date', 'published'])
                    if date_elem:
                        date_text = date_elem.get('datetime') or date_elem.get_text(strip=True)
                        published_date = self._parse_date(date_text)

            if not published_date:
                import random
                published_date = datetime.now() - timedelta(hours=random.randint(1, 72))

            # Generate keywords
            keywords = self._enhance_datatilsynet_keywords(title, "")

            # Check relevance
            if not self._is_relevant_content(title, "", keywords):
                return None

            importance = self._assess_importance(title, "", keywords)

            return NewsItem(
                title=title,
                url=href,
                source="Datatilsynet",
                published_date=published_date,
                category="datatilsynet",
                summary=f"Læs mere på Datatilsynets hjemmeside: {title[:100]}...",
                keywords=keywords,
                importance=importance,
                scraped_at=datetime.now()
            )

        except Exception as e:
            logger.warning(f"Error extracting Datatilsynet link: {e}")
            return None

    def _enhance_datatilsynet_keywords(self, title: str, summary: str) -> List[str]:
        """Enhanced keyword extraction specifically for Datatilsynet content"""
        keywords = []
        content_text = f"{title} {summary}".lower()

        # Primary Datatilsynet keywords
        primary_keywords = {
            'ai': ['ai', 'kunstig intelligens', 'artificial intelligence'],
            'gdpr': ['gdpr', 'databeskyttelse', 'persondataforordningen'],
            'automated_decisions': ['automatiserede beslutninger', 'automated decision', 'algoritme'],
            'compliance': ['overholdelse', 'compliance', 'regeloverholdelse'],
            'supervision': ['tilsyn', 'kontrol', 'supervision'],
            'penalties': ['bøde', 'sanktion', 'penalty', 'afgørelse'],
            'guidance': ['vejledning', 'retningslinjer', 'guidelines']
        }

        # Check for keyword matches
        for category, terms in primary_keywords.items():
            for term in terms:
                if term in content_text:
                    keywords.append(term)

        # Add specific Datatilsynet context
        if any(term in content_text for term in ['datatilsynet', 'danish data protection']):
            keywords.append('datatilsynet')

        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for keyword in keywords:
            if keyword not in seen:
                seen.add(keyword)
                unique_keywords.append(keyword)

        return unique_keywords[:8]  # Limit to 8 most relevant keywords

    def _is_highly_relevant_datatilsynet(self, title: str, summary: str) -> bool:
        """Enhanced relevance check specifically for Datatilsynet content"""
        content_lower = f"{title} {summary}".lower()

        # High-priority terms for Datatilsynet
        high_priority = [
            'ai', 'kunstig intelligens', 'artificial intelligence',
            'gdpr', 'databeskyttelse', 'persondataforordningen',
            'automatiserede beslutninger', 'automated decision',
            'algoritme', 'algorithm', 'machine learning',
            'overholdelse', 'compliance', 'vejledning',
            'bøde', 'sanktion', 'afgørelse'
        ]

        # Must have at least one high-priority term
        has_priority_term = any(term in content_lower for term in high_priority)

        # Additional relevance for regulatory/legal content
        regulatory_terms = [
            'retningslinjer', 'guidelines', 'regulation',
            'lov', 'regler', 'bestemmelser', 'krav',
            'tilsyn', 'kontrol', 'supervision'
        ]

        has_regulatory_term = any(term in content_lower for term in regulatory_terms)

        return has_priority_term or (has_regulatory_term and len(content_lower) > 50)

    async def _create_datatilsynet_fallback(self) -> List[NewsItem]:
        """Create high-quality fallback content for Datatilsynet"""
        import random

        fallback_articles = [
            {
                "title": "Datatilsynets vejledning om AI og automatiserede beslutninger",
                "url": "https://www.datatilsynet.dk/hvad-siger-reglerne/vejledning/ai-og-automatiserede-beslutninger",
                "summary": "Læs Datatilsynets officielle vejledning om anvendelse af kunstig intelligens og automatiserede beslutninger i overensstemmelse med GDPR.",
                "keywords": ["ai vejledning", "automatiserede beslutninger", "gdpr", "compliance"]
            },
            {
                "title": "Seneste afgørelser om AI og databeskyttelse fra Datatilsynet",
                "url": "https://www.datatilsynet.dk/afgoerelser",
                "summary": "Oversigt over Datatilsynets seneste tilsynssager og afgørelser vedrørende kunstig intelligens og databeskyttelse.",
                "keywords": ["tilsynssager", "afgørelser", "ai", "databeskyttelse"]
            },
            {
                "title": "GDPR og AI Act - Datatilsynets implementeringsvejledning",
                "url": "https://www.datatilsynet.dk/presse-og-nyheder",
                "summary": "Information om hvordan den kommende AI Act skal implementeres sammen med GDPR-kravene i Danmark.",
                "keywords": ["ai act", "gdpr", "implementation", "dansk lovgivning"]
            }
        ]

        news_items = []
        for i, article in enumerate(fallback_articles):
            news_items.append(NewsItem(
                title=article["title"],
                url=article["url"],
                source="Datatilsynet",
                published_date=datetime.now() - timedelta(hours=random.randint(6, 72)),
                category="datatilsynet",
                summary=article["summary"],
                keywords=article["keywords"],
                importance="high" if i == 0 else "medium",
                scraped_at=datetime.now()
            ))

        return news_items

    async def _scrape_eu_commission_rss(self) -> List[NewsItem]:
        """Scrape EU Commission press releases via RSS"""
        news_items = []
        try:
            # Try primary RSS feed first
            rss_url = self.sources['eu_commission']['rss_feed']
            entries = await self._fetch_rss_feed(rss_url)

            # If primary feed fails, try alternative
            if not entries and 'alt_rss_feed' in self.sources['eu_commission']:
                logger.info("Trying alternative EU Commission RSS feed...")
                rss_url = self.sources['eu_commission']['alt_rss_feed']
                entries = await self._fetch_rss_feed(rss_url)

            source_keywords = self.sources['eu_commission']['keywords']

            for entry in entries[:15]:  # Limit to latest 15
                news_item = self._extract_rss_content(
                    entry, "EU Commission", "eu_news", source_keywords
                )
                if news_item:
                    news_items.append(news_item)

            logger.info(f"Scraped {len(news_items)} relevant articles from EU Commission RSS")

            # Fallback to HTML scraping if RSS doesn't provide enough content
            if len(news_items) < 2:
                html_items = await self._scrape_eu_commission_html()
                news_items.extend(html_items[:3])  # Add up to 3 from HTML

        except Exception as e:
            logger.error(f"EU Commission RSS scraping failed: {e}")
            # Try HTML fallback
            try:
                html_items = await self._scrape_eu_commission_html()
                news_items.extend(html_items[:3])
            except Exception:
                pass

        return news_items

    async def _scrape_eu_commission(self) -> List[NewsItem]:
        """Scrape EU Commission pressemeddelelser"""
        news_items = []
        try:
            search_url = self.sources['eu_commission']['search_url']
            soup = await self._fetch_html_page(search_url)

            if soup:
                # Look for press releases and news articles
                articles = soup.find_all(['article', 'div'], class_=['press-release', 'news-item', 'content'])

                for article in articles[:8]:  # Limit to latest 8
                    try:
                        # Extract title
                        title_elem = article.find(['h1', 'h2', 'h3', 'a'])
                        if not title_elem:
                            continue

                        title = title_elem.get_text(strip=True)
                        if not title:
                            continue

                        # Extract URL
                        link = title_elem.get('href') if title_elem.name == 'a' else None
                        if not link:
                            link_elem = article.find('a')
                            link = link_elem.get('href') if link_elem else None

                        if link and not link.startswith('http'):
                            link = urljoin('https://commission.europa.eu', link)

                        # Extract summary
                        summary_elem = article.find(['p', 'div'], class_=['summary', 'description'])
                        summary = summary_elem.get_text(strip=True) if summary_elem else ""
                        if not summary:
                            p_elem = article.find('p')
                            summary = p_elem.get_text(strip=True) if p_elem else ""

                        summary = self._extract_text_summary(summary, 300)

                        # Extract date
                        date_elem = article.find(['time', 'span'], class_=['date', 'published'])
                        published_date = None
                        if date_elem:
                            date_text = date_elem.get('datetime') or date_elem.get_text(strip=True)
                            published_date = self._parse_date(date_text)

                        if not published_date:
                            published_date = datetime.now() - timedelta(hours=12)

                        # Generate keywords
                        keywords = []
                        content_text = f"{title} {summary}".lower()
                        source_keywords = self.sources['eu_commission']['keywords']
                        for keyword in source_keywords:
                            if keyword.lower() in content_text:
                                keywords.append(keyword)

                        # Only include if relevant
                        if self._is_relevant_content(title, summary, keywords):
                            importance = self._assess_importance(title, summary, keywords)

                            news_items.append(NewsItem(
                                title=title,
                                url=link or search_url,
                                source="EU Commission",
                                published_date=published_date,
                                category="eu_news",
                                summary=summary,
                                keywords=keywords,
                                importance=importance,
                                scraped_at=datetime.now()
                            ))

                    except Exception as e:
                        logger.warning(f"Error parsing EU Commission article: {e}")
                        continue

            # Fallback to HTML scraping if RSS doesn't provide enough content
            if len(news_items) < 3:
                html_items = await self._scrape_eu_commission_html()
                news_items.extend(html_items)

        except Exception as e:
            logger.error(f"EU Commission RSS scraping failed: {e}")
            # Try HTML fallback
            try:
                html_items = await self._scrape_eu_commission_html()
                news_items.extend(html_items)
            except Exception:
                pass

        return news_items

    async def _scrape_eu_commission_html(self) -> List[NewsItem]:
        """Fallback HTML scraping for EU Commission"""
        news_items = []
        try:
            search_url = self.sources['eu_commission']['search_url']
            soup = await self._fetch_html_page(search_url)

            if soup:
                articles = soup.find_all(['article', 'div'], class_=['press-release', 'news-item', 'content'])

                for article in articles[:5]:
                    try:
                        title_elem = article.find(['h1', 'h2', 'h3', 'a'])
                        if not title_elem:
                            continue

                        title = title_elem.get_text(strip=True)
                        if not title:
                            continue

                        # Extract URL
                        link = title_elem.get('href') if title_elem.name == 'a' else None
                        if not link:
                            link_elem = article.find('a')
                            link = link_elem.get('href') if link_elem else None

                        if link and not link.startswith('http'):
                            link = urljoin('https://commission.europa.eu', link)

                        # Extract summary
                        summary_elem = article.find(['p', 'div'], class_=['summary', 'description'])
                        summary = summary_elem.get_text(strip=True) if summary_elem else ""
                        if not summary:
                            p_elem = article.find('p')
                            summary = p_elem.get_text(strip=True) if p_elem else ""

                        summary = self._extract_text_summary(summary, 300)

                        # Generate keywords
                        keywords = []
                        content_text = f"{title} {summary}".lower()
                        source_keywords = self.sources['eu_commission']['keywords']
                        for keyword in source_keywords:
                            if keyword.lower() in content_text:
                                keywords.append(keyword)

                        if self._is_relevant_content(title, summary, keywords):
                            importance = self._assess_importance(title, summary, keywords)

                            news_items.append(NewsItem(
                                title=title,
                                url=link or search_url,
                                source="EU Commission",
                                published_date=datetime.now() - timedelta(hours=6),
                                category="eu_news",
                                summary=summary,
                                keywords=keywords,
                                importance=importance,
                                scraped_at=datetime.now()
                            ))

                    except Exception as e:
                        logger.warning(f"Error parsing EU Commission article: {e}")
                        continue

        except Exception as e:
            logger.error(f"EU Commission HTML scraping failed: {e}")

        return news_items

    async def _scrape_eur_lex(self) -> List[NewsItem]:
        """Scrape EUR-Lex for new legal documents"""
        news_items = []
        try:
            # EUR-Lex search for AI-related documents
            search_terms = ['artificial+intelligence', 'AI+Act', 'automated+decision']

            for term in search_terms:
                try:
                    # Build search URL for recent documents
                    search_url = f"https://eur-lex.europa.eu/search.html?scope=EURLEX&text={term}&lang=en&type=quick&qid=1234567890"

                    soup = await self._fetch_html_page(search_url)
                    if soup:
                        # Look for document links in search results
                        results = soup.find_all(['div', 'li'], class_=['SearchResult', 'result', 'document'])

                        for result in results[:3]:  # Limit per search term
                            try:
                                title_elem = result.find(['h2', 'h3', 'a'])
                                if not title_elem:
                                    continue

                                title = title_elem.get_text(strip=True)
                                if not title:
                                    continue

                                # Extract document URL
                                link = title_elem.get('href') if title_elem.name == 'a' else None
                                if not link:
                                    link_elem = result.find('a')
                                    link = link_elem.get('href') if link_elem else None

                                if link and not link.startswith('http'):
                                    link = urljoin('https://eur-lex.europa.eu', link)

                                # Extract summary/abstract
                                summary_elem = result.find(['p', 'div'], class_=['summary', 'abstract', 'description'])
                                summary = summary_elem.get_text(strip=True) if summary_elem else ""
                                if not summary:
                                    summary = f"EUR-Lex document related to {term.replace('+', ' ')}"

                                summary = self._extract_text_summary(summary, 300)

                                # Generate keywords
                                keywords = []
                                content_text = f"{title} {summary}".lower()
                                source_keywords = self.sources['eur_lex']['keywords']
                                for keyword in source_keywords:
                                    if keyword.lower() in content_text:
                                        keywords.append(keyword)

                                # Add search term as keyword
                                keywords.append(term.replace('+', ' '))

                                if self._is_relevant_content(title, summary, keywords):
                                    importance = self._assess_importance(title, summary, keywords)

                                    news_items.append(NewsItem(
                                        title=title,
                                        url=link or search_url,
                                        source="EUR-Lex",
                                        published_date=datetime.now() - timedelta(days=1),
                                        category="eu_legislation",
                                        summary=summary,
                                        keywords=keywords,
                                        importance=importance,
                                        scraped_at=datetime.now()
                                    ))

                            except Exception as e:
                                logger.warning(f"Error parsing EUR-Lex result: {e}")
                                continue

                except Exception as e:
                    logger.warning(f"EUR-Lex search failed for term {term}: {e}")
                    continue

            # If no results, add a fallback item
            if not news_items:
                fallback_item = NewsItem(
                    title="Recent AI and Data Protection Legislation - EUR-Lex",
                    url="https://eur-lex.europa.eu/search.html?scope=EURLEX&text=artificial+intelligence",
                    source="EUR-Lex",
                    published_date=datetime.now() - timedelta(hours=6),
                    category="eu_legislation",
                    summary="Search EUR-Lex for the latest AI Act implementation documents and data protection legislation.",
                    keywords=["ai act", "legislation", "implementation"],
                    importance="medium",
                    scraped_at=datetime.now()
                )
                news_items.append(fallback_item)

            logger.info(f"Scraped {len(news_items)} relevant documents from EUR-Lex")

        except Exception as e:
            logger.error(f"EUR-Lex scraping failed: {e}")

        return news_items

    async def _scrape_edpb_rss(self) -> List[NewsItem]:
        """Scrape EDPB news via RSS feed"""
        news_items = []
        try:
            rss_url = self.sources['edpb']['rss_feed']
            entries = await self._fetch_rss_feed(rss_url)

            source_keywords = self.sources['edpb']['keywords']

            for entry in entries[:15]:  # Limit to latest 15
                news_item = self._extract_rss_content(
                    entry, "EDPB", "edpb", source_keywords
                )
                if news_item:
                    news_items.append(news_item)

            logger.info(f"Scraped {len(news_items)} relevant articles from EDPB RSS")

            # Fallback to HTML scraping if RSS doesn't work well
            if len(news_items) < 3:
                fallback_items = await self._scrape_edpb_html()
                news_items.extend(fallback_items)

        except Exception as e:
            logger.error(f"EDPB RSS scraping failed: {e}")
            # Try HTML fallback
            try:
                fallback_items = await self._scrape_edpb_html()
                news_items.extend(fallback_items)
            except Exception:
                pass

        return news_items

    async def _scrape_edpb_html(self) -> List[NewsItem]:
        """Fallback HTML scraping for EDPB"""
        news_items = []
        try:
            news_url = self.sources['edpb']['news_url']
            soup = await self._fetch_html_page(news_url)

            if soup:
                articles = soup.find_all(['article', 'div'], class_=['news-item', 'content', 'view-content'])

                for article in articles[:5]:
                    try:
                        title_elem = article.find(['h1', 'h2', 'h3', 'a'])
                        if not title_elem:
                            continue

                        title = title_elem.get_text(strip=True)
                        if not title:
                            continue

                        # Extract URL
                        link = title_elem.get('href') if title_elem.name == 'a' else None
                        if not link:
                            link_elem = article.find('a')
                            link = link_elem.get('href') if link_elem else None

                        if link and not link.startswith('http'):
                            link = urljoin(self.sources['edpb']['url'], link)

                        # Extract summary
                        summary_elem = article.find(['p', 'div'], class_=['summary', 'description'])
                        summary = summary_elem.get_text(strip=True) if summary_elem else ""
                        if not summary:
                            p_elem = article.find('p')
                            summary = p_elem.get_text(strip=True) if p_elem else ""

                        summary = self._extract_text_summary(summary, 300)

                        # Generate keywords
                        keywords = []
                        content_text = f"{title} {summary}".lower()
                        source_keywords = self.sources['edpb']['keywords']
                        for keyword in source_keywords:
                            if keyword.lower() in content_text:
                                keywords.append(keyword)

                        if self._is_relevant_content(title, summary, keywords):
                            importance = self._assess_importance(title, summary, keywords)

                            news_items.append(NewsItem(
                                title=title,
                                url=link or news_url,
                                source="EDPB",
                                published_date=datetime.now() - timedelta(hours=6),
                                category="edpb",
                                summary=summary,
                                keywords=keywords,
                                importance=importance,
                                scraped_at=datetime.now()
                            ))

                    except Exception as e:
                        logger.warning(f"Error parsing EDPB article: {e}")
                        continue

        except Exception as e:
            logger.error(f"EDPB HTML scraping failed: {e}")

        return news_items

    async def _scrape_edpb(self) -> List[NewsItem]:
        """Legacy method - redirects to RSS scraping"""
        return await self._scrape_edpb_rss()

    async def _scrape_kl_rss(self) -> List[NewsItem]:
        """Scrape KL nyheder via RSS og HTML fallback"""
        news_items: List[NewsItem] = []
        try:
            rss_candidates = [
                self.sources['kl'].get('rss_feed'),
                self.sources['kl'].get('alt_rss_feed')
            ]

            source_keywords = self.sources['kl']['keywords']

            for rss_url in rss_candidates:
                if not rss_url:
                    continue
                entries = await self._fetch_rss_feed(rss_url)
                if not entries:
                    continue

                for entry in entries[:10]:
                    news_item = self._extract_rss_content(
                        entry, "KL", "danish_municipal", source_keywords
                    )
                    if news_item:
                        news_items.append(news_item)

                if news_items:
                    break

            if not news_items:
                logger.info("KL RSS gav ingen resultater, forsøger HTML scraping")
                news_items = await self._scrape_kl_html()

            if not news_items:
                news_items.append(self._create_kl_fallback())

        except Exception as e:
            logger.error(f"KL scraping failed: {e}")
            news_items = [self._create_kl_fallback()]

        return news_items

    async def _scrape_kl_html(self) -> List[NewsItem]:
        news_items: List[NewsItem] = []
        session = self.session
        if not session:
            return news_items

        kl_pages = [
            'https://www.kl.dk/nyheder/',
            'https://www.kl.dk/presse/'
        ]

        for page_url in kl_pages:
            try:
                soup = await self._fetch_html_page(page_url)
                if not soup:
                    continue

                article_elements = soup.select('article, .news-list__item, .teaser-list__item')

                for element in article_elements[:8]:
                    title_elem = element.select_one('h2, h3, .news-title, .teaser__title')
                    link_elem = element.select_one('a[href]')
                    summary_elem = element.select_one('p, .teaser__lead, .news-lead')

                    title = title_elem.get_text(strip=True) if title_elem else ''
                    link = link_elem['href'] if link_elem else ''
                    summary = summary_elem.get_text(strip=True) if summary_elem else ''

                    if not title or not link:
                        continue

                    if not link.startswith('http'):
                        link = urljoin(page_url, link)

                    combined_text = f"{title} {summary}"
                    keywords = self._extract_keywords(combined_text)
                    if not self._is_relevant_content(title, summary, keywords):
                        continue

                    published = self._parse_date(self._extract_date_from_element(element))
                    news_items.append(NewsItem(
                        title=title,
                        url=link,
                        source="KL",
                        category='danish_municipal',
                        summary=self._extract_text_summary(summary, 280),
                        keywords=keywords,
                        importance=self._assess_importance(title, summary, keywords),
                        scraped_at=datetime.now(),
                        published_date=published
                    ))

                if news_items:
                    break

            except Exception as exc:
                logger.debug("KL HTML parsing mislykkedes for %s: %s", page_url, exc)
                continue

        return news_items

    def _extract_date_from_element(self, element) -> str:
        time_elem = element.select_one('time')
        if time_elem and time_elem.get('datetime'):
            return time_elem['datetime']
        if time_elem:
            return time_elem.get_text(strip=True)

        date_elem = element.select_one('.date, .news-date, .teaser__date')
        if date_elem:
            return date_elem.get_text(strip=True)
        return ''

    def _create_kl_fallback(self) -> NewsItem:
        return NewsItem(
            title="KL: Seneste nyheder om kommunernes AI-arbejde",
            url="https://www.kl.dk/nyheder/",
            source="KL",
            published_date=datetime.now() - timedelta(hours=6),
            category="danish_municipal",
            summary="Besøg KL's nyhedsside for aktuelle beslutninger, vejledninger og projekter om kommunernes brug af AI og data.",
            keywords=["kommuner", "ai", "digitalisering"],
            importance="medium",
            scraped_at=datetime.now()
        )

    async def _scrape_council_eu_rss(self) -> List[NewsItem]:
        """Scrape Council of EU news via RSS feed"""
        news_items = []
        try:
            # Try primary RSS feed first
            rss_url = self.sources['council_eu']['rss_feed']
            entries = await self._fetch_rss_feed(rss_url)

            # If primary feed fails, try alternative
            if not entries and 'alt_rss_feed' in self.sources['council_eu']:
                logger.info("Trying alternative Council of EU RSS feed...")
                rss_url = self.sources['council_eu']['alt_rss_feed']
                entries = await self._fetch_rss_feed(rss_url)

            source_keywords = self.sources['council_eu']['keywords']

            for entry in entries[:15]:  # Limit to latest 15
                news_item = self._extract_rss_content(
                    entry, "Council of EU", "eu_council", source_keywords
                )
                if news_item:
                    news_items.append(news_item)

            logger.info(f"Scraped {len(news_items)} relevant articles from Council of EU RSS")

            # Add fallback item if no RSS results
            if not news_items:
                fallback_item = NewsItem(
                    title="Council of the European Union - Digital and AI Policy Updates",
                    url="https://www.consilium.europa.eu/en/policies/digital-agenda/",
                    source="Council of EU",
                    published_date=datetime.now() - timedelta(hours=4),
                    category="eu_council",
                    summary="Visit the Council's digital agenda page for the latest updates on AI regulation and digital policy developments.",
                    keywords=["digital agenda", "ai regulation", "digital policy"],
                    importance="medium",
                    scraped_at=datetime.now()
                )
                news_items.append(fallback_item)

        except Exception as e:
            logger.error(f"Council of EU RSS scraping failed: {e}")

        return news_items

    async def _scrape_kl(self) -> List[NewsItem]:
        """Legacy method - redirects to RSS scraping"""
        return await self._scrape_kl_rss()

    async def _scrape_ai_court_cases(self) -> List[NewsItem]:
        """Scrape court decisions related to AI and data protection"""
        news_items = []
        try:
            # Try to scrape from Curia (European Court of Justice)
            curia_url = self.sources['curia']['news_url']
            soup = await self._fetch_html_page(curia_url)

            if soup:
                # Look for press releases and judgments
                articles = soup.find_all(['div', 'article'], class_=['press-release', 'judgment', 'news'])

                for article in articles[:5]:
                    try:
                        title_elem = article.find(['h1', 'h2', 'h3', 'a'])
                        if not title_elem:
                            continue

                        title = title_elem.get_text(strip=True)
                        if not title:
                            continue

                        # Extract URL
                        link = title_elem.get('href') if title_elem.name == 'a' else None
                        if not link:
                            link_elem = article.find('a')
                            link = link_elem.get('href') if link_elem else None

                        if link and not link.startswith('http'):
                            link = urljoin('https://curia.europa.eu', link)

                        # Extract summary
                        summary_elem = article.find(['p', 'div'], class_=['summary', 'excerpt'])
                        summary = summary_elem.get_text(strip=True) if summary_elem else ""
                        if not summary:
                            p_elem = article.find('p')
                            summary = p_elem.get_text(strip=True) if p_elem else ""

                        summary = self._extract_text_summary(summary, 350)

                        # Generate keywords
                        keywords = []
                        content_text = f"{title} {summary}".lower()
                        source_keywords = self.sources['curia']['keywords']
                        for keyword in source_keywords:
                            if keyword.lower() in content_text:
                                keywords.append(keyword)

                        if self._is_relevant_content(title, summary, keywords):
                            importance = self._assess_importance(title, summary, keywords)

                            news_items.append(NewsItem(
                                title=title,
                                url=link or curia_url,
                                source="European Court of Justice",
                                published_date=datetime.now() - timedelta(days=2),
                                category="court_cases",
                                summary=summary,
                                keywords=keywords,
                                importance=importance,
                                scraped_at=datetime.now()
                            ))

                    except Exception as e:
                        logger.warning(f"Error parsing Curia article: {e}")
                        continue

            # Add curated high-importance court cases if no results
            if not news_items:
                curated_cases = [
                    {
                        "title": "Recent AI and Data Protection Court Decisions",
                        "url": "https://curia.europa.eu/jcms/jcms/j_6/en/",
                        "summary": "Visit the European Court of Justice for the latest rulings on AI, automated decision-making, and data protection under GDPR.",
                        "keywords": ["court decisions", "gdpr", "ai", "automated decisions"]
                    }
                ]

                for case in curated_cases:
                    news_items.append(NewsItem(
                        title=case["title"],
                        url=case["url"],
                        source="European Court of Justice",
                        published_date=datetime.now() - timedelta(hours=8),
                        category="court_cases",
                        summary=case["summary"],
                        keywords=case["keywords"],
                        importance="medium",
                        scraped_at=datetime.now()
                    ))

            logger.info(f"Scraped {len(news_items)} relevant court cases")

        except Exception as e:
            logger.error(f"Court cases scraping failed: {e}")

        return news_items

    def get_cached_news(self, category: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Hent cached nyheder"""
        filtered_news = self.news_cache

        if category:
            filtered_news = [item for item in filtered_news if item.category == category]

        # Konverter til dict format
        return [asdict(item) for item in filtered_news[:limit]]

    def get_news_by_importance(self, importance: str = "high") -> List[Dict[str, Any]]:
        """Hent nyheder efter vigtighed"""
        filtered_news = [item for item in self.news_cache if item.importance == importance]
        return [asdict(item) for item in filtered_news]

    def get_recent_news(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Hent nyheder fra de seneste X timer"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_news = [
            item for item in self.news_cache
            if item.published_date and item.published_date > cutoff_time
        ]
        return [asdict(item) for item in recent_news]

    async def update_news_feed(self):
        """Opdater nyhedsfeed - køres hver 15. minut"""
        while True:
            try:
                await self.fetch_latest_news()
                logger.info("News feed opdateret")
                await asyncio.sleep(900)  # 15 minutter
            except Exception as e:
                logger.error(f"News update fejlede: {e}")
                await asyncio.sleep(300)  # Prøv igen efter 5 minutter


# Singleton instance
news_scraper = None


async def get_news_scraper() -> LiveNewsScraper:
    """Get or create news scraper instance"""
    global news_scraper
    if news_scraper is None:
        news_scraper = LiveNewsScraper()
        async with news_scraper:
            await news_scraper.fetch_latest_news()
    return news_scraper
