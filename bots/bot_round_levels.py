# bot_round_real.py → VERSIÓN FINAL GANADORA (copia-pega y dejá correr)
import os, asyncio, pandas as pd, uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

# Importar trade logger
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from trade_logger import trade_logger

try:
    from BinaryOptionsToolsV2.pocketoption import PocketOptionAsync
except ImportError:
    exit("pip install BinaryOptionsToolsV2")

# ========================= CONFIGURACIÓN FINAL =========================
PAIRS = ['EURUSD_otc', 'GBPUSD_otc']  # ¡¡SOLO ESTOS DOS!! NADA MÁS
TIMEFRAME = 300
RISK_PERCENT = 1.0
MIN_AMOUNT = 1.0
COOLDOWN_SECONDS = 70  # cooldown por par

# Inicializar API
ssid = os.getenv("POCKETOPTION_SSID")
if not ssid:
    exit("Falta POCKETOPTION_SSID")
api = PocketOptionAsync(ssid=ssid)

# Cooldown por par
last_trade_time = {}

async def get_signal_round():
    global last_trade_time
    now = datetime.now()
    
    for pair in PAIRS:
        # Cooldown por par
        if pair in last_trade_time:
            if now - last_trade_time[pair] < timedelta(seconds=COOLDOWN_SECONDS):
                continue
        
        try:
            raw = await api.get_candles(pair, TIMEFRAME, TIMEFRAME * 100)
            if not raw or len(raw) < 50: 
                continue
                
            df = pd.DataFrame(raw)
            if 'timestamp' in df.columns and 'time' not in df.columns:
                df['time'] = df['timestamp']
            df = df[['time', 'open', 'close']].copy()
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df = df.set_index('time').astype(float)
            
            price = df['close'].iloc[-1]
            level = round(price * 2) / 2
            dist = abs(price - level)
            
            if dist > 0.0008:  # 8 pips máximo
                continue
                
            ema8 = df['close'].ewm(span=8, adjust=False).mean().iloc[-1]
            ema21 = df['close'].ewm(span=21, adjust=False).mean().iloc[-1]
            open_p = df['open'].iloc[-1]
            
            if price < level and ema8 > ema21 and price > open_p:
                last_trade_time[pair] = now
                return {"pair": pair, "direction": "BUY", "level": level, "dist": dist}
            if price > level and ema8 < ema21 and price < open_p:
                last_trade_time[pair] = now
                return {"pair": pair, "direction": "SELL", "level": level, "dist": dist}
                
        except Exception as e:
            print(f"Error {pair}: {e}")
            continue
    return None

async def main():
    print("BOT ROUND LEVELS GANADOR → SOLO EURUSD_otc y GBPUSD_otc")
    await asyncio.sleep(5)
    
    while True:
        try:
            balance = await api.balance()
            if balance in [None, -1.0]:
                print("Sesión expirada → actualizá SSID")
                await asyncio.sleep(60)
                continue
                
            amount = max(MIN_AMOUNT, round(balance * RISK_PERCENT / 100, 2))
            
            signal = await get_signal_round()
            if signal:
                dir_text = "COMPRA" if signal["direction"] == "BUY" else "VENTA"
                print(f"\n{signal['pair']} {dir_text} | Nivel: {signal['level']:.5f} | {signal['dist']*10000:.1f} pips")
                
                trade_id = str(uuid.uuid4())[:8]
                trade_logger.log_trade({
                    "timestamp": datetime.now(),
                    "trade_id": trade_id,
                    "pair": signal["pair"],
                    "decision": signal["direction"],
                    "pattern_detected": f"Round Level {signal['level']:.5f}",
                    "result": "PENDING"
                })
                
                # Guardar balance antes
                balance_before = balance

                if signal["direction"] == "BUY":
                    await api.buy(signal["pair"], amount, TIMEFRAME)
                else:
                    await api.sell(signal["pair"], amount, TIMEFRAME)
                    
                print(f"⏳ Esperando {TIMEFRAME}s para resultado...")
                await asyncio.sleep(TIMEFRAME + 5)

                # Verificar resultado
                try:
                    balance_after = await api.balance()
                    if balance_after > balance_before:
                        profit = balance_after - balance_before
                        print(f"✅ GANÓ: +${profit:.2f}")
                        trade_logger.update_trade_result(trade_id, "WIN", profit)
                    else:
                        loss = balance_before - balance_after
                        print(f"❌ PERDIÓ: -${loss:.2f}")
                        trade_logger.update_trade_result(trade_id, "LOSS", -loss)
                except Exception as e:
                    print(f"⚠️ No se pudo verificar resultado: {e}")

            else:
                await asyncio.sleep(7)
                
        except Exception as e:
            print("Error crítico:", e)
            await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(main())