"""
KIS API Authentication Diagnostic Tool
Shows detailed request/response for debugging.
"""
import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv

async def diagnose_kis_oauth():
    load_dotenv()

    app_key = os.getenv('KIS_APP_KEY')
    app_secret = os.getenv('KIS_APP_SECRET')
    mode = os.getenv('KIS_MODE')
    base_url = os.getenv('KIS_BASE_URL', 'https://openapi.koreainvestment.com:9443')

    print("=" * 70)
    print("KIS API OAuth Diagnostic Tool")
    print("=" * 70)
    print(f"Mode: {mode}")
    print(f"Base URL: {base_url}")
    print(f"AppKey length: {len(app_key) if app_key else 0}")
    print(f"AppSecret length: {len(app_secret) if app_secret else 0}")
    print(f"AppKey preview: {app_key[:10]}..." if app_key else "AppKey: NOT FOUND")
    print(f"AppSecret preview: {app_secret[:10]}..." if app_secret else "AppSecret: NOT FOUND")
    print("=" * 70)

    if not app_key or not app_secret:
        print("\n❌ ERROR: KIS credentials not found in .env")
        return

    url = f'{base_url}/oauth2/tokenP'

    payload = {
        'grant_type': 'client_credentials',
        'appkey': app_key,
        'appsecret': app_secret
    }

    headers = {
        'Content-Type': 'application/json; charset=utf-8'
    }

    print("\n[REQUEST]")
    print(f"URL: {url}")
    print(f"Method: POST")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("=" * 70)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                print("\n[RESPONSE]")
                print(f"Status Code: {response.status}")
                print(f"Reason: {response.reason}")
                print(f"Headers: {dict(response.headers)}")

                text = await response.text()
                print(f"\nBody (raw): {text}")

                if response.status == 200:
                    try:
                        result = json.loads(text)
                        print(f"\nBody (JSON): {json.dumps(result, indent=2)}")
                        print("\n✅ SUCCESS! Access token received.")
                        print(f"Token: {result.get('access_token', 'N/A')[:30]}...")
                    except json.JSONDecodeError:
                        print("\n⚠️ Response is not valid JSON")
                else:
                    print(f"\n❌ ERROR: HTTP {response.status}")
                    print("\nPossible Issues:")
                    print("1. API Key/Secret may be invalid or expired")
                    print("2. API Key may not be activated yet (check KIS Developers portal)")
                    print("3. Network/firewall may be blocking requests")
                    print("4. API endpoint URL may be incorrect")

                print("=" * 70)

    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(diagnose_kis_oauth())
