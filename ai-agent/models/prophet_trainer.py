"""Prophet Time-Series Forecasting Module

Trains Prophet models daily (no persistence) for D+1 to D+5 forecasting.
Extracts linear trends from predictions for feature engineering.
"""
import pandas as pd
import numpy as np
from prophet import Prophet
from sklearn.linear_model import LinearRegression
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class ProphetForecaster:
    """Prophet forecasting for stock price and buy ratio trends."""

    def __init__(self, lookback_days: int = 120, forecast_days: int = 5):
        """
        Initialize Prophet forecaster.

        Args:
            lookback_days: Training period (default: 120 trading days)
            forecast_days: Prediction horizon (default: D+1 to D+5)
        """
        self.lookback_days = lookback_days
        self.forecast_days = forecast_days

        logger.info(f"ProphetForecaster initialized (lookback={lookback_days}, forecast={forecast_days})")

    def train_and_forecast(self, df: pd.DataFrame, freq: str = 'B') -> Dict[str, np.ndarray]:
        """
        Train Prophet model and generate D+1 to D+5 forecast.

        Args:
            df: DataFrame with columns 'ds' (date) and 'y' (value)
            freq: Frequency ('B' for business days)

        Returns:
            dict: {
                'yhat': predicted values array,
                'yhat_lower': lower confidence interval,
                'yhat_upper': upper confidence interval
            }
        """
        try:
            # Validate input
            if df.empty or len(df) < 10:
                logger.warning("Insufficient data for Prophet training")
                return self._get_empty_forecast()

            if not all(col in df.columns for col in ['ds', 'y']):
                raise ValueError("DataFrame must have 'ds' and 'y' columns")

            # Train Prophet model
            # Disable cmdstanpy to avoid compatibility issues
            import warnings
            warnings.filterwarnings('ignore')

            model = Prophet(
                daily_seasonality=False,
                weekly_seasonality=True,
                yearly_seasonality=False,  # 120 days insufficient for yearly
                seasonality_mode='additive'
            )

            # Suppress Prophet fitting logs
            import logging as prophet_logging
            prophet_logging.getLogger('prophet').setLevel(prophet_logging.ERROR)

            model.fit(df, algorithm='Newton')

            # Generate forecast for next N business days
            future = model.make_future_dataframe(periods=self.forecast_days, freq=freq)
            forecast = model.predict(future)

            # Extract D+1 to D+5 predictions (last N rows)
            future_forecast = forecast.tail(self.forecast_days)

            return {
                'yhat': future_forecast['yhat'].values,
                'yhat_lower': future_forecast['yhat_lower'].values,
                'yhat_upper': future_forecast['yhat_upper'].values
            }

        except Exception as e:
            logger.error(f"Prophet training failed: {e}")
            return self._get_empty_forecast()

    def calculate_trend_slope(self, yhat: np.ndarray) -> float:
        """
        Calculate linear regression slope of D+1 to D+5 predictions.

        Args:
            yhat: Predicted values array (length = forecast_days)

        Returns:
            float: Trend slope (양수: 상승, 음수: 하락)
        """
        if len(yhat) == 0:
            return 0.0

        try:
            X = np.arange(len(yhat)).reshape(-1, 1)  # [0, 1, 2, 3, 4]
            y = yhat.reshape(-1, 1)

            model = LinearRegression()
            model.fit(X, y)

            slope = model.coef_[0][0]
            return round(slope, 6)

        except Exception as e:
            logger.error(f"Slope calculation failed: {e}")
            return 0.0

    def calculate_uncertainty(self, yhat_lower: np.ndarray, yhat_upper: np.ndarray) -> float:
        """
        Calculate average confidence interval width for D+1 to D+5.

        Args:
            yhat_lower: Lower confidence interval
            yhat_upper: Upper confidence interval

        Returns:
            float: Average interval width (클수록 불확실성 높음)
        """
        if len(yhat_lower) == 0 or len(yhat_upper) == 0:
            return 0.0

        try:
            interval_widths = yhat_upper - yhat_lower
            avg_width = np.mean(interval_widths)
            return round(avg_width, 2)

        except Exception as e:
            logger.error(f"Uncertainty calculation failed: {e}")
            return 0.0

    def _get_empty_forecast(self) -> Dict[str, np.ndarray]:
        """
        Return empty forecast result (used when training fails).

        Returns:
            dict: Empty arrays for yhat, yhat_lower, yhat_upper
        """
        return {
            'yhat': np.array([]),
            'yhat_lower': np.array([]),
            'yhat_upper': np.array([])
        }

    def prepare_series_for_prophet(
        self,
        dates: pd.Series,
        values: pd.Series
    ) -> pd.DataFrame:
        """
        Convert date/value series to Prophet format (ds/y columns).

        Args:
            dates: Date series
            values: Value series

        Returns:
            DataFrame with columns 'ds' (datetime) and 'y' (float)
        """
        df = pd.DataFrame({
            'ds': pd.to_datetime(dates),
            'y': values.astype(float)
        })

        # Remove duplicates and sort
        df = df.drop_duplicates(subset=['ds']).sort_values('ds').reset_index(drop=True)

        return df

    def validate_forecast_quality(self, forecast: Dict[str, np.ndarray]) -> bool:
        """
        Check if forecast is valid and reasonable.

        Args:
            forecast: Forecast dictionary from train_and_forecast

        Returns:
            bool: True if forecast is valid
        """
        yhat = forecast.get('yhat', np.array([]))

        # Check if forecast exists
        if len(yhat) == 0:
            return False

        # Check for NaN values
        if np.isnan(yhat).any():
            return False

        # Check for unreasonable values (e.g., negative prices)
        if np.any(yhat < 0):
            return False

        return True
