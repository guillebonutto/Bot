import os
import asyncio
from dotenv import load_dotenv
import sys

# Add parent dir to path
sys.path.append(os.getcwd())

load_dotenv()

ssid = os.getenv("POCKETOPTION_SSID")
print(f"SSID found: {'Yes' if ssid else 'No'}")
if ssid:
    print(f"SSID length: {len(ssid)}")
    print(f"SSID start: {ssid[:5]}...")

try:
    from BinaryOptionsToolsV2.pocketoption import PocketOptionAsync
    print("✅ Library imported successfully")
except ImportError as e:
    print(f"❌ Library import failed: {e}")
    from mock_pocketoption import PocketOptionAsync
    print("⚠️ Using Mock")

async def main():
    print("Connecting...")
    api = PocketOptionAsync(ssid=ssid)
    balance = await api.balance()
    print(f"Balance: {balance}")
    
    if balance == -1 or balance == -1.0:
        print("❌ Connection failed (Balance is -1)")
        print("👉 Likely invalid SSID")
    else:
        print("✅ Connection successful")

if __name__ == "__main__":
    asyncio.run(main())
