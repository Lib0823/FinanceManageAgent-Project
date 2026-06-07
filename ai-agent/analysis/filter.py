"""Stock filtering using StandardScaler and weighted scoring."""
import logging
from typing import List, Optional
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler

from config.constants import FILTER_WEIGHTS, TOP_N_STOCKS, STOCK_NAMES

logger = logging.getLogger(__name__)


class StockFilter:
    """
    KOSPI 100 → Top 30 stock filter using StandardScaler normalization.

    Scoring Formula:
        score = |foreign_net_buy| * 0.3
              + |institutional_net_buy| * 0.3
              + volume_ratio * 0.3
              + price_volatility * 0.1

    Features:
    - StandardScaler normalization (fit on daily 100 stocks)
    - Absolute value for foreign/institutional net buy (강한 움직임 포착)
    - Always includes holdings for sell analysis
    """

    def __init__(self):
        self.scaler = StandardScaler()
        self.weights = FILTER_WEIGHTS
        logger.info("StockFilter initialized with weights: %s", self.weights)

    def calculate_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate weighted scores for stock filtering.

        Args:
            df: DataFrame with columns:
                - stock_code
                - foreign_net_buy
                - institutional_net_buy
                - volume_ratio
                - price_volatility

        Returns:
            DataFrame with added columns:
                - final_score: Weighted sum of normalized features
                - is_selected: Top 30 selection flag
        """
        if df.empty:
            logger.warning("Empty DataFrame provided to calculate_scores")
            return df

        logger.info(f"Calculating scores for {len(df)} stocks")

        # Create copy to avoid modifying original
        result_df = df.copy()

        # Use absolute values for foreign/institutional net buy
        # (매수/매도 모두 강한 움직임으로 해석)
        features = pd.DataFrame({
            'foreign_net_buy_abs': np.abs(result_df['foreign_net_buy']),
            'institutional_net_buy_abs': np.abs(result_df['institutional_net_buy']),
            'volume_ratio': result_df['volume_ratio'],
            'price_volatility': result_df['price_volatility']
        })

        # StandardScaler normalization (매일 새로 fit)
        # 당일 100개 종목 기준으로 상대 비교
        try:
            normalized = self.scaler.fit_transform(features)
        except Exception as e:
            logger.error(f"StandardScaler fit_transform failed: {e}")
            # Fallback: use raw values
            normalized = features.values

        # Weighted sum scoring
        scores = (
            normalized[:, 0] * self.weights['foreign_net_buy'] +
            normalized[:, 1] * self.weights['institution_net_buy'] +
            normalized[:, 2] * self.weights['volume_ratio'] +
            normalized[:, 3] * self.weights['price_volatility']
        )

        result_df['final_score'] = scores

        # Sort by score descending
        result_df = result_df.sort_values('final_score', ascending=False).reset_index(drop=True)

        # Mark top 30 as selected (or all if fewer stocks available)
        result_df['is_selected'] = False
        actual_top_n = min(TOP_N_STOCKS, len(result_df))
        result_df.loc[:actual_top_n - 1, 'is_selected'] = True

        logger.info(f"Score range: {scores.min():.2f} ~ {scores.max():.2f}")
        if len(result_df) >= TOP_N_STOCKS:
            logger.info(f"Top {TOP_N_STOCKS} selected with score threshold: {result_df.loc[TOP_N_STOCKS - 1, 'final_score']:.2f}")
        else:
            logger.warning(f"Only {len(result_df)} stocks available (target: {TOP_N_STOCKS}), selecting all")
            logger.info(f"Minimum score: {result_df.loc[actual_top_n - 1, 'final_score']:.2f}")

        return result_df

    def filter_top_n(
        self,
        df: pd.DataFrame,
        holdings: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Select top N stocks with optional holdings inclusion.

        Args:
            df: DataFrame with calculated scores and is_selected flag
            holdings: List of stock codes to always include (for sell analysis)

        Returns:
            DataFrame with top N stocks (+ holdings if not in top N)
        """
        if df.empty:
            logger.warning("Empty DataFrame provided to filter_top_n")
            return df

        # Get initially selected top N
        top_n_df = df[df['is_selected'] == True].copy()

        # If holdings provided, ensure they're included
        if holdings:
            logger.info(f"Ensuring {len(holdings)} holdings are included")
            holdings_set = set(holdings)
            already_selected = set(top_n_df['stock_code'])

            # Find holdings not in top N
            missing_holdings = holdings_set - already_selected

            if missing_holdings:
                logger.info(f"Adding {len(missing_holdings)} holdings not in top 30: {missing_holdings}")

                # Get missing holdings from original df
                missing_df = df[df['stock_code'].isin(missing_holdings)].copy()
                missing_df['is_selected'] = True

                # Concatenate and re-sort
                top_n_df = pd.concat([top_n_df, missing_df], ignore_index=True)
                top_n_df = top_n_df.sort_values('final_score', ascending=False).reset_index(drop=True)

        logger.info(f"Final selection: {len(top_n_df)} stocks")

        return top_n_df

    def process(
        self,
        stock_data: pd.DataFrame,
        holdings: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Complete filtering process: score calculation + top N selection.

        Args:
            stock_data: Raw stock data from KIS API
            holdings: Optional holdings to always include

        Returns:
            DataFrame with top N selected stocks and scores
        """
        logger.info("Starting stock filtering process")

        # Calculate scores
        scored_df = self.calculate_scores(stock_data)

        # Filter top N (+ holdings)
        filtered_df = self.filter_top_n(scored_df, holdings=holdings)

        # Add stock names
        filtered_df['stock_name'] = filtered_df['stock_code'].map(STOCK_NAMES).fillna('Unknown')

        logger.info("Stock filtering completed successfully")

        return filtered_df
