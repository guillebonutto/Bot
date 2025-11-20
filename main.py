import pandas as pd
import numpy as np
import time
import requests
from datetime import datetime
import asyncio
from BinaryOptionsToolsV2.pocketoption import PocketOptionAsync

# ===============================
# CONFIGURACIÓN
# ===============================
PAIRS = [
    'EURUSD_otc', 'GBPUSD_otc', 'USDJPY_otc', 'AUDUSD_otc', 'USDCAD_otc',
    'AUDCAD_otc', 'USDMXN_otc', 'USDCOP_otc', 'USDARS_otc'
]

TIMEFRAMES = {
    "M1": 60,
    "M2": 120,
    "M5": 300,
    "M10": 600,
    "M15": 900,
    "M30": 1800
}

# SOLO USA M5 Y SUPERIORES (M1 y M2 dan timeout)
SELECTED_TFS = ["M5", "M10", "M15", "M30"]
LOOKBACK = 50  # Reducido para M5
MA_SHORT = 20
MA_LONG = 50  # Reducido para timeframes más altos
HTF_MULT = 2

# Filtros opcionales
USE_RSI = True
USE_REVERSAL_CANDLES = True
USE_SUPPORT_RESISTANCE = True
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

# ===============================
# TELEGRAM
# ===============================
TELEGRAM_TOKEN = "8058227630:AAHoHAKPAPGo93XXL5UmRuDhL2pXNw4S5Uo"
TELEGRAM_CHAT_ID = "913843638"


def get_ssid_from_telegram():
    """Solicita SSID desde Telegram"""
    base = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

    try:
        resp0 = requests.get(f"{base}/getUpdates", timeout=10).json()
        offset = resp0["result"][-1]["update_id"] + 1 if resp0.get("result") else None
    except:
        offset = None

    try:
        requests.post(f"{base}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": "👉 Envía tu SSID de PocketOption:"}, timeout=10)
    except:
        pass

    ssid = None
    attempts = 0

    while not ssid and attempts < 60:
        try:
            params = {"timeout": 30}
            if offset:
                params["offset"] = offset
            resp = requests.get(f"{base}/getUpdates", params=params, timeout=35).json()
            for upd in resp.get("result", []):
                offset = upd["update_id"] + 1
                txt = upd.get("message", {}).get("text", "").strip()
                if txt and len(txt) > 10:
                    ssid = txt
                    break
            attempts += 1
        except:
            time.sleep(5)
            attempts += 1

    if not ssid:
        raise Exception("No se recibió SSID")

    try:
        requests.post(f"{base}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": "✅ SSID recibido. Iniciando bot..."}, timeout=10)
    except:
        pass
    return ssid


def tg_send(msg: str):
    try:
        requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            params={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
            timeout=10
        )
    except Exception as e:
        print(f"[Telegram] Error: {e}")


# ===============================
# INDICADORES
# ===============================
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


def detectar_doble_techo(df):
    closes = df["Close"]
    if len(closes) < 10:
        return None

    # últimos 10
    window = closes[-10:]

    high1 = window.iloc[0]
    high2 = window.iloc[-3]

    if abs(high1 - high2) <= high1 * 0.0005:  # casi igual
        if window.iloc[-1] < window.mean():  # rompe hacia abajo
            return "SELL"

    return None


def detectar_compresion(df):
    highs = df['High'][-10:]
    lows = df['Low'][-10:]

    # pendiente descendente y ascendente
    if highs.iloc[-1] < highs.iloc[0] and lows.iloc[-1] > lows.iloc[0]:
        # si rompe arriba
        if df['Close'].iloc[-1] > highs.mean():
            return "BUY"
        # si rompe abajo
        if df['Close'].iloc[-1] < lows.mean():
            return "SELL"
    return None


def detectar_flag(df):
    # fuerte movimiento previo
    impuls = abs(df["Close"].iloc[-10] - df["Close"].iloc[-5]) > 3 * df["Close"].diff().abs().mean()

    if not impuls:
        return None

    # canal pequeño de retroceso
    cond_retroceso = (
            df['High'][-5:].max() - df['High'].iloc[-10] < df['High'].diff().abs().mean() * 2
    )

    if cond_retroceso:
        # ruptura
        if df['Close'].iloc[-1] > df['High'][-5:].max():
            return "BUY"
        if df['Close'].iloc[-1] < df['Low'][-5:].min():
            return "SELL"

    return None


