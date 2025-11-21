import os
import time
import asyncio
import requests
import logging
from datetime import datetime, timezone, timedelta
from functools import lru_cache
from collections import defaultdict

import pandas as pd
import numpy as np

# Import async wrapper de la librería que usás
from BinaryOptionsToolsV2.pocketoption import PocketOptionAsync

# ---------------------------
# CONFIG (ajustalo a tu gusto)
# ---------------------------
PAIRS = [
    'EURUSD_otc', 'GBPUSD_otc', 'USDJPY_otc', 'AUDUSD_otc', 'USDCAD_otc',
    'AUDCAD_otc', 'USDMXN_otc', 'USDCOP_otc', 'USDARS_otc'
]

TIMEFRAMES = {"M5": 300, "M10": 600, "M15": 900, "M30": 1800}
SELECTED_TFS = list(TIMEFRAMES.keys())

LOOKBACK = 50
MA_SHORT = 20
MA_LONG = 50
HTF_MULT = 2

USE_RSI = True
USE_REVERSAL_CANDLES = True
USE_SUPPORT_RESISTANCE = True
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

# RISK management
MAX_DAILY_LOSSES = 3
MAX_DAILY_TRADES = 10
RISK_PER_TRADE = 0.02  # 2% del balance
STREAK_LIMIT = 2  # cooling-off tras N pérdidas seguidas
COOLDOWN_SECONDS = 900  # 15 minutos
MAX_CONCURRENT_REQUESTS = 2  # Límite de requests simultáneos (reducido para evitar timeouts)

# TELEGRAM (mejor setear como variables de entorno)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Logging
logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def log(msg, level="info"):
    getattr(logging, level)(msg)
    print(msg)


def tg_send(msg: str):
    token = TELEGRAM_TOKEN
    chat = TELEGRAM_CHAT_ID
    if not token or not chat:
        log(f"[Telegram not configured] {msg}")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": msg},
            timeout=10
        )
    except Exception as e:
        log(f"[Telegram] Error enviando msg: {e}", "error")


# ---------------------------
# SMART CACHE SYSTEM
# ---------------------------
class SmartCache:
    def __init__(self):
        self.cache = {}
        self.timestamps = {}
        self.hit_count = defaultdict(int)
        self.miss_count = defaultdict(int)

    def get(self, key, ttl):
        """Obtener del cache si es válido"""
        now = time.time()
        if key in self.timestamps:
            age = now - self.timestamps[key]
            if age < ttl:
                self.hit_count[key] += 1
                return self.cache[key].copy(), age
        self.miss_count[key] += 1
        return None, 0

    def set(self, key, value):
        """Guardar en cache"""
        self.cache[key] = value
        self.timestamps[key] = time.time()

    def clear_expired(self, max_age=3600):
        """Limpiar entradas antiguas (1 hora por defecto)"""
        now = time.time()
        expired = [k for k, t in self.timestamps.items() if now - t > max_age]
        for k in expired:
            del self.cache[k]
            del self.timestamps[k]

    def stats(self):
        """Estadísticas de uso"""
        total_hits = sum(self.hit_count.values())
        total_misses = sum(self.miss_count.values())
        total = total_hits + total_misses
        if total == 0:
            return "Cache: sin uso"
        hit_rate = (total_hits / total) * 100
        return f"Cache: {hit_rate:.1f}% hit rate ({total_hits}/{total} requests)"


# Instancia global
smart_cache = SmartCache()

# ---------------------------
# Estado de riesgo y stats
# ---------------------------
daily_stats = {'losses': 0, 'trades': 0, 'date': datetime.utcnow().date()}
streak_losses = 0


def reset_daily_stats():
    today = datetime.utcnow().date()
    if daily_stats['date'] != today:
        daily_stats['losses'] = 0
        daily_stats['trades'] = 0
        daily_stats['date'] = today
        log("📅 Nuevo día - estadísticas reseteadas")


