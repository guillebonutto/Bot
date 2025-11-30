# bot_universal_FUNCIONA_YA.py
import os, asyncio, pandas as pd, time, requests
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

try:
    from BinaryOptionsToolsV2.pocketoption import PocketOptionAsync
except Exception as e:
    print("ERROR:", e)
    exit()

# ========== FORZAMOS PARES OTC (porque es lo que tenés ahora) ==========
PAIRS = ["EURUSD_otc", "GBPUSD_otc", "USDJPY_otc", "AUDUSD_otc"]
api = PocketOptionAsync(ssid=os.getenv("POCKETOPTION_SSID"))

# ========== TELEGRAM OPCIONAL ==========
def tg(msg):
    token = os.getenv("TELEGRAM_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat:
        try: requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id":chat, "text":msg}, timeout=5)
        except: pass

# ========== SEÑALES ==========
def get_signal(df):
    if len(df) < 60: return None
    df = df.copy()
    df['e8']  = df['close'].ewm(span=8,  adjust=False).mean()
    df['e21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['e55'] = df['close'].ewm(span=55, adjust=False).mean()
    
    c = df['close'].iloc[-1]
    p = df['close'].iloc[-2]
    e8, e21, e55 = df['e8'].iloc[-1], df['e21'].iloc[-1], df['e55'].iloc[-1]
    
    # EMA 8/21/55
    if e8 > e21 > e55 and p <= e8 and c > e8:
        return "BUY", "EMA"
    if e8 < e21 < e55 and p >= e8 and c < e8:
        return "SELL", "EMA"
    
    # ROUND LEVELS (solo si no hubo EMA)
    price = c
    level = round(price * 2) / 2
    if abs(price - level) <= 0.0008:  # 8 pips máximo
        if price < level and e8 > e21 and c > df['open'].iloc[-1]:
            return "BUY", "ROUND"
        if price > level and e8 < e21 and c < df['open'].iloc[-1]:
            return "SELL", "ROUND"
    
    return None, None

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

                direction, source = get_signal(df)
                if direction and not traded:
                    traded = True
                    txt = f"{datetime.now().strftime('%H:%M:%S')} → {pair} {direction} ${amount} [{source}]"
                    print(txt)
                    tg(txt)

                    if direction == "BUY":
                        await api.buy(pair, amount, 300)
                    else:
                        await api.sell(pair, amount, 300)
                    
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