def near_resistance(c, r, tol=0.0005):
    return abs(c - r) <= tol


# ===============================
# DESCARGA DE VELAS
# ===============================
async def fetch_data(api, pair, interval):
    offset = interval * LOOKBACK
    try:
        # get_candles retorna lista de dicts con keys: 'timestamp', 'open', 'close', 'high', 'low'
        raw = await asyncio.wait_for(
            api.get_candles(pair, interval, offset),
            timeout=20
        )

        if not raw:
            return pd.DataFrame()

        # Convertir a DataFrame
        df = pd.DataFrame([{
            'Timestamp': c['timestamp'],
            'Open': c['open'],
            'Close': c['close'],
            'High': c['high'],
            'Low': c['low']
        } for c in raw])

        if df.empty:
            return df

        df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='s', utc=True)
        df.set_index('Timestamp', inplace=True)
        df.sort_index(inplace=True)
        return df
    except asyncio.TimeoutError:
        print(f"⏱️ Timeout obteniendo {pair} en TF {interval}s")
        return pd.DataFrame()
    except Exception as e:
        print(f"❌ Error obteniendo velas {pair}: {e}")
        return pd.DataFrame()


# ===============================
# CÁLCULO DE INDICADORES COMPLETOS
# ===============================
def compute_indicators(df, interval):
    if len(df) < MA_LONG:
        return

    df['MA_long'] = df['Close'].ewm(span=MA_LONG, adjust=False).mean()
    df['above'] = df['Close'] > df['MA_long']
    df['below'] = df['Close'] < df['MA_long']

    df['no_touch_above'] = df['above'].rolling(10, min_periods=10).sum() == 10
    df['no_touch_below'] = df['below'].rolling(10, min_periods=10).sum() == 10

    df['EMA_conf'] = np.where(df['no_touch_above'], 1, np.where(df['no_touch_below'], -1, 0))

    # ATR
    tr1 = df['High'] - df['Low']
    tr2 = (df['High'] - df['Close'].shift()).abs()
    tr3 = (df['Low'] - df['Close'].shift()).abs()
    df['ATR'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).rolling(14, min_periods=14).mean()

    # Fuerza de tendencia
    df['trend'] = (df['Close'] - df['Close'].shift(14)) / df['ATR'].replace(0, np.nan)
    df['TF'] = np.where(df['trend'] > 1, 1, np.where(df['trend'] < -1, -1, 0))

    # Triángulo (consolidación)
    rng = df['High'].rolling(10, min_periods=10).max() - df['Low'].rolling(10, min_periods=10).min()
    df['triangle'] = (rng < df['ATR'] * 0.5).astype(int)

    # MTF
    try:
        df_htf = df['Close'].resample(f"{interval * HTF_MULT}s").last().ffill()
        ema_fast = df_htf.rolling(MA_SHORT * HTF_MULT, min_periods=MA_SHORT * HTF_MULT).mean()
        ema_slow = df_htf.ewm(span=MA_LONG * HTF_MULT, adjust=False).mean()
        htf_sig = np.where(ema_fast > ema_slow, 1, np.where(ema_fast < ema_slow, -1, 0))
        df['HTF'] = pd.Series(htf_sig, index=df_htf.index).reindex(df.index, method='ffill').fillna(0).astype(int)
    except:
        df['HTF'] = 0

    # RSI
    if USE_RSI:
        df['RSI'] = compute_rsi(df)

    if USE_REVERSAL_CANDLES:
        df['Reversal'] = df.apply(detect_reversal_candle, axis=1)

    if USE_SUPPORT_RESISTANCE:
        r = detect_resistance(df)
        df['NearResistance'] = df['Close'].apply(lambda c: near_resistance(c, r))


# ===============================
# DETECCIÓN DE LATERALIZACIÓN
# ===============================
def is_sideways(df, window=20, atr_mult=1.0):
    if len(df) < window:
        return False
    recent = df.iloc[-window:]
    pr = recent['High'].max() - recent['Low'].min()
    atr_avg = recent['ATR'].mean()
    if pd.isna(atr_avg) or atr_avg == 0:
        return True
    return pr < (atr_avg * atr_mult)