def can_trade(current_balance):
    reset_daily_stats()
    if daily_stats['losses'] >= MAX_DAILY_LOSSES:
        return False, f'🚫 Límite de pérdidas alcanzado ({MAX_DAILY_LOSSES})'
    if daily_stats['trades'] >= MAX_DAILY_TRADES:
        return False, f'🚫 Límite de operaciones diarias alcanzado ({MAX_DAILY_TRADES})'

    # Calcular monto con mínimo de $1
    max_amount = current_balance * RISK_PER_TRADE
    amount = max(max_amount, 1.0)  # Mínimo $1 siempre

    # Verificar si hay suficiente balance
    if current_balance < 1.0:
        return False, f'🚫 Balance insuficiente (${current_balance:.2f} < $1.00)'

    return True, amount


def update_streak(win: bool):
    global streak_losses
    if not win:
        streak_losses += 1
    else:
        streak_losses = 0
    return streak_losses


# ---------------------------
# Indicadores y patrones
# ---------------------------
def compute_rsi(df, period=RSI_PERIOD):
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def detect_reversal_candle(r):
    body = abs(r['Close'] - r['Open'])
    if body == 0:
        return 0
    upper = r['High'] - max(r['Close'], r['Open'])
    lower = min(r['Close'], r['Open']) - r['Low']
    return int(upper > body * 1.5 or lower > body * 1.5)


def detect_resistance(df):
    return df['High'].rolling(10, min_periods=1).max().iloc[-1]


def near_resistance(c, r, tol=0.0010):
    return abs(c - r) <= tol


# Detección de patrones simplificados — devuelven (signal, score)
def detectar_doble_techo(df):
    closes = df["Close"]
    if len(closes) < 10:
        return None, 0
    window = closes[-10:]
    high1 = window.iloc[0]
    high2 = window.iloc[-3]
    if abs(high1 - high2) <= high1 * 0.001:  # 0.1% parecido
        # criterio de ruptura: cierre bajo media ventana
        if window.iloc[-1] < window.mean():
            return "SELL", 3
    return None, 0


def detectar_compresion(df):
    highs = df['High'][-10:]
    lows = df['Low'][-10:]
    if len(highs) < 10:
        return None, 0
    if highs.iloc[-1] < highs.iloc[0] and lows.iloc[-1] > lows.iloc[0]:
        if df['Close'].iloc[-1] > highs.mean():
            return "BUY", 3
        if df['Close'].iloc[-1] < lows.mean():
            return "SELL", 3
    return None, 0


def detectar_flag(df):
    if len(df) < 12:
        return None, 0
    impuls = abs(df["Close"].iloc[-10] - df["Close"].iloc[-5]) > 3 * df["Close"].diff().abs().mean()
    if not impuls:
        return None, 0
    cond_retroceso = df['High'][-5:].max() - df['High'].iloc[-10] < df['High'].diff().abs().mean() * 2
    if cond_retroceso:
        if df['Close'].iloc[-1] > df['High'][-5:].max():
            return "BUY", 3
        if df['Close'].iloc[-1] < df['Low'][-5:].min():
            return "SELL", 3
    return None, 0


def detectar_triangulo(df, window=20):
    if len(df) < window:
        return None, 0
    highs = df['High'][-window:]
    lows = df['Low'][-window:]
    max_high = highs.max()
    min_low = lows.min()
    high_slope = (highs.iloc[-1] - highs.iloc[0]) / window
    low_slope = (lows.iloc[-1] - lows.iloc[0]) / window
    if abs(high_slope) < 1e-12 and low_slope > 0:
        if df['Close'].iloc[-1] > max_high:
            return "BUY", 3
    if abs(low_slope) < 1e-12 and high_slope < 0:
        if df['Close'].iloc[-1] < min_low:
            return "SELL", 3
    if high_slope < 0 and low_slope > 0:
        # posible breakout si está muy cerca de la resistencia
        if abs(df['Close'].iloc[-1] - max_high) < (max_high - min_low) * 0.1:
            return "BREAKOUT", 2
    return None, 0


