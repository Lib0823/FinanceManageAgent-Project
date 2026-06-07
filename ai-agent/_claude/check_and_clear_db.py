#!/usr/bin/env python3
"""
stock_financial 테이블 확인 및 Mock 데이터 삭제
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text
from config.settings import get_settings
import pandas as pd

settings = get_settings()
engine = create_engine(settings.database_url)

print("=" * 80)
print("stock_financial 테이블 현재 상태 확인")
print("=" * 80)

# 1. 전체 데이터 개수 및 기준일 확인
with engine.connect() as conn:
    query = text("""
        SELECT
            base_date,
            COUNT(*) as count
        FROM stock_financial
        GROUP BY base_date
        ORDER BY base_date DESC
    """)
    df_summary = pd.read_sql(query, conn)

print("\n📊 기준일별 레코드 수:")
print(df_summary.to_string(index=False))
print(f"\n총 레코드 수: {df_summary['count'].sum()}")

# 2. 최신 데이터 샘플 확인
with engine.connect() as conn:
    query = text("""
        SELECT stock_code, stock_name, base_date, per, roe, operating_margin
        FROM stock_financial
        ORDER BY base_date DESC, stock_code
        LIMIT 10
    """)
    df_sample = pd.read_sql(query, conn)

print("\n📈 최신 10개 레코드 샘플:")
print(df_sample.to_string(index=False))

# 3. Mock 데이터 삭제 확인
print("\n" + "=" * 80)
print("🗑️  Mock 데이터 삭제")
print("=" * 80)

# 2026-03-31 (Mock 데이터 기준일) 삭제
mock_base_date = '2026-03-31'

with engine.connect() as conn:
    # 삭제 전 개수 확인
    count_query = text("SELECT COUNT(*) as count FROM stock_financial WHERE base_date = :date")
    result = conn.execute(count_query, {'date': mock_base_date})
    count_before = result.fetchone()[0]

    print(f"\n{mock_base_date} 기준 데이터: {count_before}개")

    if count_before > 0:
        print(f"\n⚠️  {count_before}개의 Mock 데이터를 삭제합니다...")

        # 삭제 실행
        delete_query = text("DELETE FROM stock_financial WHERE base_date = :date")
        conn.execute(delete_query, {'date': mock_base_date})
        conn.commit()

        print("✅ Mock 데이터 삭제 완료!")

        # 삭제 후 확인
        result = conn.execute(count_query, {'date': mock_base_date})
        count_after = result.fetchone()[0]
        print(f"남은 데이터: {count_after}개")
    else:
        print("ℹ️  Mock 데이터 없음 (이미 삭제됨)")

# 4. 최종 상태 확인
print("\n" + "=" * 80)
print("최종 상태")
print("=" * 80)

with engine.connect() as conn:
    query = text("""
        SELECT
            base_date,
            COUNT(*) as count
        FROM stock_financial
        GROUP BY base_date
        ORDER BY base_date DESC
    """)
    df_final = pd.read_sql(query, conn)

print("\n기준일별 레코드 수:")
if df_final.empty:
    print("테이블이 비어있습니다.")
else:
    print(df_final.to_string(index=False))
    print(f"\n총 레코드 수: {df_final['count'].sum()}")

print("\n" + "=" * 80)
print("✅ 완료")
print("=" * 80)
