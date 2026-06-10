"""Sentiment Analysis Module - Stage 2-2

Two-track sentiment analysis using KR-FinBERT:
- Track 1: Market-wide RSS feed → sentiment_market (for Vue3 dashboard)
- Track 2: Stock-specific crawling → sentiment_score (for Gemini AI input)

Output: 1 feature per stock (sentiment_score)
"""
import pandas as pd
from typing import List, Dict
from datetime import datetime
import logging

from collectors.news_collector import NewsCollector
from models.kr_finbert import KRFinBERTAnalyzer

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """Sentiment analysis orchestrator using KR-FinBERT."""

    def __init__(self):
        """Initialize sentiment analyzer with KR-FinBERT model."""
        self.kr_finbert = KRFinBERTAnalyzer()
        logger.info("SentimentAnalyzer initialized")

    async def analyze_stocks(self, stock_codes: List[str]) -> pd.DataFrame:
        """
        Perform sentiment analysis for filtered stocks.

        Args:
            stock_codes: List of stock codes (30 filtered stocks)

        Returns:
            DataFrame with columns: stock_code, sentiment_score
        """
        logger.info(f"Starting sentiment analysis for {len(stock_codes)} stocks")

        async with NewsCollector() as collector:
            # Track 1: Market sentiment (calculated FIRST as fallback)
            market_sentiment = await self._analyze_market_sentiment(collector)
            logger.info(f"Market sentiment will be used as fallback: {market_sentiment:.4f}")

            # Track 2: Stock-specific sentiment (for Gemini)
            stock_sentiments = await self._analyze_stock_specific(
                stock_codes,
                collector,
                fallback_sentiment=market_sentiment
            )

        # Return stock-specific sentiments for Gemini
        return stock_sentiments

    async def _analyze_stock_specific(
        self,
        stock_codes: List[str],
        collector: NewsCollector,
        fallback_sentiment: float = 0.0
    ) -> pd.DataFrame:
        """
        Track 2: Analyze stock-specific news (Naver Finance crawling).

        Args:
            stock_codes: List of stock codes
            collector: NewsCollector instance
            fallback_sentiment: Sentiment score to use when stock news not available

        Returns:
            DataFrame with columns: stock_code, sentiment_score
        """
        results = []

        for stock_code in stock_codes:
            try:
                # Collect top 5 recent news for this stock
                articles = await collector.collect_stock_news(stock_code, max_articles=5)

                if not articles:
                    logger.warning(f"No news found for {stock_code}, using market sentiment: {fallback_sentiment:.4f}")
                    sentiment_score = fallback_sentiment
                else:
                    # Time-weighted sentiment (newest articles have higher weight)
                    sentiment_score = self.kr_finbert.analyze_multiple_time_weighted(articles)

                results.append({
                    'stock_code': stock_code,
                    'sentiment_score': sentiment_score
                })

                logger.debug(f"{stock_code}: sentiment_score = {sentiment_score:.4f}")

            except Exception as e:
                logger.error(f"Sentiment analysis failed for {stock_code}: {e}")
                # Fallback to market sentiment
                results.append({
                    'stock_code': stock_code,
                    'sentiment_score': fallback_sentiment
                })

        df = pd.DataFrame(results)
        logger.info(f"Stock-specific sentiment analysis complete: {len(df)} stocks")

        return df

    async def _analyze_market_sentiment(self, collector: NewsCollector) -> float:
        """
        Track 1: Analyze market-wide sentiment (RSS feeds).

        This is stored separately for Vue3 dashboard visualization.

        Args:
            collector: NewsCollector instance

        Returns:
            float: Market sentiment score (-1.0 to 1.0)
        """
        try:
            # Collect market news from RSS feeds
            articles = await collector.collect_market_news()

            if not articles:
                logger.warning("No market news collected, using neutral sentiment")
                return 0.0

            # Simple average for market sentiment
            market_score = self.kr_finbert.analyze_multiple_simple_average(articles)

            logger.info(f"Market sentiment score: {market_score:.4f} (from {len(articles)} articles)")

            return market_score

        except Exception as e:
            logger.error(f"Market sentiment analysis failed: {e}")
            return 0.0

    def save_market_sentiment(self, sentiment_score: float, trade_date: datetime):
        """
        Save market-wide sentiment to database (for Vue3 dashboard).

        Args:
            sentiment_score: Market sentiment score
            trade_date: Trading date
        """
        # This will be integrated with database repository
        # For now, just log it
        logger.info(f"Market sentiment on {trade_date.date()}: {sentiment_score:.4f}")

    def validate_sentiment_scores(self, df: pd.DataFrame) -> Dict[str, bool]:
        """
        Validate sentiment scores for data quality.

        Args:
            df: DataFrame with sentiment_score column

        Returns:
            dict: {validation_metric: is_valid}
        """
        validation_results = {}

        # Check for required column
        validation_results['sentiment_score_exists'] = 'sentiment_score' in df.columns

        if 'sentiment_score' in df.columns and len(df) > 0:
            # Check value range (-1.0 to 1.0)
            validation_results['sentiment_range'] = df['sentiment_score'].between(-1.0, 1.0).all()

            # Check for excessive neutral scores (might indicate collection failure)
            neutral_ratio = (df['sentiment_score'] == 0.0).sum() / len(df)
            validation_results['diverse_sentiments'] = neutral_ratio < 0.8  # Less than 80% neutral

            # Check for NaN values
            validation_results['no_nan'] = not df['sentiment_score'].isna().any()

        return validation_results
