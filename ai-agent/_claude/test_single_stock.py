"""Test single stock data fetch."""
import asyncio
import sys
sys.path.insert(0, '/Users/inbeom/IdeaProjects/FinanceManage_Agent-Project/ai-agent')

from collectors.kis_client import KISClient


async def test():
    client = KISClient()
    
    # Test single stock
    stock_code = "005930"  # Samsung Electronics
    
    print(f"Testing stock: {stock_code}")
    print("1. Getting supply/demand...")
    try:
        supply_demand = await client.get_supply_demand(stock_code)
        print(f"   ✅ Success: {supply_demand}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        
    print("\n2. Getting daily OHLCV...")
    try:
        ohlcv = await client.get_daily_ohlcv(stock_code, days=5)
        print(f"   ✅ Success: {len(ohlcv)} days")
        print(ohlcv.head())
    except Exception as e:
        print(f"   ❌ Failed: {e}")


if __name__ == "__main__":
    asyncio.run(test())
