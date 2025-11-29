# bot_ganador.py → EL ÚNICO QUE NECESITÁS AHORA
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
PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
TIMEFRAMES = {"M1": 60, "M5": 300}
RISK_PERCENT = 1.0           # 1% del balance por operación
MIN_AMOUNT = 1.0             # mínimo $1
CHECK_EVERY_SECONDS = 7      # revisa cada 7 segundos

# ========================= UTILS =========================
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
        obj_match = re.search(r'({.*})', ssid)
        if obj_match:
            return obj_match.group(1)
            
    return ssid

# Inicializar API con SSID limpio
ssid = clean_ssid(os.getenv("POCKETOPTION_SSID"))
api = PocketOptionAsync(ssid=ssid)

# ML opcional (si tenés el modelo, sino lo ignora)
try:
    import joblib
    model = joblib.load("ml_model.pkl")
    ML_ACTIVE = True
    ML_THRESHOLD = 0.62
    print("Modelo ML cargado → filtro activado")
except:
    ML_ACTIVE = False
    print("Sin modelo ML → modo puro EMA")

# ========================= INDICADORES =========================
def add_emas(df: pd.DataFrame) -> pd.DataFrame:
    df['ema8']  = df['close'].ewm(span=8, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema55'] = df['close'].ewm(span=55, adjust=False).mean()
    return df

# ========================= SEÑAL GANADORA =========================
def get_signal(df: pd.DataFrame, pair: str, duration: int):
    if len(df) < 60:
        return None

    df = add_emas(df)
    c = df['close'].iloc[-1]
    p = df['close'].iloc[-2]  # vela anterior
    e8 = df['ema8'].iloc[-1]
    e21 = df['ema21'].iloc[-1]
    e55 = df['ema55'].iloc[-1]

    # TENDENCIA ALCISTA + CRUCE EMA8
    if e8 > e21 > e55 and p <= e8 and c > e8:
        prob = 1.0
        if ML_ACTIVE:
            features = [[c, e8, e21, e55, duration/60, ["EURUSD","GBPUSD","USDJPY","AUDUSD"].index(pair)]]
            prob = model.predict_proba(features)[0][1]
            if prob < ML_THRESHOLD:
                return None
        return {"direction": "BUY", "prob": prob}

    # TENDENCIA BAJISTA + CRUCE EMA8
    if e8 < e21 < e55 and p >= e8 and c < e8:
        prob = 1.0
        if ML_ACTIVE:
            features = [[c, e8, e21, e55, duration/60, ["EURUSD","GBPUSD","USDJPY","AUDUSD"].index(pair)]]
            prob = model.predict_proba(features)[0][0]  # probabilidad de clase 0 = SELL
            if prob < ML_THRESHOLD:
                return None
        return {"direction": "SELL", "prob": prob}

    return None

# ========================= MAIN LOOP =========================
async def main():
    print("BOT GANADOR INICIADO – MODO BESTIA")
    print(f"Pares: {PAIRS} | Risk: {RISK_PERCENT}% | ML: {'SÍ' if ML_ACTIVE else 'NO'}")
    
    # CRITICAL: Wait for API initialization
    print("⏳ Esperando inicialización de la API (3 segundos)...")
    await asyncio.sleep(3)

    while True:
        try:
            balance = await api.balance()
            
            # Check for expired session
            if balance == -1.0:
                print("❌ ERROR CRÍTICO: La sesión ha expirado (Balance -1.0).")
                print("   Actualiza el POCKETOPTION_SSID en tu archivo .env con una nueva sesión.")
                await asyncio.sleep(60)
                continue

            if not balance or balance < 10:
                print(f"⚠️ Balance bajo o no disponible: ${balance}")
                await asyncio.sleep(30)
                continue

            print(f"\n{'='*60}")
            print(f"💰 Balance: ${balance:.2f}")
            amount = max(MIN_AMOUNT, round(balance * RISK_PERCENT / 100, 2))
            print(f"💵 Monto por operación: ${amount:.2f}")
            traded = False

            for pair in PAIRS:
                for name, duration in TIMEFRAMES.items():
                    try:
                        print(f"🔍 Analizando {pair} {name}...", end=" ")
                        raw = await api.get_candles(pair, duration, duration * 100)
                        if not raw:
                            print("❌ Sin datos")
                            continue

                        df = pd.DataFrame(raw)[['time','open','close','high','low']]
                        df.columns = ['time','open','close','high','low']
                        df['time'] = pd.to_datetime(df['time'], unit='s')
                        df = df.set_index('time').astype(float)

                        signal = get_signal(df, pair, duration)
                        if signal and not traded:
                            traded = True
                            dir_text = "COMPRA" if signal["direction"] == "BUY" else "VENTA"
                            prob_text = f" {signal['prob']:.1%}" if ML_ACTIVE else ""
                            print(f"\n🚀 SEÑAL ENCONTRADA!")
                            print(f"{datetime.now().strftime('%H:%M:%S')} → {pair} {name} {dir_text} ${amount}{prob_text}")

                            if signal["direction"] == "BUY":
                                await api.buy(pair, amount, duration)
                            else:
                                await api.sell(pair, amount, duration)
                        else:
                            print("⏸️ Sin señal")

                    except Exception as e:
                        print(f"⚠️ Error: {e}")
                        continue  # un par falla → sigue con el resto

            if not traded:
                print(f"\n⏳ Sin operaciones. Esperando {CHECK_EVERY_SECONDS}s...")
                await asyncio.sleep(CHECK_EVERY_SECONDS)

        except Exception as e:
            print("❌ Error crítico:", e)
            await asyncio.sleep(20)

if __name__ == "__main__":
    if not os.getenv("POCKETOPTION_SSID"):
        print("Falta POCKETOPTION_SSID en tu .env")
        exit()
    asyncio.run(main())