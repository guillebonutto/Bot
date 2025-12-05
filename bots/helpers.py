"""
Helper functions shared by all bots
"""
import asyncio
import pandas as pd


async def fetch_candles(api, pair: str, interval: int, lookback: int = 50) -> pd.DataFrame:
    """
    Fetch candles from API and return as DataFrame with lowercase columns.
    
    Args:
        api: PocketOptionAsync instance
        pair: Trading pair (e.g., 'EURUSD')
        interval: Candle interval in seconds
        lookback: Number of candles to fetch
        
    Returns:
        DataFrame with columns: timestamp (index), open, close, high, low
    """
    try:
        offset = interval * lookback
        raw = await asyncio.wait_for(
            api.get_candles(pair, interval, offset),
            timeout=30
        )
        
        if not raw or not isinstance(raw, list):
            return pd.DataFrame()
        
        df = pd.DataFrame(raw)
        if 'timestamp' not in df.columns:
            if 'time' in df.columns:
                df['timestamp'] = df['time']
            else:
                return pd.DataFrame()
        
        df = df.dropna(subset=['timestamp', 'open', 'close'])
        
        if len(df) < 5:
            return pd.DataFrame()
        
        # Create DataFrame with lowercase columns
        df = pd.DataFrame({
            'timestamp': pd.to_datetime(df['timestamp'], unit='s', utc=True),
            'open': pd.to_numeric(df['open']),
            'close': pd.to_numeric(df['close']),
            'high': pd.to_numeric(df['high']),
            'low': pd.to_numeric(df['low'])
        })
        df = df.sort_values('timestamp').set_index('timestamp')
        
        return df
        
    except asyncio.TimeoutError:
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()
