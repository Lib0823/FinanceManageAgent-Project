"""Quantitative Analysis Module - Stage 2-1

Computes 7 quantitative features for filtered top 30 stocks:

KIS-based features (4):
- morning_return: (10시 종가 - 시가) / 시가 × 100
- close_position: (종가 - 저가) / (고가 - 저가)
- foreign_net_buy: 외국인 순매수 금액 (원)
- institutional_net_buy: 기관 순매수 금액 (원)

DART-based features (3):
- per: Price/Earnings Ratio (None for loss-making companies)
- roe: Return on Equity (%)
- operating_margin: Operating Profit / Revenue (%)
"""
import pandas as pd
import numpy as np
from typing import List, Dict
from datetime import datetime, timedelta

from collectors.kis_client import KISClient
from collectors.dart_client import DARTClient


class QuantitativeAnalyzer:
    """Quantitative feature engineering for stock analysis."""

    def __init__(self, kis_client: KISClient = None):
        """
        Initialize quantitative analyzer.

        Args:
            kis_client: Optional KISClient instance (shares OAuth token cache if provided)
        """
        self.kis_client = kis_client if kis_client is not None else KISClient()
        self.dart_client = DARTClient()

    async def analyze_stocks(
        self,
        stock_codes: List[str],
        trade_date: datetime,
        stage1_data: pd.DataFrame = None
    ) -> pd.DataFrame:
        """
        Compute 7 quantitative features for given stocks.

        Args:
            stock_codes: List of stock codes (30 filtered stocks)
            trade_date: Target trading date
            stage1_data: Optional pre-fetched data from Stage 1 (contains foreign_net_buy,
                        institutional_net_buy, close_position) to avoid duplicate API calls

        Returns:
            DataFrame with columns: stock_code, morning_return, close_position,
                                   foreign_net_buy, institutional_net_buy,
                                   per, roe, operating_margin
        """
        # 1. Collect KIS-based features (reuse Stage 1 data if available)
        kis_features = await self._collect_kis_features(stock_codes, trade_date, stage1_data)

        # 2. Collect DART-based features (DB query only)
        dart_features = self.dart_client.get_latest_financials(stock_codes)

        # 3. Merge features
        result_df = pd.merge(kis_features, dart_features, on='stock_code', how='left')

        # 4. Apply outlier clipping (NumPy percentile 99)
        result_df = self._apply_outlier_clipping(result_df)

        return result_df

    async def _collect_kis_features(
        self,
        stock_codes: List[str],
        trade_date: datetime,
        stage1_data: pd.DataFrame = None
    ) -> pd.DataFrame:
        """
        Collect KIS API-based features for all stocks.

        Args:
            stock_codes: List of stock codes
            trade_date: Target trading date
            stage1_data: Pre-fetched data from Stage 1 (contains foreign_net_buy,
                        institutional_net_buy, close_position)

        Returns:
            DataFrame with columns: stock_code, morning_return, close_position,
                                   foreign_net_buy, institutional_net_buy
        """
        features_list = []

        # Convert stage1_data to dict for fast lookup
        stage1_dict = {}
        if stage1_data is not None and not stage1_data.empty:
            stage1_dict = stage1_data.set_index('stock_code').to_dict('index')

        for stock_code in stock_codes:
            try:
                # REUSE Stage 1 data if available (avoid duplicate API calls)
                stage1_row = stage1_dict.get(stock_code, {})

                # Get morning return (only data not in Stage 1)
                morning_return = await self._calculate_morning_return(stock_code, trade_date)

                # REUSE close_position from Stage 1 if available, otherwise calculate
                if 'close_position' in stage1_row:
                    close_position = stage1_row['close_position']
                else:
                    close_position = await self._calculate_close_position(stock_code, trade_date)

                # REUSE supply/demand from Stage 1 if available, otherwise fetch
                if 'foreign_net_buy' in stage1_row and 'institutional_net_buy' in stage1_row:
                    foreign_net_buy = stage1_row['foreign_net_buy']
                    institutional_net_buy = stage1_row['institutional_net_buy']
                else:
                    supply_demand = await self.kis_client.get_supply_demand(stock_code)
                    foreign_net_buy = supply_demand['foreign_net_buy']
                    institutional_net_buy = supply_demand['institutional_net_buy']

                features_list.append({
                    'stock_code': stock_code,
                    'morning_return': morning_return,
                    'close_position': close_position,
                    'foreign_net_buy': foreign_net_buy,
                    'institutional_net_buy': institutional_net_buy
                })

            except Exception as e:
                print(f"[QuantitativeAnalyzer] Failed to collect KIS features for {stock_code}: {e}")
                # Fill with default values to prevent pipeline failure
                features_list.append({
                    'stock_code': stock_code,
                    'morning_return': 0.0,
                    'close_position': 0.5,
                    'foreign_net_buy': 0,
                    'institutional_net_buy': 0
                })

        return pd.DataFrame(features_list)

    async def _calculate_morning_return(self, stock_code: str, trade_date: datetime) -> float:
        """
        Calculate morning return: (10시 종가 - 시가) / 시가 × 100

        Args:
            stock_code: Stock code
            trade_date: Target trading date

        Returns:
            float: Morning return percentage (양수: 매수세, 음수: 매도 압력)
        """
        try:
            # Get previous trading day
            prev_date = self._get_previous_trading_day(trade_date)

            # Get minute data for 09:00-10:00 period
            minute_df = await self.kis_client.get_minute_data(stock_code, prev_date)

            if minute_df.empty:
                return 0.0

            # Get first and last prices in 09:00-10:00 window
            first_price = minute_df.iloc[0]['open_price']
            last_price = minute_df.iloc[-1]['close_price']

            if first_price == 0:
                return 0.0

            morning_return = ((last_price - first_price) / first_price) * 100
            return round(morning_return, 4)

        except Exception as e:
            print(f"[QuantitativeAnalyzer] Morning return calculation failed for {stock_code}: {e}")
            return 0.0

    async def _calculate_close_position(self, stock_code: str, trade_date: datetime) -> float:
        """
        Calculate close position: (종가 - 저가) / (고가 - 저가)

        Args:
            stock_code: Stock code
            trade_date: Target trading date

        Returns:
            float: Close position (0.0~1.0, 1에 가까울수록 강세 마감)
        """
        try:
            # Get previous trading day OHLC
            prev_date = self._get_previous_trading_day(trade_date)
            ohlcv_df = await self.kis_client.get_daily_ohlcv(stock_code, days=1)

            if ohlcv_df.empty:
                return 0.5

            row = ohlcv_df.iloc[-1]  # Latest trading day
            high = row['high']
            low = row['low']
            close = row['close']

            if high == low:  # Avoid division by zero
                return 0.5

            close_position = (close - low) / (high - low)
            return round(close_position, 4)

        except Exception as e:
            print(f"[QuantitativeAnalyzer] Close position calculation failed for {stock_code}: {e}")
            return 0.5

    def _get_previous_trading_day(self, trade_date: datetime) -> str:
        """
        Get previous trading day (simplified: assumes prev business day).

        Args:
            trade_date: Current trading date

        Returns:
            str: Previous trading date in YYYYMMDD format
        """
        prev_date = trade_date - timedelta(days=1)

        # Skip weekend (simplified logic, doesn't account for holidays)
        while prev_date.weekday() >= 5:  # Saturday=5, Sunday=6
            prev_date -= timedelta(days=1)

        return prev_date.strftime('%Y%m%d')

    def _apply_outlier_clipping(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply NumPy percentile 99 clipping to prevent extreme outliers.

        Args:
            df: DataFrame with quantitative features

        Returns:
            DataFrame with clipped values
        """
        clipped_df = df.copy()

        # Define columns to clip (exclude stock_code, per, roe, operating_margin)
        clip_columns = ['morning_return', 'close_position', 'foreign_net_buy', 'institutional_net_buy']

        for col in clip_columns:
            if col in clipped_df.columns:
                valid_values = clipped_df[col].dropna()

                # Only clip if we have enough data points
                if len(valid_values) >= 2:
                    p99 = np.percentile(valid_values, 99)
                    p1 = np.percentile(valid_values, 1)
                    clipped_df[col] = clipped_df[col].clip(lower=p1, upper=p99)

        # Replace NaN and Infinity with safe values for JSON serialization
        clipped_df = clipped_df.replace([np.inf, -np.inf], np.nan)
        clipped_df = clipped_df.fillna(0)

        return clipped_df

    def validate_features(self, df: pd.DataFrame) -> Dict[str, bool]:
        """
        Validate computed features for data quality.

        Returns:
            dict: {feature_name: is_valid}
        """
        validation_results = {}

        # Check for required columns
        required_columns = ['stock_code', 'morning_return', 'close_position',
                           'foreign_net_buy', 'institutional_net_buy',
                           'per', 'roe', 'operating_margin']

        for col in required_columns:
            validation_results[f'{col}_exists'] = col in df.columns

        # Check for excessive NaN values
        if len(df) > 0:
            for col in required_columns[1:]:  # Exclude stock_code
                if col in df.columns:
                    nan_ratio = df[col].isna().sum() / len(df)
                    validation_results[f'{col}_completeness'] = nan_ratio < 0.5

        # Check for expected value ranges
        if 'close_position' in df.columns:
            validation_results['close_position_range'] = (df['close_position'].between(0, 1).all())

        return validation_results
