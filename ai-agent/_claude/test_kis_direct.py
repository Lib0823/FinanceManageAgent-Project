"""Direct KIS API OAuth test without dotenv."""
import asyncio
import aiohttp
import json

# Hardcoded credentials for testing
APP_KEY = "PSeTJxnzlAjc0WKeijyeQpuD7aEHhfBb4jv5"
APP_SECRET = "d5UVrY6J0EnF3w0/K4gd22gs5VmSOvrNB1vkXVp8RSlu4LW2d1oZvLYYB7cHshNhinQrvC4uBggOwejuPMnbS9uuBNbHSI0QfAkj88CjXss12kVwxPt8dOHFx9Fywo6VhFu9yqICSAlukQ3OcuKr2Ui/44YKzj71jw+W7R2jo/Mx6Sj9oU8="
BASE_URL = "https://openapi.koreainvestment.com:9443"


async def test_oauth():
    """Test OAuth with hardcoded credentials."""
    url = f"{BASE_URL}/oauth2/tokenP"
    
    data = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
    }
    
    headers = {
        "Content-Type": "application/json; charset=utf-8"
    }
    
    print(f"App Key length: {len(APP_KEY)}")
    print(f"App Secret length: {len(APP_SECRET)}")
    print(f"URL: {url}")
    print(f"\nRequest data:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as response:
            status = response.status
            text = await response.text()
            
            print(f"\nResponse status: {status}")
            print(f"Response body: {text}")
            
            if status == 200:
                result = json.loads(text)
                print(f"\n✅ Success! Token: {result.get('access_token', '')[:30]}...")
                return True
            else:
                print(f"\n❌ Failed!")
                return False


if __name__ == "__main__":
    success = asyncio.run(test_oauth())
