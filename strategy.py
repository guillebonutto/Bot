
import pandas as pd
import numpy as np

# Default constants (can be overridden)
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
MA_SHORT = 20
MA_LONG = 50
HTF_MULT = 2
MACD_FAST = 8
MACD_SLOW = 21
MACD_SIGNAL = 5
BREAKOUT_TOL = 0.0015
BREAKOUT_LOOKBACK = 20
BREAKOUT_USE_ATR = True

# ---------------------------
# Indicadores y patrones
# ---------------------------
def compute_rsi(df, period=RSI_PERIOD):
    delta = df['Close'].diff()

    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)

    avg_gain = pd.Series(gain).rolling(period).mean()
    avg_loss = pd.Series(loss).rolling(period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return pd.Series(rsi, index=df.index)


def compute_macd(df, fast=MACD_FAST, slow=MACD_SLOW, signal=MACD_SIGNAL):
    ema_fast = df['Close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['Close'].ewm(span=slow, adjust=False).mean()

    df['MACD'] = ema_fast - ema_slow
    df['MACD_signal'] = df['MACD'].ewm(span=signal, adjust=False).mean()
    df['MACD_hist'] = df['MACD'] - df['MACD_signal']

    return df


def detectar_divergencia_macd(df, lookback=20):
    """
    Devuelve:
    ("divergencia_macd", "BUY", score)
    ("divergencia_macd", "SELL", score)
    o (None, None, 0)
    """

    if len(df) < lookback + 5 or 'MACD' not in df.columns:
        return None, None, 0

    closes = df['Close'][-lookback:]
    macd = df['MACD'][-lookback:]

    # --- Detectar puntos locales ---
    price_min1 = closes.iloc[:lookback//2].idxmin()
    price_min2 = closes.iloc[lookback//2:].idxmin()

    price_max1 = closes.iloc[:lookback//2].idxmax()
    price_max2 = closes.iloc[lookback//2:].idxmax()

    # -----------------------------
    # 🚀 Divergencia alcista
    # -----------------------------
    if closes.loc[price_min2] < closes.loc[price_min1] and macd.loc[price_min2] > macd.loc[price_min1]:
        return "divergencia_macd", "BUY", 4

    # -----------------------------
    # 🔥 Divergencia bajista
    # -----------------------------
    if closes.loc[price_max2] > closes.loc[price_max1] and macd.loc[price_max2] < macd.loc[price_max1]:
        return "divergencia_macd", "SELL", 4

    return None, None, 0


def detect_reversal_candle(r):
    body = abs(r['Close'] - r['Open'])
    if body == 0:
        return 0
    upper = r['High'] - max(r['Close'], r['Open'])
    lower = min(r['Close'], r['Open']) - r['Low']
    
    # Reversión ALCISTA (mecha inferior larga) -> 1
    if lower > body * 1.5:
        return 1
    # Reversión BAJISTA (mecha superior larga) -> -1
    if upper > body * 1.5:
        return -1
        
    return 0


def detect_resistance(df):
    return df['High'].rolling(10, min_periods=1).max().iloc[-1]

def detect_support(df):
    return df['Low'].rolling(10, min_periods=1).min().iloc[-1]

def near_support(c, s, tol=0.0010):
    return abs(c - s) <= tol

def near_resistance(c, r, tol=0.0010):
    return abs(c - r) <= tol


# Detección de patrones simplificados — devuelven (signal, score)
def detectar_doble_techo(df):
    closes = df["Close"]
    if len(closes) < 20:
        return None, None, 0

    window = closes[-20:]

    # Buscar dos techos locales reales
    peak1 = window.iloc[5]
    peak2 = window.iloc[14]

    if abs(peak1 - peak2) <= peak1 * 0.0015:  # 0.15% de similitud
        # Confirmación de ruptura
        if window.iloc[-1] < window.mean():
            return "doble_techo", "SELL", 4

    return None, None, 0


def detectar_compresion(df):
    if len(df) < 12:
        return None, None, 0

    highs = df['High'][-10:]
    lows = df['Low'][-10:]

    if highs.iloc[-1] < highs.iloc[0] and lows.iloc[-1] > lows.iloc[0]:
        # ruptura real y más suave
        if df['Close'].iloc[-1] > highs.max():
            return "compresion", "BUY", 3
        if df['Close'].iloc[-1] < lows.min():
            return "compresion", "SELL", 3

    return None, None, 0


def detectar_flag(df):
    if len(df) < 20:
        return None, None, 0

    change = df["Close"].diff().abs()
    impuls = (df['Close'].iloc[-15] - df['Close'].iloc[-10])

    if abs(impuls) < change.mean() * 4:
        return None, None, 0

    retro_high = df['High'][-10:].max()
    retro_low = df['Low'][-10:].min()

    if df['Close'].iloc[-1] > retro_high:
        return "flag", "BUY", 3

    if df['Close'].iloc[-1] < retro_low:
        return "flag", "SELL", 3

    return None, None, 0


def detectar_triangulo(df, window=20):
    if len(df) < window:
        return None, None, 0

    highs = df['High'][-window:]
    lows = df['Low'][-window:]

    high_slope = (highs.iloc[-1] - highs.iloc[0])
    low_slope = (lows.iloc[-1] - lows.iloc[0])

    # Contracción real
    if high_slope < 0 and low_slope > 0:
        rango = highs.max() - lows.min()
        if abs(df['Close'].iloc[-1] - highs.max()) < rango * 0.15:
            return "triangulo", "BUY", 2
        if abs(df['Close'].iloc[-1] - lows.min()) < rango * 0.15:
            return "triangulo", "SELL", 2

    return None, None, 0


def detectar_ruptura_canal(df, window=20, tol=0.0015):
    if len(df) < window:
        return None, None, 0

    high = df['High'][-window:].max()
    low = df['Low'][-window:].min()
    c = df['Close'].iloc[-1]

    if abs(c - high) <= high * tol:
        return "ruptura_canal", "BUY", 3
    if abs(c - low) <= low * tol:
        return "ruptura_canal", "SELL", 3

    return None, None, 0


def validar_rsi(df, th_low=RSI_OVERSOLD, th_high=RSI_OVERBOUGHT):
    if 'RSI' not in df.columns or df['RSI'].isna().all():
        return None
    last_rsi = df['RSI'].iloc[-1]
    if last_rsi < th_low:
        return "BUY"
    if last_rsi > th_high:
        return "SELL"
    return None


def validacion_senal_debil(signal_dir, df, score, min_score=3):
    # Si la señal ya es suficientemente fuerte
    if score >= min_score:
        return True

    detectors = [
        detectar_doble_techo,
        detectar_compresion,
        detectar_flag,
        detectar_triangulo,
        detectar_ruptura_canal,
        detectar_divergencia_macd
    ]

    # Confirmación adicional por patrones
    for det in detectors:
        pname, pdir, pscore = det(df)

        # Interpretar BREAKOUT como señal direccional
        if pdir == "BREAKOUT":
            pdir = signal_dir

        if pdir == signal_dir:
            # Confirmar con RSI
            rsi_val = validar_rsi(df)
            if rsi_val == signal_dir:
                return True

    return False


# ---------------------------
# Calculo de indicadores
# ---------------------------
def compute_indicators(df, interval,
                        macd_fast=MACD_FAST, macd_slow=MACD_SLOW, macd_signal=MACD_SIGNAL,
                        rsi_period=RSI_PERIOD, pivot_window=9, atr_period=7,
                        htf_mult=HTF_MULT, ma_long=MA_LONG, ma_short=MA_SHORT):
    # seguridad: no modificar original y asegurar index ordenado
    df = df.copy()
    df = df.sort_index()

    # ---------- EMA long (conf) ----------
    df['EMA_long'] = df['Close'].ewm(span=ma_long, adjust=False).mean()
    df['above'] = df['Close'] > df['EMA_long']
    df['below'] = df['Close'] < df['EMA_long']
    df['no_touch_above'] = df['above'].rolling(10, min_periods=10).sum() == 10
    df['no_touch_below'] = df['below'].rolling(10, min_periods=10).sum() == 10
    df['EMA_conf'] = np.where(df['no_touch_above'], 1,
                              np.where(df['no_touch_below'], -1, 0))

    # ---------- TR and ATR using EMA (recommended for fast reaction) ----------
    df["H-L"] = df["High"] - df["Low"]
    df["H-PC"] = (df["High"] - df["Close"].shift()).abs()
    df["L-PC"] = (df["Low"] - df["Close"].shift()).abs()
    df["TR"] = df[["H-L", "H-PC", "L-PC"]].max(axis=1)

    # ATR con EWM evita NaNs largos y es más responsivo (bueno para binarias)
    # usamos min_periods=1 para tener valor desde la primera fila posible
    df['ATR'] = df['TR'].ewm(span=atr_period, adjust=False, min_periods=1).mean()

    # ---------- Trend / TF ----------
    # proteger división por cero / NaN
    last_atr = df['ATR'].replace(0, np.nan)
    df['trend'] = (df['Close'] - df['Close'].shift(14)) / last_atr
    df['TF'] = np.where(df['trend'] > 1, 1, np.where(df['trend'] < -1, -1, 0))

    # ---------- Triangle (congestion) ----------
    high_10 = df['High'].rolling(10, min_periods=1).max()
    low_10 = df['Low'].rolling(10, min_periods=1).min()
    rng = high_10 - low_10
    # proteger NaN de ATR: si ATR NaN, considerar triangle=False
    df['triangle'] = ((rng < df['ATR'] * 0.5) & df['ATR'].notna()).astype(int)

    # ---------- HTF EMA cross (resample por índice datetime) ----------
    try:
        # Asegurar que el índice es datetime
        if not isinstance(df.index, pd.DatetimeIndex):
            # Intentar convertir si hay columna timestamp o time
            if 'timestamp' in df.columns:
                df.index = pd.to_datetime(df['timestamp'], unit='s', utc=True)
            elif 'time' in df.columns:
                df.index = pd.to_datetime(df['time'], unit='s', utc=True)
        
        if isinstance(df.index, pd.DatetimeIndex):
            df_htf = df['Close'].resample(f"{interval * htf_mult}s").last().ffill()
            ema_fast = df_htf.ewm(span=ma_short * htf_mult, adjust=False).mean()
            ema_slow = df_htf.ewm(span=ma_long * htf_mult, adjust=False).mean()
            htf_sig = np.where(ema_fast > ema_slow, 1, np.where(ema_fast < ema_slow, -1, 0))
            df['HTF'] = pd.Series(htf_sig, index=df_htf.index).reindex(df.index, method='ffill').fillna(0).astype(int)
        else:
            df['HTF'] = 0
    except Exception:
        df['HTF'] = 0

    # ---------- RSI (Wilder / EMA alpha = 1/period) ----------
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / rsi_period, min_periods=1, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / rsi_period, min_periods=1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df['RSI'] = 100 - (100 / (1 + rs))

    # ---------- Reversal candle (vectorizado) ----------
    body = (df['Close'] - df['Open']).abs()
    upper = df['High'] - df[['Close', 'Open']].max(axis=1)
    lower = df[['Close', 'Open']].min(axis=1) - df['Low']
    df['Reversal'] = ((upper > body * 1.5) | (lower > body * 1.5)).astype(int)

    # ---------- Support / Resistance simples ----------
    df['Support_level'] = df['Low'].rolling(10, min_periods=1).min()
    df['Resistance_level'] = df['High'].rolling(10, min_periods=1).max()
    df['NearSupport'] = (df['Close'] - df['Support_level']).abs() <= (df['Support_level'] * 0.001)
    df['NearResistance'] = (df['Close'] - df['Resistance_level']).abs() <= (df['Resistance_level'] * 0.001)

    # ---------- MACD ----------
    df['EMA_fast_macd'] = df['Close'].ewm(span=macd_fast, adjust=False).mean()
    df['EMA_slow_macd'] = df['Close'].ewm(span=macd_slow, adjust=False).mean()
    df['MACD'] = df['EMA_fast_macd'] - df['EMA_slow_macd']
    df['MACD_signal'] = df['MACD'].ewm(span=macd_signal, adjust=False).mean()
    df['MACD_hist'] = df['MACD'] - df['MACD_signal']

    # ---------- Pivots (local minima / maxima) ----------
    if pivot_window % 2 == 0:
        pivot_window += 1
    df['local_min'] = df['Close'] == df['Close'].rolling(pivot_window, center=True, min_periods=1).min()
    df['local_max'] = df['Close'] == df['Close'].rolling(pivot_window, center=True, min_periods=1).max()

    lows_idx = df.index[df['local_min']].to_list()
    highs_idx = df.index[df['local_max']].to_list()

    # ---------- Inicializar divergencias ----------
    df['MACD_Bull_Div'] = False
    df['MACD_Bear_Div'] = False
    df['RSI_Bull_Div'] = False
    df['RSI_Bear_Div'] = False

    if len(lows_idx) >= 2:
        i1, i2 = lows_idx[-2], lows_idx[-1]
        p1, p2 = df.at[i1, 'Close'], df.at[i2, 'Close']
        m1, m2 = df.at[i1, 'MACD'], df.at[i2, 'MACD']
        if (p2 < p1) and (m2 > m1):
            df.at[i2, 'MACD_Bull_Div'] = True
        r1, r2 = df.at[i1, 'RSI'], df.at[i2, 'RSI']
        if (p2 < p1) and (r2 > r1):
            df.at[i2, 'RSI_Bull_Div'] = True

    if len(highs_idx) >= 2:
        j1, j2 = highs_idx[-2], highs_idx[-1]
        ph1, ph2 = df.at[j1, 'Close'], df.at[j2, 'Close']
        mh1, mh2 = df.at[j1, 'MACD'], df.at[j2, 'MACD']
        if (ph2 > ph1) and (mh2 < mh1):
            df.at[j2, 'MACD_Bear_Div'] = True
        rr1, rr2 = df.at[j1, 'RSI'], df.at[j2, 'RSI']
        if (ph2 > ph1) and (rr2 < rr1):
            df.at[j2, 'RSI_Bear_Div'] = True

    # limpieza auxiliar (no borramos ATR)
    df.drop(columns=['TR', 'EMA_fast_macd', 'EMA_slow_macd', 'local_min', 'local_max'], inplace=True, errors='ignore')

    return df


def is_sideways(df, window=20, atr_mult=1.0):
    if len(df) < window:
        return False
    recent = df.iloc[-window:]
    pr = recent['High'].max() - recent['Low'].min()
    atr_avg = recent['ATR'].mean()
    if pd.isna(atr_avg) or atr_avg == 0:
        return True
    return pr < (atr_avg * atr_mult)


def score_signal(row, signal_direction="BUY", use_rsi=True, use_reversal=True, use_support=True, use_resistance=True, rsi_oversold=RSI_OVERSOLD, rsi_overbought=RSI_OVERBOUGHT):
    score = 0
    score += int(row.get('EMA_conf', 0) != 0)
    score += int(row.get('TF', 0) == row.get('EMA_conf', 0))
    score += int(row.get('triangle', 0) == 1)
    
    # RSI
    if use_rsi and not pd.isna(row.get('RSI', np.nan)):
        if row['RSI'] < rsi_oversold and signal_direction == "BUY":
            score += 1
        elif row['RSI'] > rsi_overbought and signal_direction == "SELL":
            score += 1
            
    # Reversal (1=Bullish, -1=Bearish)
    if use_reversal:
        rev = row.get('Reversal', 0)
        if signal_direction == "BUY" and rev == 1:
            score += 1
        elif signal_direction == "SELL" and rev == -1:
            score += 1
            
    # Support/Resistance Logic
    # BUY: Good if NearSupport, Bad if NearResistance
    if signal_direction == "BUY":
        if use_support and row.get('NearSupport', False):
            score += 1
        if use_resistance and row.get('NearResistance', False):
            score -= 1 # Penalizar compra en resistencia
            
    # SELL: Good if NearResistance, Bad if NearSupport
    elif signal_direction == "SELL":
        if use_resistance and row.get('NearResistance', False):
            score += 1
        if use_support and row.get('NearSupport', False):
            score -= 1 # Penalizar venta en soporte
            
    return int(score)


def get_signal_indicators(df, last_row):
    """Extraer todos los indicadores de una vela para logging."""
    indicators = {
        'price': float(last_row['Close']) if not pd.isna(last_row.get('Close')) else 0,
        'ema': float(last_row.get('EMA_long', 0)) if not pd.isna(last_row.get('EMA_long')) else 0,
        'rsi': float(last_row.get('RSI', 0)) if not pd.isna(last_row.get('RSI')) else None,
        'ema_conf': int(last_row.get('EMA_conf', 0)),
        'tf_signal': int(last_row.get('TF', 0)),
        'atr': float(last_row.get('ATR', 0)) if not pd.isna(last_row.get('ATR')) else 0,
        'triangle_active': int(last_row.get('triangle', 0)),
        'reversal_candle': int(last_row.get('Reversal', 0)),
        'near_support': bool(last_row.get('NearSupport', False)),
        'near_resistance': bool(last_row.get('NearResistance', False)),
        'htf_signal': int(last_row.get('HTF', 0)) if 'HTF' in last_row.index else 0,
    }
    
    # Obtener niveles de soporte/resistencia si existen
    if 'NearSupport' in df.columns:
        support = detect_support(df)
        resistance = detect_resistance(df)
        indicators['support_level'] = float(support) if not pd.isna(support) else None
        indicators['resistance_level'] = float(resistance) if not pd.isna(resistance) else None
    else:
        indicators['support_level'] = None
        indicators['resistance_level'] = None
    
    return indicators


def confirm_breakout(df, direction, lookback=BREAKOUT_LOOKBACK, breakout_tol=BREAKOUT_TOL, use_atr=BREAKOUT_USE_ATR):
    """
    Confirma breakout con 3 criterios flexibles:
     - porcentaje (breakout_tol)
     - o separación respecto a ATR (si BREAKOUT_USE_ATR)
     - o simple cierre fuera del rango (sin multiplicador) como fallback
    Devuelve (bool, reason_str)
    """
    if len(df) < lookback + 1:
        return False, "too_short"

    # Excluir la vela actual del cálculo del máximo/mínimo previo
    # Queremos saber si la vela actual ROMPIÓ el rango de las anteriores
    window = df.iloc[-(lookback+1):-1]
    
    if window.empty:
         return False, "window_empty"

    high = window['High'].max()
    low = window['Low'].min()
    last_close = df['Close'].iloc[-1]
    last_high = df['High'].iloc[-1]
    last_low = df['Low'].iloc[-1]

    # criterio 1: porcentaje tolerante
    if direction == "BUY":
        pct_ok = last_close > high * (1 + breakout_tol)
        if pct_ok:
            return True, f"pct_ok ({last_close:.5f} > {high*(1+breakout_tol):.5f})"
    else:
        pct_ok = last_close < low * (1 - breakout_tol)
        if pct_ok:
            return True, f"pct_ok ({last_close:.5f} < {low*(1-breakout_tol):.5f})"

    # criterio 2: ATR-based (si está disponible)
    if use_atr and 'ATR' in df.columns and not pd.isna(df['ATR'].iloc[-1]):
        atr = df['ATR'].iloc[-1]
        # exigir que el cierre supere el nivel por al menos una fracción del ATR
        if direction == "BUY":
            atr_ok = (last_close - high) > (0.25 * atr)   # 25% del ATR
            if atr_ok:
                return True, f"atr_ok (+{last_close-high:.6f} > {0.25*atr:.6f})"
            # permitir si la mecha (High) toca por encima del nivel por más de 0.5*ATR
            if (last_high - high) > (0.5 * atr):
                return True, f"atr_mecha_ok (high {last_high:.6f})"
        else:
            atr_ok = (low - last_close) > (0.25 * atr)
            if atr_ok:
                return True, f"atr_ok ({low-last_close:.6f} > {0.25*atr:.6f})"
            if (low - last_low) > (0.5 * atr):
                return True, f"atr_mecha_ok (low {last_low:.6f})"

    # criterio 3: fallback simple: cierre fuera del rango (sin multiplicador)
    if direction == "BUY" and last_close > high:
        return True, "simple_close_above_high"
    if direction == "SELL" and last_close < low:
        return True, "simple_close_below_low"

    # si llegamos acá => rechazado
    reason = f"rejected last_close={last_close:.6f} high={high:.6f} low={low:.6f}"
    return False, reason


def htf_confirms(df, direction):
    if 'HTF' not in df.columns:
        return False
    last_htf = df['HTF'].iloc[-1]
    return (direction == "BUY" and last_htf == 1) or (direction == "SELL" and last_htf == -1)
