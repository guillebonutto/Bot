import asyncio
import sys
import pandas as pd
sys.path.append('c:/Users/Guille/Downloads/PocketOptions')
import main

async def run_test():
    print("Testing PocketOptionError handling...")
    
    # Get the error class being used
    ErrorClass = getattr(main, 'PocketOptionError', None)
    if not ErrorClass:
        print("PocketOptionError not found in main module, cannot test.")
        return

    # Create mock API
    api = main.PocketOptionAsync(ssid='test')
    
    # Mock get_candles to raise the error
    async def mock_get_candles_error(*args, **kwargs):
        print("Raising PocketOptionError...")
        raise ErrorClass("Invalid asset: Asset is not active")

    # Patch the method
    api.get_candles = mock_get_candles_error

    # Call fetch_data_optimized
    print("Calling fetch_data_optimized...")
    df = await main.fetch_data_optimized(api, 'INVALID_PAIR', 300)
    
    print(f"Result type: {type(df)}")
    print(f"Result empty: {df.empty}")
    
    if df.empty:
        print("✅ SUCCESS: Handled error gracefully, returned empty DataFrame.")
    else:
        print("❌ FAILURE: Did not return empty DataFrame.")

asyncio.run(run_test())
