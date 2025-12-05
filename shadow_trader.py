"""
Shadow Trader - Forward testing module (SIMPLIFIED)
Simulates trades without executing them to validate strategy performance.
"""
import pandas as pd
import os
from datetime import datetime, timezone
from strategy import compute_indicators, is_sideways


class ShadowTrader:
    """
    Simplified Shadow Trader that logs potential trades without complex strategy testing.
    For now, just tracks basic signals.
    """
    
    def __init__(self, log_file="shadow_trades.csv"):
        self.log_file = log_file
        self.pending_trades = []
        
        # Initialize CSV if not exists
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w') as f:
                f.write("timestamp,pair,tf,signal,entry_price\\n")
    
    def process_candle(self, df, pair, tf):
        """
        Called every cycle for every pair/tf.
        Simplified version - just logs basic info.
        """
        try:
            if df.empty or len(df) < 20:
                return
            
            # Compute basic indicators
            df = compute_indicators(df, interval=300)
            last = df.iloc[-1]
            
            # Simple signal detection based on EMA
            ema_conf = last.get('ema_conf', 0)
            
            if ema_conf != 0 and not is_sideways(df):
                signal = 'BUY' if ema_conf > 0 else 'SELL'
                self.log_signal(pair, tf, signal, last['close'])
                
        except Exception:
            # Silently fail to not disrupt main bot
            pass
    
    def log_signal(self, pair, tf, signal, price):
        """Log a potential signal."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            with open(self.log_file, 'a') as f:
                f.write(f"{timestamp},{pair},{tf},{signal},{price}\\n")
        except Exception:
            pass
    
    def get_summary(self):
        """Return a simple summary."""
        return "📊 Shadow Trading: Simplified mode (logging signals only)"
