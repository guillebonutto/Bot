"""
Bot #3: Round Levels
Strategy: Rejection of .000/.500 levels
Timeframes: M5, M15
"""
import os
import sys
import asyncio
import numpy as np
import pandas as pd
from typing import Optional, Dict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bots.base_bot import BaseBot


class RoundLevelsBot(BaseBot):
    """
    Round Levels Strategy:
    1. Price near .000 or .500 level
    2. Rejection candle (pin bar with wick > 2x body)
    3. Volume above average (if available)
    4. No news events nearby
    """
    
    def __init__(self):
        super().__init__(bot_name="round_levels")
        
        # Strategy parameters
        self.level_tolerance = 0.0005  # 5 pips
        self.wick_ratio_min = 2.0
    
    def get_nearest_round_level(self, price: float) -> tuple:
        """
        Get nearest .000 or .500 level.
        Returns: (level_price, distance, level_type)
        """
        # Round to 3 decimals for forex pairs
        price_rounded = round(price, 3)
        
        # Get integer and decimal parts
        integer_part = int(price)
        decimal_part = price - integer_part
        
        # Find nearest .000 or .500
        levels = [
            integer_part + 0.000,
            integer_part + 0.500,
            integer_part + 1.000
        ]
        
        # Find closest
        distances = [abs(price - level) for level in levels]
        min_idx = np.argmin(distances)
        nearest_level = levels[min_idx]
        distance = distances[min_idx]
        
        # Determine type
        if nearest_level % 1 == 0:
            level_type = ".000"
        else:
            level_type = ".500"
        
        return nearest_level, distance, level_type
    
    def detect_rejection_candle(self, candle: pd.Series, direction: str) -> bool:
        """
        Detect rejection candle with long wick.
        
        Args:
            candle: Candle data
            direction: 'BUY' (bullish rejection) or 'SELL' (bearish rejection)
        """
        body = abs(candle['close'] - candle['open'])
        
        if body == 0:
            return False
        
        upper_wick = candle['high'] - max(candle['close'], candle['open'])
        lower_wick = min(candle['close'], candle['open']) - candle['low']
        
        if direction == 'BUY':
            # Bullish rejection: long lower wick
            return lower_wick > body * self.wick_ratio_min
        else:
            # Bearish rejection: long upper wick
            return upper_wick > body * self.wick_ratio_min
    
    async def generate_signal(self) -> Optional[Dict]:
        """Generate Round Levels signal."""
        from bots.helpers import fetch_candles
        from strategy import compute_indicators
        
        for pair in self.pairs:
            for tf in self.timeframes:
                try:
                    # Get candles
                    interval = self.config['trading']['timeframes'][tf]
                    lookback = 30
                    
                    df = await fetch_candles(self.api, pair, interval, lookback)
                    
                    if df.empty:
                        continue
                    
                    df = compute_indicators(df, interval)
                    
                    last = df.iloc[-1]
                    close = last['close']
                    
                    # Find nearest round level
                    level, distance, level_type = self.get_nearest_round_level(close)
                    
                    # Check if near level
                    if distance > self.level_tolerance:
                        continue
                    
                    # Determine expected rejection direction
                    if close < level:
                        # Price below level, expect bullish rejection
                        expected_direction = 'BUY'
                    else:
                        # Price above level, expect bearish rejection
                        expected_direction = 'SELL'
                    
                    # Check for rejection candle
                    if not self.detect_rejection_candle(last, expected_direction):
                        continue
                    
                    # Validate candle closed in expected direction
                    if expected_direction == 'BUY' and last['close'] <= last['open']:
                        continue
                    if expected_direction == 'SELL' and last['close'] >= last['open']:
                        continue
                    
                    # Calculate score
                    score = 10  # High score for round level rejections
                    
                    # Build signal
                    signal = {
                        'pair': pair,
                        'tf': tf,
                        'direction': expected_direction,
                        'score': score,
                        'pattern': f'Round Level Rejection ({level_type} @ {level:.5f})',
                        'price': close,
                        'features': {
                            'distance_to_level': distance,
                            'wick_ratio': self.calculate_wick_ratio(last, expected_direction),
                            'volume_spike': 1.0,  # TODO: Add volume if available
                            'time_of_day': last.name.hour if hasattr(last.name, 'hour') else 0
                        }
                    }
                    
                    self.log(
                        f"📊 Signal found: {pair} {expected_direction} "
                        f"@ {level_type} level {level:.5f}"
                    )
                    return signal
                    
                except Exception as e:
                    self.log(f"⚠️ Error processing {pair} {tf}: {e}", "error")
                    continue
        
        return None
    
    def calculate_wick_ratio(self, candle: pd.Series, direction: str) -> float:
        """Calculate wick to body ratio."""
        body = abs(candle['close'] - candle['open'])
        
        if body == 0:
            return 0.0
        
        if direction == 'BUY':
            wick = min(candle['close'], candle['open']) - candle['low']
        else:
            wick = candle['high'] - max(candle['close'], candle['open'])
        
        return wick / body


async def main():
    """Run Round Levels Bot."""
    bot = RoundLevelsBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
