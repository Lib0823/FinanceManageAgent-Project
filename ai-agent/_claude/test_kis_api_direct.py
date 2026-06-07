import asyncio
import sys
sys.path.insert(0, '.')

from collectors.kis_client import KISClient

async def test():
    client = KISClient()
    
    # Test OAuth first
    print("1. Testing OAuth token...")
    try:
        token = await client.get_access_token()
        print(f"✅ OAuth token obtained: {token[:20]}...")
    except Exception as e:
        print(f"❌ OAuth failed: {e}")
        return
    
    # Test single stock data
    print("\n2. Testing get_supply_demand for 005930 (삼성전자)...")
    try:
        result = await client.get_supply_demand('005930')
        print(f"✅ Supply/Demand: {result}")
    except Exception as e:
        print(f"❌ Supply/Demand failed: {e}")
    
    # Test daily OHLCV
    print("\n3. Testing get_daily_ohlcv for 005930...")
    try:
        result = await client.get_daily_ohlcv('005930', days=5)
        print(f"✅ Daily OHLCV: {len(result)} rows")
        print(result.head() if not result.empty else "Empty DataFrame")
    except Exception as e:
        print(f"❌ Daily OHLCV failed: {e}")

asyncio.run(test())
