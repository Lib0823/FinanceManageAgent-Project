"""Final test with fresh Python process."""
import sys
sys.path.insert(0, '/Users/inbeom/IdeaProjects/FinanceManage_Agent-Project/ai-agent')

from collectors.kis_client import KISClient

print("Creating new KISClient...")
client = KISClient()
print(f"AppSecret length: {len(client.app_secret)}")
print(f"Expected: 180")
print(f"Match: {len(client.app_secret) == 180}")
