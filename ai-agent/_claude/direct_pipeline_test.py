"""
Direct pipeline test to understand why only 30/100 stocks are collected.
This bypasses the FastAPI server to get immediate debug output.
"""
import asyncio
import sys
sys.path.insert(0, '.')

from collectors.kis_client import KISClient
from config.constants import KOSPI_100


async def test_pipeline_collection():
    """Test the actual fetch_stock_data_parallel method."""

    print("="*80)
    print("DIRECT PIPELINE COLLECTION TEST")
    print("="*80)
    print(f"Testing with {len(KOSPI_100)} KOSPI stocks\n")

    kis_client = KISClient()

    # This is exactly what the pipeline does
    print("Calling fetch_stock_data_parallel...")
    result_df = await kis_client.fetch_stock_data_parallel(KOSPI_100)

    print(f"\n{'='*80}")
    print("RESULTS")
    print("="*80)
    print(f"Total stocks in KOSPI_100: {len(KOSPI_100)}")
    print(f"Stocks collected: {len(result_df)}")
    print(f"Success rate: {len(result_df)/len(KOSPI_100)*100:.1f}%")

    if len(result_df) > 0:
        print(f"\nFirst 5 collected stocks:")
        print(result_df[['stock_code', 'foreign_net_buy', 'institutional_net_buy']].head())

        # Check for non-zero values
        non_zero_foreign = (result_df['foreign_net_buy'] != 0).sum()
        non_zero_inst = (result_df['institutional_net_buy'] != 0).sum()
        print(f"\nNon-zero values:")
        print(f"  Foreign net buy: {non_zero_foreign}/{len(result_df)} ({non_zero_foreign/len(result_df)*100:.1f}%)")
        print(f"  Institutional net buy: {non_zero_inst}/{len(result_df)} ({non_zero_inst/len(result_df)*100:.1f}%)")


if __name__ == "__main__":
    asyncio.run(test_pipeline_collection())