def detectar_ruptura_canal(df, window=20, tol=0.0003):
    if len(df) < window:
        return None, 0
    canal_alto = df['High'][-window:].max()
    canal_bajo = df['Low'][-window:].min()
    c = df['Close'].iloc[-1]
    if abs(c - canal_alto) < (canal_alto * tol):
        return "BUY", 2
    if abs(c - canal_bajo) < (canal_bajo * tol):
        return "SELL", 2
    return None, 0


def validar_rsi(df, th_low=RSI_OVERSOLD, th_high=RSI_OVERBOUGHT):
    if 'RSI' not in df.columns or df['RSI'].isna().all():
        return None
    last_rsi = df['RSI'].iloc[-1]
    if last_rsi < th_low:
        return "BUY"
    if last_rsi > th_high:
        return "SELL"
    return None


def validacion_senal_debil(signal_dir, df, score, min_score=4):
    # Si el score está en el umbral, pedir confirmación por patrón y rsi
    if score >= min_score:
        return True
    # pedir patrón + rsi
    patron, pscore = detectar_flag(df)
    if not patron:
        patron, pscore = detectar_triangulo(df)
    if not patron:
        patron, pscore = detectar_doble_techo(df)
    rsi_val = validar_rsi(df)
    if patron and rsi_val == signal_dir:
        return True
    return False


# ---------------------------
# Fetch de velas OPTIMIZADO con caché
# ---------------------------
async def fetch_data_optimized(api, pair, interval, lookback=LOOKBACK):
    """
    Fetch con cache inteligente y retry automático
    """
    cache_key = f"{pair}_{interval}_{lookback}"

    # Intentar caché primero
    cached_df, age = smart_cache.get(cache_key, ttl=interval)
    if cached_df is not None:
        return cached_df

    # Cache miss → descargar con retry y delays más largos
    for attempt in range(3):
        try:
            offset = interval * lookback
            # Timeout más largo: 30s, 45s, 60s
            timeout_duration = 30 + (attempt * 15)

            raw = await asyncio.wait_for(
                api.get_candles(pair, interval, offset),
                timeout=timeout_duration
            )

            if not raw or not isinstance(raw, list):
                if attempt < 2:
                    # Backoff más largo: 3s, 6s
                    await asyncio.sleep(3 * (2 ** attempt))
                    continue
                log(f"⚠️ Respuesta vacía para {pair} {interval}s tras {attempt + 1} intentos", "warning")
                return pd.DataFrame()

            # Procesar datos
            df = pd.DataFrame(raw)
            if 'timestamp' not in df.columns:
                if 'time' in df.columns:
                    df['timestamp'] = df['time']
                else:
                    log(f"⚠️ Sin timestamp en {pair} {interval}s", "warning")
                    return pd.DataFrame()

            df = df.dropna(subset=['timestamp', 'open', 'close'])
            df = df[(df['open'] != 0) & (df['close'] != 0)]

            if len(df) < 5:
                log(f"⚠️ Pocas velas válidas para {pair} {interval}s ({len(df)})", "warning")
                return pd.DataFrame()

            df2 = pd.DataFrame({
                'Timestamp': pd.to_datetime(df['timestamp'], unit='s', utc=True),
                'Open': pd.to_numeric(df['open']),
                'Close': pd.to_numeric(df['close']),
                'High': pd.to_numeric(df['high']),
                'Low': pd.to_numeric(df['low'])
            })
            df2 = df2.sort_values('Timestamp').set_index('Timestamp')

            # Guardar en caché
            smart_cache.set(cache_key, df2)
            log(f"✅ Descargado {pair} {interval}s ({len(df2)} velas)", "debug")

            # Delay corto tras descarga exitosa para no saturar
            await asyncio.sleep(0.5)
            return df2

        except asyncio.TimeoutError:
            if attempt < 2:
                wait_time = 3 * (2 ** attempt)
                log(f"⏱️ Timeout {attempt + 1}/3 para {pair} {interval}s, esperando {wait_time}s...", "warning")
                await asyncio.sleep(wait_time)
            else:
                log(f"❌ Timeout definitivo para {pair} {interval}s después de 3 intentos", "error")
                return pd.DataFrame()
        except Exception as e:
            log(f"❌ Error descargando {pair} {interval}s: {e}", "error")
            if attempt < 2:
                await asyncio.sleep(2)
            else:
                return pd.DataFrame()

    return pd.DataFrame()


