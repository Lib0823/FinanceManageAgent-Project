"""Collect DART financial data for all KOSPI 100 stocks.

This script collects quarterly financial data (PER, ROE, operating margin)
from DART Open API for all KOSPI 100 stocks and saves to database.

Usage:
    python _claude/collect_all_dart_data.py
"""
import sys
sys.path.insert(0, '.')

import logging
from datetime import date
from collectors.dart_client import DARTAPIClient
from config.constants import KOSPI_100

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def collect_all_dart_data():
    """Collect DART financial data for all KOSPI 100 stocks."""
    print("=" * 80)
    print("DART DATA COLLECTION FOR ALL KOSPI 100 STOCKS")
    print("=" * 80)

    try:
        # Initialize DART client
        print("\n1. Initializing DART API Client...")
        client = DARTAPIClient()
        print(f"   ✅ Client initialized")

        # Download corp_code mapping
        print("\n2. Downloading corp_code mapping...")
        corp_code_map = client.download_corp_code_list()
        print(f"   ✅ Downloaded {len(corp_code_map)} corp codes")

        # Collect financial data for all KOSPI 100 stocks
        print(f"\n3. Collecting financial data for {len(KOSPI_100)} KOSPI stocks...")
        print(f"   Target: Q1 2024 financial data")
        print(f"   This may take a few minutes...\n")

        df = client.collect_financials_for_stocks(
            stock_codes=KOSPI_100,
            base_date=date(2024, 3, 31)  # Q1 2024
        )

        # Display results
        print(f"\n   ✅ Collected data for {len(df)} stocks")
        print(f"\n4. Data Summary:")
        print(f"   Total stocks collected: {len(df)}")
        print(f"   Stocks with PER data: {df['per'].notna().sum()}")
        print(f"   Stocks with ROE data: {df['roe'].notna().sum()}")
        print(f"   Stocks with Operating Margin data: {df['operating_margin'].notna().sum()}")

        # Show sample data
        print(f"\n5. Sample Data (first 10 stocks):")
        print(df.head(10).to_string(index=False))

        # Save to database
        print(f"\n6. Saving to database...")
        success = client.save_to_database(df)

        if success:
            print(f"   ✅ Successfully saved {len(df)} records to stock_financial table")

            # Verify from database
            print(f"\n7. Verifying database records...")
            db_df = client.get_latest_financials(KOSPI_100)
            print(f"   ✅ Verified {len(db_df)} records in database")

            # Show statistics
            print(f"\n8. Database Statistics:")
            print(f"   Total records: {len(db_df)}")
            print(f"   Records with PER: {db_df['per'].notna().sum()}")
            print(f"   Records with ROE: {db_df['roe'].notna().sum()}")
            print(f"   Records with Operating Margin: {db_df['operating_margin'].notna().sum()}")
        else:
            print(f"   ❌ Failed to save to database")

        print("\n" + "=" * 80)
        print("✅ DART DATA COLLECTION COMPLETE")
        print("=" * 80)

        print("\nNext steps:")
        print("1. Verify data in database: SELECT * FROM stock_financial WHERE base_date = '2024-03-31';")
        print("2. Run pipeline integration test to verify all tables have data")

    except Exception as e:
        print(f"\n❌ Collection Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    collect_all_dart_data()
