"""Debug supply/demand API response."""
import asyncio
import sys
sys.path.insert(0, '/Users/inbeom/IdeaProjects/FinanceManage_Agent-Project/ai-agent')

from collectors.kis_client import KISClient


async def test():
    client = KISClient()
    
    stock_code = "005930"
    endpoint = '/uapi/domestic-stock/v1/quotations/inquire-investor'
    tr_id = 'FHKST01010900'
    
    params = {
        'FID_COND_MRKT_DIV_CODE': 'J',
        'FID_INPUT_ISCD': stock_code
    }
    
    print(f"Fetching supply/demand for {stock_code}...")
    result = await client.request('GET', endpoint, tr_id, params=params)
    
    print(f"\nFull result type: {type(result)}")
    print(f"Result keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
    print(f"\nFull result:")
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Check output structure
    output = result.get('output', {})
    print(f"\nOutput type: {type(output)}")
    if isinstance(output, list):
        print(f"Output is a list with {len(output)} items")
        if output:
            print(f"First item: {output[0]}")
    elif isinstance(output, dict):
        print(f"Output keys: {output.keys()}")


if __name__ == "__main__":
    asyncio.run(test())
