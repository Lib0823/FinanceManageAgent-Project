"""Test .env loading with explicit path."""
import sys
from pathlib import Path
sys.path.insert(0, '/Users/inbeom/IdeaProjects/FinanceManage_Agent-Project/ai-agent')

# Test 1: Direct file read
print("=== Test 1: Direct file read ===")
env_path = Path('/Users/inbeom/IdeaProjects/FinanceManage_Agent-Project/ai-agent/.env')
print(f"Env file exists: {env_path.exists()}")

with open(env_path) as f:
    for line in f:
        if 'KIS_APP_SECRET=' in line:
            secret = line.strip().split('=', 1)[1]
            print(f"Secret from file: {len(secret)} chars")
            print(f"First 30: {secret[:30]}")
            print(f"Last 30: {secret[-30:]}")

# Test 2: load_dotenv with explicit path
print("\n=== Test 2: load_dotenv with explicit path ===")
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=env_path)

secret_loaded = os.getenv('KIS_APP_SECRET')
print(f"Secret loaded: {len(secret_loaded) if secret_loaded else 0} chars")
if secret_loaded:
    print(f"First 30: {secret_loaded[:30]}")
    print(f"Last 30: {secret_loaded[-30:]}")
    print(f"Match: {secret_loaded == secret}")

# Test 3: KISClient
print("\n=== Test 3: KISClient ===")
from collectors.kis_client import KISClient

client = KISClient()
print(f"Client AppSecret: {len(client.app_secret)} chars")
print(f"First 30: {client.app_secret[:30]}")
print(f"Last 30: {client.app_secret[-30:]}")
