import asyncio
import json
from BinaryOptionsToolsV2.pocketoption import PocketOptionAsync

# The SSID provided by the user
SSID_RAW = '42["auth",{"session":"smpnruupr5doq4bhin92jbnb75","isDemo":1,"uid":72378748,"platform":2}]'

def clean_ssid(ssid):
    import re
    obj_match = re.search(r'({.*})', ssid)
    if obj_match:
        return obj_match.group(1)
    return ssid

async def main():
    ssid = clean_ssid(SSID_RAW)
    print(f"Testing with SSID JSON: {ssid}")
    
    api = PocketOptionAsync(ssid=ssid)
    
    print("\n1. Testing Payouts...")
    try:
        payouts = await api.payout("EURUSD_otc")
        print(f"Payout result: {payouts}")
    except Exception as e:
        print(f"Payout failed: {e}")

    print("\n2. Testing Candles (EURUSD_otc)...")
    try:
        candles = await api.get_candles("EURUSD_otc", 60, 300)
        print(f"Candles result: Got {len(candles) if candles else 0} candles")
        if candles:
            print(f"First candle: {candles[0]}")
    except Exception as e:
        print(f"Candles failed: {e}")

    print("\n3. Testing Balance...")
    try:
        balance = await api.balance()
        print(f"Balance result: {balance}")
    except Exception as e:
        print(f"Balance failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
