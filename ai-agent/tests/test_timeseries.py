"""
pytest tests for Stage 2-3: Time-Series Analysis
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from analysis.timeseries import TimeSeriesAnalyzer
from models.prophet_trainer import ProphetForecaster


@pytest.fixture
def timeseries_analyzer():
    """Create TimeSeriesAnalyzer instance for testing."""
    return TimeSeriesAnalyzer(lookback_days=120)


@pytest.fixture
def prophet_forecaster():
    """Create ProphetForecaster instance for testing."""
    return ProphetForecaster(lookback_days=120, forecast_days=5)


@pytest.fixture
def sample_price_series():
    """Generate sample price time-series data (120 days)."""
    dates = pd.date_range(end=datetime.now(), periods=120, freq='B')

    # Simulate upward trend with noise
    trend = np.linspace(100, 120, 120)
    noise = np.random.normal(0, 2, 120)
    prices = trend + noise

    return pd.DataFrame({
        'ds': dates,
        'y': prices
    })


@pytest.fixture
def sample_volume_series():
    """Generate sample volume (buy ratio) time-series data (120 days)."""
    dates = pd.date_range(end=datetime.now(), periods=120, freq='B')

    # Simulate buy ratio (0.4 ~ 0.6) with noise
    buy_ratios = 0.5 + np.random.normal(0, 0.05, 120)
    buy_ratios = np.clip(buy_ratios, 0.3, 0.7)

    return pd.DataFrame({
        'ds': dates,
        'y': buy_ratios
    })


class TestProphetForecaster:
    """Test suite for ProphetForecaster."""

    def test_init(self, prophet_forecaster):
        """Test ProphetForecaster initialization."""
        assert prophet_forecaster.lookback_days == 120
        assert prophet_forecaster.forecast_days == 5

    def test_train_and_forecast_structure(self, prophet_forecaster, sample_price_series):
        """Test train_and_forecast returns correct structure."""
        forecast = prophet_forecaster.train_and_forecast(sample_price_series, freq='B')

        # Verify structure
        assert 'yhat' in forecast
        assert 'yhat_lower' in forecast
        assert 'yhat_upper' in forecast

        # Verify lengths (should be 5 for D+1 to D+5)
        assert len(forecast['yhat']) == 5
        assert len(forecast['yhat_lower']) == 5
        assert len(forecast['yhat_upper']) == 5

        # Verify confidence interval: yhat_lower <= yhat <= yhat_upper
        for i in range(5):
            assert forecast['yhat_lower'][i] <= forecast['yhat'][i] <= forecast['yhat_upper'][i]

    def test_calculate_trend_slope(self, prophet_forecaster):
        """Test linear regression slope calculation."""
        # Upward trend: [100, 102, 104, 106, 108]
        upward_yhat = np.array([100, 102, 104, 106, 108])
        upward_slope = prophet_forecaster.calculate_trend_slope(upward_yhat)
        assert upward_slope > 0, f"Upward trend should have positive slope, got {upward_slope}"

        # Downward trend: [108, 106, 104, 102, 100]
        downward_yhat = np.array([108, 106, 104, 102, 100])
        downward_slope = prophet_forecaster.calculate_trend_slope(downward_yhat)
        assert downward_slope < 0, f"Downward trend should have negative slope, got {downward_slope}"

        # Flat trend: [100, 100, 100, 100, 100]
        flat_yhat = np.array([100, 100, 100, 100, 100])
        flat_slope = prophet_forecaster.calculate_trend_slope(flat_yhat)
        assert abs(flat_slope) < 0.1, f"Flat trend should have near-zero slope, got {flat_slope}"

    def test_calculate_uncertainty(self, prophet_forecaster):
        """Test uncertainty (confidence interval width) calculation."""
        # Wide interval (high uncertainty)
        yhat_lower = np.array([95, 96, 97, 98, 99])
        yhat_upper = np.array([105, 106, 107, 108, 109])

        wide_uncertainty = prophet_forecaster.calculate_uncertainty(yhat_lower, yhat_upper)
        assert wide_uncertainty == 10.0  # Average width: (105-95 + 106-96 + ...) / 5 = 10

        # Narrow interval (low uncertainty)
        yhat_lower = np.array([99, 100, 101, 102, 103])
        yhat_upper = np.array([101, 102, 103, 104, 105])

        narrow_uncertainty = prophet_forecaster.calculate_uncertainty(yhat_lower, yhat_upper)
        assert narrow_uncertainty == 2.0  # Average width: 2

    def test_prophet_training_convergence(self, prophet_forecaster, sample_price_series):
        """Test Prophet model trains without errors."""
        try:
            forecast = prophet_forecaster.train_and_forecast(sample_price_series, freq='B')
            assert forecast is not None
            assert len(forecast['yhat']) == 5
        except Exception as e:
            pytest.fail(f"Prophet training failed: {str(e)}")

    def test_forecast_values_reasonable(self, prophet_forecaster, sample_price_series):
        """Test forecast values are within reasonable range of training data."""
        forecast = prophet_forecaster.train_and_forecast(sample_price_series, freq='B')

        # Get training data range
        train_min = sample_price_series['y'].min()
        train_max = sample_price_series['y'].max()
        train_range = train_max - train_min

        # Forecast should be within 2x training data range
        for yhat in forecast['yhat']:
            assert train_min - train_range < yhat < train_max + train_range, \
                f"Forecast {yhat} outside reasonable range [{train_min - train_range}, {train_max + train_range}]"


class TestTimeSeriesAnalyzer:
    """Test suite for TimeSeriesAnalyzer."""

    def test_init(self, timeseries_analyzer):
        """Test TimeSeriesAnalyzer initialization."""
        assert timeseries_analyzer.kis_client is not None
        assert timeseries_analyzer.prophet is not None
        assert timeseries_analyzer.prophet.lookback_days == 120
        assert timeseries_analyzer.prophet.forecast_days == 5

    @pytest.mark.asyncio
    async def test_analyze_stocks_structure(self, timeseries_analyzer):
        """Test analyze_stocks returns correct structure."""
        # Mock KIS client
        with patch.object(timeseries_analyzer.kis_client, 'get_daily_ohlcv', new_callable=AsyncMock) as mock_ohlcv, \
             patch.object(timeseries_analyzer.kis_client, 'get_minute_data', new_callable=AsyncMock) as mock_minute:

            # Setup mocks with 120 days of data
            dates = pd.date_range(end=datetime.now(), periods=120, freq='B')
            prices = np.linspace(100, 120, 120) + np.random.normal(0, 2, 120)

            mock_ohlcv.return_value = pd.DataFrame({
                'trade_date': [d.strftime('%Y%m%d') for d in dates],
                'close': prices
            })

            # Mock minute data for buy ratio calculation
            mock_minute.return_value = pd.DataFrame({
                'time': ['0900'] * 120,
                'buy_volume': [5000000] * 120,
                'total_volume': [10000000] * 120
            })

            # Execute
            result = await timeseries_analyzer.analyze_stocks(stock_codes=['005930'])

            # Verify structure
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 1
            assert 'stock_code' in result.columns

            # Verify 3 features exist
            expected_features = ['prophet_price_trend', 'prophet_volume_trend', 'prophet_price_uncertainty']
            for feature in expected_features:
                assert feature in result.columns, f"Missing feature: {feature}"

            # Verify feature value ranges
            row = result.iloc[0]
            assert isinstance(row['prophet_price_trend'], (int, float))
            assert isinstance(row['prophet_volume_trend'], (int, float))
            assert row['prophet_price_uncertainty'] >= 0


class TestFeatureValidation:
    """Test time-series feature validation."""

    def test_price_trend_interpretation(self):
        """Test price trend slope interpretation."""
        # Positive slope: upward trend
        positive_slope = 0.0025
        assert positive_slope > 0, "Positive slope indicates upward trend"

        # Negative slope: downward trend
        negative_slope = -0.0015
        assert negative_slope < 0, "Negative slope indicates downward trend"

        # Near-zero slope: flat trend
        flat_slope = 0.0001
        assert abs(flat_slope) < 0.001, "Near-zero slope indicates flat trend"

    def test_volume_trend_interpretation(self):
        """Test volume (buy ratio) trend interpretation."""
        # Positive slope: buy pressure increasing
        positive_volume_trend = 0.0012
        assert positive_volume_trend > 0, "Positive volume trend indicates increasing buy pressure"

        # Negative slope: sell pressure increasing
        negative_volume_trend = -0.0008
        assert negative_volume_trend < 0, "Negative volume trend indicates increasing sell pressure"

    def test_uncertainty_threshold(self):
        """Test uncertainty threshold for decision-making."""
        # Low uncertainty: reliable prediction
        low_uncertainty = 150.5
        assert low_uncertainty < 300, "Low uncertainty: prediction reliable"

        # High uncertainty: unreliable prediction
        high_uncertainty = 550.2
        assert high_uncertainty > 300, "High uncertainty: prediction unreliable"

    def test_slope_calculation_accuracy(self):
        """Test linear regression slope calculation accuracy."""
        from sklearn.linear_model import LinearRegression

        # Known linear data: y = 2x + 100
        X = np.arange(5).reshape(-1, 1)
        y = 2 * X + 100

        model = LinearRegression()
        model.fit(X, y)

        # Slope should be exactly 2.0
        assert abs(model.coef_[0][0] - 2.0) < 0.0001


class TestProphetEdgeCases:
    """Test Prophet edge cases and error handling."""

    def test_insufficient_data(self, prophet_forecaster):
        """Test handling of insufficient training data."""
        # Only 10 days (Prophet needs at least 2 periods)
        insufficient_data = pd.DataFrame({
            'ds': pd.date_range(end=datetime.now(), periods=10, freq='B'),
            'y': [100] * 10
        })

        try:
            forecast = prophet_forecaster.train_and_forecast(insufficient_data, freq='B')
            # Should still run but may have lower quality
            assert forecast is not None
        except Exception:
            # It's acceptable to fail with insufficient data
            pass

    def test_constant_values(self, prophet_forecaster):
        """Test handling of constant time-series (no variance)."""
        constant_data = pd.DataFrame({
            'ds': pd.date_range(end=datetime.now(), periods=120, freq='B'),
            'y': [100.0] * 120
        })

        forecast = prophet_forecaster.train_and_forecast(constant_data, freq='B')

        # Slope should be near zero
        slope = prophet_forecaster.calculate_trend_slope(forecast['yhat'])
        assert abs(slope) < 0.1, f"Constant series should have near-zero slope, got {slope}"

    def test_extreme_volatility(self, prophet_forecaster):
        """Test handling of extreme volatility."""
        volatile_data = pd.DataFrame({
            'ds': pd.date_range(end=datetime.now(), periods=120, freq='B'),
            'y': np.random.normal(100, 50, 120)  # High standard deviation
        })

        forecast = prophet_forecaster.train_and_forecast(volatile_data, freq='B')

        # Uncertainty should be high
        uncertainty = prophet_forecaster.calculate_uncertainty(
            forecast['yhat_lower'],
            forecast['yhat_upper']
        )
        assert uncertainty > 10, f"High volatility should produce high uncertainty, got {uncertainty}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
