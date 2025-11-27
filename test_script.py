import asyncio
import sys
import pandas as pd
sys.path.append('c:/Users/Guille/Downloads/PocketOptions')
import main

async def run_test():
    print("Testing MockPocketOptionAsync interface...")
    
    api = main.PocketOptionAsync(ssid='test')
    
    # Test is_demo
    print(f"is_demo: {api.is_demo()}")
    
    # Test balance
    bal = await api.balance()
    print(f"Balance: {bal} (Type: {type(bal)})")
    
    # Test fetch_data_optimized (which calls get_candles)
    print("Fetching candles...")
    df = await main.fetch_data_optimized(api, 'EURUSD_otc', 300, lookback=10)
    
    print(f"Candles DataFrame shape: {df.shape}")
    if not df.empty:
        print("Candles head:")
        print(df.head())
        print("✅ fetch_data_optimized successful")
    else:
        print("❌ fetch_data_optimized returned empty DataFrame")

    # Test buy/sell simulation
    print("Testing buy order...")
    trade_id, result = await api.buy('EURUSD_otc', 10, 60)
    print(f"Buy result: {trade_id}, {result}")
    
    print("Testing check_win...")
    win_res = await api.check_win(trade_id)
    print(f"Check win result: {win_res}")

asyncio.run(run_test())
