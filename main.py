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

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()  # This loads .env automatically

# Import async wrapper de la librería que usás
import sys
try:
    from BinaryOptionsToolsV2.pocketoption import PocketOptionAsync
    # Intentar importar error si existe, sino definirlo localmente
    try:
        from BinaryOptionsToolsV2.pocketoption import PocketOptionError
    except ImportError:
        class PocketOptionError(Exception):
            pass
except ImportError as e:
    # Check for version mismatch
    if sys.version_info[:2] != (3, 11):
        print(f"⚠️ WARNING: BinaryOptionsToolsV2 import failed.")
        print(f"   Current Python: {sys.version.split()[0]}")
        print(f"   The library likely requires Python 3.11.")
        print(f"   Try running with: .\\venv\\Scripts\\python.exe main.py")
    
    print(f"⚠️ Import Error Details: {e}")
    
    from mock_pocketoption import PocketOptionAsync
    class PocketOptionError(Exception):
        pass
    print("⚠️ Running in SIMULATION MODE (Mock API) due to missing library.")

# Import trade logger
from trade_logger import trade_logger

# Import ML-Trades integration
try:
    from ml_trades_integration import ml_trades, predict_success
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("⚠️ ml_trades_integration no disponible (opcional)")

# Import Strategy Logic
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
    htf_confirms,
    is_sideways,
    detect_support,
    detect_resistance,
    detectar_divergencia_rsi,
    get_signal_indicators
)
from shadow_trader import ShadowTrader
from bot_state import BotState
from risk_manager import RiskManager
from signal_types import Direction, SignalSource, PatternType

# ---------------------------
# CONFIG (ajustalo a tu gusto)
# ---------------------------
PAIRS = [
    'EURUSD_otc', 'GBPUSD_otc', 'USDJPY_otc', 'AUDUSD_otc', 'USDCAD_otc',
    'AUDCAD_otc', 'USDMXN_otc', 'USDCOP_otc', 'USDARS_otc', "#INTC_otc"
]

TIMEFRAMES = {"M5": 300, "M10": 600, "M15": 900, "M30": 1800}

SELECTED_TFS = list(TIMEFRAMES.keys())
LOOKBACK = 50
MA_SHORT = 20
MA_LONG = 50
HTF_MULT = 2

RSI_PERIOD = 7  # rápido y estable

MACD_FAST = 8
MACD_SLOW = 21
MACD_SIGNAL = 5

USE_RSI = True
USE_REVERSAL_CANDLES = True
USE_RESISTANCE = True
USE_SUPPORT = True
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

# --- Nuevas configs para MODO PRO ---
TARGET_WINRATE = 0.55              # objetivo mínimo de winrate reciente (55%)
ROLLING_WINDOW_TRADES = 20         # para calcular winrate reciente
MIN_SCORE_BASE = 4                 # score mínimo base para operar
ADAPTIVE_SCORE_INCREMENT = 1       # cuánto subir el score mínimo si winrate cae
MIN_SCORE_MAX = 7                  # tope al que puede subir el min score
BREAKOUT_TOL = 0.0015              # tolerancia para confirmar breakout (ajustable)
BREAKOUT_LOOKBACK = 20             # lookback para definir niveles de resistencia/soporte
BREAKOUT_STRICT = False      # si True exige la condición estricta; False usa criterio más flexible
BREAKOUT_USE_ATR = True      # si True permite confirmar breakout usando ATR
DEBUG_BREAKOUT = True        # imprime info cuando un breakout se rechaza (ponelo False en prod)

