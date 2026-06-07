"""Test KIS API connection and Stage 1 pipeline."""
import asyncio
import sys
from datetime import date
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from collectors.kis_client import KISClient
from analysis.filter import StockFilter
from pipeline.orchestrator import PipelineOrchestrator
from config.settings import get_settings
from database.models import Base, engine


async def test_kis_auth():
    """Test 1: KIS API authentication"""
    print("\n" + "="*60)
    print("TEST 1: KIS API Authentication")
    print("="*60)

    try:
        settings = get_settings()
        client = KISClient()  # KISClient reads settings directly

        # Test OAuth token retrieval
        token = await client.get_access_token()
        print(f"✅ OAuth Token Retrieved: {token[:20]}...")
        print(f"✅ Token Expiry: {client.token_expires_at}")
        print(f"✅ Mode: {settings.kis_mode}")
        return True

    except Exception as e:
        print(f"❌ Authentication Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_kis_api_call():
    """Test 2: KIS API data retrieval"""
    print("\n" + "="*60)
    print("TEST 2: KIS API Data Retrieval (Single Stock)")
    print("="*60)

    try:
        settings = get_settings()
        client = KISClient()  # KISClient reads settings directly

        # Test with Samsung Electronics (005930)
        test_stock = "005930"
        print(f"📊 Testing stock: {test_stock} (삼성전자)")

        # Get supply/demand data
        supply_demand = await client.get_supply_demand(test_stock)
        print(f"✅ Foreign Net Buy: {supply_demand['foreign_net_buy']:,}원")
        print(f"✅ Institutional Net Buy: {supply_demand['institutional_net_buy']:,}원")

        # Get OHLCV data (last 5 days)
        ohlcv = await client.get_daily_ohlcv(test_stock, days=5)
        print(f"✅ Retrieved {len(ohlcv)} days of OHLCV data")
        print(f"   Latest close: {ohlcv.iloc[0]['close']:,}원")

        return True

    except Exception as e:
        print(f"❌ API Call Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_setup():
    """Test 3: Database table creation"""
    print("\n" + "="*60)
    print("TEST 3: Database Setup")
    print("="*60)

    try:
        # Create tables
        Base.metadata.create_all(engine)
        print("✅ Database tables created/verified")

        # Check if stock_filter_score table exists
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if 'stock_filter_score' in tables:
            print("✅ Table 'stock_filter_score' exists")
            columns = [c['name'] for c in inspector.get_columns('stock_filter_score')]
            print(f"   Columns: {', '.join(columns)}")
        else:
            print("❌ Table 'stock_filter_score' not found")
            return False

        return True

    except Exception as e:
        print(f"❌ Database Setup Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_stage1_pipeline():
    """Test 4: Stage 1 filtering pipeline (KOSPI 100 → Top 30)"""
    print("\n" + "="*60)
    print("TEST 4: Stage 1 Pipeline Execution")
    print("="*60)
    print("⏳ This will take ~40-60 seconds (100 stocks, rate limited)...")

    try:
        orchestrator = PipelineOrchestrator()

        # Run Stage 1 with today's date
        result = await orchestrator.run_stage1_filtering(
            trade_date=date.today(),
            holdings=None  # No holdings for test
        )

        print("\n📊 Pipeline Results:")
        print(f"✅ Total stocks analyzed: {result['total_stocks']}")
        print(f"✅ Selected stocks (Top 30): {result['selected_stocks']}")
        print(f"✅ Execution time: {result['execution_time']:.2f} seconds")
        print(f"✅ Database save: {'Success' if result['db_save_success'] else 'Failed'}")

        print(f"\n🏆 Top 5 Selected Stocks:")
        for i, stock in enumerate(result['top_stocks'][:5], 1):
            print(f"   {i}. {stock['stock_code']}: Score {stock['final_score']:.2f}")

        return True

    except Exception as e:
        print(f"❌ Pipeline Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_database_query():
    """Test 5: Query saved results from database"""
    print("\n" + "="*60)
    print("TEST 5: Database Query Results")
    print("="*60)

    try:
        from database.repository import DatabaseRepository

        repo = DatabaseRepository()

        # Get latest filter date
        latest_date = repo.get_latest_filter_date()
        print(f"✅ Latest filter date: {latest_date}")

        if latest_date:
            # Get selected stocks
            selected = repo.get_selected_stocks(latest_date)
            print(f"✅ Selected stocks count: {len(selected)}")
            print(f"   Sample stocks: {', '.join(selected[:5])}...")

            # Get full results
            results_df = repo.get_filter_scores(latest_date)
            if results_df is not None:
                print(f"✅ Total records retrieved: {len(results_df)}")
                print(f"   Selected (is_selected=True): {results_df['is_selected'].sum()}")
                print(f"   Not selected: {(~results_df['is_selected']).sum()}")

        return True

    except Exception as e:
        print(f"❌ Database Query Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print(" "*25 + "AI-AGENT TEST SUITE")
    print(" "*20 + "Stage 1: KOSPI 100 Filtering")
    print("="*80)

    results = {}

    # Test 1: KIS Authentication
    results['auth'] = await test_kis_auth()

    # Test 2: KIS API Call (single stock)
    if results['auth']:
        results['api'] = await test_kis_api_call()
    else:
        print("\n⚠️  Skipping API test (auth failed)")
        results['api'] = False

    # Test 3: Database Setup
    results['db_setup'] = test_database_setup()

    # Test 4: Stage 1 Pipeline (full 100 stocks)
    if results['auth'] and results['api'] and results['db_setup']:
        results['pipeline'] = await test_stage1_pipeline()
    else:
        print("\n⚠️  Skipping pipeline test (prerequisites failed)")
        results['pipeline'] = False

    # Test 5: Database Query
    if results['pipeline']:
        results['db_query'] = await test_database_query()
    else:
        print("\n⚠️  Skipping database query test (pipeline not run)")
        results['db_query'] = False

    # Summary
    print("\n" + "="*80)
    print(" "*30 + "TEST SUMMARY")
    print("="*80)

    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name.upper():15s}: {status}")

    total = len(results)
    passed = sum(results.values())
    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n🎉 All tests passed! Stage 1 pipeline is ready.")
    else:
        print("\n⚠️  Some tests failed. Please check logs above.")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
