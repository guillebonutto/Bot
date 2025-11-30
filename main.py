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
    detectar_ruptura_canal,
    detectar_triangulo,
    detectar_compresion,
    detectar_divergencia_rsi,
    is_sideways
)
from shadow_trader import ShadowTrader
from bot_state import BotState
from risk_manager import RiskManager
from signal_types import Direction, SignalSource
from config_loader import load_config

# ---------------------------
# CONFIG
# ---------------------------
# La configuración se carga desde config.yaml
# Ver config_loader.py y run_bot()

# TELEGRAM (mejor setear como variables de entorno)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Logging
from logger_config import setup_logger

# Setup logger
logger = setup_logger(
    name="trading_bot",
    log_file="bot.log",
    level=logging.INFO
)

def log(msg, level="info"):
    """Log message with specified level."""
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(msg)

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
# UTILS
# ---------------------------
def clean_ssid(ssid: str) -> str:
    """Clean SSID if it contains raw websocket frame or quotes."""
    if not ssid: return ""
    
    # Remove surrounding quotes
    if (ssid.startswith("'") and ssid.endswith("'")) or \
       (ssid.startswith('"') and ssid.endswith('"')):
        ssid = ssid[1:-1]
        
    # Extract from raw websocket frame 42["auth", ...]
    if ssid.startswith('42["'):
        import re
        print("⚠️ Detectado SSID en formato raw websocket. Extrayendo objeto JSON completo...")
        
        # We need the FULL JSON object { ... }, not just the session ID string
        # Regex to find the first { and the last } (greedy)
        # But usually it's 42["auth", {JSON}]
        obj_match = re.search(r'({.*})', ssid)
        if obj_match:
            return obj_match.group(1)
            
    return ssid

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
# Fetch de velas OPTIMIZADO con caché
# ---------------------------
async def fetch_data_optimized(api, pair, interval, lookback=50):
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
            
            if len(df) < 5:
                log(f"⚠️ Pocas velas válidas para {pair} {interval}s ({len(df)})", "warning")
                return pd.DataFrame()

            # IMPORTANT: Lowercase column names for strategy.py compatibility
            df2 = pd.DataFrame({
                'timestamp': pd.to_datetime(df['timestamp'], unit='s', utc=True),
                'open': pd.to_numeric(df['open']),
                'close': pd.to_numeric(df['close']),
                'high': pd.to_numeric(df['high']),
                'low': pd.to_numeric(df['low'])
            })
            df2 = df2.sort_values('timestamp').set_index('timestamp')

            # Guardar en caché
            smart_cache.set(cache_key, df2)

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
async def generate_signal(api, pair, tf, bot_state, config, shadow_trader=None):
    """
    Generate trading signal with clear 3-step flow:
    1. Compute all possible signals (indicators + patterns)
    2. Score and rank all candidates
    3. Select best signal if above threshold
    """
    # Extract config
    timeframes = config['trading']['timeframes']
    ma_long = config['trading']['ma_long']
    use_rsi = config['indicators']['use_rsi']
    target_winrate = 0.55
    min_score_base = 6 # Adjusted for new scoring system (max 10)
    min_score_max = 9
    adaptive_inc = 1
    
    lookback = config['trading']['lookback']
    interval = timeframes[tf]
    df = await fetch_data_optimized(api, pair, interval, lookback)

    if df.empty or len(df) < ma_long:
        return None

    # Shadow trading (forward testing)
    if shadow_trader:
        try:
            shadow_trader.process_candle(df, pair, tf)
        except Exception as e:
            log(f"Error en Shadow Trader: {e}", "error")

    # Pass config settings to compute_indicators
    df = compute_indicators(df, interval)
    last = df.iloc[-1]

    # ============================================================
    # STEP 1: Compute ALL possible signals
    # ============================================================
    candidates = []
    
    # 1A. Pattern-based signals
    detectors = [
        detectar_doble_techo,
        detectar_ruptura_canal,
        detectar_triangulo
    ]
    
    for detector_func in detectors:
        pattern_name, direction_str, pscore = detector_func(df)
        
        if direction_str is None:
            continue
        
        # Convert string direction to enum
        direction = Direction.BUY if direction_str == 'BUY' else Direction.SELL
        
        candidates.append({
            'source': SignalSource.PATTERN,
            'direction': direction,
            'score': pscore,
            'pattern': pattern_name,
            'data': last
        })
        
    # 1B. Divergence
    div_type = detectar_divergencia_rsi(df)
    if div_type:
        direction = Direction.BUY if "Alcista" in div_type else Direction.SELL
        candidates.append({
            'source': SignalSource.PATTERN,
            'direction': direction,
            'score': 7, # High score for divergence
            'pattern': div_type,
            'data': last
        })

    # 1C. Indicator-based signal (EMA Confirmation)
    # Using new ema_conf from strategy.py: 2 (strong buy), 1 (buy), -1 (sell), -2 (strong sell)
    ema_conf = last.get('ema_conf', 0)
    if ema_conf != 0:
        direction = Direction.BUY if ema_conf > 0 else Direction.SELL
        score = 4 if abs(ema_conf) == 1 else 6
        
        # RSI Filter
        if use_rsi:
            rsi = last.get('rsi', 50)
            if direction == Direction.BUY and rsi > 70:
                score -= 2 # Overbought
            elif direction == Direction.SELL and rsi < 30:
                score -= 2 # Oversold
        
        candidates.append({
            'source': SignalSource.INDICATOR,
            'direction': direction,
            'score': score,
            'pattern': 'EMA Trend',
            'data': last
        })

    # ============================================================
    # STEP 2: Score and Rank
    # ============================================================
    
    if not candidates:
        return None
        
    # Filter out signals in sideways market if they are trend-following
    sideways = is_sideways(df)
    if sideways:
        # Penalize score in sideways markets
        for c in candidates:
            c['score'] -= 2

    # Sort by score descending
    candidates.sort(key=lambda x: x['score'], reverse=True)
    best_signal = candidates[0]
    
    # ============================================================
    # STEP 3: Select Best Signal
    # ============================================================
    
    # Adaptive Threshold Logic
    current_wr = rolling_winrate()
    min_score = min_score_base
    
    if current_wr is not None:
        if current_wr > target_winrate:
            min_score = max(5, min_score_base - 1)
        else:
            min_score = min(min_score_max, min_score_base + adaptive_inc)
            
    if best_signal['score'] >= min_score:
        # Build signal dict
        indicators_used = []
        if last.get('ema_conf', 0) != 0:
            indicators_used.append(f"EMA_conf={last['ema_conf']}")
        if 'rsi' in last:
            indicators_used.append(f"RSI={last['rsi']:.1f}")
        if 'macd' in last:
            indicators_used.append(f"MACD={last['macd']:.4f}")
        
        return {
            'pair': pair,
            'tf': tf,
            'signal': str(best_signal['direction']),
            'timestamp': last.name,
            'duration': timeframes[tf],
            'score': best_signal['score'],
            'pattern': str(best_signal['pattern']) if best_signal['pattern'] else None,
            'source': str(best_signal['source']),
            'price': float(last['close']),
            'ema': float(last.get('ema_long', np.nan)),
            'indicators': ', '.join(indicators_used) if indicators_used else 'N/A'
        }
        
    return None