# ===============================
# SCORE DE SEÑAL
# ===============================
def score_signal(row):
    score = 0
    score += int(row['EMA_conf'] != 0)
    # score += int(row['EMA_conf'] == row['HTF'])
    score += int(row['TF'] == row['EMA_conf'])
    score += int(row['triangle'] == 1)

    if USE_RSI and not pd.isna(row.get('RSI', np.nan)):
        if row['RSI'] < RSI_OVERSOLD or row['RSI'] > RSI_OVERBOUGHT:
            score += 1

    if USE_REVERSAL_CANDLES:
        if row.get('Reversal', 0) == 1:
            score += 1

    if USE_SUPPORT_RESISTANCE:
        if not row.get('NearResistance', False):
            score += 1

    return score


# ===============================
# GENERAR SEÑAL PARA UNA TEMPORALIDAD
# ===============================
async def generate_signal(api, pair, tf):
    interval = TIMEFRAMES[tf]
    df = await fetch_data(api, pair, interval)

    if df.empty:
        print(f"   ⚠️ DF vacío")
        return None

    if len(df) < MA_LONG:
        print(f"   ⚠️ Muy pocas velas ({len(df)})")
        return None

    compute_indicators(df, interval)
    last = df.iloc[-1]

    # ===============================
    # PRIMERA BÚSQUEDA: SEÑAL NORMAL
    # ===============================
    # Quitar HTF completamente
    if last['EMA_conf'] == 0:
        print("   ⚠️ EMA_conf = 0 (sin tendencia)")
        signal = None
    elif last['TF'] == 0:
        print("   ⚠️ TrendForce = 0")
        signal = None
    elif is_sideways(df):
        print("   ⚠️ Mercado lateral")
        signal = None
    else:
        score = score_signal(last)
        if score >= 3:
            signal = 'BUY' if last['EMA_conf'] > 0 else 'SELL'
        else:
            print(f"   ⚠️ Score insuficiente ({score})")
            signal = None

    # =======================================
    # SI NO HAY SEÑAL → USAR PATRONES CHARTISTAS
    # =======================================
    if signal is None:
        print("   🔍 No hay señal normal → buscando patrones…")

        signal = detectar_doble_techo(df)
        if signal:
            print(f"   ✅ Patrón detectado: DOBLE TECHO → {signal}")
        else:
            signal = detectar_compresion(df)
            if signal:
                print(f"   ✅ Patrón detectado: COMPRESION → {signal}")
            else:
                signal = detectar_flag(df)
                if signal:
                    print(f"   ✅ Patrón detectado: FLAG → {signal}")

    # Si sigue siendo None → nada para operar
    if signal is None:
        return None

    # Duración dinámica por TF
    if tf == "M5":
        duration = 300
    elif tf == "M10":
        duration = 600
    elif tf == "M15":
        duration = 900
    elif tf == "M30":
        duration = 1800
    else:
        duration = 300

    return {
        'pair': pair,
        'tf': tf,
        'signal': signal,
        'timestamp': last.name,
        'duration': duration,
        'score': score if 'score' in locals() else 0,
        'pattern': None if 'score' in locals() else signal,
        'price': last['Close'],
        'ema': last.get('MA_long', None)
    }


