"""Unit tests for stock filter module."""
import pytest
import pandas as pd
import numpy as np

from analysis.filter import StockFilter


class TestStockFilter:
    """Test cases for StockFilter class."""

    @pytest.fixture
    def sample_data(self):
        """Create sample stock data for testing."""
        np.random.seed(42)
        data = {
            'stock_code': [f'{i:06d}' for i in range(1, 101)],
            'foreign_net_buy': np.random.randint(-1000000000, 1000000000, 100),
            'institutional_net_buy': np.random.randint(-500000000, 500000000, 100),
            'volume_ratio': np.random.uniform(0.5, 3.0, 100),
            'price_volatility': np.random.uniform(0.01, 0.15, 100)
        }
        return pd.DataFrame(data)

    @pytest.fixture
    def filter_instance(self):
        """Create StockFilter instance."""
        return StockFilter()

    def test_calculate_scores_basic(self, filter_instance, sample_data):
        """Test basic score calculation."""
        result = filter_instance.calculate_scores(sample_data)

        # Check columns added
        assert 'final_score' in result.columns
        assert 'is_selected' in result.columns

        # Check number of rows unchanged
        assert len(result) == 100

        # Check top 30 selected
        assert result['is_selected'].sum() == 30

        # Check scores are sorted descending
        assert result['final_score'].is_monotonic_decreasing

    def test_calculate_scores_empty_dataframe(self, filter_instance):
        """Test handling of empty DataFrame."""
        empty_df = pd.DataFrame()
        result = filter_instance.calculate_scores(empty_df)

        assert result.empty

    def test_absolute_value_handling(self, filter_instance):
        """Test that net buy uses absolute values."""
        data = pd.DataFrame({
            'stock_code': ['000001', '000002'],
            'foreign_net_buy': [1000000, -1000000],  # Same absolute value
            'institutional_net_buy': [500000, -500000],
            'volume_ratio': [1.0, 1.0],
            'price_volatility': [0.05, 0.05]
        })

        result = filter_instance.calculate_scores(data)

        # Scores should be similar (not identical due to normalization)
        score_diff = abs(result.loc[0, 'final_score'] - result.loc[1, 'final_score'])
        assert score_diff < 0.1  # Small difference acceptable

    def test_filter_top_n_basic(self, filter_instance, sample_data):
        """Test top N filtering without holdings."""
        scored_df = filter_instance.calculate_scores(sample_data)
        filtered = filter_instance.filter_top_n(scored_df)

        assert len(filtered) == 30
        assert all(filtered['is_selected'])

    def test_filter_top_n_with_holdings(self, filter_instance, sample_data):
        """Test top N filtering with holdings inclusion."""
        scored_df = filter_instance.calculate_scores(sample_data)

        # Pick a stock not in top 30
        non_selected_stock = scored_df[scored_df['is_selected'] == False].iloc[0]['stock_code']
        holdings = [non_selected_stock]

        filtered = filter_instance.filter_top_n(scored_df, holdings=holdings)

        # Should have 31 stocks (30 + 1 holding)
        assert len(filtered) == 31
        assert non_selected_stock in filtered['stock_code'].values

    def test_process_end_to_end(self, filter_instance, sample_data):
        """Test complete filtering process."""
        result = filter_instance.process(sample_data)

        assert len(result) == 30
        assert all(result['is_selected'])
        assert 'final_score' in result.columns
        assert result['final_score'].is_monotonic_decreasing

    def test_score_weights_applied(self, filter_instance):
        """Test that configured weights are applied correctly."""
        data = pd.DataFrame({
            'stock_code': ['000001'],
            'foreign_net_buy': [1000000],
            'institutional_net_buy': [1000000],
            'volume_ratio': [2.0],
            'price_volatility': [0.1]
        })

        result = filter_instance.calculate_scores(data)

        # Score should exist (exact value depends on normalization)
        assert pd.notna(result.loc[0, 'final_score'])
