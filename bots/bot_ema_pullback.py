# bot_ganador.py → EL ÚNICO QUE NECESITÁS AHORA
import os
import asyncio
import pandas as pd
import time
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
PAIRS = ['EURUSD_otc', 'GBPUSD_otc', 'AUDUSD_otc', 'USDCAD_otc', 'AUDCAD_otc', 'USDMXN_otc', 'USDCOP_otc']
TIMEFRAMES = {"M1": 60, "M5": 300}
RISK_PERCENT = 1.0
MIN_AMOUNT = 1.0
CHECK_EVERY_SECONDS = 7
COOLDOWN_SECONDS = 60

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(msg: str):
    """Enviar mensaje por Telegram"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        import requests
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
            timeout=10
        )
    except Exception as e:
        print(f"⚠️ Error Telegram: {e}")

# ========================= UTILS =========================
def clean_ssid(ssid: str) -> str:
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

ssid = clean_ssid(os.getenv("POCKETOPTION_SSID"))
api = PocketOptionAsync(ssid=ssid)

try:
    import joblib
    model = joblib.load("ml_model.pkl")
    ML_ACTIVE = True
    ML_THRESHOLD = 0.62
    print("Modelo ML cargado")
except:
    ML_ACTIVE = False
    print("Sin modelo ML")

# ========================= INDICADORES =========================
def add_emas(df: pd.DataFrame) -> pd.DataFrame:
    df['ema8']  = df['close'].ewm(span=8, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema55'] = df['close'].ewm(span=55, adjust=False).mean()
    return df

def get_signal(df: pd.DataFrame, pair: str, duration: int):
    if len(df) < 60:
        return None
    df = add_emas(df)
    c = df['close'].iloc[-1]
    p = df['close'].iloc[-2]
    e8 = df['ema8'].iloc[-1]
    e21 = df['ema21'].iloc[-1]
    e55 = df['ema55'].iloc[-1]

    if e8 > e21 > e55 and p <= e8 and c > e8:
        prob = 1.0
        if ML_ACTIVE:
            try:
                pair_idx = PAIRS.index(pair)
            except ValueError:
                pair_idx = 0
            features = [[c, e8, e21, e55, duration/60, pair_idx]]
            prob = model.predict_proba(features)[0][1]
            if prob < ML_THRESHOLD:
                return None
        return {"direction": "BUY", "prob": prob}

    if e8 < e21 < e55 and p >= e8 and c < e8:
        prob = 1.0
        if ML_ACTIVE:
            try:
                pair_idx = PAIRS.index(pair)
            except ValueError:
                pair_idx = 0
            features = [[c, e8, e21, e55, duration/60, pair_idx]]
            prob = model.predict_proba(features)[0][0]
            if prob < ML_THRESHOLD:
                return None
        return {"direction": "SELL", "prob": prob}

    return None

# ========================= MAIN LOOP =========================
async def main():
    print("BOT EMA PULLBACK INICIADO")
    print(f"Pares: {len(PAIRS)} | Risk: {RISK_PERCENT}% | Cooldown: {COOLDOWN_SECONDS}s")
    
    await asyncio.sleep(3)
    recent_trades = {}

    while True:
        try:
            balance = await api.balance()
            
            if balance == -1.0:
                print("❌ Sesión expirada")
                await asyncio.sleep(60)
                continue

            if not balance or balance < 10:
                print(f"⚠️ Balance bajo: ${balance}")
                await asyncio.sleep(30)
                continue

            print(f"\n{'='*60}")
            print(f"💰 Balance: ${balance:.2f}")
            amount = max(MIN_AMOUNT, round(balance * RISK_PERCENT / 100, 2))
            print(f"💵 Monto: ${amount:.2f}")
            traded = False

            current_time = time.time()
            recent_trades = {k: v for k, v in recent_trades.items() if current_time - v < COOLDOWN_SECONDS}

            for pair in PAIRS:
                if pair in recent_trades:
                    time_left = COOLDOWN_SECONDS - (current_time - recent_trades[pair])
                    print(f"⏸️ {pair} cooldown ({time_left:.0f}s)")
                    continue

                for name, duration in TIMEFRAMES.items():
                    try:
                        print(f"🔍 {pair} {name}...", end=" ")
                        raw = await api.get_candles(pair, duration, duration * 100)
                        if not raw:
                            print("❌")
                            continue

                        df = pd.DataFrame(raw)
                        if 'timestamp' in df.columns and 'time' not in df.columns:
                            df['time'] = df['timestamp']
                        
                        required_cols = ['time', 'open', 'close', 'high', 'low']
                        if not all(col in df.columns for col in required_cols):
                            print("❌")
                            continue
                        
                        df = df[required_cols]
                        df['time'] = pd.to_datetime(df['time'], unit='s')
                        df = df.set_index('time').astype(float)

                        signal = get_signal(df, pair, duration)
                        if signal and not traded:
                            traded = True
                            dir_text = "COMPRA" if signal["direction"] == "BUY" else "VENTA"
                            prob_text = f" {signal['prob']:.1%}" if ML_ACTIVE else ""
                            
                            print(f"\n🚀 SEÑAL!")
                            print(f"{datetime.now().strftime('%H:%M:%S')} → {pair} {name} {dir_text} ${amount}{prob_text}")

                            # Guardar balance antes
                            balance_before = balance

                            if signal["direction"] == "BUY":
                                await api.buy(pair, amount, duration)
                            else:
                                await api.sell(pair, amount, duration)
                            
                            # Telegram: Operación ejecutada
                            send_telegram(
                                f"🚀 SEÑAL EJECUTADA\n"
                                f"Par: {pair}\n"
                                f"Dirección: {dir_text}\n"
                                f"TF: {name}\n"
                                f"Monto: ${amount}\n"
                                f"Balance: ${balance:.2f}{prob_text}"
                            )
                            
                            recent_trades[pair] = current_time
                            print(f"⏳ Esperando {duration}s...")
                            await asyncio.sleep(duration + 5)
                            
                            # Verificar resultado
                            try:
                                balance_after = await api.balance()
                                if balance_after > balance_before:
                                    profit = balance_after - balance_before
                                    print(f"✅ GANÓ: +${profit:.2f}")
                                    send_telegram(
                                        f"✅ GANÓ!\n"
                                        f"Par: {pair}\n"
                                        f"Ganancia: +${profit:.2f}\n"
                                        f"Balance: ${balance_after:.2f}"
                                    )
                                else:
                                    loss = balance_before - balance_after
                                    print(f"❌ PERDIÓ: -${loss:.2f}")
                                    send_telegram(
                                        f"❌ PERDIÓ\n"
                                        f"Par: {pair}\n"
                                        f"Pérdida: -${loss:.2f}\n"
                                        f"Balance: ${balance_after:.2f}"
                                    )
                            except Exception as e:
                                print(f"⚠️ No se pudo verificar resultado: {e}")
                            
                            break
                        else:
                            print("⏸️")

                    except Exception as e:
                        print(f"⚠️ {e}")
                        continue
                
                if traded:
                    break

            if not traded:
                print(f"\n⏳ Esperando {CHECK_EVERY_SECONDS}s...")
                await asyncio.sleep(CHECK_EVERY_SECONDS)

        except Exception as e:
            print(f"❌ Error: {e}")
            await asyncio.sleep(20)

if __name__ == "__main__":
    if not os.getenv("POCKETOPTION_SSID"):
        print("Falta POCKETOPTION_SSID en .env")
        exit()
    asyncio.run(main())