# ===============================
# MAIN LOOP DEL BOT
# ===============================
async def main():
    print("=" * 70)
    print("🤖 BOT MULTI-TIMEFRAME")
    print("=" * 70)

    ssid = get_ssid_from_telegram()

    # Inicializar API correctamente con SSID
    api = PocketOptionAsync(ssid=ssid)

    print("\n🔍 Verificando conexión...")
    try:
        is_demo = api.is_demo()
        balance = await api.balance()
        print(f"✅ Cuenta: {'DEMO' if is_demo else 'REAL'}")
        current_balance = await api.balance()
        print(f"💰 Balance actual: ${current_balance:.2f}")
        tg_send(f"🤖 Bot Multi-TF iniciado\n✅ Cuenta {'DEMO' if is_demo else 'REAL'}\nBalance {balance}")
    except Exception as e:
        print(f"⚠️ No se pudo verificar cuenta: {e}")
        tg_send("🤖 Bot Multi-TF iniciado")

    print(f"\n📊 Timeframes: {', '.join(SELECTED_TFS)}")
    print(f"💰 Monto por operación: $1")
    print("=" * 70)
    print("\n✅ Bot operativo\n")

    cycle = 0
    stats = {'wins': 0, 'losses': 0, 'total': 0}

    while True:
        try:
            cycle += 1
            print(f"\n{'=' * 70}")
            print(f"CICLO #{cycle} - {datetime.utcnow().strftime('%H:%M:%S UTC')}")
            if stats['total'] > 0:
                wr = stats['wins'] / stats['total'] * 100
                print(f"📊 Stats: {stats['wins']}W/{stats['losses']}L ({wr:.1f}%)")
            print(f"{'=' * 70}")

            best_signal = None
            best_score = 0

            # Analizar todos los pares y timeframes
            for pair in PAIRS:
                print(f"\n📊 Analizando {pair}:")
                for tf in SELECTED_TFS:
                    print(f"   {tf}...", end=" ", flush=True)
                    signal = await generate_signal(api, pair, tf)

                    if signal:
                        print(f"✅ Score: {signal['score']}")
                        if signal['score'] > best_score:
                            best_score = signal['score']
                            best_signal = signal
                    else:
                        print("❌")

                    await asyncio.sleep(0.5)

            if best_signal:
                sig = best_signal
                msg = (
                    f"📌 SEÑAL DETECTADA\n"
                    f"{'=' * 30}\n"
                    f"Par: {sig['pair']}\n"
                    f"Timeframe: {sig['tf']}\n"
                    f"Dirección: {sig['signal']}\n"
                    f"Score: {sig['score']}/7\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"💰 Precio: {sig['price']:.5f}\n"
                    f"📊 EMA: {sig['ema']:.5f}\n"
                    f"⏱️ Duración: {sig['duration']}s ({sig['duration'] // 60}min)\n"
                    f"💵 Monto: $1"
                )
                print(f"\n{msg}")
                tg_send(msg)

                try:
                    # Ejecutar operación usando buy() o sell()
                    if sig['signal'] == 'BUY':
                        trade_id, result = await asyncio.wait_for(
                            api.buy(
                                asset=sig['pair'],
                                amount=1.0,
                                time=sig['duration'],
                                check_win=False
                            ),
                            timeout=20
                        )
                    else:
                        trade_id, result = await asyncio.wait_for(
                            api.sell(
                                asset=sig['pair'],
                                amount=1.0,
                                time=sig['duration'],
                                check_win=False
                            ),
                            timeout=20
                        )

                    print(f"✅ Operación ejecutada - ID: {trade_id}")
                    tg_send(f"✅ Operación ejecutada\nID: {trade_id}")

                    # Esperar y verificar resultado
                    await asyncio.sleep(sig['duration'] + 15)

                    try:
                        win_result = await asyncio.wait_for(
                            api.check_win(trade_id),
                            timeout=15
                        )

                        stats['total'] += 1

                        if isinstance(win_result, dict):
                            raw = win_result.get('win', -1)
                        elif isinstance(win_result, (int, float)):
                            raw = win_result
                        elif isinstance(win_result, bool):
                            raw = 1 if win_result else 0
                        else:
                            raw = -1

                        # GANADA SI EL PAGO > 0
                        win = raw > 0

                        if win:
                            stats['wins'] += 1
                            icon, text = "✅", "GANADA"
                        else:
                            stats['losses'] += 1
                            icon, text = "❌", "PERDIDA"

                        wr = stats['wins'] / stats['total'] * 100
                        result_msg = f"{icon} {text}\n{stats['wins']}W/{stats['losses']}L ({wr:.1f}%)"
                        print(result_msg)
                        tg_send(result_msg)
                    except Exception as e:
                        print(f"⚠️ Error verificando: {e}")
                        tg_send(f"⚠️ No se pudo verificar resultado de {trade_id}")

                except Exception as e:
                    print(f"❌ Error ejecutando operación: {e}")
                    tg_send(f"❌ Error: {str(e)[:100]}")
            else:
                print("\n⚠️ Sin señales válidas")
                tg_send(f"⚠️ Sin señales - Ciclo #{cycle}")
                await asyncio.sleep(300)  # 5 minutos

        except Exception as e:
            print(f"⚠️ Error en el loop: {e}")
            tg_send(f"⚠️ Error: {str(e)[:100]}")
            await asyncio.sleep(60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Bot detenido por el usuario")
        tg_send("🛑 Bot detenido")
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        tg_send(f"❌ Error fatal: {str(e)[:100]}")
