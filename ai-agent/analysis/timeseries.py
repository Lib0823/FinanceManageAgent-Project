"""Time-Series Analysis Module - Stage 2-3

Uses Prophet for 120-day training → D+1 to D+5 forecasting.
No database storage (daily fit, no model persistence).

Output: 3 features per stock
- prophet_price_trend: Linear slope of D+1~D+5 price predictions
- prophet_volume_trend: Linear slope of D+1~D+5 buy ratio predictions
- prophet_price_uncertainty: Average confidence interval width
"""
import pandas as pd
import numpy as np
from typing import List, Dict
from datetime import datetime
import logging

from collectors.kis_client import KISClient
from models.prophet_trainer import ProphetForecaster

logger = logging.getLogger(__name__)


class TimeSeriesAnalyzer:
    """Time-series forecasting using Prophet for stock analysis."""

    def __init__(self, kis_client: 'KISClient' = None, lookback_days: int = 120):
        """
        Initialize time-series analyzer.

        Args:
            kis_client: Optional KISClient instance (shares OAuth token cache if provided)
            lookback_days: Training period for Prophet (default: 120 trading days)
        """
        from collectors.kis_client import KISClient
        self.kis_client = kis_client if kis_client is not None else KISClient()
        self.prophet = ProphetForecaster(lookback_days=lookback_days, forecast_days=5)
        self.lookback_days = lookback_days

        logger.info(f"TimeSeriesAnalyzer initialized (lookback={lookback_days} days)")

    async def analyze_stocks(self, stock_codes: List[str]) -> pd.DataFrame:
        """
        Perform time-series analysis for filtered stocks.

        Args:
            stock_codes: List of stock codes (30 filtered stocks)

        Returns:
            DataFrame with columns: stock_code, prophet_price_trend,
                                   prophet_volume_trend, prophet_price_uncertainty
        """
        logger.info(f"Starting time-series analysis for {len(stock_codes)} stocks")

        results = []

        for stock_code in stock_codes:
            try:
                # Analyze single stock
                features = await self._analyze_single_stock(stock_code)
                results.append(features)

                logger.debug(f"{stock_code}: price_trend={features['prophet_price_trend']:.4f}, "
                           f"volume_trend={features['prophet_volume_trend']:.4f}, "
                           f"uncertainty={features['prophet_price_uncertainty']:.2f}")

            except Exception as e:
                logger.error(f"Time-series analysis failed for {stock_code}: {e}")
                # Fallback to neutral values
                results.append({
                    'stock_code': stock_code,
                    'prophet_price_trend': 0.0,
                    'prophet_volume_trend': 0.0,
                    'prophet_price_uncertainty': 0.0
                })

        df = pd.DataFrame(results)
        logger.info(f"Time-series analysis complete: {len(df)} stocks")

        return df

    async def _analyze_single_stock(self, stock_code: str) -> Dict:
        """
        Analyze single stock with Prophet forecasting.

        Args:
            stock_code: Stock code

        Returns:
            dict: {stock_code, prophet_price_trend, prophet_volume_trend, prophet_price_uncertainty,
                   plus detailed D+1~D+5 values for web display}
        """
        # 1. Prepare price series (120-day OHLCV)
        price_series = await self._prepare_price_series(stock_code)

        # 2. Prepare volume (buy ratio) series (120-day minute data)
        volume_series = await self._prepare_buy_ratio_series(stock_code)

        # 3. Forecast price
        price_forecast = self.prophet.train_and_forecast(price_series)
        prophet_price_trend = self.prophet.calculate_trend_slope(price_forecast['yhat'])
        prophet_price_uncertainty = self.prophet.calculate_uncertainty(
            price_forecast['yhat_lower'],
            price_forecast['yhat_upper']
        )

        # 4. Forecast volume (buy ratio)
        volume_forecast = self.prophet.train_and_forecast(volume_series)
        prophet_volume_trend = self.prophet.calculate_trend_slope(volume_forecast['yhat'])

        # 5. Extract detailed D+1~D+5 values for web display
        result = {
            'stock_code': stock_code,
            'prophet_price_trend': prophet_price_trend,
            'prophet_volume_trend': prophet_volume_trend,
            'prophet_price_uncertainty': prophet_price_uncertainty
        }

        # Add detailed price predictions (D+1 to D+5)
        if len(price_forecast['yhat']) >= 5:
            for i in range(5):
                result[f'yhat_price_d{i+1}'] = float(price_forecast['yhat'][i])
                result[f'yhat_price_lower_d{i+1}'] = float(price_forecast['yhat_lower'][i])
                result[f'yhat_price_upper_d{i+1}'] = float(price_forecast['yhat_upper'][i])

        # Add detailed volume predictions (D+1 to D+5)
        if len(volume_forecast['yhat']) >= 5:
            for i in range(5):
                result[f'yhat_volume_d{i+1}'] = float(volume_forecast['yhat'][i])
                result[f'yhat_volume_lower_d{i+1}'] = float(volume_forecast['yhat_lower'][i])
                result[f'yhat_volume_upper_d{i+1}'] = float(volume_forecast['yhat_upper'][i])

        return result

    async def _prepare_price_series(self, stock_code: str) -> pd.DataFrame:
        """
        Prepare price series for Prophet training.

        Args:
            stock_code: Stock code

        Returns:
            DataFrame with columns 'ds' (date) and 'y' (close price)
        """
        try:
            # Fetch 120-day OHLCV
            ohlcv_df = await self.kis_client.get_daily_ohlcv(stock_code, days=self.lookback_days)

            if ohlcv_df.empty:
                logger.warning(f"No OHLCV data for {stock_code}")
                return pd.DataFrame(columns=['ds', 'y'])

            # Convert to Prophet format
            price_series = self.prophet.prepare_series_for_prophet(
                dates=pd.to_datetime(ohlcv_df['trade_date'], format='%Y%m%d'),
                values=ohlcv_df['close']
            )

            logger.debug(f"Price series prepared: {len(price_series)} days for {stock_code}")

            return price_series

        except Exception as e:
            logger.error(f"Price series preparation failed for {stock_code}: {e}")
            return pd.DataFrame(columns=['ds', 'y'])

    async def _prepare_buy_ratio_series(self, stock_code: str) -> pd.DataFrame:
        """
        Prepare buy ratio series for Prophet training.

        Buy ratio = 매수체결량 / 총거래량 (daily aggregated from minute data)

        Args:
            stock_code: Stock code

        Returns:
            DataFrame with columns 'ds' (date) and 'y' (buy ratio)
        """
        try:
            # Fetch 120-day OHLCV for date reference
            ohlcv_df = await self.kis_client.get_daily_ohlcv(stock_code, days=self.lookback_days)

            if ohlcv_df.empty:
                logger.warning(f"No OHLCV data for buy ratio calculation: {stock_code}")
                return pd.DataFrame(columns=['ds', 'y'])

            # For MVP: Use volume data as proxy for buy ratio
            # (Minute data fetching for 120 days would be too many API calls)
            # This is a simplified approach - actual buy ratio calculation would require
            # minute-level bid/ask volume data

            # Calculate a proxy: (close - low) / (high - low) as daily "buying pressure"
            # This gives 0.0-1.0 range similar to buy ratio concept
            buy_pressure = (ohlcv_df['close'] - ohlcv_df['low']) / (ohlcv_df['high'] - ohlcv_df['low'])
            buy_pressure = buy_pressure.fillna(0.5)  # Neutral if high=low

            # Convert to Prophet format
            buy_ratio_series = self.prophet.prepare_series_for_prophet(
                dates=pd.to_datetime(ohlcv_df['trade_date'], format='%Y%m%d'),
                values=buy_pressure
            )

            logger.debug(f"Buy ratio series prepared: {len(buy_ratio_series)} days for {stock_code}")

            return buy_ratio_series

        except Exception as e:
            logger.error(f"Buy ratio series preparation failed for {stock_code}: {e}")
            return pd.DataFrame(columns=['ds', 'y'])

    def validate_features(self, df: pd.DataFrame) -> Dict[str, bool]:
        """
        Validate time-series features for data quality.

        Args:
            df: DataFrame with time-series features

        Returns:
            dict: {validation_metric: is_valid}
        """
        validation_results = {}

        # Check for required columns
        required_columns = ['stock_code', 'prophet_price_trend', 'prophet_volume_trend',
                           'prophet_price_uncertainty']

        for col in required_columns:
            validation_results[f'{col}_exists'] = col in df.columns

        if len(df) > 0:
            # Check for excessive zero values (might indicate forecasting failure)
            if 'prophet_price_trend' in df.columns:
                zero_ratio = (df['prophet_price_trend'] == 0.0).sum() / len(df)
                validation_results['diverse_price_trends'] = zero_ratio < 0.8

            if 'prophet_volume_trend' in df.columns:
                zero_ratio = (df['prophet_volume_trend'] == 0.0).sum() / len(df)
                validation_results['diverse_volume_trends'] = zero_ratio < 0.8

            # Check for NaN values
            for col in required_columns[1:]:  # Exclude stock_code
                if col in df.columns:
                    validation_results[f'{col}_no_nan'] = not df[col].isna().any()

            # Check uncertainty range (should be positive)
            if 'prophet_price_uncertainty' in df.columns:
                validation_results['uncertainty_positive'] = (df['prophet_price_uncertainty'] >= 0).all()

        return validation_results
