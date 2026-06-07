#!/usr/bin/env python3
"""Check pipeline data in database"""
import psycopg2
import os

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='financemanage',
    user='postgres',
    password='postgres'
)

cur = conn.cursor()

print("=" * 80)
print("Stage 1: stock_filter_score (2026-06-03)")
print("=" * 80)
cur.execute("""
    SELECT trade_date, COUNT(*), SUM(CASE WHEN is_selected THEN 1 ELSE 0 END) as selected
    FROM stock_filter_score
    WHERE trade_date = '2026-06-03'
    GROUP BY trade_date
""")
result = cur.fetchone()
if result:
    print(f"Trade Date: {result[0]}")
    print(f"Total Stocks: {result[1]}")
    print(f"Selected Stocks: {result[2]}")
else:
    print("No data found")

print("\n" + "=" * 80)
print("Stage 2-2: news_analysis (2026-06-03)")
print("=" * 80)
cur.execute("""
    SELECT COUNT(*) FROM news_analysis WHERE analysis_date = '2026-06-03'
""")
count = cur.fetchone()[0]
print(f"Total Records: {count}")

print("\n" + "=" * 80)
print("Stage 2-3: prophet_forecast (2026-06-03)")
print("=" * 80)
cur.execute("""
    SELECT COUNT(DISTINCT stock_code) FROM prophet_forecast
    WHERE base_date = '2026-06-03'
""")
count = cur.fetchone()[0]
print(f"Stocks with Forecasts: {count}")

print("\n" + "=" * 80)
print("Stage 4: ai_trade_decision (2026-06-03)")
print("=" * 80)
cur.execute("""
    SELECT decision_type, COUNT(*) FROM ai_trade_decision
    WHERE trade_date = '2026-06-03'
    GROUP BY decision_type
""")
results = cur.fetchall()
if results:
    for decision_type, count in results:
        print(f"{decision_type}: {count} stocks")
else:
    print("No decisions found")

print("\n" + "=" * 80)
print("Stage 5: safety_filter_result (2026-06-03)")
print("=" * 80)
cur.execute("""
    SELECT decision, COUNT(*), SUM(CASE WHEN passed THEN 1 ELSE 0 END) as passed
    FROM safety_filter_result
    WHERE filter_date = '2026-06-03'
    GROUP BY decision
""")
results = cur.fetchall()
if results:
    for decision, total, passed in results:
        print(f"{decision}: {total} total, {passed} passed")
else:
    print("No filter results found")

cur.close()
conn.close()