# ---------------------------
# Calculo de indicadores
# ---------------------------
def compute_indicators(df, interval):
    # Nota: df debe tener len >= MA_LONG
    df['MA_long'] = df['Close'].ewm(span=MA_LONG, adjust=False).mean()
    df['above'] = df['Close'] > df['MA_long']
    df['below'] = df['Close'] < df['MA_long']
    df['no_touch_above'] = df['above'].rolling(10, min_periods=10).sum() == 10
    df['no_touch_below'] = df['below'].rolling(10, min_periods=10).sum() == 10
    df['EMA_conf'] = np.where(df['no_touch_above'], 1, np.where(df['no_touch_below'], -1, 0))

    tr1 = df['High'] - df['Low']
    tr2 = (df['High'] - df['Close'].shift()).abs()
    tr3 = (df['Low'] - df['Close'].shift()).abs()
    df['ATR'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).rolling(14, min_periods=14).mean()

    df['trend'] = (df['Close'] - df['Close'].shift(14)) / df['ATR'].replace(0, np.nan)
    df['TF'] = np.where(df['trend'] > 1, 1, np.where(df['trend'] < -1, -1, 0))

    rng = df['High'].rolling(10, min_periods=10).max() - df['Low'].rolling(10, min_periods=10).min()
    df['triangle'] = (rng < df['ATR'] * 0.5).astype(int)

    try:
        df_htf = df['Close'].resample(f"{interval * HTF_MULT}s").last().ffill()
        ema_fast = df_htf.rolling(MA_SHORT * HTF_MULT, min_periods=MA_SHORT * HTF_MULT).mean()
        ema_slow = df_htf.ewm(span=MA_LONG * HTF_MULT, adjust=False).mean()
        htf_sig = np.where(ema_fast > ema_slow, 1, np.where(ema_fast < ema_slow, -1, 0))
        df['HTF'] = pd.Series(htf_sig, index=df_htf.index).reindex(df.index, method='ffill').fillna(0).astype(int)
    except Exception:
        df['HTF'] = 0

    if USE_RSI:
        df['RSI'] = compute_rsi(df)
    if USE_REVERSAL_CANDLES:
        df['Reversal'] = df.apply(detect_reversal_candle, axis=1)
    if USE_SUPPORT_RESISTANCE:
        r = detect_resistance(df)
        df['NearResistance'] = df['Close'].apply(lambda c: near_resistance(c, r))


def is_sideways(df, window=20, atr_mult=1.0):
    if len(df) < window:
        return False
    recent = df.iloc[-window:]
    pr = recent['High'].max() - recent['Low'].min()
    atr_avg = recent['ATR'].mean()
    if pd.isna(atr_avg) or atr_avg == 0:
        return True
    return pr < (atr_avg * atr_mult)


def score_signal(row):
    score = 0
    score += int(row.get('EMA_conf', 0) != 0)
    score += int(row.get('TF', 0) == row.get('EMA_conf', 0))
    score += int(row.get('triangle', 0) == 1)
    if USE_RSI and not pd.isna(row.get('RSI', np.nan)):
        if row['RSI'] < RSI_OVERSOLD or row['RSI'] > RSI_OVERBOUGHT:
            score += 1
    if USE_REVERSAL_CANDLES:
        if row.get('Reversal', 0) == 1:
            score += 1
    if USE_SUPPORT_RESISTANCE:
        if not row.get('NearResistance', False):
            score += 1
    return int(score)


