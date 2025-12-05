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

def normalize_df(df):
    if df.empty:
        return df
        
    # Mapeo de nombres posibles a los que necesitamos
    col_map = {
        'timestamp': 'time',
        't': 'time',
        'time': 'time',
        'o': 'open',
        'open': 'open',
        'c': 'close',
        'close': 'close',
        'h': 'high',
        'high': 'high',
        'l': 'low',
        'low': 'low'
    }
    
    # Renombrar columnas si existen
    df = df.rename(columns=col_map)
    
    # Asegurarnos de tener las columnas mínimas
    required = ['time', 'open', 'close']
    missing = [col for col in required if col not in df.columns]
    if missing:
        print(f"Columnas faltantes: {missing}")
        return pd.DataFrame()
        
    df = df[required].copy()
    df['time'] = pd.to_datetime(df['time'], unit='s', errors='coerce')
    df = df.dropna(subset=['time'])
    df = df.set_index('time')
    df = df.astype(float)
    return df

# Inicializar API
print("🔐 Buscando SSID en variables de entorno...")
ssid = os.getenv("POCKETOPTION_SSID")
if not ssid:
    print("⚠️ POCKETOPTION_SSID no encontrado en variables de entorno")
    ssid = input("🔐 Introduce tu SSID de PocketOption: ").strip()
    if not ssid:
        exit("SSID requerido")

print(f"✓ SSID obtenido, inicializando API...")
try:
    api = PocketOptionAsync(ssid=ssid)
    print("✓ API inicializada correctamente")
except Exception as e:
    print(f"❌ Error inicializando API: {e}")
    exit(f"Error: {e}")

# Cooldown por par
last_trade_time = {}

async def get_signal_round():
    now = datetime.now()
    
    for pair in PAIRS:
        if pair in last_trade_time and now - last_trade_time[pair] < timedelta(seconds=70):
            continue
            
        try:
            raw = await api.get_candles(pair, 300, 300*100)
            if not raw or len(raw) < 50:
                continue
                
            df = pd.DataFrame(raw)
            df = normalize_df(df)  # ← ESTA ES LA CLAVE
            if df.empty or len(df) < 50:
                continue
                
            price = df['close'].iloc[-1]
            open_p = df['open'].iloc[-1]
            level = round(price * 2) / 2
            dist = abs(price - level)
            
            if dist > 0.0018:  # 18 pips máximo
                continue
                
            ema8 = df['close'].ewm(span=8, adjust=False).mean().iloc[-1]
            ema21 = df['close'].ewm(span=21, adjust=False).mean().iloc[-1]
            
            # Filtro de vela fuerte
            body = abs(price - open_p)
            avg_body = df['close'].diff().abs().rolling(10).mean().iloc[-1]
            if body < avg_body * 0.8:
                continue
                
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
    print("✓ Iniciando bucle principal en 5 segundos...")
    await asyncio.sleep(5)
    print("✓ Bucle principal iniciado")
    
    while True:
        try:
            print("🔄 Obteniendo balance...")
            balance = await api.balance()
            print(f"✓ Balance: ${balance:.2f}")
            if balance in [None, -1.0]:
                print("Sesión expirada → actualizá SSID")
                await asyncio.sleep(60)
                continue
                
            amount = max(MIN_AMOUNT, round(balance * RISK_PERCENT / 100, 2))
            
            print("🔎 Buscando señal...")
            signal = await get_signal_round()
            print(f"  → Resultado: {'Señal encontrada' if signal else 'Sin señal'}")
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