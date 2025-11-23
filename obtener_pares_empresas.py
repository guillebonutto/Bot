import asyncio
from BinaryOptionsToolsV2.pocketoption import PocketOptionAsync


async def bruteforce_assets():
    ssid = input("SSID: ").strip()
    api = PocketOptionAsync(ssid=ssid)

    # Lista exhaustiva de posibles nombres para acciones
    stock_variations = []

    # Empresas comunes
    companies = {
        'Apple': ['AAPL', 'Apple'],
        'Microsoft': ['MSFT', 'Microsoft'],
        'Google': ['GOOGL', 'GOOG', 'Google', 'Alphabet'],
        'Amazon': ['AMZN', 'Amazon'],
        'Tesla': ['TSLA', 'Tesla'],
        'Meta': ['META', 'Meta', 'Facebook', 'FB'],
        'Intel': ['INTC', 'Intel'],
        'NVIDIA': ['NVDA', 'NVIDIA', 'Nvidia'],
        'AMD': ['AMD'],
        'Netflix': ['NFLX', 'Netflix'],
    }

    # Generar todas las variaciones posibles
    for company, tickers in companies.items():
        for ticker in tickers:
            # Sin sufijo
            stock_variations.append(ticker)
            # Con _otc
            stock_variations.append(f"{ticker}_otc")
            # Con #
            stock_variations.append(f"#{ticker}")
            stock_variations.append(f"#{ticker}_otc")
            # Mayúsculas/minúsculas
            stock_variations.append(ticker.upper())
            stock_variations.append(f"{ticker.upper()}_otc")

    print(f"\n🔍 Probando {len(stock_variations)} variaciones...\n")

    working_assets = []

    for i, asset in enumerate(stock_variations, 1):
        try:
            candles = await asyncio.wait_for(
                api.get_candles(asset, 300, 1500),
                timeout=3
            )
            if candles and len(candles) > 0:
                print(f"✅ [{i}/{len(stock_variations)}] {asset} - FUNCIONA! ({len(candles)} velas)")
                working_assets.append(asset)
        except asyncio.TimeoutError:
            print(f"⏱️ [{i}/{len(stock_variations)}] {asset} - Timeout")
        except Exception as e:
            error_msg = str(e)[:40]
            if "Invalid asset" not in error_msg:
                print(f"⚠️ [{i}/{len(stock_variations)}] {asset} - {error_msg}")

        # Pequeño delay para no saturar
        if i % 10 == 0:
            await asyncio.sleep(1)

    print(f"\n{'=' * 50}")
    print(f"✅ ACTIVOS QUE FUNCIONAN ({len(working_assets)}):")
    print(f"{'=' * 50}")
    for asset in working_assets:
        print(f"  '{asset}',")

    print(f"\n💡 Copia estos nombres a tu lista PAIRS")


asyncio.run(bruteforce_assets())