# Wrapper con semaphore para limitar concurrencia
async def generate_signal_with_semaphore(semaphore, api, pair, tf, bot_state, config, shadow_trader=None):
    async with semaphore:
        try:
            return await generate_signal(api, pair, tf, bot_state, config, shadow_trader)
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
    # Iniciar self-ping para evitar dormir
    asyncio.create_task(keep_alive())

    # Clean SSID before using
    ssid = clean_ssid(ssid)
    api = PocketOptionAsync(ssid=ssid)
    
    # CRITICAL: Wait for API initialization
    # PocketOption API needs time to initialize assets and connection
    log("⏳ Esperando inicialización de la API (3 segundos)...", "info")
    await asyncio.sleep(3)
    
    # Load configuration
    try:
        config = load_config()
        pairs = config['trading']['pairs']
        selected_tfs = config['trading']['selected_timeframes']
        risk_config = config['risk']
        system_config = config['system']
    except Exception as e:
        log(f"❌ Error cargando configuración: {e}", "error")
        tg_send(f"❌ Error fatal: Configuración inválida ({e})")
        return

    # intentar obtener balance / cuenta con retry
    balance = None
    for attempt in range(3):
        if stop_event and stop_event.is_set(): return

        try:
            is_demo = api.is_demo()
            balance = await api.balance()

            if balance is not None: # Puede ser 0.0
                if balance == -1.0:
                    log("❌ ERROR CRÍTICO: La sesión ha expirado (Balance -1.0).", "error")
                    log("   Actualiza el POCKETOPTION_SSID en tu archivo .env con una nueva sesión.", "error")
                    tg_send("❌ ERROR CRÍTICO: Sesión expirada (Balance -1.0). Actualiza .env")
                    # No podemos continuar con sesión expirada
                    return

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

    log(f"\n📊 Pares: {len(pairs)} | Timeframes: {', '.join(selected_tfs)}")
    log(f"💰 Risk por operación: {risk_config['risk_per_trade'] * 100}%")
    log(f"🛡️ Max pérdidas diarias: {risk_config['max_daily_losses']}")
    log(f"🚦 Max requests simultáneos: {system_config['max_concurrent_requests']}")
    log("=" * 70 + "\n")

    cycle = 0
    
    # Initialize thread-safe state management
    bot_state = BotState()
    
    # Initialize RiskManager from config
    risk_manager = RiskManager(
        max_daily_losses=risk_config['max_daily_losses'],
        max_daily_trades=risk_config['max_daily_trades'],
        risk_per_trade=risk_config['risk_per_trade'],
        max_drawdown=risk_config['max_drawdown'],
        streak_limit=risk_config['streak_limit'],
        max_risk_per_trade=risk_config.get('max_risk_per_trade', 0.05),
        demo_mode=system_config.get('demo_mode', True)
    )
    
    # Variables para backoff
    current_sleep = 5
    error_sleep = 5

    # Semaphore para limitar concurrencia
    semaphore = asyncio.Semaphore(system_config['max_concurrent_requests'])

    while True:
        if stop_event and stop_event.is_set():
            log("🛑 Deteniendo bot...", "info")
            break

        try:
            cycle += 1
            # log(f"🔄 Ciclo {cycle}...", "debug")
            
            # 0. Check news
            if is_news_event():
                log("📰 Evento de noticias detectado - Pausando 5 min", "warning")
                await asyncio.sleep(300)
                continue

            # 1. Update balance (periodically)
            if cycle % 10 == 0:
                try:
                    balance = await api.balance()
                    if balance is not None:
                        # log(f"💰 Balance actual: ${balance:.2f}", "debug")
                        pass
                except Exception:
                    pass
            
            # Check for expired session in loop
            if balance == -1.0:
                log("❌ ERROR CRÍTICO: La sesión ha expirado (Balance -1.0).", "error")
                tg_send("❌ ERROR CRÍTICO: Sesión expirada. Deteniendo bot.")
                break

            # 2. Check Risk Limits
            can_trade, reason = await risk_manager.can_trade(balance, bot_state)
            if not can_trade:
                log(f"🛡️ Risk Manager: {reason} - Esperando...", "warning")
                await asyncio.sleep(60)
                continue

            # 3. Generate Signals (Concurrent)
            tasks = []
            for pair in pairs:
                for tf in selected_tfs:
                    tasks.append(
                        generate_signal_with_semaphore(
                            semaphore, api, pair, tf, bot_state, config
                        )
                    )
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter valid signals
            valid_signals = []
            for res in results:
                if isinstance(res, dict) and res is not None:
                    valid_signals.append(res)
                elif isinstance(res, Exception):
                    log(f"⚠️ Error en tarea de señal: {res}", "error")

            # 4. Execute Trades
            if valid_signals:
                # Reset idle backoff
                current_sleep = 5
                
                # Sort by score
                valid_signals.sort(key=lambda x: x['score'], reverse=True)
                
                # Execute top signal(s)
                for signal in valid_signals[:1]: # Execute only best signal per cycle
                    log(f"🚀 SEÑAL ENCONTRADA: {signal['pair']} {signal['signal']} (Score: {signal['score']})", "info")
                    
                    # Validate again with RiskManager before execution
                    can_trade, reason = await risk_manager.can_trade(balance, bot_state)
                    if not can_trade:
                        log(f"🛡️ Trade rechazado por Risk Manager: {reason}", "warning")
                        break
                        
                    # Calculate amount
                    amount = risk_manager.calculate_position_size(balance)
                    
                    # Execute
                    try:
                        log(f"⚡ Ejecutando trade en {signal['pair']}...", "info")
                        
                        # Determine direction and execute
                        trade_id = None
                        trade_info = None
                        
                        if signal['signal'] == 'BUY' or signal['signal'] == str(Direction.BUY):
                             trade_id, trade_info = await api.buy(signal['pair'], amount, signal['duration'])
                        else:
                             trade_id, trade_info = await api.sell(signal['pair'], amount, signal['duration'])
                        
                        if trade_id:
                            log(f"✅ Trade enviado exitoso: {signal['pair']} ${amount} (ID: {trade_id})", "info")
                            
                            # Update balance locally immediately (mock or real)
                            # For mock, we know it deducts immediately. For real API, it might take a moment.
                            # We can force a balance refresh or manually deduct for display.
                            if balance is not None:
                                balance -= amount
                                log(f"💰 Balance actualizado (estimado): ${balance:.2f}", "info")
                            
                            # Record trade
                            await bot_state.add_trade({
                                'pair': signal['pair'],
                                'amount': amount,
                                'result': 'PENDING', # Will be updated later if we tracked it
                                'trade_id': trade_id,
                                'timestamp': datetime.now(timezone.utc)
                            })
                            
                            # Send Telegram
                            tg_send(
                                f"🚀 SEÑAL EJECUTADA\n"
                                f"Pair: {signal['pair']}\n"
                                f"Dir: {signal['signal']}\n"
                                f"Score: {signal['score']}\n"
                                f"Amount: ${amount}\n"
                                f"Pattern: {signal['pattern']}"
                            )
                            
                            # Launch background task to check win result (Mock only for now)
                            if hasattr(api, 'check_win'):
                                async def check_result_later(tid, duration):
                                    await asyncio.sleep(duration)
                                    res = await api.check_win(tid)
                                    log(f"🏁 Resultado Trade {tid}: {res}", "info")
                                    # Balance update should happen in next cycle or we can fetch it
                                    
                                asyncio.create_task(check_result_later(trade_id, signal['duration']))

                        else:
                             log(f"❌ Error: No se recibió ID de trade", "error")
                        
                    except Exception as e:
                        log(f"❌ Error ejecutando trade: {e}", "error")
            else:
                # 🔄 ADAPTIVE SLEEP (Exponential Backoff for idle time)
                # No signals found, increase sleep time
                current_sleep = min(current_sleep * 1.5, 30)
                if current_sleep > 10:
                    log(f"💤 Sin señales, durmiendo {current_sleep:.1f}s...", "debug")

            await asyncio.sleep(current_sleep)

        except Exception as e:
            log(f"⚠️ Error en loop principal: {e}", "error")
            
            # 🔄 ERROR BACKOFF
            error_sleep = min(error_sleep * 2, 300)  # Max 5 min
            log(f"🛑 Pausa por error: {error_sleep}s", "warning")
            await asyncio.sleep(error_sleep)
        else:
            # Reset error backoff on successful iteration
            error_sleep = 5

if __name__ == "__main__":
    # Load config to get credentials if not in env (optional)
    # For now assume env vars
    ssid = os.getenv("POCKETOPTION_SSID")
    if not ssid:
        print("❌ Error: POCKETOPTION_SSID no definido en .env")
        sys.exit(1)
        
    try:
        asyncio.run(run_bot(ssid, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))
    except KeyboardInterrupt:
        print("\n👋 Bot detenido por usuario")
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
