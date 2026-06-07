#!/usr/bin/env python3
"""
수정 후 데이터베이스 확인 스크립트
news_analysis와 prophet_forecast 테이블의 데이터를 확인합니다.
"""
import psycopg2
from config.settings import settings

def check_database():
    """Check database tables after repository fixes."""
    # Database connection
    conn = psycopg2.connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password
    )
    cursor = conn.cursor()

    print("=" * 80)
    print("데이터베이스 확인: 수정 후 (2026-05-29)")
    print("=" * 80)

    # Check news_analysis table
    cursor.execute("""
        SELECT COUNT(*), analysis_date
        FROM news_analysis
        WHERE analysis_date >= '2026-05-27'
        GROUP BY analysis_date
        ORDER BY analysis_date DESC
    """)
    results = cursor.fetchall()
    print(f"\n📰 news_analysis 테이블 (최근 데이터):")
    if results:
        for count, date in results:
            print(f"  - {date}: {count} records")
    else:
        print("  ❌ 데이터 없음")

    # Check prophet_forecast table
    cursor.execute("""
        SELECT COUNT(*), forecast_date
        FROM prophet_forecast
        WHERE forecast_date >= '2026-05-27'
        GROUP BY forecast_date
        ORDER BY forecast_date DESC
    """)
    results = cursor.fetchall()
    print(f"\n📈 prophet_forecast 테이블 (최근 데이터):")
    if results:
        for count, date in results:
            print(f"  - {date}: {count} records")
    else:
        print("  ❌ 데이터 없음")

    # Check ai_trade_decision table
    cursor.execute("""
        SELECT COUNT(*), decision_date
        FROM ai_trade_decision
        WHERE decision_date >= '2026-05-27'
        GROUP BY decision_date
        ORDER BY decision_date DESC
    """)
    results = cursor.fetchall()
    print(f"\n🤖 ai_trade_decision 테이블 (최근 데이터):")
    if results:
        for count, date in results:
            print(f"  - {date}: {count} records")
    else:
        print("  ❌ 데이터 없음")

    # Check safety_filter_result table
    cursor.execute("""
        SELECT COUNT(*), filter_date
        FROM safety_filter_result
        WHERE filter_date >= '2026-05-27'
        GROUP BY filter_date
        ORDER BY filter_date DESC
    """)
    results = cursor.fetchall()
    print(f"\n🛡️ safety_filter_result 테이블 (최근 데이터):")
    if results:
        for count, date in results:
            print(f"  - {date}: {count} records")
    else:
        print("  ❌ 데이터 없음")

    # Check quantitative_features (stock_filter_score table)
    cursor.execute("""
        SELECT COUNT(*), trade_date
        FROM stock_filter_score
        WHERE trade_date >= '2026-05-27' AND morning_return IS NOT NULL
        GROUP BY trade_date
        ORDER BY trade_date DESC
    """)
    results = cursor.fetchall()
    print(f"\n📊 quantitative_features (최근 데이터):")
    if results:
        for count, date in results:
            print(f"  - {date}: {count} records")
    else:
        print("  ❌ 데이터 없음")

    cursor.close()
    conn.close()

    print("\n" + "=" * 80)

if __name__ == "__main__":
    check_database()
