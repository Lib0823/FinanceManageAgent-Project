"""News Collection Module - RSS Feed + Stock-Specific Crawling

Two-track approach:
- Track 1: Market-wide RSS feed (for Vue3 dashboard visualization)
- Track 2: Stock-specific crawling (for Gemini AI decision input)
"""
import asyncio
import aiohttp
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class NewsCollector:
    """Collect news from RSS feeds and web scraping for sentiment analysis."""

    # Track 1: Market-wide RSS sources
    RSS_SOURCES = [
        'https://www.hankyung.com/feed/finance',
        'https://www.mk.co.kr/rss/30000001/',
        'https://www.yonhapnews.co.kr/rss/economy.xml'
    ]

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def collect_market_news(self, cutoff_time: Optional[datetime] = None) -> List[Dict]:
        """
        Track 1: Collect market-wide news from RSS feeds.

        Args:
            cutoff_time: Only include news after this time (default: yesterday 18:00)

        Returns:
            List of articles: [{title, summary, published, source}]
        """
        if cutoff_time is None:
            # Default: yesterday 18:00 KST
            cutoff_time = datetime.now().replace(hour=18, minute=0, second=0, microsecond=0) - timedelta(days=1)

        all_articles = []

        for rss_url in self.RSS_SOURCES:
            try:
                articles = await self._fetch_rss_feed(rss_url, cutoff_time)
                all_articles.extend(articles)
                logger.info(f"Collected {len(articles)} articles from {rss_url}")

            except Exception as e:
                logger.error(f"Failed to fetch RSS feed {rss_url}: {e}")

        # Remove duplicates by title prefix (first 20 chars)
        unique_articles = self._deduplicate_articles(all_articles, key_length=20)

        logger.info(f"Total market news collected: {len(unique_articles)} (after deduplication)")
        return unique_articles

    async def _fetch_rss_feed(self, rss_url: str, cutoff_time: datetime) -> List[Dict]:
        """
        Fetch and parse RSS feed.

        Args:
            rss_url: RSS feed URL
            cutoff_time: Minimum publish time

        Returns:
            List of articles
        """
        try:
            if self.session is None:
                raise RuntimeError("Session not initialized. Use 'async with' context manager.")

            async with self.session.get(rss_url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                response.raise_for_status()
                xml_content = await response.text()

            feed = feedparser.parse(xml_content)
            articles = []

            for entry in feed.entries:
                try:
                    # Parse publication time
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_time = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        pub_time = datetime(*entry.updated_parsed[:6])
                    else:
                        continue  # Skip if no time information

                    # Filter by cutoff time
                    if pub_time < cutoff_time:
                        continue

                    # Extract summary/description
                    summary = ''
                    if hasattr(entry, 'summary'):
                        summary = entry.summary[:200]  # First 200 chars
                    elif hasattr(entry, 'description'):
                        summary = entry.description[:200]

                    articles.append({
                        'title': entry.title if hasattr(entry, 'title') else '',
                        'summary': summary,
                        'published': pub_time,
                        'source': rss_url
                    })

                except Exception as e:
                    logger.warning(f"Failed to parse RSS entry: {e}")

            return articles

        except Exception as e:
            logger.error(f"RSS fetch failed for {rss_url}: {e}")
            return []

    def _deduplicate_articles(self, articles: List[Dict], key_length: int = 20) -> List[Dict]:
        """
        Remove duplicate articles based on title prefix.

        Args:
            articles: List of article dicts
            key_length: Length of title prefix to use as deduplication key

        Returns:
            Deduplicated list of articles
        """
        seen_keys = set()
        unique_articles = []

        for article in articles:
            title = article.get('title', '')
            key = title[:key_length].lower().strip()

            if key and key not in seen_keys:
                seen_keys.add(key)
                unique_articles.append(article)

        return unique_articles

    async def collect_stock_news(self, stock_code: str, max_articles: int = 5) -> List[Dict]:
        """
        Track 2: Collect stock-specific news via Naver Finance crawling.

        Args:
            stock_code: 6-digit stock code
            max_articles: Maximum number of articles to collect

        Returns:
            List of articles: [{title, content, published, url}]
        """
        try:
            # Use .nhn extension (Naver's legacy format)
            url = f'https://finance.naver.com/item/news_news.nhn?code={stock_code}&page=1'

            if self.session is None:
                raise RuntimeError("Session not initialized. Use 'async with' context manager.")

            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                response.raise_for_status()
                html = await response.text()

            soup = BeautifulSoup(html, 'html.parser')
            articles = []

            # Find news items in table - try multiple selectors
            news_items = soup.select('.tb_cont tr')
            if not news_items:
                # Fallback: try different selector
                news_items = soup.select('table.type5 tr')

            news_items = news_items[:max_articles * 2]  # Fetch extra for filtering

            for item in news_items:
                try:
                    # Try multiple selector patterns for title
                    title_element = item.select_one('.title a')
                    if not title_element:
                        title_element = item.select_one('td a')

                    # Try multiple selector patterns for date
                    date_element = item.select_one('.date')
                    if not date_element:
                        date_element = item.select_one('td.date')

                    if not title_element or not date_element:
                        continue

                    title = title_element.text.strip()
                    link = title_element.get('href', '')
                    date_str = date_element.text.strip()

                    # Skip if link is empty
                    if not link:
                        continue

                    # Parse date (YYYY.MM.DD HH:MM format)
                    published = self._parse_naver_date(date_str)

                    # Fetch full article content
                    content = await self._fetch_article_content(link)

                    articles.append({
                        'title': title,
                        'content': content[:200] if content else title[:200],  # Fallback to title if content empty
                        'published': published,
                        'url': link
                    })

                    if len(articles) >= max_articles:
                        break

                except Exception as e:
                    logger.warning(f"Failed to parse news item for {stock_code}: {e}")

            logger.info(f"Collected {len(articles)} stock-specific news for {stock_code}")
            return articles

        except Exception as e:
            logger.error(f"Stock news collection failed for {stock_code}: {e}")
            return []

    async def _fetch_article_content(self, url: str) -> str:
        """
        Fetch full article content from Naver News URL.

        Args:
            url: Article URL

        Returns:
            Article content text
        """
        try:
            # Convert relative URL to absolute
            if url.startswith('/'):
                url = f'https://finance.naver.com{url}'

            if self.session is None:
                return ''

            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response.raise_for_status()
                html = await response.text()

            soup = BeautifulSoup(html, 'html.parser')

            # Find article body (Naver News structure)
            article_body = soup.select_one('#news_read')
            if not article_body:
                article_body = soup.select_one('.articleCont')

            if article_body:
                # Remove scripts and styles
                for script in article_body(['script', 'style']):
                    script.decompose()

                text = article_body.get_text(separator=' ', strip=True)
                return text

            return ''

        except Exception as e:
            logger.warning(f"Failed to fetch article content: {e}")
            return ''

    def _parse_naver_date(self, date_str: str) -> datetime:
        """
        Parse Naver date format (YYYY.MM.DD HH:MM) to datetime.

        Args:
            date_str: Date string from Naver

        Returns:
            datetime object
        """
        try:
            return datetime.strptime(date_str, '%Y.%m.%d %H:%M')
        except ValueError:
            try:
                # Fallback: try without time
                return datetime.strptime(date_str, '%Y.%m.%d')
            except ValueError:
                # Return current time if parsing fails
                return datetime.now()
