
import pandas as pd
import numpy as np
import os
from datetime import datetime, timezone
import logging
from strategy import (
    compute_indicators,
    detectar_doble_techo,
    detectar_compresion,
    detectar_flag,
    detectar_triangulo,
    detectar_ruptura_canal,
    detectar_divergencia_macd,
    validar_rsi,
    validacion_senal_debil,
    score_signal,
    confirm_breakout,
    is_sideways
)

class ShadowStrategy:
    def __init__(self, name, params):
        self.name = name
        self.params = params
        self.stats = {'wins': 0, 'losses': 0, 'trades': 0, 'profit': 0.0}
        
    def process(self, df, pair, tf):
        # Unpack params with defaults
        rsi_period = self.params.get('rsi_period', 14)
        ma_long = self.params.get('ma_long', 50)
        breakout_tol = self.params.get('breakout_tol', 0.0015)
        min_score = self.params.get('min_score', 4)
        
        # Compute indicators for this strategy
        # Note: In a real optimized system, we might share common indicators,
        # but for flexibility, we re-compute if params differ.
        # To save CPU, we could check if params match default and reuse df, 
        # but let's keep it simple for now.
        df_strat = compute_indicators(
            df, 
            interval=300 if 'M5' in tf else (600 if 'M10' in tf else 900),
            rsi_period=rsi_period,
            ma_long=ma_long
        )
        
        last = df_strat.iloc[-1]
        
        # Logic similar to main.py but using self.params
        indicator_signal = None
        indicator_score = 0
        
        if last.get('EMA_conf', 0) != 0 and last.get('TF', 0) != 0 and not is_sideways(df_strat):
            indicator_score = score_signal(last, use_rsi=True)
            if last['EMA_conf'] > 0 and indicator_score >= min_score:
                indicator_signal = 'BUY'
            elif last['EMA_conf'] < 0 and indicator_score >= min_score:
                indicator_signal = 'SELL'
                
        signal = None
        detectors = [detectar_doble_techo, detectar_compresion, detectar_flag, detectar_triangulo, detectar_ruptura_canal]
        
        if indicator_signal:
             if validacion_senal_debil(indicator_signal, df_strat, indicator_score, min_score=min_score):
                 signal = indicator_signal
        
        if not signal:
            for det in detectors:
                pname, direction, pscore = det(df_strat)
                if direction:
                    if pname != "ruptura_canal":
                        rsi_val = validar_rsi(df_strat)
                        if rsi_val and rsi_val != direction:
                            continue
                    
                    ok, _ = confirm_breakout(df_strat, direction, breakout_tol=breakout_tol)
                    if ok:
                        signal = direction
                        break
        
        return signal, df_strat.iloc[-1]['Close']

class ShadowTrader:
    def __init__(self, log_file="shadow_trades.csv"):
        self.strategies = []
        self.log_file = log_file
        self.pending_trades = [] # List of dicts: {'strategy': name, 'pair': pair, 'signal': signal, 'entry_price': price, 'start_time': time, 'duration': duration}
        
        # Initialize CSV if not exists
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w') as f:
                f.write("timestamp,strategy,pair,tf,signal,result,profit_loss\n")
                
        # Define default strategies to test
        self.add_strategy("Default", {'rsi_period': 14, 'ma_long': 50, 'breakout_tol': 0.0015})
        self.add_strategy("Aggressive", {'rsi_period': 7, 'ma_long': 20, 'breakout_tol': 0.0010, 'min_score': 3})
        self.add_strategy("Conservative", {'rsi_period': 14, 'ma_long': 100, 'breakout_tol': 0.0020, 'min_score': 5})
        self.add_strategy("Breakout_Focus", {'rsi_period': 14, 'ma_long': 50, 'breakout_tol': 0.0005}) # Very strict breakout

    def add_strategy(self, name, params):
        self.strategies.append(ShadowStrategy(name, params))
        
    def process_candle(self, df, pair, tf):
        """
        Called every cycle for every pair/tf.
        Runs all strategies and records virtual trades.
        """
        # 1. Check pending trades (did they win/lose?)
        # In a real async loop, we might check this differently, 
        # but here we check if enough time passed or if we have new price data.
        # Since we get 'df', we can check if the *previous* candle closed the trade.
        # For simplicity in this "shadow" mode, we'll assume we check outcome 
        # based on the *next* candle close available in 'df'.
        
        # Actually, to keep it simple and real-time:
        # We will just log the SIGNAL here. 
        # Tracking the result requires persistence or keeping state across cycles.
        # Let's implement a simple state tracker.
        
        current_time = df.iloc[-1].name # Timestamp
        last_close = df.iloc[-1]['Close']
        
        # Check pending trades for this pair
        completed_trades = []
        for trade in self.pending_trades:
            if trade['pair'] == pair and trade['tf'] == tf:
                # Check if expired
                # Assuming fixed duration (e.g. 1 candle length) for simplicity in shadow mode
                # or we can use time diff.
                # Let's assume 1 candle duration.
                if current_time > trade['start_time']:
                    # Trade finished
                    win = False
                    if trade['signal'] == 'BUY':
                        win = last_close > trade['entry_price']
                    else:
                        win = last_close < trade['entry_price']
                    
                    self.log_trade(trade['strategy'], pair, tf, trade['signal'], 'WIN' if win else 'LOSS')
                    completed_trades.append(trade)
        
        for t in completed_trades:
            self.pending_trades.remove(t)
            
        # 2. Run strategies to find NEW signals
        for strat in self.strategies:
            signal, price = strat.process(df, pair, tf)
            if signal:
                # Register new pending trade
                self.pending_trades.append({
                    'strategy': strat.name,
                    'pair': pair,
                    'tf': tf,
                    'signal': signal,
                    'entry_price': price,
                    'start_time': current_time
                })
                # Log entry (optional, or just log result)
                # print(f"[Shadow] {strat.name} signal: {signal} on {pair}")

    def log_trade(self, strategy_name, pair, tf, signal, result):
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        pnl = 0.92 if result == 'WIN' else -1.0
        
        with open(self.log_file, 'a') as f:
            f.write(f"{timestamp},{strategy_name},{pair},{tf},{signal},{result},{pnl}\n")
            
        # Update in-memory stats
        for s in self.strategies:
            if s.name == strategy_name:
                s.stats['trades'] += 1
                if result == 'WIN':
                    s.stats['wins'] += 1
                    s.stats['profit'] += 0.92
                else:
                    s.stats['losses'] += 1
                    s.stats['profit'] -= 1.0

    def get_summary(self):
        lines = ["📊 Shadow Trading Results:"]
        for s in self.strategies:
            wr = (s.stats['wins'] / s.stats['trades'] * 100) if s.stats['trades'] > 0 else 0
            lines.append(f"  • {s.name}: {s.stats['wins']}W-{s.stats['losses']}L ({wr:.1f}%) | PnL: {s.stats['profit']:.2f}")
        return "\n".join(lines)
