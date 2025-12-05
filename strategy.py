# strategy_pro.py
import numpy as np
import pandas as pd
from typing import Tuple, Optional

# ===================================================================
# INDICADORES BASE (perfectos)
# ===================================================================
def compute_indicators(df: pd.DataFrame, interval: int):
    df = df.copy()
    
    # EMAs
    df['ema_short'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_long'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema_conf'] = np.where(df['close'] > df['ema_short'], 
                              np.where(df['ema_short'] > df['ema_long'], 2, 1), 
                              np.where(df['ema_short'] < df['ema_long'], -2, -1))

    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi'] = 100 - (100 / (1 + rs))
    df['rsi'] = df['rsi'].fillna(50)

    # MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']

    # Bollinger Bands
    df['bb_mid'] = df['close'].rolling(20).mean()
    std = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_mid'] + (std * 2)
    df['bb_lower'] = df['bb_mid'] - (std * 2)
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid']

    # ATR
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()

    # ADX (simplificado pero efectivo)
    plus_di = 100 * ((df['high'] - df['high'].shift()) / df['atr']).ewm(span=14).mean()
    minus_di = 100 * ((df['low'].shift() - df['low']) / df['atr']).ewm(span=14).mean()
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-6)
    df['adx'] = dx.ewm(span=14).mean()

    return df
# ===================================================================
# DETECTORES CORREGIDOS (AHORA SÍ FUNCIONAN)
# ===================================================================
def detectar_doble_techo(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str], int]:
    lookback = 50
    if len(df) < lookback: return None, None, 0
    
    # Filter: Require some trend activity
    if 'adx' in df.columns and df['adx'].iloc[-1] < 20: return None, None, 0
    
    high = df['high'].iloc[-lookback:]
    low = df['low'].iloc[-lookback:]
    close = df['close'].iloc[-1]

    peaks = []
    for i in range(5, len(high)-5):
        if high.iloc[i] == high.iloc[i-5:i+6].max():
            peaks.append((i, high.iloc[i]))
    
    if len(peaks) < 2: return None, None, 0
    
    p1_idx, p1_price = peaks[-2]
    p2_idx, p2_price = peaks[-1]
    
    if abs(p1_price - p2_price) / p1_price > 0.0012: return None, None, 0
    if p2_idx - p1_idx < 8 or p2_idx - p1_idx > 45: return None, None, 0
    
    valley = low.iloc[p1_idx:p2_idx].min()
    if (p1_price - valley) / p1_price < 0.004: return None, None, 0
    
    neck_level = valley + (p1_price - valley) * 0.15
    if close < neck_level:
        return "Doble Techo Confirmado", "SELL", 9
    return "Doble Techo Formándose", None, 6

def detectar_ruptura_canal(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str], int]:
    window = 30
    if len(df) < window: return None, None, 0
    
    # Filter: Strong trend required for breakout
    if 'adx' in df.columns and df['adx'].iloc[-1] < 25: return None, None, 0
    
    resistance = df['high'].iloc[-window:].max()
    support = df['low'].iloc[-window:].min()
    close = df['close'].iloc[-1]
    prev_close = df['close'].iloc[-2]
    
    range_size = resistance - support
    if range_size < df['atr'].iloc[-1] * 1.5: return None, None, 0  # canal muy estrecho
    
    if close > resistance and prev_close <= resistance:
        if close > resistance + range_size * 0.12:
            return "Ruptura Alcista", "BUY", 8
    if close < support and prev_close >= support:
        if close < support - range_size * 0.12:
            return "Ruptura Bajista", "SELL", 8
    return None, None, 0

def detectar_triangulo(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str], int]:
    window = 40
    if len(df) < window: return None, None, 0
    
    highs = df['high'].iloc[-window:]
    lows = df['low'].iloc[-window:]
    x = np.arange(len(highs))
    
    slope_h, intercept_h = np.polyfit(x, highs, 1)
    slope_l, intercept_l = np.polyfit(x, lows, 1)
    
    if slope_h < -0.00002 and slope_l > 0.00002:
        meet_x = (intercept_l - intercept_h) / (slope_h - slope_l)
        if 30 < meet_x < window * 1.4:
            projected = slope_h * meet_x + intercept_h
            if abs(df['close'].iloc[-1] - projected) < df['atr'].iloc[-1] * 3:
                direction = "BUY" if df['close'].iloc[-1] > df['open'].iloc[-1] else "SELL"
                return "Triángulo Cerca del Vértice", direction, 10
    return None, None, 0

def detectar_compresion(df: pd.DataFrame) -> bool:
    if 'bb_width' not in df.columns or 'adx' not in df.columns:
        return False
    recent_width = df['bb_width'].iloc[-1]
    past_width = df['bb_width'].iloc[-20:-5].mean()
    return recent_width < past_width * 0.5 and df['adx'].iloc[-1] < 18

def detectar_divergencia_rsi(df: pd.DataFrame) -> Optional[str]:
    lookback = 35
    if len(df) < lookback: return None
    
    price = df['close'].iloc[-lookback:]
    rsi = df['rsi'].iloc[-lookback:]
    
    last_low_price = price.iloc[-12:].min()
    last_low_rsi = rsi.loc[price.iloc[-12:].idxmin()]
    prev_low_price = price.iloc[:-12].min()
    prev_low_rsi = rsi.loc[price.iloc[:-12].idxmin()]
    
    if last_low_price < prev_low_price and last_low_rsi > prev_low_rsi:
        return "Divergencia Alcista"
    if last_low_price > prev_low_price and last_low_rsi < prev_low_rsi:
        return "Divergencia Bajista"
    return None

def is_sideways(df: pd.DataFrame) -> bool:
    if 'adx' not in df.columns: return False
    return df['adx'].iloc[-1] < 20 and df['bb_width'].iloc[-1] < df['bb_width'].iloc[-20:].quantile(0.3)