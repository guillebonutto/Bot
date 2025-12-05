
import pandas as pd
import numpy as np
import os
import glob
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

# Configuration for Backtest
INITIAL_BALANCE = 1000
RISK_PER_TRADE = 0.02
PAYOUT = 0.92  # 92% payout for wins

def load_history(directory="history"):
    files = glob.glob(os.path.join(directory, "*.csv"))
    data = {}
    for f in files:
        # Expected filename format: PAIR_otc_TF.csv
        filename = os.path.basename(f)
        parts = filename.replace(".csv", "").split("_")
        if len(parts) >= 3:
            pair = parts[0] + "_" + parts[1]
            tf = parts[2]
            
            try:
                df = pd.read_csv(f)
                # Normalize columns to match strategy expectations (Capitalized)
                df = df.rename(columns={
                    'open': 'Open',
                    'close': 'Close',
                    'high': 'High',
                    'low': 'Low',
                    'volume': 'Volume'
                })

                # Ensure columns are correct
                if 'time' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['time'], unit='s', utc=True)
                elif 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                df = df.sort_values('timestamp').reset_index(drop=True)
                
                key = f"{pair}_{tf}"
                data[key] = df
            except Exception as e:
                print(f"Error loading {f}: {e}")
                
    return data

def run_backtest(df, pair, tf, params):
    """
    Run strategy on a single dataframe with given parameters.
    """
    # Unpack parameters
    rsi_period = params.get('rsi_period', 14)
    ma_long = params.get('ma_long', 50)
    breakout_tol = params.get('breakout_tol', 0.0015)
    
    # Compute indicators
    # Note: We pass parameters to compute_indicators
    df = compute_indicators(
        df, 
        interval=300 if 'M5' in tf else (600 if 'M10' in tf else 900),
        rsi_period=rsi_period,
        ma_long=ma_long
    )
    
    trades = []
    balance = INITIAL_BALANCE
    
    # Iterate through candles (simulate real-time)
    # Start after enough data for indicators
    start_idx = ma_long + 50 
    
    for i in range(start_idx, len(df)):
        # Slice data up to current candle 'i'
        # In real-time, we make decision at close of candle 'i' (or open of 'i+1')
        # Here we use 'i' as the last closed candle
        current_slice = df.iloc[:i+1]
        last = current_slice.iloc[-1]
        
        # --- Strategy Logic (Mirrors main.py) ---
        indicator_signal = None
        indicator_score = 0
        
        # Check indicators
        if last.get('EMA_conf', 0) != 0 and last.get('TF', 0) != 0 and not is_sideways(current_slice):
            indicator_score = score_signal(last, use_rsi=True) # Simplified score call
            if last['EMA_conf'] > 0 and indicator_score >= 4:
                indicator_signal = 'BUY'
            elif last['EMA_conf'] < 0 and indicator_score >= 4:
                indicator_signal = 'SELL'
        
        # Check patterns
        signal = None
        detectors = [detectar_doble_techo, detectar_compresion, detectar_flag, detectar_triangulo, detectar_ruptura_canal]
        
        # 1. Indicators Signal
        if indicator_signal:
             # Validate weak signal
             if validacion_senal_debil(indicator_signal, current_slice, indicator_score, min_score=4):
                 signal = indicator_signal
        
        # 2. Pattern Signal (if no indicator signal)
        if not signal:
            for det in detectors:
                pname, direction, pscore = det(current_slice)
                if direction:
                    # RSI Check (Skip for ruptura_canal)
                    if pname != "ruptura_canal":
                        rsi_val = validar_rsi(current_slice)
                        if rsi_val and rsi_val != direction:
                            continue
                    
                    # Breakout Check
                    ok, _ = confirm_breakout(current_slice, direction, breakout_tol=breakout_tol)
                    if ok:
                        signal = direction
                        break
        
        # Execute Trade
        if signal:
            # Determine outcome
            # For binary options, we look ahead 'duration' candles.
            # Assuming 1 candle duration for simplicity or fixed time.
            # Let's assume 1 candle duration (next candle close)
            if i + 1 < len(df):
                next_candle = df.iloc[i+1]
                win = False
                if signal == 'BUY':
                    win = next_candle['Close'] > last['Close']
                else:
                    win = next_candle['Close'] < last['Close']
                
                # Record trade
                amount = max(balance * RISK_PER_TRADE, 1.0)
                pnl = amount * PAYOUT if win else -amount
                balance += pnl
                
                trades.append({
                    'timestamp': last['timestamp'],
                    'pair': pair,
                    'tf': tf,
                    'signal': signal,
                    'result': 'WIN' if win else 'LOSS',
                    'pnl': pnl,
                    'balance': balance
                })
                
    return trades

def optimize():
    print("🚀 Starting Self-Learning Optimization...")
    data = load_history()
    print(f"Loaded {len(data)} datasets.")
    
    # Define parameter grid
    param_grid = [
        {'rsi_period': 14, 'ma_long': 50, 'breakout_tol': 0.0015}, # Default
        {'rsi_period': 7, 'ma_long': 50, 'breakout_tol': 0.0015},  # Faster RSI
        {'rsi_period': 14, 'ma_long': 100, 'breakout_tol': 0.0015}, # Slower Trend
        {'rsi_period': 14, 'ma_long': 50, 'breakout_tol': 0.0010}, # Stricter Breakout
        {'rsi_period': 14, 'ma_long': 50, 'breakout_tol': 0.0020}, # Looser Breakout
    ]
    
    best_params = None
    best_profit = -float('inf')
    
    for params in param_grid:
        print(f"\nTesting params: {params}")
        total_profit = 0
        total_trades = 0
        wins = 0
        
        for key, df in data.items():
            pair, tf = key.split("_", 1) # simple split
            trades = run_backtest(df, pair, tf, params)
            
            for t in trades:
                total_profit += t['pnl']
                if t['result'] == 'WIN':
                    wins += 1
            total_trades += len(trades)
            
        winrate = (wins / total_trades * 100) if total_trades > 0 else 0
        print(f"  -> Profit: ${total_profit:.2f} | Trades: {total_trades} | Winrate: {winrate:.1f}%")
        
        if total_profit > best_profit:
            best_profit = total_profit
            best_params = params
            
    print("\n" + "="*50)
    print(f"🏆 BEST STRATEGY FOUND")
    print(f"Params: {best_params}")
    print(f"Profit: ${best_profit:.2f}")
    print("="*50)
    
    # Save to config (mock)
    with open("best_strategy_config.txt", "w") as f:
        f.write(str(best_params))

if __name__ == "__main__":
    optimize()
