"""
Test script to identify which KOSPI 100 stocks are failing during data collection.

This script tests each stock individually to:
1. Identify which stocks fail and which succeed
2. Capture specific error messages for failed stocks
3. Verify feature values for successful stocks
4. Determine if the issue is invalid codes, API response format, or other problems
"""
import asyncio
import sys
sys.path.insert(0, '.')

from collectors.kis_client import KISClient
from config.constants import KOSPI_100


async def test_all_kospi_100():
    """Test KIS API data collection for all 100 KOSPI stocks."""

    print("="*80)
    print("KOSPI 100 Stock Collection Test")
    print("="*80)
    print(f"Total stocks to test: {len(KOSPI_100)}\n")

    kis_client = KISClient()

    success_count = 0
    fail_count = 0
    failed_codes = []
    success_details = []
    error_details = []

    for idx, stock_code in enumerate(KOSPI_100, 1):
        try:
            print(f"[{idx}/100] Testing {stock_code}...", end=" ")

            # Test both API calls that fetch_stock_data_parallel makes
            supply_demand = await kis_client.get_supply_demand(stock_code)
            ohlcv = await kis_client.get_daily_ohlcv(stock_code, days=21)

            # Validate data
            if supply_demand and not ohlcv.empty and len(ohlcv) >= 2:
                success_count += 1

                # Extract feature values to verify they're not all zero
                foreign_buy = supply_demand.get('foreign_net_buy', 0)
                inst_buy = supply_demand.get('institutional_net_buy', 0)

                print(f"✅ SUCCESS")
                print(f"    Foreign: {foreign_buy:,}원, Institutional: {inst_buy:,}원")
                print(f"    OHLCV rows: {len(ohlcv)}")

                success_details.append({
                    'code': stock_code,
                    'foreign_net_buy': foreign_buy,
                    'institutional_net_buy': inst_buy,
                    'ohlcv_rows': len(ohlcv)
                })

            else:
                fail_count += 1
                failed_codes.append(stock_code)

                error_msg = []
                if not supply_demand:
                    error_msg.append("No supply_demand data")
                if ohlcv.empty:
                    error_msg.append("Empty OHLCV")
                elif len(ohlcv) < 2:
                    error_msg.append(f"Insufficient OHLCV rows ({len(ohlcv)})")

                error_str = ", ".join(error_msg)
                print(f"❌ FAILED: {error_str}")

                error_details.append({
                    'code': stock_code,
                    'error': error_str
                })

        except Exception as e:
            fail_count += 1
            failed_codes.append(stock_code)

            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"❌ EXCEPTION: {error_msg}")

            error_details.append({
                'code': stock_code,
                'error': error_msg
            })

        # Small delay to respect rate limiting
        await asyncio.sleep(0.1)

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Success: {success_count}/100 ({success_count}%)")
    print(f"Failed: {fail_count}/100 ({fail_count}%)")

    if failed_codes:
        print(f"\nFailed stock codes ({len(failed_codes)}):")
        print(", ".join(failed_codes))

    # Analyze feature values
    if success_details:
        print("\n" + "="*80)
        print("FEATURE VALUE ANALYSIS (Successful Stocks)")
        print("="*80)

        zero_foreign = sum(1 for s in success_details if s['foreign_net_buy'] == 0)
        zero_inst = sum(1 for s in success_details if s['institutional_net_buy'] == 0)
        both_zero = sum(1 for s in success_details
                       if s['foreign_net_buy'] == 0 and s['institutional_net_buy'] == 0)

        print(f"Stocks with foreign_net_buy = 0: {zero_foreign}/{success_count}")
        print(f"Stocks with institutional_net_buy = 0: {zero_inst}/{success_count}")
        print(f"Stocks with BOTH = 0: {both_zero}/{success_count}")

        if both_zero == success_count:
            print("\n⚠️  WARNING: ALL successful stocks have feature values = 0!")
            print("This suggests the API response parsing may be incorrect.")
        elif both_zero > success_count * 0.8:
            print(f"\n⚠️  WARNING: {both_zero/success_count*100:.1f}% of stocks have zero values!")
            print("This is suspicious - need to check API response structure.")
        else:
            print("\n✅ Feature values appear to have real data (not all zeros)")

    # Error pattern analysis
    if error_details:
        print("\n" + "="*80)
        print("ERROR PATTERN ANALYSIS")
        print("="*80)

        # Group errors by type
        error_types = {}
        for detail in error_details:
            error = detail['error']
            if error not in error_types:
                error_types[error] = []
            error_types[error].append(detail['code'])

        for error_type, codes in error_types.items():
            print(f"\n{error_type}: {len(codes)} stocks")
            print(f"  Codes: {', '.join(codes[:10])}" +
                  (f" ... and {len(codes)-10} more" if len(codes) > 10 else ""))

    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)

    if fail_count > 50:
        print("🚨 CRITICAL: More than 50% failure rate")
        print("   - Check KOSPI_100 list for invalid/delisted codes")
        print("   - Verify KIS API response format")
        print("   - Check error handling logic")
    elif fail_count > 20:
        print("⚠️  HIGH: 20-50% failure rate")
        print("   - Some stock codes may be invalid")
        print("   - Check error messages for patterns")
    elif fail_count > 0:
        print("✅ LOW: Minor failures (< 20%)")
        print("   - Review specific failed codes")
    else:
        print("✅ PERFECT: All 100 stocks collected successfully!")

    if both_zero == success_count and success_count > 0:
        print("\n🔍 NEXT STEP: Inspect KIS API response structure")
        print("   - Print raw response for a successful stock")
        print("   - Verify supply_demand keys match expected format")


if __name__ == "__main__":
    asyncio.run(test_all_kospi_100())
