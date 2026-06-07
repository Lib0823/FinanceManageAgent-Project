#!/usr/bin/env python3
"""
저장된 DART 데이터 검증
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
print("DART 데이터 검증")
print("=" * 80)

with engine.connect() as conn:
    query = text("""
        SELECT
            stock_code,
            stock_name,
            base_date,
            per,
            roe,
            operating_margin
        FROM stock_financial
        WHERE base_date = '2025-09-30'
        ORDER BY stock_code
    """)
    df = pd.read_sql(query, conn)

print("\n📊 저장된 DART 데이터 (2025-09-30):")
print("=" * 80)

if df.empty:
    print("❌ 데이터 없음!")
else:
    for _, row in df.iterrows():
        print(f"\n종목: {row['stock_code']} ({row['stock_name']})")
        print(f"  기준일: {row['base_date']}")
        print(f"  PER: {row['per'] if pd.notna(row['per']) else 'N/A'}")
        print(f"  ROE: {row['roe']:.2f}%" if pd.notna(row['roe']) else "  ROE: N/A")
        print(f"  영업이익률: {row['operating_margin']:.2f}%" if pd.notna(row['operating_margin']) else "  영업이익률: N/A")

print("\n" + "=" * 80)
print(f"✅ 총 {len(df)}개 종목 데이터 확인 완료")
print("=" * 80)
