import pandas as pd
import asyncio
import time


# ==========================
#   SISTEMA PRO DE VELAS
# ==========================

async def get_candles_pro(api, pair: str, tf_seconds: int, limit: int = 200, retries: int = 6):
    """
    Sistema profesional de obtención de velas para PocketOption.

    - Maneja respuestas vacías o corruptas
    - Reintenta automáticamente con backoff progresivo
    - Filtra velas inválidas
    - Normaliza columnas
    - Garantiza orden correcto ASC
    - Evita crasheos del bot
    """

    for intento in range(1, retries + 1):
        try:
            raw = await api.get_candles(pair, tf_seconds, limit)

            # validar que es lista con contenido
            if not raw or not isinstance(raw, list):
                print(f"⚠️ [{pair}] Velas vacías en {tf_seconds}s (intento {intento}/{retries})")
                await asyncio.sleep(0.25 * intento)
                continue

            # normalizar a dataframe
            df = pd.DataFrame(raw)

            # columnas mínimas necesarias
            required = {"time", "open", "close", "high", "low"}
            if not required.issubset(df.columns):
                print(f"⚠️ [{pair}] Faltan columnas en {tf_seconds}s (intento {intento}/{retries})")
                await asyncio.sleep(0.25 * intento)
                continue

            # eliminar velas corruptas
            df = df.dropna()
            df = df[df["open"] != 0]
            df = df[df["close"] != 0]

            if len(df) < 5:
                print(f"⚠️ [{pair}] Muy pocas velas válidas en {tf_seconds}s (intento {intento}/{retries})")
                await asyncio.sleep(0.25 * intento)
                continue

            # ordenar por timestamp
            df = df.sort_values("time").reset_index(drop=True)

            # convertir timestamp a datetime
            df["timestamp"] = pd.to_datetime(df["time"], unit="s")

            return df

        except Exception as e:
            print(f"❌ Error grave obteniendo velas [{pair}] {tf_seconds}s → {str(e)}")
            await asyncio.sleep(0.5 * intento)

    print(f"⛔ [{pair}] Fallo permanente: sin velas válidas en {tf_seconds}s tras {retries} intentos")
    return None
