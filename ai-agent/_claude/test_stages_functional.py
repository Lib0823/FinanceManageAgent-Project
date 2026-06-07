"""
Functional test for Stages 2-1, 2-2, 2-3, and Stage 4 (without actual API calls).
"""
import pandas as pd
import numpy as np
from datetime import datetime
import sys

def test_stage_2_1_quantitative():
    """Test quantitative analysis with dummy data."""
    print("\n### Stage 2-1: Quantitative Analysis Test ###")

    try:
        from analysis.quantitative import QuantitativeAnalyzer

        # Create analyzer instance
        analyzer = QuantitativeAnalyzer()
        print("✅ QuantitativeAnalyzer instance created")

        # Test outlier clipping function
        test_df = pd.DataFrame({
            'stock_code': ['005930', '000660'],
            'morning_return': [2.5, 150.0],  # 150.0 is outlier
            'close_position': [0.85, 0.65],
            'foreign_net_buy': [50000000, -20000000],
            'institutional_net_buy': [30000000, 10000000],
            'per': [12.5, 8.3],
            'roe': [15.2, 22.5],
            'operating_margin': [18.5, 25.3]
        })

        clipped_df = analyzer._apply_outlier_clipping(test_df)

        # Verify outlier was clipped
        assert clipped_df['morning_return'].max() < 150.0, "Outlier clipping failed"
        print("✅ Outlier clipping works correctly")
        print(f"   Original morning_return max: 150.0")
        print(f"   Clipped morning_return max: {clipped_df['morning_return'].max():.2f}")

        return True

    except Exception as e:
        print(f"❌ Stage 2-1 test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_stage_2_2_sentiment():
    """Test sentiment analysis with dummy text."""
    print("\n### Stage 2-2: Sentiment Analysis Test ###")

    try:
        from models.kr_finbert import KRFinBERTAnalyzer

        # Create KR-FinBERT instance (will download model if not cached)
        print("⏳ Loading KR-FinBERT model (may take 30-60 seconds)...")
        analyzer = KRFinBERTAnalyzer()
        print("✅ KR-FinBERT model loaded successfully")

        # Test with sample Korean financial text
        positive_text = "삼성전자 실적 호조로 주가 급등 전망"
        negative_text = "SK하이닉스 실적 악화로 주가 하락 우려"

        positive_score = analyzer.analyze_single(positive_text)
        negative_score = analyzer.analyze_single(negative_text)

        print(f"✅ Positive sentiment test: '{positive_text}'")
        print(f"   Score: {positive_score:.4f} (expected > 0)")

        print(f"✅ Negative sentiment test: '{negative_text}'")
        print(f"   Score: {negative_score:.4f} (expected < 0)")

        # Verify scores make sense
        assert positive_score > 0, "Positive text should have positive score"
        assert negative_score < 0, "Negative text should have negative score"
        print("✅ Sentiment analysis works correctly")

        # Test time-weighted average
        articles = [
            {'text': positive_text, 'published': datetime.now()},
            {'text': negative_text, 'published': datetime.now()},
            {'text': positive_text, 'published': datetime.now()}
        ]

        avg_score = analyzer.analyze_multiple_time_weighted(articles)
        print(f"✅ Time-weighted average: {avg_score:.4f}")

        return True

    except Exception as e:
        print(f"❌ Stage 2-2 test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_stage_2_3_timeseries():
    """Test Prophet forecasting with dummy time-series data."""
    print("\n### Stage 2-3: Time-Series Analysis Test ###")

    try:
        from models.prophet_trainer import ProphetForecaster

        # Create Prophet instance
        forecaster = ProphetForecaster(lookback_days=120, forecast_days=5)
        print("✅ ProphetForecaster instance created")

        # Generate dummy time-series data (120 days)
        dates = pd.date_range(end=datetime.now(), periods=120, freq='B')

        # Simulate upward trend with noise
        trend = np.linspace(100, 120, 120)
        noise = np.random.normal(0, 2, 120)
        prices = trend + noise

        df = pd.DataFrame({
            'ds': dates,
            'y': prices
        })

        print("⏳ Training Prophet model (may take 20-30 seconds)...")
        forecast = forecaster.train_and_forecast(df, freq='B')
        print("✅ Prophet training and forecasting completed")

        # Extract features
        trend_slope = forecaster.calculate_trend_slope(forecast['yhat'])
        uncertainty = forecaster.calculate_uncertainty(
            forecast['yhat_lower'],
            forecast['yhat_upper']
        )

        print(f"✅ Price trend slope: {trend_slope:.4f} (expected > 0 for upward trend)")
        print(f"✅ Price uncertainty: {uncertainty:.2f}")

        # Verify trend is positive (we simulated upward trend)
        assert trend_slope > 0, "Trend slope should be positive for upward trend"
        print("✅ Time-series analysis works correctly")

        return True

    except Exception as e:
        print(f"❌ Stage 2-3 test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_stage_4_gemini():
    """Test Gemini decision generation (mock mode)."""
    print("\n### Stage 4: Gemini AI Decision Test ###")

    try:
        from ai.decision_generator import TradingDecisionGenerator

        # Create decision generator (will use mock mode without API key)
        generator = TradingDecisionGenerator()
        print("✅ TradingDecisionGenerator instance created")

        # Create dummy feature DataFrames (3 stocks for testing)
        quant_features = pd.DataFrame({
            'stock_code': ['005930', '000660', '051910'],
            'morning_return': [1.2, -0.5, 0.8],
            'close_position': [0.85, 0.45, 0.75],
            'foreign_net_buy': [50000000, -20000000, 10000000],
            'institutional_net_buy': [30000000, -15000000, 5000000],
            'per': [12.5, 8.3, 15.2],
            'roe': [15.2, 10.5, 22.5],
            'operating_margin': [18.5, 12.3, 25.3]
        })

        sentiment_features = pd.DataFrame({
            'stock_code': ['005930', '000660', '051910'],
            'sentiment_score': [0.65, -0.45, 0.35]
        })

        timeseries_features = pd.DataFrame({
            'stock_code': ['005930', '000660', '051910'],
            'prophet_price_trend': [0.0025, -0.0015, 0.0018],
            'prophet_volume_trend': [0.0012, -0.0008, 0.0005],
            'prophet_price_uncertainty': [250.5, 380.2, 210.8]
        })

        print("⏳ Generating AI decision (mock mode)...")
        decision = generator.generate_decisions(
            quant_features,
            sentiment_features,
            timeseries_features
        )

        print("✅ AI decision generated successfully (mock mode)")

        # Validate decision structure
        validation = generator.validate_decision(decision)

        print(f"\n📊 Decision Validation Results:")
        for key, is_valid in validation.items():
            symbol = "✅" if is_valid else "❌"
            print(f"   {symbol} {key}: {is_valid}")

        # Print decision
        print(f"\n📈 BUY TOP3:")
        for i, item in enumerate(decision['buy_top3'], 1):
            print(f"   {i}. {item['stock_code']}: {item['reason']}")

        print(f"\n📉 SELL TOP3:")
        for i, item in enumerate(decision['sell_top3'], 1):
            print(f"   {i}. {item['stock_code']}: {item['reason']}")

        # Verify all validation passed
        assert all(validation.values()), "Decision validation failed"
        print("\n✅ Stage 4 (Gemini AI Decision) works correctly")

        return True

    except Exception as e:
        print(f"❌ Stage 4 test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("Functional Test for Stages 2-1, 2-2, 2-3, and Stage 4")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Stage 2-1 (Quantitative)", test_stage_2_1_quantitative()))
    results.append(("Stage 2-2 (Sentiment)", test_stage_2_2_sentiment()))
    results.append(("Stage 2-3 (Time-Series)", test_stage_2_3_timeseries()))
    results.append(("Stage 4 (Gemini AI)", test_stage_4_gemini()))

    # Summary
    print("\n" + "=" * 60)
    print("Functional Test Results")
    print("=" * 60)

    for stage, passed in results:
        symbol = "✅" if passed else "❌"
        print(f"{symbol} {stage}: {'PASSED' if passed else 'FAILED'}")

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    print(f"\nTotal: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("🎉 All functional tests passed!")
        return 0
    else:
        print(f"⚠️ {total_count - passed_count} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
