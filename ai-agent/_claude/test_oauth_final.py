"""Final OAuth test."""
import asyncio
import sys
sys.path.insert(0, '/Users/inbeom/IdeaProjects/FinanceManage_Agent-Project/ai-agent')

from collectors.kis_client import KISClient


async def test():
    client = KISClient()
    print(f"Mode: {client.mode}")
    print(f"AppKey: {client.app_key[:10]}...")
    print(f"AppSecret length: {len(client.app_secret)}")
    
    print("\nAttempting OAuth...")
    try:
        token = await client.get_access_token()
        print(f"✅ Success! Token: {token[:30]}...")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test())
    sys.exit(0 if success else 1)