# Logging
logging.basicConfig(
    filename="bot.log",
    level=logging.DEBUG,
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
                # devolver copia para evitar modificaciones externas
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
daily_stats = {'losses': 0, 'trades': 0, 'date': datetime.now(timezone.utc).date()}
streak_losses = 0

# historial de trades para calcular winrate rolling (MODO PRO)
trade_history = []  # lista de dicts: {'win': True/False, 'timestamp': datetime}


def reset_daily_stats():
    today = datetime.now(timezone.utc).date()
    if daily_stats['date'] != today:
        daily_stats['losses'] = 0
        daily_stats['trades'] = 0
        daily_stats['date'] = today
        log("📅 Nuevo día - estadísticas reseteadas")


# can_trade function removed - now using RiskManager.can_trade()


def update_streak(win: bool):
    global streak_losses
    if not win:
        streak_losses += 1
    else:
        streak_losses = 0
    return streak_losses


def rolling_winrate(n=None):
    if daily_stats['trades'] == 0:
        return None
    wins = daily_stats['trades'] - daily_stats['losses']
    return wins / daily_stats['trades']


# ---------------------------
# Indicadores y patrones
# ---------------------------




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

            # Usar wait_for para timeout real
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
            # df = df[(df['open'] != 0) & (df['close'] != 0)] # Optional: filter zero prices

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
            # log(f"✅ Descargado {pair} {interval}s ({len(df2)} velas)", "debug")

            return df2

        except asyncio.TimeoutError:
            wait_time = 5 * (attempt + 1)
            if attempt < 2:
                log(f"⏱️ Timeout {attempt + 1}/3 para {pair} {interval}s, esperando {wait_time}s...", "warning")
                await asyncio.sleep(wait_time)
            else:
                log(f"❌ Timeout definitivo para {pair} {interval}s después de 3 intentos", "error")
                return pd.DataFrame()
        except PocketOptionError as e:
            # Error específico de activo inactivo
            log(f"⚠️ Activo {pair} inactivo o no disponible: {e}", "warning")
            return pd.DataFrame()
        except Exception as e:
            log(f"❌ Error descargando {pair} {interval}s: {e}", "error")
            if attempt < 2:
                await asyncio.sleep(2)
            else:
                return pd.DataFrame()

    return pd.DataFrame()



# ---------------------------
# Generar señal (core) con Semaphore
# ---------------------------
async def generate_signal(api, pair, tf, bot_state, shadow_trader=None):
    """
    Generate trading signal with clear 3-step flow:
    1. Compute all possible signals (indicators + patterns)
    2. Score and rank all candidates
    3. Select best signal if above threshold
    
    Returns:
        dict with signal details or None if no valid signal
    """
    interval = TIMEFRAMES[tf]
    df = await fetch_data_optimized(api, pair, interval)

    if df.empty or len(df) < MA_LONG:
        return None

    # Shadow trading (forward testing)
    if shadow_trader:
        try:
            shadow_trader.process_candle(df, pair, tf)
        except Exception as e:
            log(f"Error en Shadow Trader: {e}", "error")

    df = compute_indicators(df, interval)
    last = df.iloc[-1]

    # ============================================================
    # STEP 1: Compute ALL possible signals
    # ============================================================
    candidates = []
    
    # 1A. Indicator-based signal
    if not (last.get('EMA_conf', 0) == 0 or last.get('TF', 0) == 0 or is_sideways(df)):
        if last['EMA_conf'] > 0:
            direction = Direction.BUY
        elif last['EMA_conf'] < 0:
            direction = Direction.SELL
        else:
            direction = None
        
        if direction:
            score = score_signal(last, signal_direction=str(direction))
            candidates.append({
                'source': SignalSource.INDICATOR,
                'direction': direction,
                'score': score,
                'pattern': None,
                'data': last
            })
    
    # 1B. Pattern-based signals
    detectors = [
        (detectar_doble_techo, PatternType.DOUBLE_TOP),
        (detectar_compresion, PatternType.COMPRESSION),
        (detectar_flag, PatternType.FLAG),
        (detectar_triangulo, PatternType.TRIANGLE),
        (detectar_ruptura_canal, PatternType.CHANNEL_BREAKOUT),
        (detectar_divergencia_rsi, PatternType.RSI_DIVERGENCE)
    ]
    
    for detector_func, pattern_type in detectors:
        pattern_name, direction_str, pscore = detector_func(df)
        
        if direction_str is None:
            continue
        
        # Convert string direction to enum
        direction = Direction.BUY if direction_str == 'BUY' else Direction.SELL
        
        # RSI validation (skip for channel breakout)
        if USE_RSI and pattern_type != PatternType.CHANNEL_BREAKOUT:
            rsi_val = validar_rsi(df)
            if rsi_val and rsi_val != direction_str:
                log(f"⏸️ Patrón {pattern_type} rechazado por RSI conflictivo: {pair} {tf}", "debug")
                continue
        
        # Breakout confirmation
        ok, reason = confirm_breakout(df, direction=direction_str)
        if not ok:
            log(f"⏸️ Patrón {pattern_type} rechazado - breakout no confirmado: {pair} {tf}", "debug")
            continue
        
        candidates.append({
            'source': SignalSource.PATTERN,
            'direction': direction,
            'score': int(pscore),
            'pattern': pattern_type,
            'data': last
        })
    
    # ============================================================
    # STEP 2: Score and rank all candidates
    # ============================================================
    if not candidates:
        return None
    
    # Calculate adaptive minimum score based on winrate
    min_score = MIN_SCORE_BASE
    
    # Get trade history from bot_state
    trade_history = await bot_state.get_trade_history()
    
    if len(trade_history) >= 10:
        # Calculate rolling winrate (last 20 trades)
        recent_trades = trade_history[-20:]
        wins = sum(1 for t in recent_trades if t['win'])
        current_wr = wins / len(recent_trades)
        
        if current_wr < TARGET_WINRATE:
            deficit = TARGET_WINRATE - current_wr
            inc = int(np.ceil(deficit * 10)) * ADAPTIVE_SCORE_INCREMENT
            min_score = min(MIN_SCORE_MAX, MIN_SCORE_BASE + inc)
        
        log(f"🔧 Winrate reciente: {current_wr:.2f} (trades: {len(recent_trades)}) → min_score = {min_score}", "debug")
    
    # Filter by minimum score
    valid_candidates = [c for c in candidates if c['score'] >= min_score]
    
    if not valid_candidates:
        log(f"⏸️ Todas las señales descartadas por score insuficiente (min={min_score}): {pair} {tf}", "debug")
        return None
    
    # Sort by score (highest first)
    valid_candidates.sort(key=lambda x: x['score'], reverse=True)
    
    # ============================================================
    # STEP 3: Select best signal and validate
    # ============================================================
    best = valid_candidates[0]
    direction_str = str(best['direction'])
    
    # Additional validation for weak signals
    if not validacion_senal_debil(direction_str, df, best['score'], min_score=min_score):
        log(f"⏸️ Mejor señal descartada por validación débil: {pair} {tf}", "debug")
        return None
    
    # Build signal dict
    indicators_used = []
    if last.get('EMA_conf', 0) != 0:
        indicators_used.append(f"EMA_conf={last['EMA_conf']}")
    if last.get('TF', 0) != 0:
        indicators_used.append(f"TF={last['TF']}")
    if 'RSI' in last:
        indicators_used.append(f"RSI={last['RSI']:.1f}")
    if 'MACD' in last:
        indicators_used.append(f"MACD={last['MACD']:.4f}")
    
    return {
        'pair': pair,
        'tf': tf,
        'signal': direction_str,
        'timestamp': last.name,
        'duration': TIMEFRAMES[tf],
        'score': best['score'],
        'pattern': str(best['pattern']) if best['pattern'] else None,
        'source': str(best['source']),
        'price': float(last['Close']),
        'ema': float(last.get('EMA_long', np.nan)),
        'indicators': ', '.join(indicators_used) if indicators_used else 'N/A'
    }
    

# Wrapper con semaphore para limitar concurrencia
async def generate_signal_with_semaphore(semaphore, api, pair, tf, bot_state, shadow_trader=None):
    async with semaphore:
        try:
            return await generate_signal(api, pair, tf, bot_state, shadow_trader)
        except Exception as e:
            log(f"⚠️ Exception en generate_signal_with_semaphore {pair} {tf}: {e}", "warning")
            return None

# ---------------------------
def is_news_event():
    # TODO: reemplazar por API de calendario económico (econ-calendar) o newsapi
    now = datetime.now(timezone.utc)
    # ejemplo simple: no operar los viernes entre 13:00 y 14:00 UTC (dummy)
    if now.weekday() == 4 and 13 <= now.hour <= 14:
        return True
    return False


# ---------------------------
# HEALTH CHECK SERVER (For Cloud Deployment)
# ---------------------------
async def health_check_handler(reader, writer):
    try:
        await reader.read(100) # Read request (ignore content)
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/plain\r\n"
            "Content-Length: 2\r\n"
            "\r\n"
            "OK"
        )
        writer.write(response.encode())
        await writer.drain()
    except Exception:
        pass
    finally:
        writer.close()

