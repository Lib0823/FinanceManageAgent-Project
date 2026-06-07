"""Test DART API integration and data collection.

This script tests:
1. API key configuration
2. Corp code mapping download
3. Financial statement fetching
4. Metric extraction
5. Database storage

Usage:
    python _claude/test_dart_api.py
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


def test_dart_api():
    """Run comprehensive DART API integration test."""
    print("=" * 80)
    print("DART API INTEGRATION TEST")
    print("=" * 80)

    try:
        # Step 1: Initialize client
        print("\n1. Initializing DART API Client...")
        client = DARTAPIClient()
        print(f"   ✅ Client initialized with API key: {client.api_key[:10]}...")

        # Step 2: Download corp_code mapping
        print("\n2. Downloading corp_code mapping...")
        corp_code_map = client.download_corp_code_list()
        print(f"   ✅ Downloaded {len(corp_code_map)} corp codes")

        # Show sample mappings
        sample_stocks = ['005930', '000660', '051910']  # 삼성전자, SK하이닉스, LG화학
        print(f"\n   Sample mappings:")
        for stock_code in sample_stocks:
            corp_code = corp_code_map.get(stock_code)
            if corp_code:
                print(f"     {stock_code} → {corp_code}")
            else:
                print(f"     {stock_code} → Not found")

        # Step 3: Test financial statement fetching (single stock)
        print("\n3. Testing financial statement fetch (삼성전자)...")
        corp_code = client.get_corp_code('005930')
        print(f"   Corp code: {corp_code}")

        financial_data = client.get_financial_statements(
            corp_code=corp_code,
            bsns_year='2024',
            reprt_code='11013'  # Q3 2024
        )

        if financial_data and 'list' in financial_data:
            print(f"   ✅ Fetched {len(financial_data['list'])} financial items")

            # Extract metrics
            metrics = client.extract_financial_metrics(financial_data)
            if metrics:
                print(f"   ✅ Extracted metrics:")
                print(f"      PER: {metrics.get('per')}")
                print(f"      ROE: {metrics.get('roe')}%")
                print(f"      Operating Margin: {metrics.get('operating_margin')}%")
            else:
                print(f"   ❌ Failed to extract metrics")
        else:
            print(f"   ❌ No financial data available")

        # Step 4: Collect data for multiple stocks (test with 5 stocks)
        print(f"\n4. Collecting financial data for 5 KOSPI stocks...")
        test_stocks = KOSPI_100[:5]  # First 5 stocks
        print(f"   Test stocks: {test_stocks}")

        df = client.collect_financials_for_stocks(
            stock_codes=test_stocks,
            base_date=date(2024, 3, 31)
        )

        print(f"\n   ✅ Collected data for {len(df)} stocks:")
        print("\n" + df.to_string(index=False))

        # Step 5: Save to database
        print(f"\n5. Saving to database...")
        success = client.save_to_database(df)

        if success:
            print(f"   ✅ Saved {len(df)} records to stock_financial table")

            # Verify from database
            print(f"\n6. Verifying database records...")
            db_df = client.get_latest_financials(test_stocks)
            print(f"   ✅ Retrieved {len(db_df)} records from database")
            print("\n" + db_df.to_string(index=False))
        else:
            print(f"   ❌ Failed to save to database")

        print("\n" + "=" * 80)
        print("✅ DART API INTEGRATION TEST COMPLETE")
        print("=" * 80)

        print("\nNext steps:")
        print("1. Run full collection for all KOSPI 100 stocks:")
        print("   python _claude/collect_all_dart_data.py")
        print("2. Verify pipeline integration")

    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("\nPlease ensure DART_API_KEY is set in .env file")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    test_dart_api()
