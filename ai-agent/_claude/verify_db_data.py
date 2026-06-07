#!/usr/bin/env python3
"""
Direct database verification without module imports
"""
import psycopg2
import os

# Database connection from .env
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    dbname="financemanage",
    user="admin",
    password="admin1234"
)
cursor = conn.cursor()

print("=" * 80)
print("데이터베이스 검증 (2026-06-07)")
print("=" * 80)

# Check news_analysis
cursor.execute("""
    SELECT analysis_date, COUNT(*) as count
    FROM news_analysis
    WHERE analysis_date >= '2026-06-01'
    GROUP BY analysis_date
    ORDER BY analysis_date DESC
    LIMIT 10
""")
results = cursor.fetchall()
print(f"\n📰 news_analysis (최근 5일):")
if results:
    for date, count in results:
        print(f"  {date}: {count} records")
else:
    print("  ❌ 데이터 없음")

# Check prophet_forecast
cursor.execute("""
    SELECT forecast_date, COUNT(*) as count
    FROM prophet_forecast
    WHERE forecast_date >= '2026-06-01'
    GROUP BY forecast_date
    ORDER BY forecast_date DESC
    LIMIT 10
""")
results = cursor.fetchall()
print(f"\n📈 prophet_forecast (최근 5일):")
if results:
    for date, count in results:
        print(f"  {date}: {count} records")
else:
    print("  ❌ 데이터 없음")

# Check for overflow values - show problematic records
cursor.execute("""
    SELECT stock_code, forecast_date,
           yhat_d1, yhat_d2, yhat_d3, yhat_d4, yhat_d5,
           price_trend, volume_trend, price_uncertainty
    FROM prophet_forecast
    WHERE forecast_date = (SELECT MAX(forecast_date) FROM prophet_forecast)
    ORDER BY stock_code
    LIMIT 5
""")
results = cursor.fetchall()
print(f"\n🔍 prophet_forecast 샘플 데이터 (최신 날짜, 5개):")
if results:
    for row in results:
        print(f"  종목: {row[0]}, 날짜: {row[1]}")
        print(f"    D+1~D+5 예측: {row[2]}, {row[3]}, {row[4]}, {row[5]}, {row[6]}")
        print(f"    Trends: price={row[7]}, volume={row[8]}, uncertainty={row[9]}")
else:
    print("  ❌ 데이터 없음")

# Check stock_filter_score
cursor.execute("""
    SELECT score_date, COUNT(*) as count
    FROM stock_filter_score
    WHERE score_date >= '2026-05-27'
    GROUP BY score_date
    ORDER BY score_date DESC
    LIMIT 5
""")
results = cursor.fetchall()
print(f"\n🎯 stock_filter_score (최근 5일):")
if results:
    for date, count in results:
        print(f"  {date}: {count} records")
else:
    print("  ❌ 데이터 없음")

cursor.close()
conn.close()

print("\n" + "=" * 80)
