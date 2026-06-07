"""Test KIS API authentication."""
import asyncio
import sys
sys.path.insert(0, '/Users/inbeom/IdeaProjects/FinanceManage_Agent-Project/ai-agent')

from collectors.kis_client import KISClient


async def test_auth():
    """Test KIS API OAuth authentication."""
    client = KISClient()

    print(f"Mode: {client.mode}")
    print(f"Base URL: {client.base_url}")
    print(f"App Key: {client.app_key[:10]}...")
    print(f"App Secret length: {len(client.app_secret)}")

    print("\nAttempting to get access token...")
    try:
        token = await client.get_access_token()
        print(f"✅ Access token acquired: {token[:20]}...")
        return True
    except Exception as e:
        print(f"❌ Failed to get access token: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_auth())
    sys.exit(0 if success else 1)
