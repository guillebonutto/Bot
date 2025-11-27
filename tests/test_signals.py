import pytest
import pandas as pd
import numpy as np
import unittest
from unittest.mock import AsyncMock, MagicMock
from main import generate_signal
from bot_state import BotState
from signal_types import Direction, SignalSource

# Mock data helper
def create_mock_df(trend='flat', length=100):
    dates = pd.date_range(start='2024-01-01', periods=length, freq='1min')
    df = pd.DataFrame(index=dates)
    df['timestamp'] = dates.astype(int) // 10**9
    
    base_price = 1.1000
    if trend == 'up':
        prices = np.linspace(base_price, base_price + 0.0050, length)
    elif trend == 'down':
        prices = np.linspace(base_price, base_price - 0.0050, length)
    else:
        prices = np.full(length, base_price)
        
    # Add some noise
    noise = np.random.normal(0, 0.0001, length)
    df['Close'] = prices + noise
    df['Open'] = df['Close'].shift(1).fillna(base_price)
    df['High'] = df[['Open', 'Close']].max(axis=1) + 0.0002
    df['Low'] = df[['Open', 'Close']].min(axis=1) - 0.0002
    
    # Required columns for indicators
    df['close'] = df['Close']
    df['open'] = df['Open']
    df['high'] = df['High']
    df['low'] = df['Low']
    
    return df

@pytest.mark.asyncio
async def test_generate_signal_insufficient_data():
    api = AsyncMock()
    bot_state = BotState()
    
    # Mock empty data
    with unittest.mock.patch('main.fetch_data_optimized', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = pd.DataFrame()
        
        signal = await generate_signal(api, 'EURUSD', 'M5', bot_state)
        assert signal is None

@pytest.mark.asyncio
async def test_generate_signal_uptrend():
    api = AsyncMock()
    bot_state = BotState()
    
    # Mock uptrend data
    df = create_mock_df(trend='up')
    
    # Mock indicators to return BUY signal
    with unittest.mock.patch('main.fetch_data_optimized', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = df
        
        with unittest.mock.patch('main.compute_indicators') as mock_compute:
            # Return df with EMA_conf > 0
            df_indicators = df.copy()
            df_indicators['EMA_conf'] = 1
            df_indicators['TF'] = 1
            df_indicators['EMA_long'] = 1.1000
            df_indicators['ATR'] = 0.0010  # Add ATR for is_sideways
            mock_compute.return_value = df_indicators
            
            # Mock score_signal to return high score
            with unittest.mock.patch('main.score_signal', return_value=80):
                signal = await generate_signal(api, 'EURUSD', 'M5', bot_state)
                
                assert signal is not None
                assert signal['signal'] == 'BUY'
                assert signal['score'] == 80
                assert signal['source'] == str(SignalSource.INDICATOR)