# ---------------------------
# Generar señal (core) con Semaphore
# ---------------------------
async def generate_signal(api, pair, tf):
    interval = TIMEFRAMES[tf]
    df = await fetch_data_optimized(api, pair, interval)

    if df.empty or len(df) < MA_LONG:
        return None

    compute_indicators(df, interval)
    last = df.iloc[-1]

    # prioridad 1: señal por indicadores (sin exigir HTF)
    if last.get('EMA_conf', 0) == 0 or last.get('TF', 0) == 0 or is_sideways(df):
        indicator_signal = None
        indicator_score = 0
    else:
        indicator_score = score_signal(last)
        indicator_signal = 'BUY' if last['EMA_conf'] > 0 else 'SELL' if indicator_score >= 3 else None

    # si no señal por indicadores -> buscar patrones
    if not indicator_signal:
        # combinar detectores con prioridad
        detectors = [detectar_doble_techo, detectar_compresion, detectar_flag, detectar_triangulo,
                     detectar_ruptura_canal]
        for det in detectors:
            p, pscore = det(df)
            if p:
                # validación extra con RSI si existe
                rsi_ok = True
                if USE_RSI and 'RSI' in df.columns:
                    rsi_val = validar_rsi(df)
                    if rsi_val and rsi_val != p:
                        rsi_ok = False
                if rsi_ok:
                    return {
                        'pair': pair,
                        'tf': tf,
                        'signal': p,
                        'timestamp': last.name,
                        'duration': TIMEFRAMES[tf],
                        'score': int(pscore),
                        'pattern': p,
                        'price': float(last['Close']),
                        'ema': float(last.get('MA_long', np.nan))
                    }
        return None

    # si hay señal por indicadores -> validar si es débil
    if not validacion_senal_debil(indicator_signal, df, indicator_score, min_score=4):
        return None

    return {
        'pair': pair,
        'tf': tf,
        'signal': indicator_signal,
        'timestamp': last.name,
        'duration': TIMEFRAMES[tf],
        'score': int(indicator_score),
        'pattern': None,
        'price': float(last['Close']),
        'ema': float(last.get('MA_long', np.nan))
    }


# Wrapper con semaphore para limitar concurrencia
async def generate_signal_with_semaphore(semaphore, api, pair, tf):
    async with semaphore:
        return await generate_signal(api, pair, tf)


# ---------------------------
# Noticias (dummy) / TODO: integrar API real
# ---------------------------
def is_news_event():
    # TODO: reemplazar por API de calendario económico (econ-calendar) o newsapi
    now = datetime.utcnow()
    # ejemplo simple: no operar los viernes entre 13:00 y 14:00 UTC (dummy)
    if now.weekday() == 4 and 13 <= now.hour <= 14:
        return True
    return False


