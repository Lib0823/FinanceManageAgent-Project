"""
Debug KISClient initialization to see what credentials it's loading.
"""
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 70)
print("Debug: Environment Variables")
print("=" * 70)
print(f"KIS_APP_KEY from env: {os.getenv('KIS_APP_KEY', 'NOT FOUND')[:20]}...")
print(f"KIS_APP_SECRET from env: {os.getenv('KIS_APP_SECRET', 'NOT FOUND')[:20]}...")
print(f"KIS_MODE from env: {os.getenv('KIS_MODE', 'NOT FOUND')}")
print("=" * 70)

from config.settings import settings

print("\nDebug: Settings Object")
print("=" * 70)
print(f"kis_app_key from settings: {settings.kis_app_key[:20] if settings.kis_app_key else 'NOT FOUND'}...")
print(f"kis_app_secret from settings: {settings.kis_app_secret[:20] if settings.kis_app_secret else 'NOT FOUND'}...")
print(f"kis_mode from settings: {settings.kis_mode}")
print(f"kis_base_url from settings: {settings.kis_base_url}")
print("=" * 70)

from collectors.kis_client import KISClient

print("\nDebug: KISClient Instance")
print("=" * 70)
client = KISClient()
print(f"client.app_key: {client.app_key[:20] if client.app_key else 'NOT FOUND'}...")
print(f"client.app_secret: {client.app_secret[:20] if client.app_secret else 'NOT FOUND'}...")
print(f"client.mode: {client.mode}")
print(f"client.base_url: {client.base_url}")
print("=" * 70)

if client.app_key and 'your_kis' in client.app_key.lower():
    print("\n⚠️ WARNING: KISClient is using PLACEHOLDER credentials!")
    print("The settings object didn't load the real values from .env")
elif client.app_key and client.app_key.startswith('PSe'):
    print("\n✅ CORRECT: KISClient is using REAL credentials")
else:
    print("\n❓ UNKNOWN: KISClient credentials status unclear")