async def start_health_server():
    port = int(os.environ.get("PORT", 8080))
    try:
        server = await asyncio.start_server(health_check_handler, '0.0.0.0', port)
        log(f"🏥 Health check server listening on port {port}", "info")
        # Run server in background
        async with server:
            await server.serve_forever()
    except Exception as e:
        log(f"⚠️ No se pudo iniciar health check server: {e}", "warning")

async def keep_alive():
    """Tarea en segundo plano para evitar que el contenedor se duerma (Self-Ping)"""
    port = int(os.environ.get("PORT", 8080))
    url = f"http://127.0.0.1:{port}"
    while True:
        await asyncio.sleep(300) # Cada 5 minutos
        try:
            requests.get(url, timeout=5)
            # No logueamos nada para no ensuciar, o solo debug
        except Exception:
            pass

# ---------------------------
# MAIN
# ---------------------------
async def run_bot(ssid, telegram_token, telegram_chat_id, logger_callback=None, stop_event=None):
    """
    Función principal para ejecutar el bot desde la GUI o consola.
    """
    global TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
    
    # Redirigir logs si hay callback
    def log_gui(msg, level="info"):
        getattr(logging, level)(msg)
        print(msg)
        if logger_callback:
            logger_callback(f"[{level.upper()}] {msg}")

    # Sobreescribir función log global temporalmente
    global log
    original_log = log
    log = log_gui

    log("=" * 70)
    log("🤖 BOT MULTI-TF MODO PRO - ARRANQUE")
    log("=" * 70)

    TELEGRAM_TOKEN = telegram_token
    TELEGRAM_CHAT_ID = telegram_chat_id

    # Iniciar servidor de health check en segundo plano
    asyncio.create_task(start_health_server())
    # Iniciar self-ping para evitar dormir
    asyncio.create_task(keep_alive())

    api = PocketOptionAsync(ssid=ssid)

    # intentar obtener balance / cuenta con retry
    balance = None
    for attempt in range(3):
        if stop_event and stop_event.is_set(): return

        try:
            is_demo = api.is_demo()
            balance = await api.balance()

            if balance is not None: # Puede ser 0.0
                log(f"✅ Cuenta: {'DEMO' if is_demo else 'REAL'} - Balance: ${balance:.2f}")
                tg_send(f"🤖 Bot iniciado\n{'DEMO' if is_demo else 'REAL'}\n💰 Balance: ${balance:.2f}")
                break
            else:
                if attempt < 2:
                    log(f"⚠️ Balance inválido ({balance}), reintentando... ({attempt + 1}/3)", "warning")
                    await asyncio.sleep(2)
                else:
                    log(f"⚠️ No se pudo obtener balance válido tras 3 intentos", "warning")
                    tg_send(f"🤖 Bot iniciado - Cuenta {'DEMO' if is_demo else 'REAL'}\n⚠️ Balance no disponible")
        except Exception as e:
            if attempt < 2:
                log(f"⚠️ Error obteniendo balance ({attempt + 1}/3): {e}", "warning")
                await asyncio.sleep(2)
            else:
                log(f"❌ Error verificando cuenta tras 3 intentos: {e}", "error")
                tg_send("🤖 Bot iniciado (error obteniendo datos de cuenta)")

    log(f"\n📊 Pares: {len(PAIRS)} | Timeframes: {', '.join(SELECTED_TFS)}")
    log(f"💰 Risk por operación: {RISK_PER_TRADE * 100}%")
    log(f"🛡️ Max pérdidas diarias: {MAX_DAILY_LOSSES}")
    log(f"🚦 Max requests simultáneos: {MAX_CONCURRENT_REQUESTS}")
    log("=" * 70 + "\n")

    cycle = 0
    
    # Initialize thread-safe state management
    bot_state = BotState()
    
    # MODO TESTING: Límites muy altos para recopilar datos
    # TODO: Restaurar límites estrictos para producción
    risk_manager = RiskManager(
        max_daily_losses=999,      # Prácticamente sin límite para testing
        max_daily_trades=999,      # Prácticamente sin límite para testing
        risk_per_trade=RISK_PER_TRADE,
        max_drawdown=0.95,         # 95% drawdown (muy alto, solo para testing)
        streak_limit=999           # Sin límite de racha para testing
    )
    print("⚠️ MODO TESTING: Límites de riesgo desactivados para entrenamiento")
    print("   ⚠️ NO usar en cuenta REAL sin restaurar límites estrictos")

    
    # Set initial balance for drawdown tracking
    if balance is not None:
        await bot_state.set_initial_balance(balance)

    # Inicializar Shadow Trader (Forward Testing)
    shadow_trader = ShadowTrader()
    print("👻 Shadow Trader activado: Probando estrategias en paralelo...")

    while True:
        if stop_event and stop_event.is_set():
            log("🛑 Deteniendo bot por solicitud del usuario...")
            break

        try:
            if is_news_event():
                log("⚠️ Evento de noticias activo — pausa 15 min")
                tg_send("⚠️ Noticias importantes — pausa temporal.")
                await asyncio.sleep(COOLDOWN_SECONDS)
                continue

            cycle += 1
            log(f"\n{'=' * 70}")
            log(f"CICLO #{cycle} - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")

            current_balance = None
            try:
                current_balance = await api.balance()
                if current_balance is not None:
                    log(f"💰 Balance actual: ${current_balance:.2f}")
                else:
                    log(f"⚠️ Balance inválido: {current_balance}", "warning")
                    current_balance = 0.0
            except Exception as e:
                log(f"⚠️ Error obteniendo balance: {e}", "warning")
                current_balance = 0.0

            # Verificar si podemos tradear usando RiskManager
            can, result = await risk_manager.can_trade(current_balance or 0, bot_state)
            if not can:
                log(f"🚫 No puedo tradear: {result}")
                tg_send(f"{result} — pausa hasta nuevo día")
                await asyncio.sleep(COOLDOWN_SECONDS)
                continue
            
            # result contiene el amount si can=True
            amount = float(result.replace("$", ""))

            # Mostrar stats del cache cada 10 ciclos
            if cycle % 10 == 0:
                cache_stats = smart_cache.stats()
                log(f"📊 {cache_stats}")
                smart_cache.clear_expired()  # Limpiar cache viejo

            # Analizar en paralelo con límite de concurrencia MUY BAJO
            semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

            # Agrupar por timeframe para mejor caché
            all_signals = []
            for tf in SELECTED_TFS:
                if stop_event and stop_event.is_set(): break
                
                tasks = [
                    generate_signal_with_semaphore(semaphore, api, pair, tf, bot_state, shadow_trader)
                    for pair in PAIRS
                ]
                log(f"🔍 Analizando {len(PAIRS)} pares en TF {tf} (max {MAX_CONCURRENT_REQUESTS} simultáneos)...")
                tf_results = await asyncio.gather(*tasks, return_exceptions=True)
                all_signals.extend(tf_results)

                # Pequeño delay entre timeframes para no saturar
                await asyncio.sleep(1)
            
            if stop_event and stop_event.is_set(): break

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
                for _ in range(30): # Wait in chunks to allow stop
                    if stop_event and stop_event.is_set(): break
                    await asyncio.sleep(1)
                continue

            sig = best_signal

            # Enriquecer info de breakdown si existe
            if 'breakdown' in sig and sig['breakdown']:
                breakdown_str = (
                    f"\n  └─ EMA_conf: {sig['breakdown'].get('EMA_conf', 0)} | "
                    f"TF: {sig['breakdown'].get('TF', 0)} | "
                    f"RSI: {sig['breakdown'].get('RSI', 'N/A')} | "
                    f"Triangle: {sig['breakdown'].get('triangle', 0)}"
                )
                log(f"   Desglose: {breakdown_str}", "debug")

            pattern_info = sig.get('pattern', None)
            if not pattern_info:
                # Usar la descripción detallada si existe
                pattern_info = sig.get('pattern_detailed', "Indicadores (EMA+TF+Confirmación)")

            # ✨ PREDICCIÓN ML (OPCIONAL)
            ml_prediction = None
            ml_prob = None
            if ML_AVAILABLE:
                try:
                    # Preparar features para ML
                    ml_features = {
                        'rsi': sig.get('breakdown', {}).get('RSI', None),
                        'ema_conf': sig.get('breakdown', {}).get('EMA_conf', 0),
                        'tf_signal': sig.get('breakdown', {}).get('TF', 0),
                        'atr': sig.get('breakdown', {}).get('atr', 0),
                        'triangle_active': sig.get('breakdown', {}).get('triangle', 0),
                        'reversal_candle': sig.get('breakdown', {}).get('reversal', 0),
                        'near_support': sig.get('breakdown', {}).get('near_support', False),
                        'near_resistance': sig.get('breakdown', {}).get('near_resistance', False),
                        'signal_score': sig.get('score', 0),
                        'decision': sig['signal'],
                        'pair': sig['pair'],
                        'price': sig.get('price', 0),
                    }
                    
                    ml_prediction, ml_prob = predict_success(ml_features)
                    
                    if ml_prob is not None:
                        log(f"🤖 ML Predicción: {ml_prob:.1%} de probabilidad de ganancia", "debug")
                except Exception as e:
                    log(f"⚠️ Error en predicción ML: {e}", "warning")

            msg = (
                f"📌 SEÑAL DETECTADA\n"
                f"{'=' * 30}\n"
                f"Par: {sig['pair']}\n"
                f"TF: {sig['tf']}\n"
                f"Dirección: {sig['signal']}\n"
                f"Score: {sig['score']}\n"
                f"Patrón/Indicadores: {pattern_info}\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"💰 Precio: {sig['price']:.5f}\n"
                f"📊 EMA: {sig['ema']:.5f}\n"
                f"⏱️ Duración: {sig['duration'] // 60}min\n"
                f"💵 Monto: ${amount:.2f}"
            )
            
            if ml_prob is not None:
                msg += f"\n🤖 ML: {ml_prob:.1%}"
            
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
                
                # Extraer indicadores detallados para logging
                indicators = sig.get('breakdown', {})
                if not indicators:
                    # Si no está en breakdown, construir desde la señal
                    indicators = {
                        'rsi': sig.get('rsi', None),
                        'ema_conf': sig.get('ema_conf', 0),
                        'tf_signal': sig.get('tf_score', 0),
                        'atr': sig.get('atr', 0),
                        'triangle': sig.get('triangle', 0),
                        'reversal': sig.get('reversal', 0),
                    }
                
                # Registrar operación ANTES del resultado
                trade_logger.log_trade({
                    'timestamp': datetime.now(timezone.utc),
                    'trade_id': str(trade_id),
                    'pair': sig['pair'],
                    'timeframe': sig['tf'],
                    'decision': sig['signal'],
                    'signal_score': sig.get('score', 0),
                    'pattern_detected': sig.get('pattern', sig.get('pattern_detailed', 'Indicadores')),
                    'price': sig.get('price', 0),
                    'ema': sig.get('ema', 0),
                    'rsi': indicators.get('RSI', indicators.get('rsi', None)),
                    'ema_conf': indicators.get('EMA_conf', indicators.get('ema_conf', 0)),
                    'tf_signal': indicators.get('TF', indicators.get('tf_signal', 0)),
                    'atr': indicators.get('atr', 0),
                    'triangle_active': indicators.get('triangle', indicators.get('triangle_active', 0)),
                    'reversal_candle': indicators.get('reversal', indicators.get('reversal_candle', 0)),
                    'near_support': indicators.get('near_support', False),
                    'near_resistance': indicators.get('near_resistance', False),
                    'support_level': indicators.get('support_level', None),
                    'resistance_level': indicators.get('resistance_level', None),
                    'htf_signal': indicators.get('htf_signal', 0),
                    'result': 'PENDING',
                    'expiry_time': sig['duration'],
                })

                # esperar expiración + margen
                log(f"⏳ Esperando resultado ({sig['duration'] // 60}min)...")
                for _ in range(sig['duration'] + 10):
                    if stop_event and stop_event.is_set(): break
                    await asyncio.sleep(1)
                
                if stop_event and stop_event.is_set(): break

                # verificar resultado
                try:
                    win_result = await asyncio.wait_for(api.check_win(trade_id), timeout=20)
                    stats['total'] += 1

                    log(f"[DEBUG] Resultado crudo: {win_result}")

                    # Detectar si ganó basándose en diferentes formatos de respuesta
                    win = False
                    profit = 0

                    if isinstance(win_result, dict):
                        # Formato 1: {'result': 'win'} o {'result': 'loss'}
                        if 'result' in win_result:
                            win = (win_result['result'] == 'win')
                        # Formato 2: {'win': 1.85} (profit) o {'win': 0}
                        elif 'win' in win_result:
                            win = (win_result['win'] > 0)
                            profit = float(win_result.get('win', 0))
                        # Formato 3: {'profit': 0.92} o {'profit': 0}
                        elif 'profit' in win_result:
                            win = (win_result['profit'] > 0)
                            profit = float(win_result.get('profit', 0))
                    elif isinstance(win_result, (int, float)):
                        win = (win_result > 0)
                        profit = float(win_result)
                    elif isinstance(win_result, bool):
                        win = win_result

                    log(f"[DEBUG] Interpretado como: {'GANADA' if win else 'PERDIDA'}")
                    
                    # Actualizar resultado en el logger
                    result_text = 'WIN' if win else 'LOSS'
                    profit_loss = profit if win else -amount
                    
                    trade_logger.update_trade_result(
                        trade_id,
                        result=result_text,
                        profit_loss=profit_loss if win else None
                    )

                    # Registrar en trade_history (MODO PRO)
                    trade_history.append({'win': bool(win), 'timestamp': datetime.now(timezone.utc)})
                    if len(trade_history) > max(ROLLING_WINDOW_TRADES * 3, 200):
                        trade_history[:] = trade_history[-ROLLING_WINDOW_TRADES*3:]

                    if win:
                        stats['wins'] += 1
                        icon, text = "✅", "GANADA"
                        profit_msg = f" (+${profit:.2f})" if profit > 0 else ""
                    else:
                        stats['losses'] += 1
                        icon, text = "❌", "PERDIDA"
                        daily_stats['losses'] += 1
                        profit_msg = f" (-${amount:.2f})"

                    daily_stats['trades'] += 1
                    wr = stats['wins'] / stats['total'] * 100 if stats['total'] > 0 else 0.0
                    result_msg = (
                        f"{icon} {text}{profit_msg}\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📊 Stats Totales:\n"
                        f"   {stats['wins']}W / {stats['losses']}L ({wr:.1f}%)\n"
                        f"📅 Stats Hoy:\n"
                        f"   {daily_stats['trades']} operaciones\n"
                        f"   {daily_stats['losses']} pérdidas"
                    )
                    log(result_msg)
                    tg_send(result_msg)

                except Exception as e:
                    log(f"⚠️ Error verificando resultado: {e}", "warning")
                    tg_send(f"⚠️ No se pudo verificar resultado de {trade_id}")

            except Exception as e:
                log(f"❌ Error ejecutando operación: {e}", "error")
                tg_send(f"❌ Error ejecutando operación: {str(e)[:120]}")

            # 🤖 SINCRONIZAR CON ML (opcional)
            if ML_AVAILABLE:
                try:
                    log("🔄 Sincronizando trades con ML...", "debug")
                    synced = ml_trades.sync_trades_to_ml(auto_train=False)
                    if synced > 0:
                        log(f"✅ {synced} trades sincronizados con ML", "debug")
                except Exception as e:
                    log(f"⚠️ Error sincronizando ML: {e}", "warning")

            await asyncio.sleep(5)

        except Exception as e:
            log(f"⚠️ Error en loop principal: {e}", "error")
            tg_send(f"⚠️ Error en loop: {str(e)[:120]}")
            await asyncio.sleep(30)
    
    # Restaurar log original
    log = original_log


