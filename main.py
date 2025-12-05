# bot_universal_FUNCIONA_YA.py
import os, asyncio, pandas as pd, time, requests
from datetime import datetime
from dotenv import load_dotenv
from trade_logger import trade_logger
from shadow_trades_logger import shadow_trades_logger
from telegram_formatter import telegram, send_trade_signal, send_trade_result

load_dotenv()

try:
    from BinaryOptionsToolsV2.pocketoption import PocketOptionAsync
except Exception as e:
    print("ERROR:", e)
    exit()

# ========== FORZAMOS PARES OTC (porque es lo que tenés ahora) ==========
PAIRS = ["EURUSD_otc", "GBPUSD_otc", "USDJPY_otc", "AUDUSD_otc"]
api = PocketOptionAsync(ssid=os.getenv("POCKETOPTION_SSID"))

# ========== TELEGRAM OPCIONAL (ahora con formato bonito) ==========
def tg(msg):
    """Función legacy - usa telegram_formatter.py ahora"""
    # Los mensajes ahora se envían con telegram_formatter
    pass

# ========== SEÑALES ==========
def get_signal(df):
    if len(df) < 60: return None, None, None
    df = df.copy()
    df['e8']  = df['close'].ewm(span=8,  adjust=False).mean()
    df['e21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['e55'] = df['close'].ewm(span=55, adjust=False).mean()
    
    c = df['close'].iloc[-1]
    p = df['close'].iloc[-2]
    e8, e21, e55 = df['e8'].iloc[-1], df['e21'].iloc[-1], df['e55'].iloc[-1]
    
    # EMA 8/21/55
    if e8 > e21 > e55 and p <= e8 and c > e8:
        return "BUY", "EMA", {"e8": e8, "e21": e21, "e55": e55, "price": c}
    if e8 < e21 < e55 and p >= e8 and c < e8:
        return "SELL", "EMA", {"e8": e8, "e21": e21, "e55": e55, "price": c}
    
    # ROUND LEVELS (solo si no hubo EMA)
    price = c
    level = round(price * 2) / 2
    if abs(price - level) <= 0.0008:  # 8 pips máximo
        if price < level and e8 > e21 and c > df['open'].iloc[-1]:
            return "BUY", "ROUND", {"e8": e8, "e21": e21, "e55": e55, "price": c, "level": level}
        if price > level and e8 < e21 and c < df['open'].iloc[-1]:
            return "SELL", "ROUND", {"e8": e8, "e21": e21, "e55": e55, "price": c, "level": level}
    
    return None, None, None

# ========== MAIN ==========
async def main():
    print("BOT UNIVERSAL 2025 → CORRIENDO EN MODO BESTIA")
    tg("Bot universal iniciado")
    await asyncio.sleep(5)  # dar tiempo a la API

    cooldown = {}
    while True:
        try:
            balance = await api.balance()
            if balance in [None, -1.0]:
                print("Sesión muerta o balance -1 → reiniciá el SSID")
                await asyncio.sleep(60)
                continue
                
            amount = max(1.0, round(balance * 0.01, 2))
            now = time.time()
            traded = False

            # limpiar cooldowns viejos
            cooldown = {k: v for k, v in cooldown.items() if now - v < 65}

            for pair in PAIRS:
                if pair in cooldown:
                    continue

                # pedir velas M5
                raw = await api.get_candles(pair, 300, 30000)
                if not raw or len(raw) < 50:
                    continue
                    
                df = pd.DataFrame(raw)
                if 'time' not in df.columns:
                    df['time'] = df.get('timestamp', df.index)
                df = df[['time', 'open', 'close']].copy()
                df['time'] = pd.to_datetime(df['time'], unit='s')
                df = df.set_index('time').astype(float)

                direction, source, metrics = get_signal(df)
                if direction and not traded:
                    traded = True
                    txt = f"{datetime.now().strftime('%H:%M:%S')} → {pair} {direction} ${amount} [{source}]"
                    print(txt)
                    tg(txt)

                    trade_id = None
                    try:
                        if direction == "BUY":
                            # api.buy returns (trade_id, trade_details) or just trade_id depending on implementation
                            # Based on inspection, it returns (trade_id, trade)
                            result = await api.buy(pair, amount, 300)
                        else:
                            result = await api.sell(pair, amount, 300)
                        
                        # Handle result tuple
                        if isinstance(result, tuple):
                            trade_id = result[0]
                        else:
                            trade_id = result

                        # LOGGING
                        if trade_id:
                            trade_data = {
                                'timestamp': datetime.now(),
                                'trade_id': trade_id,
                                'pair': pair,
                                'tf': 'M5',
                                'timeframe': 'M5',
                                'decision': direction,
                                'signal': direction,
                                'pattern_detected': source,
                                'pattern': source,
                                'price': metrics.get('price', 0),
                                'ema': metrics.get('e8', 0),
                                'rsi': metrics.get('rsi', 0),
                                'ema_conf': metrics.get('ema_conf', 0),
                                'tf_signal': metrics.get('tf_signal', 0),
                                'atr': metrics.get('atr', 0),
                                'triangle_active': metrics.get('triangle_active', 0),
                                'reversal_candle': metrics.get('reversal_candle', 0),
                                'near_support': metrics.get('near_support', 0),
                                'near_resistance': metrics.get('near_resistance', 0),
                                'htf_signal': metrics.get('htf_signal', 0),
                                'notes': f"e21={metrics.get('e21',0):.5f}, e55={metrics.get('e55',0):.5f}",
                                'expiry_time': 300,
                                'result': 'PENDING'
                            }
                            # Registrar en ambos loggers
                            trade_logger.log_trade(trade_data)
                            shadow_trades_logger.log_trade(trade_data)
                            print(f"   └── Guardado en CSV: ID {trade_id}")
                            print(f"   └── Guardado en shadow_trades.csv: {trade_id}")

                    except Exception as e:
                        print(f"Error ejecutando orden: {e}")
                    
                    cooldown[pair] = now
                    await asyncio.sleep(65)
                    break

            if not traded:
                print(f"{datetime.now().strftime('%H:%M:%S')} → analizando 4 pares... (sin señal)")
                await asyncio.sleep(7)

        except Exception as e:
            print("ERROR:", e)
            await asyncio.sleep(15)

if __name__ == "__main__":
    asyncio.run(main())