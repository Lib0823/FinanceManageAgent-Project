"""Check if data was saved to database tables after pipeline execution."""
import sys
sys.path.insert(0, '.')

from datetime import date, timedelta
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'financemanage')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'yourpassword')

engine = create_engine(
    f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
)

# Check date (yesterday or specified)
check_date = date(2026, 6, 4)

print("="*80)
print(f"DATABASE TABLES CHECK FOR {check_date}")
print("="*80)

with engine.connect() as conn:
    # 1. stock_filter_score
    result = conn.execute(text("""
        SELECT COUNT(*), MIN(score_date), MAX(score_date)
        FROM stock_filter_score
        WHERE score_date = :check_date
    """), {'check_date': check_date})
    row = result.fetchone()
    print(f"\n1. stock_filter_score (Stage 1 output):")
    print(f"   Count: {row[0]} records")
    print(f"   Date range: {row[1]} ~ {row[2]}")

    if row[0] > 0:
        result = conn.execute(text("""
            SELECT stock_code, foreign_net_buy, institutional_net_buy, scaler_score, is_selected
            FROM stock_filter_score
            WHERE score_date = :check_date
            ORDER BY scaler_score DESC
            LIMIT 5
        """), {'check_date': check_date})
        print(f"   Top 5 stocks:")
        for r in result:
            print(f"     {r[0]}: foreign={r[1]:,}, inst={r[2]:,}, score={r[3]:.2f}, selected={r[4]}")

    # 2. ai_trade_decision
    result = conn.execute(text("""
        SELECT COUNT(*), MIN(decision_date), MAX(decision_date)
        FROM ai_trade_decision
        WHERE decision_date = :check_date
    """), {'check_date': check_date})
    row = result.fetchone()
    print(f"\n2. ai_trade_decision (Stage 4 output):")
    print(f"   Count: {row[0]} records")
    print(f"   Date range: {row[1]} ~ {row[2]}")

    if row[0] > 0:
        result = conn.execute(text("""
            SELECT decision, stock_code, stock_name, rank, LEFT(reason, 50)
            FROM ai_trade_decision
            WHERE decision_date = :check_date
            ORDER BY decision, rank
        """), {'check_date': check_date})
        print(f"   Decisions:")
        for r in result:
            print(f"     {r[0]} #{r[3]}: {r[2]} ({r[1]}) - {r[4]}...")

    # 3. safety_filter_result
    result = conn.execute(text("""
        SELECT COUNT(*), MIN(filter_date), MAX(filter_date)
        FROM safety_filter_result
        WHERE filter_date = :check_date
    """), {'check_date': check_date})
    row = result.fetchone()
    print(f"\n3. safety_filter_result (Stage 5 output):")
    print(f"   Count: {row[0]} records")
    print(f"   Date range: {row[1]} ~ {row[2]}")

    if row[0] > 0:
        result = conn.execute(text("""
            SELECT decision, passed, COUNT(*)
            FROM safety_filter_result
            WHERE filter_date = :check_date
            GROUP BY decision, passed
        """), {'check_date': check_date})
        print(f"   Summary:")
        for r in result:
            status = "✅ PASSED" if r[1] else "❌ FILTERED"
            print(f"     {r[0]} {status}: {r[2]} stocks")

    # 4. news_analysis (optional - Stage 2-2)
    result = conn.execute(text("""
        SELECT COUNT(*), MIN(analysis_date), MAX(analysis_date)
        FROM news_analysis
        WHERE analysis_date = :check_date
    """), {'check_date': check_date})
    row = result.fetchone()
    print(f"\n4. news_analysis (Stage 2-2 output - optional):")
    print(f"   Count: {row[0]} records")
    if row[0] > 0:
        print(f"   Date range: {row[1]} ~ {row[2]}")

    # 5. prophet_forecast (optional - Stage 2-3)
    result = conn.execute(text("""
        SELECT COUNT(*), MIN(forecast_date), MAX(forecast_date)
        FROM prophet_forecast
        WHERE forecast_date = :check_date
    """), {'check_date': check_date})
    row = result.fetchone()
    print(f"\n5. prophet_forecast (Stage 2-3 output - optional):")
    print(f"   Count: {row[0]} records")
    if row[0] > 0:
        print(f"   Date range: {row[1]} ~ {row[2]}")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print("✅ Working tables (should have data):")
print("   - stock_filter_score (Stage 1)")
print("   - ai_trade_decision (Stage 4)")
print("   - safety_filter_result (Stage 5)")
print("\n⚠️  Not yet implemented (optional features):")
print("   - news_analysis (Stage 2-2 sentiment analysis)")
print("   - prophet_forecast (Stage 2-3 time-series forecasting)")
print("="*80)