if __name__ == "__main__":
    try:
        # Configuración para despliegue (SOLO variables de entorno)
        ssid = os.environ.get("POCKETOPTION_SSID")
        token = os.environ.get("TELEGRAM_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")

        # Validar credenciales obligatorias
        if not ssid:
            print("❌ ERROR: Variable de entorno POCKETOPTION_SSID no configurada")
            print("   Configura tus credenciales en variables de entorno:")
            print("   export POCKETOPTION_SSID='tu_ssid'")
            print("   export TELEGRAM_TOKEN='tu_token'")
            print("   export TELEGRAM_CHAT_ID='tu_chat_id'")
            sys.exit(1)
        
        # Validar Telegram (opcional pero recomendado)
        if token and not chat_id:
            print("⚠️ WARNING: TELEGRAM_TOKEN configurado pero falta TELEGRAM_CHAT_ID")
            print("   Las notificaciones de Telegram no funcionarán")
        
        # Test rápido de Telegram si está configurado
        if token and chat_id:
            try:
                test_response = requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": "🤖 Bot iniciando..."},
                    timeout=5
                )
                if test_response.status_code != 200:
                    print(f"⚠️ WARNING: Telegram test falló (código {test_response.status_code})")
                    print("   Verifica TELEGRAM_TOKEN y TELEGRAM_CHAT_ID")
            except Exception as e:
                print(f"⚠️ WARNING: No se pudo conectar a Telegram: {e}")
        
        # Debug: mostrar SSID (primeros/últimos caracteres por seguridad)
        print(f"\n🔍 DEBUG: SSID length={len(ssid)}, first 5 chars='{ssid[:5]}', last 5 chars='{ssid[-5:]}'")
        print(f"🔍 DEBUG: SSID repr={repr(ssid)}")

        asyncio.run(run_bot(ssid, token, chat_id))
    except KeyboardInterrupt:
        log("\n\n👋 Bot detenido por el usuario", "info")
        tg_send("🛑 Bot detenido manualmente")
        # Mostrar estadísticas finales del cache
        final_stats = smart_cache.stats()
        log(f"📊 Estadísticas finales: {final_stats}")
    except Exception as e:
        log(f"\n❌ Error fatal: {e}", "error")
        tg_send(f"❌ Error fatal: {str(e)[:120]}")
