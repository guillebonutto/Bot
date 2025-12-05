"""
Bot #2: Trend Following
Strategy: H1 trend confirmation + M5 entry
Timeframes: H1 (confirmation), M5 (entry)
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


class TrendFollowingBot(BaseBot):
    """
    Trend Following Strategy:
    1. H1: ADX > 25 (strong trend)
    2. H1: EMA20 > EMA50 (uptrend) or EMA20 < EMA50 (downtrend)
    3. M5: Price crosses EMA20 in trend direction
    4. M5: MACD confirms direction
    """
    
    def __init__(self):
        super().__init__(bot_name="trend_following")
        
        # Strategy parameters
        self.adx_threshold = 25
        self.ema_short = 20
        self.ema_long = 50
        
        # Override timeframes
        self.timeframes = ["H1", "M5"]
    
    async def get_htf_trend(self, pair: str) -> Optional[str]:
        """
        Get H1 trend direction.
        Returns: 'BUY', 'SELL', or None
        """
        from bots.helpers import fetch_candles
        from strategy import compute_indicators
        
        try:
            interval_h1 = self.config['trading']['timeframes']['H1']
            
            df_h1 = await fetch_candles(self.api, pair, interval_h1, 50)
            
            if df_h1.empty:
                return None
            
            df_h1 = compute_indicators(df_h1, interval_h1)
            
            last = df_h1.iloc[-1]
            
            # Check ADX
            adx = last.get('adx', 0)
            if adx < self.adx_threshold:
                return None
            
            # Check EMA alignment
            ema_short = last['ema_short']
            ema_long = last['ema_long']
            
            if ema_short > ema_long:
                return 'BUY'
            elif ema_short < ema_long:
                return 'SELL'
            else:
                return None
                
        except Exception as e:
            self.log(f"⚠️ Error getting H1 trend for {pair}: {e}", "error")
            return None
    
    async def generate_signal(self) -> Optional[Dict]:
        """Generate Trend Following signal."""
        
        for pair in self.pairs:
            try:
                # Step 1: Get H1 trend
                htf_trend = await self.get_htf_trend(pair)
                
                if not htf_trend:
                    continue
                
                # Step 2: Check M5 for entry
                interval_m5 = self.config['trading']['timeframes']['M5']
                
                from bots.helpers import fetch_candles
                from strategy import compute_indicators
                
                df_m5 = await fetch_candles(self.api, pair, interval_m5, 50)
                
                if df_m5.empty:
                    continue
                
                df_m5 = compute_indicators(df_m5, interval_m5)
                
                last = df_m5.iloc[-1]
                prev = df_m5.iloc[-2]
                
                # Get indicators
                close = last['close']
                prev_close = prev['close']
                ema_short = last['ema_short']
                prev_ema_short = prev['ema_short']
                macd_hist = last.get('macd_hist', 0)
                
                # Check for EMA cross in trend direction
                crossed_up = prev_close <= prev_ema_short and close > ema_short
                crossed_down = prev_close >= prev_ema_short and close < ema_short
                
                # Validate with MACD
                macd_bullish = macd_hist > 0
                macd_bearish = macd_hist < 0
                
                # Generate signal
                if htf_trend == 'BUY' and crossed_up and macd_bullish:
                    direction = 'BUY'
                    score = 9
                elif htf_trend == 'SELL' and crossed_down and macd_bearish:
                    direction = 'SELL'
                    score = 9
                else:
                    continue
                
                # Build signal
                signal = {
                    'pair': pair,
                    'tf': 'M5',
                    'direction': direction,
                    'score': score,
                    'pattern': f'Trend Following (H1 {htf_trend})',
                    'price': close,
                    'features': {
                        'adx_h1': last.get('adx', 0),
                        'ema_alignment': 1 if htf_trend == 'BUY' else -1,
                        'macd_hist': macd_hist,
                        'volume_ratio': 1.0  # TODO: Add volume if available
                    }
                }
                
                self.log(f"📊 Signal found: {pair} {direction} (H1 trend: {htf_trend})")
                return signal
                
            except Exception as e:
                self.log(f"⚠️ Error processing {pair}: {e}", "error")
                continue
        
        return None


async def main():
    """Run Trend Following Bot."""
    bot = TrendFollowingBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
