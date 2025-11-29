import os
import re
import asyncio
from dotenv import load_dotenv
import sys

# Load env
load_dotenv()
raw_ssid = os.getenv("POCKETOPTION_SSID")

print(f"Original SSID length: {len(raw_ssid) if raw_ssid else 0}")
print(f"Original SSID start: {raw_ssid[:10] if raw_ssid else 'None'}...")

# Clean version
clean_ssid = None
if raw_ssid:
    matches = re.findall(r'[a-zA-Z0-9]{20,}', raw_ssid)
    if matches:
        clean_ssid = max(matches, key=len)
        print(f"Cleaned SSID: {clean_ssid[:5]}...{clean_ssid[-5:]}")

async def test_ssid(ssid_to_test, label):
    print(f"\n--- Testing {label} ---")
    if not ssid_to_test:
        print("Skip (empty)")
        return

    try:
        from BinaryOptionsToolsV2.pocketoption import PocketOptionAsync
        print(f"Library imported. Testing connection with: {ssid_to_test[:10]}...")
        
        api = PocketOptionAsync(ssid=ssid_to_test)
        balance = await api.balance()
        print(f"Result Balance: {balance}")
        
        if balance != -1 and balance != -1.0:
            print("✅ SUCCESS!")
            return True
        else:
            print("❌ Connection failed (Balance -1)")
            return False
            
    except Exception as e:
        print(f"❌ CRASH: {e}")
        return False

async def main():
    # Test 1: Cleaned
    if clean_ssid:
        success = await test_ssid(clean_ssid, "CLEANED SSID")
        if success:
            return

    # Test 2: Raw
    await test_ssid(raw_ssid, "RAW SSID")

if __name__ == "__main__":
    asyncio.run(main())