# ---------------------------
# MAIN
# ---------------------------
async def main():
    log("=" * 70)
    log("🤖 BOT MULTI-TF OPTIMIZADO - ARRANQUE")
    log("=" * 70)

    # pedir tokens si no están seteados
    global TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
    if not TELEGRAM_TOKEN:
        TELEGRAM_TOKEN = input("Introduce TELEGRAM_TOKEN (o deja vacío): ").strip() or None
    if TELEGRAM_TOKEN and not TELEGRAM_CHAT_ID:
        TELEGRAM_CHAT_ID = input("Introduce TELEGRAM_CHAT_ID (numérico): ").strip() or None

    ssid = input("Introduce tu SSID de PocketOption: ").strip()
    api = PocketOptionAsync(ssid=ssid)

    # intentar obtener balance / cuenta con múltiples métodos
    try:
        is_demo = api.is_demo()
        log(f"✅ Modo cuenta: {'DEMO' if is_demo else 'REAL'}")

        balance = None
        try:
            balance = await api.balance()
            if balance and balance > 0:
                log(f"💰 Balance obtenido: ${balance:.2f}")
            else:
                log(f"⚠️ Balance inválido: {balance}", "warning")
                balance = None
        except Exception as e:
            log(f"⚠️ Error con balance(): {e}", "warning")

        if balance and balance > 0:
            log(f"✅ Cuenta: {'DEMO' if is_demo else 'REAL'} - Balance: ${balance:.2f}")
            tg_send(f"🤖 Bot iniciado\n{'DEMO' if is_demo else 'REAL'}\n💰 Balance: ${balance:.2f}")
        else:
            log(f"⚠️ No se pudo obtener balance válido")
            tg_send(f"🤖 Bot iniciado - Cuenta {'DEMO' if is_demo else 'REAL'}\n⚠️ Balance no disponible")
    except Exception as e:
        log(f"⚠️ Error verificando cuenta: {e}", "error")
        tg_send("🤖 Bot iniciado (error obteniendo datos de cuenta)")

    log(f"\n📊 Pares: {len(PAIRS)} | Timeframes: {', '.join(SELECTED_TFS)}")
    log(f"💰 Risk por operación: {RISK_PER_TRADE * 100}%")
    log(f"🛡️ Max pérdidas diarias: {MAX_DAILY_LOSSES}")
    log(f"🚦 Max requests simultáneos: {MAX_CONCURRENT_REQUESTS}")
    log("=" * 70 + "\n")

    cycle = 0
    stats = {'wins': 0, 'losses': 0, 'total': 0}

    while True:
        try:
            if is_news_event():
                log("⚠️ Evento de noticias activo — pausa 15 min")
                tg_send("⚠️ Noticias importantes — pausa temporal.")
                await asyncio.sleep(COOLDOWN_SECONDS)
                continue

            cycle += 1
            log(f"\n{'=' * 70}")
            log(f"CICLO #{cycle} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")

            current_balance = None
            try:
                current_balance = await api.balance()
                if current_balance and current_balance > 0:
                    log(f"💰 Balance actual: ${current_balance:.2f}")
                else:
                    log(f"⚠️ Balance inválido: {current_balance}", "warning")
                    current_balance = None
            except Exception as e:
                log(f"⚠️ Error obteniendo balance: {e}", "warning")

            # Mostrar stats del cache cada 10 ciclos
            if cycle % 10 == 0:
                cache_stats = smart_cache.stats()
                log(f"📊 {cache_stats}")
                smart_cache.clear_expired()  # Limpiar cache viejo

            # Analizar en paralelo con límite de concurrencia MUY BAJO
            # Priorizar por timeframe: primero M5, luego M10, etc
            semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

            # Agrupar por timeframe para mejor caché
            all_signals = []
            for tf in SELECTED_TFS:
                tasks = [
                    generate_signal_with_semaphore(semaphore, api, pair, tf)
                    for pair in PAIRS
                ]
                log(f"🔍 Analizando {len(PAIRS)} pares en TF {tf} (max {MAX_CONCURRENT_REQUESTS} simultáneos)...")
                tf_results = await asyncio.gather(*tasks, return_exceptions=True)
                all_signals.extend(tf_results)

                # Pequeño delay entre timeframes para no saturar
                await asyncio.sleep(1)

            start_time = time.time()
            elapsed = time.time() - start_time
            log(f"⏱️ Análisis completado en {elapsed:.1f}s")

            # recoger mejores señales válidas
            best_signal = None
            best_score = -1
            valid_signals = 0

            for res in all_signals:
                if isinstance(res, Exception):
                    log(f"⚠️ Exception en generate_signal: {res}", "warning")
                    continue
                if not res:
                    continue

                valid_signals += 1
                sc = res.get('score', 0)
                if sc > best_score:
                    best_score = sc
                    best_signal = res

            log(f"✅ Señales válidas encontradas: {valid_signals}/{len(all_signals)}")

            if not best_signal:
                log("⏸️ Sin señales válidas en este ciclo. Esperando 30s...")
                await asyncio.sleep(30)
                continue

            # verificar si podemos tradear
            can, amount = can_trade(current_balance or 0)
            if not can:
                log(f"🚫 No puedo tradear: {amount}")
                tg_send(f"{amount} — pausa hasta nuevo día")
                await asyncio.sleep(COOLDOWN_SECONDS)
                continue

            sig = best_signal
            msg = (
                f"📌 SEÑAL DETECTADA\n"
                f"{'=' * 30}\n"
                f"Par: {sig['pair']}\n"
                f"TF: {sig['tf']}\n"
                f"Dirección: {sig['signal']}\n"
                f"Score: {sig['score']}\n"
                f"Patrón: {sig.get('pattern', 'Indicadores')}\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"💰 Precio: {sig['price']:.5f}\n"
                f"📊 EMA: {sig['ema']:.5f}\n"
                f"⏱️ Duración: {sig['duration'] // 60}min\n"
                f"💵 Monto: ${amount:.2f}"
            )
            log(msg)
            tg_send(msg)

            # Ejecutar operación
            try:
                if sig['signal'] == 'BUY':
                    trade_id, result = await asyncio.wait_for(
                        api.buy(asset=sig['pair'], amount=round(amount, 2), time=sig['duration'], check_win=False),
                        timeout=20
                    )
                else:
                    trade_id, result = await asyncio.wait_for(
                        api.sell(asset=sig['pair'], amount=round(amount, 2), time=sig['duration'], check_win=False),
                        timeout=20
                    )
                log(f"✅ Operación ejecutada ID: {trade_id}")
                tg_send(f"✅ Operación ejecutada\nID: {trade_id}")

                # esperar expiración + margen
                log(f"⏳ Esperando resultado ({sig['duration'] // 60}min)...")
                await asyncio.sleep(sig['duration'] + 10)

                # verificar resultado
                try:
                    win_result = await asyncio.wait_for(api.check_win(trade_id), timeout=20)
                    stats['total'] += 1
                    
                    log(f"[DEBUG] Resultado crudo de la API: {win_result}")
                    
                    if isinstance(win_result, dict):
                        raw = win_result.get('win', -1)
                    elif isinstance(win_result, (int, float)):
                        raw = win_result
                    elif isinstance(win_result, bool):
                        raw = 1 if win_result else 0
                    else:
                        raw = -1

                    win = (raw > 0)

                    if win:
                        stats['wins'] += 1
                        icon, text = "✅", "GANADA"
                    else:
                        stats['losses'] += 1
                        icon, text = "❌", "PERDIDA"
                        daily_stats['losses'] += 1

                    daily_stats['trades'] += 1
                    wr = stats['wins'] / stats['total'] * 100 if stats['total'] > 0 else 0.0
                    result_msg = (
                        f"{icon} {text}\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📊 Stats Totales:\n"
                        f"   {stats['wins']}W / {stats['losses']}L ({wr:.1f}%)\n"
                        f"📅 Stats Hoy:\n"
                        f"   {daily_stats['trades']} operaciones\n"
                        f"   {daily_stats['losses']} pérdidas"
                    )
                    log(result_msg)
                    tg_send(result_msg)

                    # actualizar racha y aplicar cooling-off si hace falta
                    streak = update_streak(win)
                    if streak >= STREAK_LIMIT:
                        cool_msg = f"⚠️ Racha de {streak} pérdidas. Cooling-off {COOLDOWN_SECONDS // 60}min."
                        log(cool_msg)
                        tg_send(cool_msg)
                        await asyncio.sleep(COOLDOWN_SECONDS)

                except Exception as e:
                    log(f"⚠️ Error verificando resultado: {e}", "warning")
                    tg_send(f"⚠️ No se pudo verificar resultado de {trade_id}")

            except Exception as e:
                log(f"❌ Error ejecutando operación: {e}", "error")
                tg_send(f"❌ Error ejecutando operación: {str(e)[:120]}")

            await asyncio.sleep(5)

        except Exception as e:
            log(f"⚠️ Error en loop principal: {e}", "error")
            tg_send(f"⚠️ Error en loop: {str(e)[:120]}")
            await asyncio.sleep(30)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("\n\n👋 Bot detenido por el usuario", "info")
        tg_send("🛑 Bot detenido manualmente")
        # Mostrar estadísticas finales del cache
        final_stats = smart_cache.stats()
        log(f"📊 Estadísticas finales: {final_stats}")
    except Exception as e:
        log(f"\n❌ Error fatal: {e}", "error")
        tg_send(f"❌ Error fatal: {str(e)[:120]}")