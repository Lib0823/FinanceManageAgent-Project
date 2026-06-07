"""Insert mock financial data into stock_financial table.

This is a TEMPORARY solution for development/testing.
Real DART API integration should be implemented for production.

Usage:
    python _claude/insert_mock_financials.py
"""
import sys
sys.path.insert(0, '.')

import random
from datetime import date
from sqlalchemy import create_engine, text
from config.settings import get_settings
from config.constants import KOSPI_100, STOCK_NAMES

# Database connection
settings = get_settings()
engine = create_engine(settings.database_url)

# Latest quarter base_date (Q1 2026)
BASE_DATE = date(2026, 3, 31)

def generate_realistic_financials(stock_code: str) -> dict:
    """
    Generate realistic financial metrics for a stock.

    Args:
        stock_code: 6-digit stock code

    Returns:
        dict: {per, roe, operating_margin}
    """
    # Use stock_code to seed random for consistency
    seed = int(stock_code)
    random.seed(seed)

    # Blue chip stocks (Top 30) have better metrics
    top_30 = KOSPI_100[:30]
    is_blue_chip = stock_code in top_30

    if is_blue_chip:
        # Top 30: Lower PER, higher ROE and margins
        per = round(random.uniform(8.0, 18.0), 2)
        roe = round(random.uniform(10.0, 20.0), 2)
        operating_margin = round(random.uniform(8.0, 18.0), 2)
    else:
        # Others: More varied metrics
        per = round(random.uniform(5.0, 30.0), 2)
        roe = round(random.uniform(3.0, 25.0), 2)
        operating_margin = round(random.uniform(2.0, 15.0), 2)

    # 10% chance of loss-making company (PER = None)
    if random.random() < 0.1:
        per = None

    return {
        'stock_code': stock_code,
        'stock_name': STOCK_NAMES.get(stock_code, 'Unknown'),
        'base_date': BASE_DATE,
        'per': per,
        'roe': roe,
        'operating_margin': operating_margin
    }

def insert_mock_data():
    """Insert mock financial data for all KOSPI 100 stocks."""
    # Deduplicate KOSPI_100 list (001740 appears twice in constants.py)
    unique_stocks = list(set(KOSPI_100))

    print("="*80)
    print(f"INSERTING MOCK FINANCIAL DATA FOR {len(unique_stocks)} UNIQUE STOCKS")
    print("="*80)
    print(f"Base Date: {BASE_DATE}")
    print(f"Target Table: stock_financial")
    if len(unique_stocks) < len(KOSPI_100):
        print(f"⚠️  Note: KOSPI_100 has {len(KOSPI_100) - len(unique_stocks)} duplicate(s), using {len(unique_stocks)} unique stocks")
    print()

    # Generate data for all unique stocks
    financials = [generate_realistic_financials(code) for code in unique_stocks]

    # Delete existing data for this base_date (if any)
    with engine.connect() as conn:
        delete_query = text("DELETE FROM stock_financial WHERE base_date = :base_date")
        result = conn.execute(delete_query, {'base_date': BASE_DATE})
        conn.commit()
        print(f"Deleted {result.rowcount} existing records for {BASE_DATE}")

    # Insert new data
    with engine.connect() as conn:
        insert_query = text("""
            INSERT INTO stock_financial (stock_code, stock_name, base_date, per, roe, operating_margin)
            VALUES (:stock_code, :stock_name, :base_date, :per, :roe, :operating_margin)
        """)

        for financial in financials:
            conn.execute(insert_query, financial)

        conn.commit()
        print(f"Inserted {len(financials)} financial records")

    # Verify insertion
    with engine.connect() as conn:
        verify_query = text("""
            SELECT COUNT(*),
                   COUNT(CASE WHEN per IS NULL THEN 1 END) as loss_making_count
            FROM stock_financial
            WHERE base_date = :base_date
        """)
        result = conn.execute(verify_query, {'base_date': BASE_DATE})
        row = result.fetchone()

        print()
        print("="*80)
        print("VERIFICATION")
        print("="*80)
        print(f"Total records: {row[0]}")
        print(f"Loss-making companies (PER=NULL): {row[1]}")

        # Show sample data
        sample_query = text("""
            SELECT stock_code, per, roe, operating_margin
            FROM stock_financial
            WHERE base_date = :base_date
            ORDER BY stock_code
            LIMIT 10
        """)
        result = conn.execute(sample_query, {'base_date': BASE_DATE})

        print()
        print("Sample data (first 10 stocks):")
        print(f"{'Stock Code':<12} {'PER':<10} {'ROE (%)':<10} {'Op. Margin (%)':<15}")
        print("-"*50)

        for r in result:
            per_str = f"{r[1]:.2f}" if r[1] is not None else "적자"
            print(f"{r[0]:<12} {per_str:<10} {r[2]:<10.2f} {r[3]:<15.2f}")

    print()
    print("="*80)
    print("✅ MOCK DATA INSERTION COMPLETE")
    print("="*80)
    print("⚠️  NOTE: This is MOCK data for testing purposes only.")
    print("    Real DART API integration is required for production use.")
    print("="*80)

if __name__ == '__main__':
    try:
        insert_mock_data()
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
