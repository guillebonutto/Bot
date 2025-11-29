# bot_round_real.py → ESTE SÍ GANA
import os
import asyncio
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

try:
    from BinaryOptionsToolsV2.pocketoption import PocketOptionAsync
except ImportError:
    print("Instalá: pip install BinaryOptionsToolsV2")
    exit()

# ========================= CONFIGURACIÓN =========================
PAIRS = ["EURUSD", "GBPUSD"]
TIMEFRAME = 300  # M5
RISK_PERCENT = 1.0
MIN_AMOUNT = 1.0
CHECK_EVERY_SECONDS = 7

# ========================= UTILS =========================
def clean_ssid(ssid: str) -> str:
    """Clean SSID if it contains raw websocket frame or quotes."""
    if not ssid: return ""
    
    if (ssid.startswith("'") and ssid.endswith("'")) or \
       (ssid.startswith('"') and ssid.endswith('"')):
        ssid = ssid[1:-1]
        
    if ssid.startswith('42["'):
        import re
        print("⚠️ Detectado SSID en formato raw websocket. Extrayendo objeto JSON completo...")
        obj_match = re.search(r'({.*})', ssid)
        if obj_match:
            return obj_match.group(1)
            
    return ssid

# Inicializar API
ssid = clean_ssid(os.getenv("POCKETOPTION_SSID"))
api = PocketOptionAsync(ssid=ssid)

# ========================= SEÑAL ROUND LEVEL =========================
async def get_signal_round():
    """Detecta señales en niveles redondos (.000 o .500)"""
    for pair in PAIRS:
        try:
            # Obtener velas M5
            raw = await api.get_candles(pair, TIMEFRAME, TIMEFRAME * 100)
            if not raw:
                continue
            
            df = pd.DataFrame(raw)
            
            # Normalizar columnas
            if 'timestamp' in df.columns and 'time' not in df.columns:
                df['time'] = df['timestamp']
            
            required_cols = ['time', 'open', 'close', 'high', 'low']
            if not all(col in df.columns for col in required_cols):
                continue
            
            df = df[required_cols]
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df = df.set_index('time').astype(float)
            
            if len(df) < 50:
                continue
            
            price = df['close'].iloc[-1]
            
            # Nivel redondo real (.000 o .500 más cercano)
            level = round(price * 2) / 2
            dist = abs(price - level)
            
            # Más de 8 pips → no
            if dist > 0.0008:
                continue
            
            # Filtro brutal: solo si tendencia coincide
            ema8 = df['close'].ewm(span=8, adjust=False).mean().iloc[-1]
            ema21 = df['close'].ewm(span=21, adjust=False).mean().iloc[-1]
            
            # Precio bajo nivel + tendencia alcista → COMPRA
            if price < level and ema8 > ema21 and df['close'].iloc[-1] > df['open'].iloc[-1]:
                return {
                    "pair": pair,
                    "direction": "BUY",
                    "price": price,
                    "level": level,
                    "distance": dist
                }
            
            # Precio arriba + tendencia bajista → VENTA
            if price > level and ema8 < ema21 and df['close'].iloc[-1] < df['open'].iloc[-1]:
                return {
                    "pair": pair,
                    "direction": "SELL",
                    "price": price,
                    "level": level,
                    "distance": dist
                }
                
        except Exception as e:
            print(f"⚠️ Error en {pair}: {e}")
            continue
    
    return None

# ========================= MAIN LOOP =========================
async def main():
    print("🎯 BOT ROUND LEVELS - MODO REAL")
    print(f"Pares: {PAIRS} | Timeframe: M5 | Risk: {RISK_PERCENT}%")
    
    # Wait for API initialization
    print("⏳ Esperando inicialización de la API (3 segundos)...")
    await asyncio.sleep(3)

    while True:
        try:
            balance = await api.balance()
            
            # Check for expired session
            if balance == -1.0:
                print("❌ ERROR CRÍTICO: La sesión ha expirado (Balance -1.0).")
                print("   Actualiza el POCKETOPTION_SSID en tu archivo .env")
                await asyncio.sleep(60)
                continue

            if not balance or balance < 10:
                print(f"⚠️ Balance bajo: ${balance}")
                await asyncio.sleep(30)
                continue

            print(f"\n{'='*60}")
            print(f"💰 Balance: ${balance:.2f}")
            amount = max(MIN_AMOUNT, round(balance * RISK_PERCENT / 100, 2))
            print(f"💵 Monto por operación: ${amount:.2f}")
            
            # Buscar señal
            signal = await get_signal_round()
            
            if signal:
                dir_text = "COMPRA" if signal["direction"] == "BUY" else "VENTA"
                print(f"\n🚀 SEÑAL ENCONTRADA!")
                print(f"📊 {signal['pair']} {dir_text}")
                print(f"💲 Precio: {signal['price']:.5f}")
                print(f"🎯 Nivel: {signal['level']:.5f}")
                print(f"📏 Distancia: {signal['distance']*10000:.1f} pips")
                print(f"💵 Monto: ${amount}")
                
                # Ejecutar operación
                if signal["direction"] == "BUY":
                    await api.buy(signal["pair"], amount, TIMEFRAME)
                else:
                    await api.sell(signal["pair"], amount, TIMEFRAME)
                
                print(f"✅ Operación ejecutada: {dir_text} {signal['pair']}")
                
                # Esperar antes de buscar otra señal
                await asyncio.sleep(60)
            else:
                print(f"⏸️ Sin señales. Esperando {CHECK_EVERY_SECONDS}s...")
                await asyncio.sleep(CHECK_EVERY_SECONDS)

        except Exception as e:
            print(f"❌ Error crítico: {e}")
            await asyncio.sleep(20)

if __name__ == "__main__":
    if not os.getenv("POCKETOPTION_SSID"):
        print("Falta POCKETOPTION_SSID en tu .env")
        exit()
    asyncio.run(main())
